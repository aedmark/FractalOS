# tests/mesh_command_test.py
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'core'))

from filesystem import fs_manager
import commands.mesh_cp as mesh_cp
import commands.scp as scp
import commands.attach as attach
import commands.detach as detach
import commands.wall as wall
import commands.talk as talk

class MeshCommandTests(unittest.TestCase):
    def setUp(self):
        fs_manager.reset()
        self.user_context = {"name": "Guest", "group": "Guest"}
        self.config_on = {"NETWORKING_ENABLED": True}
        self.config_off = {"NETWORKING_ENABLED": False}

        # Create a test file in /home/Guest/test.txt
        fs_manager.write_file("/home/Guest/test.txt", "Sample file content", self.user_context)

    def test_networking_disabled(self):
        for cmd in [mesh_cp, scp, attach, wall, talk]:
            res = cmd.run(["anything"], {}, self.user_context, config=self.config_off)
            self.assertFalse(res.get("success", True), f"{cmd} should fail when networking is disabled")
            self.assertIn("networking is disabled", res["error"]["message"])

    def test_attach_syntax(self):
        # List
        res = attach.run([], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_attach_list")

        # Attach to node
        res = attach.run(["oos-1234"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_attach")
        self.assertEqual(res.get("targetId"), "oos-1234")

        # Detach flag
        res = attach.run([], {"detach": True}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_detach")

    def test_detach(self):
        res = detach.run([], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_detach")

    def test_wall(self):
        res = wall.run(["Server", "maintenance", "soon"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_wall")
        self.assertEqual(res.get("message"), "Server maintenance soon")
        self.assertEqual(res.get("sender"), "Guest")

    def test_talk(self):
        res = talk.run(["oos-999", "Hello", "there!"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_talk")
        self.assertEqual(res.get("targetId"), "oos-999")
        self.assertEqual(res.get("message"), "Hello there!")

    def test_mesh_cp_push(self):
        # Scp style: mesh-cp <local> <remote:path>
        res = mesh_cp.run(["/home/Guest/test.txt", "node-42:remote_test.txt"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_file_send")
        self.assertEqual(res.get("targetId"), "node-42")
        self.assertEqual(res.get("remotePath"), "remote_test.txt")
        self.assertEqual(res.get("content"), "Sample file content")
        self.assertEqual(res.get("size"), len("Sample file content"))

        # Send subcommand style: mesh-cp send <node> <local> [<remote>]
        res2 = mesh_cp.run(["send", "node-42", "/home/Guest/test.txt", "custom_remote.txt"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res2.get("effect"), "mesh_file_send")
        self.assertEqual(res2.get("targetId"), "node-42")
        self.assertEqual(res2.get("remotePath"), "custom_remote.txt")
        self.assertEqual(res2.get("content"), "Sample file content")

    def test_mesh_cp_pull(self):
        # Scp style: mesh-cp <remote:path> <local>
        res = mesh_cp.run(["node-42:backup.tar", "/home/Guest/backup.tar"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_file_pull")
        self.assertEqual(res.get("targetId"), "node-42")
        self.assertEqual(res.get("remotePath"), "backup.tar")
        self.assertEqual(res.get("localPath"), "/home/Guest/backup.tar")

        # Pull subcommand style: mesh-cp pull <node> <remote> [<local>]
        res2 = mesh_cp.run(["pull", "node-42", "data.json", "/home/Guest/data.json"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res2.get("effect"), "mesh_file_pull")
        self.assertEqual(res2.get("targetId"), "node-42")
        self.assertEqual(res2.get("remotePath"), "data.json")
        self.assertEqual(res2.get("localPath"), "/home/Guest/data.json")

    def test_scp_alias(self):
        res = scp.run(["/home/Guest/test.txt", "node-55:file.txt"], {}, self.user_context, config=self.config_on)
        self.assertEqual(res.get("effect"), "mesh_file_send")
        self.assertEqual(res.get("targetId"), "node-55")

if __name__ == '__main__':
    unittest.main()
