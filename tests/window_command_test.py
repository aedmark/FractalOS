#!/usr/bin/env python3
"""
Unit tests for P7-10: TUI Window Management commands (wm, window, and app flags).
"""

import unittest
import sys
import os

# Add resources/core to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "core")))

from commands import wm, window, top, edit, paint, peers

class TestWindowManagement(unittest.TestCase):
    def setUp(self):
        self.user = {"name": "root", "primaryGroup": "root"}

    def test_wm_list_and_defaults(self):
        # wm with no args defaults to list action
        res = wm.run([], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "list")

        # wm list
        res_list = wm.run(["list"], {}, self.user)
        self.assertEqual(res_list.get("effect"), "window_action")
        self.assertEqual(res_list.get("action"), "list")

    def test_wm_actions(self):
        # focus
        res = wm.run(["focus", "win-1"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "focus")
        self.assertEqual(res.get("window_id"), "win-1")

        # mode
        res = wm.run(["mode", "win-1", "docked-right"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "set_mode")
        self.assertEqual(res.get("mode"), "docked-right")

        # dock
        res = wm.run(["dock", "win-1", "left"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "dock")
        self.assertEqual(res.get("direction"), "left")

        # float
        res = wm.run(["float", "win-1"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "float")

        # minimize and restore
        res = wm.run(["min", "win-1"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "minimize")

        res = wm.run(["restore", "win-1"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "restore")

        # close
        res = wm.run(["close", "win-1"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "close")

        # tile
        res = wm.run(["tile"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "tile")

    def test_wm_validation_errors(self):
        # missing ID
        res = wm.run(["focus"], {}, self.user)
        self.assertFalse(res.get("success"))
        self.assertIn("missing window ID", res.get("error", {}).get("message", ""))

        # invalid mode
        res = wm.run(["mode", "win-1", "spiral"], {}, self.user)
        self.assertFalse(res.get("success"))
        self.assertIn("invalid layout mode", res.get("error", {}).get("message", ""))

        # unknown subcommand
        res = wm.run(["dance"], {}, self.user)
        self.assertFalse(res.get("success"))
        self.assertIn("unknown subcommand", res.get("error", {}).get("message", ""))

    def test_window_alias(self):
        res = window.run(["list"], {}, self.user)
        self.assertEqual(res.get("effect"), "window_action")
        self.assertEqual(res.get("action"), "list")

    def test_top_command_window_modes(self):
        # default top is docked-right
        res = top.run([], {}, self.user)
        self.assertEqual(res.get("effect"), "launch_app")
        self.assertEqual(res.get("app_name"), "Top")
        self.assertEqual(res.get("options", {}).get("windowMode"), "docked-right")

        # top --float
        res_float = top.run([], {"float": True}, self.user)
        self.assertEqual(res_float.get("options", {}).get("windowMode"), "floating")

        # top --full
        res_full = top.run([], {"full": True}, self.user)
        self.assertEqual(res_full.get("options", {}).get("windowMode"), "fullscreen")

    def test_paint_and_peers_window_modes(self):
        res_paint = paint.run([], {"dock": True}, self.user)
        self.assertEqual(res_paint.get("effect"), "launch_app")
        self.assertEqual(res_paint.get("options", {}).get("windowMode"), "docked-right")

        res_peers = peers.run([], {"--gui": True, "--dock": True}, self.user)
        self.assertEqual(res_peers.get("effect"), "launch_app")
        self.assertEqual(res_peers.get("options", {}).get("windowMode"), "docked-right")

if __name__ == "__main__":
    unittest.main()
