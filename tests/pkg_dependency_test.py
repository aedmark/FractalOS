import sys
import os
import json
import asyncio
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../resources/core"))

from filesystem import fs_manager
from commands import pkg

class TestPkgDependencies(unittest.TestCase):
    def setUp(self):
        fs_manager.reset()
        fs_manager.save_func = lambda: None
        self.root_context = {
            "name": "root",
            "current_user": "root",
            "current_group": "root",
            "current_path": "/home/root"
        }
        fs_manager.current_path = "/home/root"

    def test_recursive_dependency_installation(self):
        # Create corelib (leaf)
        corelib_code = '''
def metadata():
    return {"name": "corelib", "version": "1.0.0", "description": "Core library", "dependencies": []}
def run(args, flags, user_context, **kwargs):
    return "corelib"
def man(*args, **kwargs): return "corelib man"
'''
        # Create helper (depends on corelib)
        helper_code = '''
def metadata():
    return {"name": "helper", "version": "1.1.0", "description": "Helper tool", "dependencies": ["corelib"]}
def run(args, flags, user_context, **kwargs):
    return "helper"
def man(*args, **kwargs): return "helper man"
'''
        # Create app (depends on helper)
        app_code = '''
def metadata():
    return {"name": "app", "version": "2.0.0", "description": "Main application", "dependencies": ["helper"]}
def run(args, flags, user_context, **kwargs):
    return "app"
def man(*args, **kwargs): return "app man"
'''
        fs_manager.write_file("/home/root/corelib.py", corelib_code, self.root_context)
        fs_manager.write_file("/home/root/helper.py", helper_code, self.root_context)
        fs_manager.write_file("/home/root/app.py", app_code, self.root_context)

        # Publish all 3 to local community repo
        asyncio.run(pkg.run(["publish", "/home/root/corelib.py"], {}, self.root_context))
        asyncio.run(pkg.run(["publish", "/home/root/helper.py"], {}, self.root_context))
        asyncio.run(pkg.run(["publish", "/home/root/app.py"], {}, self.root_context))

        # Reset packages manifest to clean state
        manifest_node = fs_manager.get_node("/etc/pkg_manifest.json")
        if manifest_node:
            manifest_node["content"] = "{}"

        # Install app - should recursively install corelib and helper!
        inst_res = asyncio.run(pkg.run(["install", "app"], {}, self.root_context))
        self.assertTrue(inst_res["success"], f"Install failed: {inst_res}")
        self.assertIn("Installed dependencies", inst_res["output"])
        self.assertIn("helper", inst_res["output"])
        self.assertIn("corelib", inst_res["output"])

        # Verify all 3 exist in /etc/packages/commands/
        self.assertIsNotNone(fs_manager.get_node("/etc/packages/commands/corelib.py"))
        self.assertIsNotNone(fs_manager.get_node("/etc/packages/commands/helper.py"))
        self.assertIsNotNone(fs_manager.get_node("/etc/packages/commands/app.py"))

        # Verify all 3 registered in /etc/pkg_manifest.json
        manifest = json.loads(fs_manager.get_node("/etc/pkg_manifest.json")["content"])
        self.assertIn("corelib", manifest)
        self.assertIn("helper", manifest)
        self.assertIn("app", manifest)

    def test_circular_dependency_detection(self):
        cycle_a = '''
def metadata(): return {"name": "cycle_a", "version": "1.0.0", "dependencies": ["cycle_b"]}
def run(*args, **kwargs): return "a"
def man(*args, **kwargs): return "a"
'''
        cycle_b = '''
def metadata(): return {"name": "cycle_b", "version": "1.0.0", "dependencies": ["cycle_a"]}
def run(*args, **kwargs): return "b"
def man(*args, **kwargs): return "b"
'''
        fs_manager.write_file("/home/root/cycle_a.py", cycle_a, self.root_context)
        fs_manager.write_file("/home/root/cycle_b.py", cycle_b, self.root_context)
        asyncio.run(pkg.run(["publish", "/home/root/cycle_a.py"], {}, self.root_context))
        asyncio.run(pkg.run(["publish", "/home/root/cycle_b.py"], {}, self.root_context))

        inst_res = asyncio.run(pkg.run(["install", "cycle_a"], {}, self.root_context))
        self.assertFalse(inst_res["success"])
        self.assertIn("Circular dependency detected", inst_res["error"]["suggestion"])
        self.assertIn("cycle_a -> cycle_b -> cycle_a", inst_res["error"]["suggestion"])

    def test_no_deps_flag(self):
        pkg_code = '''
def metadata(): return {"name": "solo_app", "version": "1.0.0", "dependencies": ["nonexistent_dep"]}
def run(*args, **kwargs): return "solo"
def man(*args, **kwargs): return "solo"
'''
        fs_manager.write_file("/home/root/solo.py", pkg_code, self.root_context)
        asyncio.run(pkg.run(["publish", "/home/root/solo.py"], {}, self.root_context))

        # With --no-deps, it should skip trying to resolve nonexistent_dep
        res = asyncio.run(pkg.run(["install", "solo_app"], {"no_deps": True}, self.root_context))
        self.assertTrue(res["success"], f"Failed with --no-deps: {res}")
        self.assertIsNotNone(fs_manager.get_node("/etc/packages/commands/solo_app.py"))

    def test_dependency_tree_inspection(self):
        # Inspect dependency tree of installed app from first test scenario
        self.test_recursive_dependency_installation()

        # Text output
        deps_res = asyncio.run(pkg.run(["deps", "app"], {}, self.root_context))
        self.assertIsInstance(deps_res, str)
        self.assertIn("DEPENDENCY TREE: app", deps_res)
        self.assertIn("helper", deps_res)
        self.assertIn("corelib", deps_res)

        # JSON output
        deps_json_str = asyncio.run(pkg.run(["deps", "app"], {"json": True}, self.root_context))
        deps_json = json.loads(deps_json_str)
        self.assertEqual(deps_json["package"], "app")
        self.assertIn("tree", deps_json)
        self.assertEqual(deps_json["tree"]["name"], "app")
        self.assertEqual(deps_json["tree"]["dependencies"][0]["name"], "helper")
        self.assertEqual(deps_json["tree"]["dependencies"][0]["dependencies"][0]["name"], "corelib")

    def test_uninstall_guardrails(self):
        self.test_recursive_dependency_installation()

        # Attempt to remove helper which app depends on
        rm_res = asyncio.run(pkg.run(["remove", "helper"], {}, self.root_context))
        self.assertFalse(rm_res["success"])
        self.assertIn("cannot remove 'helper' because it is required by: app", rm_res["error"]["message"])
        self.assertIn("--force", rm_res["error"]["suggestion"])

        # Force removal should succeed
        force_rm_res = asyncio.run(pkg.run(["remove", "helper"], {"force": True}, self.root_context))
        self.assertTrue(force_rm_res["success"])
        self.assertIn("Removed package 'helper'", force_rm_res["output"])
        self.assertIn("Orphaned dependent packages: app", force_rm_res["output"])
        self.assertIsNone(fs_manager.get_node("/etc/packages/commands/helper.py"))

    def test_dynamic_wheels_collection(self):
        wheel_pkg = '''
def metadata():
    return {"name": "mathtool", "version": "1.0.0", "wheels": ["numpy", "scipy"], "dependencies": []}
def run(*args, **kwargs): return "math"
def man(*args, **kwargs): return "math"
'''
        fs_manager.write_file("/home/root/mathtool.py", wheel_pkg, self.root_context)
        asyncio.run(pkg.run(["publish", "/home/root/mathtool.py"], {}, self.root_context))

        inst_res = asyncio.run(pkg.run(["install", "mathtool"], {}, self.root_context))
        self.assertTrue(inst_res["success"])
        self.assertIn("numpy", inst_res["wheels"])
        self.assertIn("scipy", inst_res["wheels"])
        self.assertEqual(inst_res["effect"], "update_commands_manifest")

if __name__ == "__main__":
    unittest.main()
