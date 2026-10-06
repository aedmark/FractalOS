import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../resources/core"))

from commands import clip, pbcopy, pbpaste

class TestClipboardCommands(unittest.TestCase):
    def setUp(self):
        self.context = {"current_user": "Guest", "current_group": "Guest", "current_path": "/home/Guest"}

    def test_clip_copy_args(self):
        res = clip.run(["copy", "hello", "world"], {}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "copy")
        self.assertEqual(res["text"], "hello world")

    def test_clip_copy_stdin(self):
        res = clip.run([], {}, self.context, stdin_data="piped data")
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "copy")
        self.assertEqual(res["text"], "piped data")

    def test_clip_paste(self):
        res = clip.run(["paste"], {}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "paste")

    def test_clip_clear(self):
        res = clip.run(["clear"], {}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "clear")

    def test_clip_status(self):
        res = clip.run(["status"], {}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "status")

    def test_clip_flags(self):
        res = clip.run([], {"paste": True}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "paste")

        res = clip.run(["hello"], {"copy": True}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "copy")
        self.assertEqual(res["text"], "hello")

    def test_pbcopy_args(self):
        res = pbcopy.run(["alpha", "beta"], {}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "copy")
        self.assertEqual(res["text"], "alpha beta")
        self.assertTrue(res["silent"])

    def test_pbcopy_stdin(self):
        res = pbcopy.run([], {}, self.context, stdin_data="from stdin")
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "copy")
        self.assertEqual(res["text"], "from stdin")

    def test_pbpaste(self):
        res = pbpaste.run([], {}, self.context)
        self.assertEqual(res["effect"], "clipboard_action")
        self.assertEqual(res["action"], "paste")

if __name__ == "__main__":
    unittest.main()
