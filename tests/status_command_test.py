#!/usr/bin/env python3
"""
Unit tests for P7-11: status and notify commands.
"""

import unittest
import sys
import os

# Add resources/core to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "core")))

from commands import status, notify

class TestStatusAndNotifyCommands(unittest.TestCase):
    def setUp(self):
        self.user = {"name": "root", "primaryGroup": "root"}

    def test_status_summary_and_subcommands(self):
        # status with no args defaults to summary
        res = status.run([], {}, self.user)
        self.assertEqual(res.get("effect"), "status_action")
        self.assertEqual(res.get("action"), "summary")

        # status bar on / off
        res_bar_on = status.run(["bar", "on"], {}, self.user)
        self.assertEqual(res_bar_on.get("effect"), "status_action")
        self.assertEqual(res_bar_on.get("action"), "toggle_bar")
        self.assertTrue(res_bar_on.get("value"))

        res_bar_off = status.run(["bar", "off"], {}, self.user)
        self.assertFalse(res_bar_off.get("value"))

        # status mute on / off
        res_mute_on = status.run(["mute", "on"], {}, self.user)
        self.assertEqual(res_mute_on.get("effect"), "status_action")
        self.assertEqual(res_mute_on.get("action"), "set_mute")
        self.assertTrue(res_mute_on.get("value"))

        res_mute_off = status.run(["mute", "off"], {}, self.user)
        self.assertFalse(res_mute_off.get("value"))

        # status notifications
        res_notif = status.run(["notifications"], {}, self.user)
        self.assertEqual(res_notif.get("effect"), "status_action")
        self.assertEqual(res_notif.get("action"), "list_notifications")

        # status clear
        res_clear = status.run(["clear"], {}, self.user)
        self.assertEqual(res_clear.get("effect"), "status_action")
        self.assertEqual(res_clear.get("action"), "clear_notifications")

    def test_status_errors(self):
        res_bad_bar = status.run(["bar", "maybe"], {}, self.user)
        self.assertFalse(res_bad_bar.get("success"))
        self.assertIn("invalid argument", res_bad_bar.get("error", {}).get("message", ""))

        res_bad_mute = status.run(["mute", "perhaps"], {}, self.user)
        self.assertFalse(res_bad_mute.get("success"))

        res_unknown = status.run(["fly"], {}, self.user)
        self.assertFalse(res_unknown.get("success"))
        self.assertIn("unknown option", res_unknown.get("error", {}).get("message", ""))

    def test_notify_command(self):
        # standard notify
        res = notify.run(["Hello", "world"], {}, self.user)
        self.assertEqual(res.get("effect"), "notify")
        self.assertEqual(res.get("message"), "Hello world")
        self.assertEqual(res.get("level"), "info")
        self.assertFalse(res.get("silent"))

        # notify with level flags
        res_ok = notify.run(["Done"], {"success": True}, self.user)
        self.assertEqual(res_ok.get("level"), "success")

        res_warn = notify.run(["Caution"], {"warn": True}, self.user)
        self.assertEqual(res_warn.get("level"), "warn")

        res_err = notify.run(["Failure"], {"error": True, "silent": True}, self.user)
        self.assertEqual(res_err.get("level"), "error")
        self.assertTrue(res_err.get("silent"))

        # notify list and clear
        res_list = notify.run(["list"], {}, self.user)
        self.assertEqual(res_list.get("effect"), "status_action")
        self.assertEqual(res_list.get("action"), "list_notifications")

        res_clear = notify.run(["clear"], {}, self.user)
        self.assertEqual(res_clear.get("effect"), "status_action")
        self.assertEqual(res_clear.get("action"), "clear_notifications")

    def test_notify_errors(self):
        res = notify.run([], {}, self.user)
        self.assertFalse(res.get("success"))
        self.assertIn("missing notification message", res.get("error", {}).get("message", ""))

if __name__ == "__main__":
    unittest.main()
