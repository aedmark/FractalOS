"""
Tests for FractalOS Package Security & Sandboxing (P7-16)
Verification hashes, integrity checks, permission scopes, and static auditing.
"""
import sys
import os
import unittest
import asyncio
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT, "resources", "core")
COMMANDS_DIR = os.path.join(CORE_DIR, "commands")
if COMMANDS_DIR not in sys.path:
    sys.path.insert(0, COMMANDS_DIR)
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from filesystem import fs_manager
from executor import command_executor, SecurityError
import pkg

class TestPackageSecurity(unittest.TestCase):
    def setUp(self):
        fs_manager.reset()
        fs_manager.save_function = lambda x: None
        self.root_context = {
            "name": "root",
            "current_user": "root",
            "current_group": "root",
            "current_path": "/home/root"
        }
        self.user_context = {
            "name": "gordon",
            "current_user": "gordon",
            "current_group": "users",
            "current_path": "/home/gordon"
        }
        fs_manager.create_directory("/home/gordon", self.root_context, parents=True)
        fs_manager.current_path = "/home/root"

    def test_01_clean_integrity_verification(self):
        async def _run():
            # Install fortune
            inst_res = await pkg.run(["install", "fortune"], {}, self.root_context)
            self.assertTrue(inst_res["success"])

            # Verify fortune
            verify_res = await pkg.run(["verify", "fortune"], {}, self.user_context)
            self.assertIn("Verified", verify_res)
            self.assertIn("fortune", verify_res)

            # JSON verify
            json_res = await pkg.run(["verify"], {"json": True}, self.user_context)
            data = json.loads(json_res)
            self.assertTrue(data["verified"])
            self.assertEqual(len(data["packages"]), 1)
            self.assertEqual(data["packages"][0]["status"], "verified")
        asyncio.run(_run())

    def test_02_tamper_detection_in_verify_and_executor(self):
        async def _run():
            # Install cal
            await pkg.run(["install", "cal"], {}, self.root_context)

            # Verify it runs initially via executor
            exec_res = await command_executor.execute("cal", json.dumps(self.user_context))
            exec_data = json.loads(exec_res)
            self.assertTrue(exec_data.get("success"), f"Initial run failed: {exec_data}")

            # Maliciously alter the file on disk post-install
            cal_path = "/etc/packages/commands/cal.py"
            fs_manager.write_file(cal_path, "def run(*a, **k): return 'TAMPERED'", self.root_context)

            # pkg verify should detect tampering!
            verify_res = await pkg.run(["verify", "cal"], {}, self.user_context)
            self.assertFalse(verify_res.get("success", True) if isinstance(verify_res, dict) else False)
            self.assertIn("TAMPERED", verify_res["output"] if isinstance(verify_res, dict) else verify_res)

            # JSON verify should flag tampered status
            json_res = await pkg.run(["verify"], {"json": True}, self.user_context)
            data = json.loads(json_res)
            self.assertFalse(data["verified"])
            self.assertEqual(data["packages"][0]["status"], "tampered")

            # Executor must refuse execution with Security Error!
            exec_tampered = await command_executor.execute("cal", json.dumps(self.user_context))
            tampered_data = json.loads(exec_tampered)
            self.assertFalse(tampered_data["success"])
            self.assertIn("Security Error", tampered_data["error"]["message"])
            self.assertIn("integrity check", tampered_data["error"]["message"])
        asyncio.run(_run())

    def test_03_reinstall_clears_integrity_failure(self):
        async def _run():
            # Install cowsay
            await pkg.run(["install", "cowsay"], {}, self.root_context)

            # Tamper with cowsay
            fs_manager.write_file("/etc/packages/commands/cowsay.py", "# corrupt", self.root_context)

            # Reinstall with --force
            reinst_res = await pkg.run(["install", "cowsay"], {"force": True}, self.root_context)
            self.assertTrue(reinst_res["success"])

            # Verify passes now
            verify_res = await pkg.run(["verify", "cowsay"], {}, self.user_context)
            self.assertIn("Verified", verify_res)

            # Executor runs cleanly
            exec_res = await command_executor.execute("cowsay Hello", json.dumps(self.user_context))
            exec_data = json.loads(exec_res)
            self.assertTrue(exec_data["success"])
        asyncio.run(_run())

    def test_04_bundle_checksum_mismatch_rejection(self):
        async def _run():
            # Create dummy package bundle with forged checksum
            bad_bundle = {
                "format": "fractalos-package-v1",
                "name": "spoofed",
                "version": "1.0.0",
                "checksum": "0000000000000000000000000000000000000000000000000000000000000000",
                "source": "def run(*a, **k): return 'spoofed'\ndef man(*a, **k): return 'man'\n"
            }
            bundle_path = "/home/gordon/spoofed.fpkg"
            fs_manager.write_file(bundle_path, json.dumps(bad_bundle), self.root_context)

            # Attempt install without skip-verify should fail with Security Error
            res = await pkg.run(["install", bundle_path], {}, self.root_context)
            self.assertFalse(res["success"])
            self.assertIn("Security Error: Checksum mismatch", res["error"]["suggestion"])

            # Install with --skip-verify succeeds
            res_skip = await pkg.run(["install", bundle_path], {"skip_verify": True}, self.root_context)
            self.assertTrue(res_skip["success"])
            self.assertIn("Successfully installed", res_skip["output"])
        asyncio.run(_run())

    def test_05_permission_scope_elevation_guardrails(self):
        async def _run():
            # Create package requesting elevated "root" scope
            root_tool_code = '''
def metadata():
    return {
        "name": "roottool",
        "version": "1.0.0",
        "description": "Tool requiring root",
        "permissions": ["root", "fs:system"]
    }
def run(*a, **k): return "root tool executed"
def man(*a, **k): return "man"
'''
            tool_path = "/home/root/roottool.py"
            fs_manager.write_file(tool_path, root_tool_code, self.root_context)

            # Install without trust -> Rejected!
            reject_res = await pkg.run(["install", tool_path], {}, self.root_context)
            self.assertFalse(reject_res["success"])
            self.assertIn("elevated permission scopes", reject_res["error"]["suggestion"])

            # Install with --trust -> Allowed!
            trust_res = await pkg.run(["install", tool_path], {"trust": True}, self.root_context)
            self.assertTrue(trust_res["success"])
        asyncio.run(_run())

    def test_06_pkg_audit_static_security_analysis(self):
        async def _run():
            # 1. Audit safe package (banner)
            await pkg.run(["install", "banner"], {}, self.root_context)
            audit_banner = await pkg.run(["audit", "banner"], {}, self.user_context)
            self.assertIn("SAFE", audit_banner)
            self.assertIn("banner", audit_banner)

            # 2. Audit risky code with eval and subprocess
            bad_code = '''
def metadata():
    return {"name": "risky", "version": "1.0.0", "permissions": ["root"]}
def run(*a, **k):
    eval("2 + 2")
    return open("/etc/shadow").read()
def man(*a, **k): return "man"
'''
            risky_path = "/home/gordon/risky.py"
            fs_manager.write_file(risky_path, bad_code, self.root_context)

            audit_risky = await pkg.run(["audit", risky_path], {}, self.user_context)
            self.assertIn("HIGH RISK", audit_risky)
            self.assertIn("eval()", audit_risky)
            self.assertIn("/etc/", audit_risky)

            # JSON audit
            json_audit = await pkg.run(["audit", risky_path], {"json": True}, self.user_context)
            audit_data = json.loads(json_audit)
            self.assertEqual(len(audit_data), 1)
            self.assertEqual(audit_data[0]["risk_level"], "HIGH RISK")
            self.assertTrue(any("eval" in f["message"] for f in audit_data[0]["findings"]))
        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
