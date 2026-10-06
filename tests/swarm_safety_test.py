"""
tests/swarm_safety_test.py - Unit tests for P7-08 Swarm Safety & Voltage Policies.
"""

import sys
import os
import unittest
import asyncio
import json

CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "core"))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from filesystem import fs_manager
from audit import audit_manager
from swarm_manager import SwarmManager, DEFAULT_SWARM_POLICY
from bone_driver import BoneDriver
from commands import swarm, mesh_agent, samwise

class DummyAIManager:
    def __init__(self, plan_commands=None, plan_voltage=5.0, should_refuse=False):
        self.plan_commands = plan_commands or ["ls /"]
        self.plan_voltage = plan_voltage
        self.should_refuse = should_refuse

    def _get_ai_config(self):
        return {"provider": "ollama", "model": "llama3"}

    async def plan_autopilot(self, prompt, provider, model, options):
        if self.should_refuse:
            return {"success": True, "refusal": "I refuse to actuate this.", "plan_text": "Refusal", "commands": []}
        return {
            "success": True,
            "refusal": None,
            "commands": self.plan_commands,
            "plan_text": "\n".join(f"1. {c}" for c in self.plan_commands),
            "voltage": self.plan_voltage,
            "safety_status": BoneDriver.get_safety_report(self.plan_voltage),
            "needs_checkpoint": False,
            "warning": None,
            "rejections": 0,
            "attempts": 1
        }

    async def perform_autopilot(self, prompt, history, provider, model, options):
        planned = await self.plan_autopilot(prompt, provider, model, options)
        if not planned["success"]:
            return planned

        voltage = planned["voltage"]
        plan_text = planned["plan_text"]
        safety_status = planned["safety_status"]

        # Check budget limit
        max_v = options.get("max_voltage_budget")
        if max_v is not None and voltage is not None and voltage > max_v:
            return {
                "success": False,
                "voltage": voltage,
                "safety_status": safety_status,
                "error": f"🛑 SWARM VOLTAGE EXCEEDED: Plan voltage ({voltage} V) exceeds allowed threshold ({max_v} V).\nPlan:\n{plan_text}"
            }

        # Check GPIO prohibition
        swarm_ctx = options.get("swarm_context")
        if swarm_ctx and not swarm_ctx.get("allow_gpio", False):
            for cmd in planned["commands"]:
                parts = cmd.split()
                if parts and parts[0] == "gpio":
                    sub = parts[1].lower() if len(parts) > 1 else ""
                    if sub in {"mode", "write", "simulate", "monitor", "watch", "stop", "unmonitor"}:
                        return {
                            "success": False,
                            "voltage": voltage,
                            "safety_status": safety_status,
                            "error": f"🛑 SWARM POLICY VIOLATION: Remote physical hardware actuation (gpio {sub}) is prohibited on this node.\nPlan:\n{plan_text}"
                        }

        if options.get("dry_run", False):
            return {
                "success": True,
                "dry_run": True,
                "data": f"### 🍄 BONEAMANITA AUTOPILOT PLAN (DRY RUN)\n**Status:** {safety_status} (Voltage: {voltage} V)\n\n**Plan:**\n{plan_text}",
                "plan_text": plan_text,
                "commands": planned["commands"],
                "voltage": voltage,
                "safety_status": safety_status
            }

        return {
            "success": True,
            "data": f"Executed: {', '.join(planned['commands'])}",
            "voltage": voltage,
            "safety_status": safety_status
        }

    async def perform_agentic_search(self, prompt, history, provider, model, options):
        return {"success": True, "data": f"Synthesized answer for: {prompt}"}

    async def plan_agentic_search(self, prompt, history, provider, model, options):
        return {"success": True, "plan_text": "pwd", "commands": ["pwd"]}


class TestSwarmSafety(unittest.TestCase):
    def setUp(self):
        fs_manager.set_save_function(lambda x: None)
        fs_manager.reset()

    def test_swarm_policy_defaults_and_updates(self):
        sm = SwarmManager(fs_manager, None, audit_manager)
        policy = sm.get_policy()
        self.assertEqual(policy["max_remote_voltage"], 10.0)
        self.assertFalse(policy["allow_remote_gpio"])
        self.assertFalse(policy["allow_remote_force"])
        self.assertTrue(policy["allow_remote_autopilot"])

        # Update policy
        res = sm.set_policy_value("max_remote_voltage", "15.5")
        self.assertTrue(res["success"])
        self.assertEqual(res["updated"]["max_remote_voltage"], 15.5)

        # Check persistence in /etc/swarm.conf
        reloaded = sm.get_policy()
        self.assertEqual(reloaded["max_remote_voltage"], 15.5)

        # Update boolean
        res_gpio = sm.set_policy_value("allow_remote_gpio", "true")
        self.assertTrue(res_gpio["success"])
        self.assertTrue(sm.get_policy()["allow_remote_gpio"])

        # Reset policy
        sm.reset_policy()
        reset_pol = sm.get_policy()
        self.assertEqual(reset_pol["max_remote_voltage"], 10.0)
        self.assertFalse(reset_pol["allow_remote_gpio"])

    def test_remote_autopilot_disabled_rejection(self):
        sm = SwarmManager(fs_manager, None, audit_manager)
        sm.set_policy_value("allow_remote_autopilot", False)

        payload = {
            "sourceId": "peer-node-1234",
            "senderUser": "alice",
            "prompt": "Run full diagnostics",
            "isAutopilot": True
        }
        res = asyncio.run(sm.handle_remote_agent_request(payload))
        self.assertFalse(res["success"])
        self.assertIn("SWARM POLICY VIOLATION", res["error"])
        self.assertIn("disabled", res["error"])

    def test_voltage_budget_threshold_enforcement(self):
        ai = DummyAIManager(plan_commands=["mkdir /test", "touch /test/f"], plan_voltage=12.0)
        sm = SwarmManager(fs_manager, ai, audit_manager)
        sm.set_policy_value("max_remote_voltage", 10.0)

        # 12.0 V exceeds default 10.0 V limit
        payload = {
            "sourceId": "peer-node-1234",
            "senderUser": "alice",
            "prompt": "Create test files",
            "isAutopilot": True
        }
        res = asyncio.run(sm.handle_remote_agent_request(payload))
        self.assertFalse(res["success"])
        self.assertIn("SWARM VOLTAGE EXCEEDED", res["error"])
        self.assertEqual(res["voltage"], 12.0)

        # Caller specifies custom budget of 8.0 V when node allows 15.0 V
        sm.set_policy_value("max_remote_voltage", 15.0)
        payload["maxVoltage"] = 8.0
        res2 = asyncio.run(sm.handle_remote_agent_request(payload))
        self.assertFalse(res2["success"])
        self.assertIn("SWARM VOLTAGE EXCEEDED", res2["error"])

    def test_gpio_actuation_interlock(self):
        ai = DummyAIManager(plan_commands=["gpio mode 18 out", "gpio write 18 1"], plan_voltage=7.0)
        sm = SwarmManager(fs_manager, ai, audit_manager)
        # Default policy: allow_remote_gpio = False
        self.assertFalse(sm.get_policy()["allow_remote_gpio"])

        payload = {
            "sourceId": "peer-node-1234",
            "senderUser": "alice",
            "prompt": "Turn on pin 18",
            "isAutopilot": True
        }
        res = asyncio.run(sm.handle_remote_agent_request(payload))
        self.assertFalse(res["success"])
        self.assertIn("SWARM POLICY VIOLATION", res["error"])
        self.assertIn("gpio mode", res["error"])

        # Enable GPIO actuation in policy
        sm.set_policy_value("allow_remote_gpio", True)
        res_allowed = asyncio.run(sm.handle_remote_agent_request(payload))
        self.assertTrue(res_allowed["success"])
        self.assertIn("Executed: gpio mode 18 out", res_allowed["data"])

    def test_dry_run_mode_and_audit_logging(self):
        ai = DummyAIManager(plan_commands=["touch /tmp/hello"], plan_voltage=5.0)
        sm = SwarmManager(fs_manager, ai, audit_manager)

        payload = {
            "sourceId": "peer-node-9999",
            "senderUser": "bob",
            "prompt": "Check touching file",
            "isAutopilot": True,
            "isDryRun": True
        }
        res = asyncio.run(sm.handle_remote_agent_request(payload))
        self.assertTrue(res["success"])
        self.assertTrue(res.get("dry_run"))
        self.assertEqual(res.get("voltage"), 5.0)

        # Verify audit log contains entry with peer provenance and voltage
        entries = audit_manager.get_swarm_entries()
        self.assertTrue(len(entries) > 0)
        latest = entries[-1]
        self.assertIn("PEER: peer-node-9999 (bob)", latest)
        self.assertIn("VOLTAGE: 5.0V", latest)
        self.assertIn("SWARM_PLAN_DRY_RUN", latest)

    def test_swarm_and_mesh_agent_commands(self):
        # Test 'swarm status'
        res_status = asyncio.run(swarm.run([], {}, {"name": "Guest", "group": "Guest"}))
        self.assertTrue(res_status["success"])
        self.assertIn("Swarm Status", res_status["output"])
        self.assertIn("Max Remote Voltage Budget", res_status["output"])

        # Test 'swarm policy set'
        res_set = asyncio.run(swarm.run(["policy", "set", "max_remote_voltage", "18.0"], {}, {"name": "root", "group": "root"}))
        self.assertTrue(res_set["success"])
        self.assertIn("18.0", res_set["output"])

        # Test 'swarm log'
        res_log = asyncio.run(swarm.run(["log"], {}, {"name": "Guest", "group": "Guest"}))
        self.assertTrue(res_log["success"])

        # Test 'mesh-agent' with voltage budget and dry-run flags
        flags = {"--autopilot": True, "--max-voltage": "7.5", "--dry-run": True}
        res_mesh = asyncio.run(mesh_agent.run(["node-alpha", "Check", "sensors"], flags, {"name": "Guest", "group": "Guest"}))
        self.assertEqual(res_mesh["effect"], "mesh_agent_delegate")
        self.assertEqual(res_mesh["target"], "node-alpha")
        self.assertEqual(res_mesh["prompt"], "Check sensors")
        self.assertTrue(res_mesh["isAutopilot"])
        self.assertEqual(res_mesh["maxVoltage"], 7.5)
        self.assertTrue(res_mesh["isDryRun"])

        # Test 'samwise --node' with max-voltage
        flags_sam = {"node": "node-beta", "autopilot": True, "max-voltage": "6.0"}
        res_sam = asyncio.run(samwise.run(["Run", "test"], flags_sam, {"name": "Guest", "group": "Guest"}, ai_manager=DummyAIManager()))
        self.assertEqual(res_sam["effect"], "mesh_agent_delegate")
        self.assertEqual(res_sam["target"], "node-beta")
        self.assertEqual(res_sam["maxVoltage"], 6.0)

if __name__ == "__main__":
    unittest.main()
