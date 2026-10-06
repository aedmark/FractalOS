#!/usr/bin/env python3
"""
Unit tests for peers.py and netstat.py (mesh presence & discovery).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources/core")))

from commands import peers, netstat

class TestPeersCommand(unittest.TestCase):
    def setUp(self):
        self.ctx = {"username": "alice"}
        self.config = {"NETWORKING_ENABLED": True}

    def test_peers_default_display(self):
        res = peers.run([], {}, self.ctx)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "peers_display")
        self.assertFalse(res.get("doPing"))
        self.assertFalse(res.get("asJson"))

    def test_peers_with_ping_flag(self):
        res = peers.run([], {"--ping": True}, self.ctx)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "peers_display")
        self.assertTrue(res.get("doPing"))

    def test_peers_with_json_flag(self):
        res = peers.run([], {"--json": True}, self.ctx)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "peers_display")
        self.assertTrue(res.get("asJson"))

    def test_peers_info_subcommand(self):
        res = peers.run(["info", "oos-node-42"], {}, self.ctx)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "peers_info")
        self.assertEqual(res.get("targetId"), "oos-node-42")

    def test_peers_info_missing_arg(self):
        res = peers.run(["info"], {}, self.ctx)
        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("success", True))
        self.assertIn("missing node ID", res.get("error", {}).get("message", ""))

    def test_peers_gui_launch(self):
        res = peers.run([], {"--gui": True}, self.ctx)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "launch_app")
        self.assertEqual(res.get("app_name"), "Peers")

    def test_netstat_mesh_flag(self):
        res = netstat.run([], {"--mesh": True}, self.ctx, config=self.config)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "peers_display")

    def test_netstat_gui_flag(self):
        res = netstat.run([], {"--gui": True}, self.ctx, config=self.config)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "launch_app")
        self.assertEqual(res.get("app_name"), "Peers")

    def test_netstat_disabled_networking(self):
        res = netstat.run([], {"--mesh": True}, self.ctx, config={"NETWORKING_ENABLED": False})
        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("success", True))
        self.assertIn("networking is disabled", res.get("error", {}).get("message", ""))

    def test_man_and_help(self):
        self.assertIn("Mesh node presence", peers.man([], {}, self.ctx))
        self.assertIn("Usage: peers", peers.help([], {}, self.ctx))
        self.assertIn("netstat", netstat.man([], {}, self.ctx))

if __name__ == "__main__":
    unittest.main()
