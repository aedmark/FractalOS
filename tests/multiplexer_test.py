"""
tests/multiplexer_test.py - Unit tests for P7-09 Terminal Split Panes & Multiplexing commands.
"""

import sys
import os
import unittest
import asyncio

CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "core"))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from commands import split, split_v, split_h, panes, focus, close_pane

class TestMultiplexerCommands(unittest.TestCase):
    def setUp(self):
        self.user_context = {"name": "Guest", "group": "Guest"}

    def test_split_default_and_flags(self):
        # Default split is vertical
        res = asyncio.run(split.run([], {}, self.user_context))
        self.assertEqual(res["effect"], "multiplexer_action")
        self.assertEqual(res["action"], "split_vertical")
        self.assertEqual(res["orientation"], "vertical")
        self.assertIsNone(res["command"])

        # Horizontal split with -h
        res_h = asyncio.run(split.run([], {"-h": True}, self.user_context))
        self.assertEqual(res_h["action"], "split_horizontal")
        self.assertEqual(res_h["orientation"], "horizontal")

        # Split with command -c "top"
        res_cmd = asyncio.run(split.run(["v"], {"-c": "top"}, self.user_context))
        self.assertEqual(res_cmd["action"], "split_vertical")
        self.assertEqual(res_cmd["command"], "top")

    def test_split_subcommands(self):
        # split list
        res_list = asyncio.run(split.run(["list"], {}, self.user_context))
        self.assertEqual(res_list["effect"], "multiplexer_action")
        self.assertEqual(res_list["action"], "list")

        # split focus
        res_focus = asyncio.run(split.run(["focus", "pane-2"], {}, self.user_context))
        self.assertEqual(res_focus["effect"], "multiplexer_action")
        self.assertEqual(res_focus["action"], "focus")
        self.assertEqual(res_focus["paneId"], "pane-2")

        # split close
        res_close = asyncio.run(split.run(["close", "pane-2"], {}, self.user_context))
        self.assertEqual(res_close["effect"], "multiplexer_action")
        self.assertEqual(res_close["action"], "close")
        self.assertEqual(res_close["paneId"], "pane-2")

        # split zoom
        res_zoom = asyncio.run(split.run(["zoom"], {}, self.user_context))
        self.assertEqual(res_zoom["effect"], "multiplexer_action")
        self.assertEqual(res_zoom["action"], "zoom")

    def test_convenience_commands(self):
        # split-v
        res_v = asyncio.run(split_v.run([], {}, self.user_context))
        self.assertEqual(res_v["effect"], "multiplexer_action")
        self.assertEqual(res_v["action"], "split_vertical")

        # split-h with command
        res_h = asyncio.run(split_h.run([], {"-c": "peers"}, self.user_context))
        self.assertEqual(res_h["effect"], "multiplexer_action")
        self.assertEqual(res_h["action"], "split_horizontal")
        self.assertEqual(res_h["command"], "peers")

        # panes
        res_panes = asyncio.run(panes.run([], {}, self.user_context))
        self.assertEqual(res_panes["effect"], "multiplexer_action")
        self.assertEqual(res_panes["action"], "list")

        # focus
        res_f = asyncio.run(focus.run(["next"], {}, self.user_context))
        self.assertEqual(res_f["effect"], "multiplexer_action")
        self.assertEqual(res_f["action"], "focus")
        self.assertEqual(res_f["paneId"], "next")

        # close-pane
        res_cp = asyncio.run(close_pane.run([], {}, self.user_context))
        self.assertEqual(res_cp["effect"], "multiplexer_action")
        self.assertEqual(res_cp["action"], "close")

    def test_man_pages(self):
        self.assertIn("SYNOPSIS", split.man([], {}, self.user_context))
        self.assertIn("SYNOPSIS", split_v.man([], {}, self.user_context))
        self.assertIn("SYNOPSIS", split_h.man([], {}, self.user_context))
        self.assertIn("SYNOPSIS", panes.man([], {}, self.user_context))
        self.assertIn("SYNOPSIS", focus.man([], {}, self.user_context))
        self.assertIn("SYNOPSIS", close_pane.man([], {}, self.user_context))

if __name__ == "__main__":
    unittest.main()
