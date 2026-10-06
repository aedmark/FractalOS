#!/usr/bin/env python3
"""
Unit tests for commands/mesh_agent.py (Distributed Agent Task Delegation).
"""

import sys
import os
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources/core")))

from commands import mesh_agent

class TestMeshAgentCommand(unittest.TestCase):
    def setUp(self):
        self.ctx = {"username": "Guest"}

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_missing_arguments(self):
        res = self.run_async(mesh_agent.run([], {}, self.ctx))
        self.assertFalse(res["success"])
        self.assertIn("missing", res["error"]["message"])

        res_single = self.run_async(mesh_agent.run(["node-beta"], {}, self.ctx))
        self.assertFalse(res_single["success"])

    def test_query_delegation(self):
        res = self.run_async(mesh_agent.run(["node-beta", "What is uptime?"], {}, self.ctx))
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "mesh_agent_delegate")
        self.assertEqual(res.get("target"), "node-beta")
        self.assertEqual(res.get("prompt"), "What is uptime?")
        self.assertFalse(res.get("isAutopilot"))
        self.assertEqual(res.get("timeout"), 30)

    def test_autopilot_and_flags(self):
        flags = {"--autopilot": True, "--timeout": "45", "--json": True}
        res = self.run_async(mesh_agent.run(["node-gamma", "read pin 17 and alert"], flags, self.ctx))
        self.assertEqual(res.get("effect"), "mesh_agent_delegate")
        self.assertEqual(res.get("target"), "node-gamma")
        self.assertEqual(res.get("prompt"), "read pin 17 and alert")
        self.assertTrue(res.get("isAutopilot"))
        self.assertEqual(res.get("timeout"), 45)
        self.assertTrue(res.get("asJson"))

    def test_man_and_help(self):
        man_text = mesh_agent.man([], {}, self.ctx)
        self.assertIn("mesh-agent", man_text)
        self.assertIn("SYNOPSIS", man_text)

        help_text = mesh_agent.help([], {}, self.ctx)
        self.assertIn("Usage:", help_text)

if __name__ == "__main__":
    unittest.main()
