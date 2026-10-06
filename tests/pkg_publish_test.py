import sys
import os
import json
import asyncio
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../resources/core"))

from filesystem import fs_manager
from commands import pkg

class TestPkgPublish(unittest.TestCase):
    def setUp(self):
        fs_manager.reset()
        fs_manager.save_func = lambda: None
        self.context = {
            "name": "Guest",
            "current_user": "Guest",
            "current_group": "Guest",
            "current_path": "/home/Guest"
        }
        self.root_context = {
            "name": "root",
            "current_user": "root",
            "current_group": "root",
            "current_path": "/home/root"
        }
        fs_manager.current_path = "/home/Guest"

    def test_pkg_init_and_validate(self):
        # 1. pkg init testtool
        res = asyncio.run(pkg.run(["init", "testtool"], {}, self.context))
        self.assertTrue(res["success"], f"init failed: {res}")
        self.assertIn("Created package template", res["output"])

        # Check file was written to /home/Guest/testtool.py
        node = fs_manager.get_node("/home/Guest/testtool.py")
        self.assertIsNotNone(node)
        self.assertIn("def metadata():", node["content"])
        self.assertIn("def run(", node["content"])

        # 2. pkg validate ./testtool.py
        val_res = asyncio.run(pkg.run(["validate", "/home/Guest/testtool.py"], {}, self.context))
        self.assertIsInstance(val_res, str)
        self.assertIn("VALIDATION REPORT: testtool", val_res)
        self.assertIn("SUCCESS:", val_res)

        # 3. pkg validate with --json
        val_json_str = asyncio.run(pkg.run(["validate", "/home/Guest/testtool.py"], {"json": True}, self.context))
        val_json = json.loads(val_json_str)
        self.assertTrue(val_json["valid"])
        self.assertEqual(val_json["name"], "testtool")
        self.assertEqual(val_json["version"], "1.0.0")

    def test_pkg_validate_invalid(self):
        # Syntax error
        fs_manager.write_file("/home/Guest/broken.py", "def foo(: broken syntax", self.context)
        res = asyncio.run(pkg.run(["validate", "/home/Guest/broken.py"], {}, self.context))
        self.assertFalse(res["success"])
        self.assertIn("compilation failure", res["error"]["message"])

        # Missing run() function
        fs_manager.write_file("/home/Guest/norun.py", "def metadata(): return {'name': 'norun', 'version': '1.0.0'}\ndef man(): pass", self.context)
        res2 = asyncio.run(pkg.run(["validate", "/home/Guest/norun.py"], {}, self.context))
        self.assertFalse(res2["success"])
        self.assertIn("validation error", res2["error"]["message"])

    def test_pkg_pack(self):
        asyncio.run(pkg.run(["init", "packdemo"], {}, self.context))
        res = asyncio.run(pkg.run(["pack", "/home/Guest/packdemo.py"], {}, self.context))
        self.assertIn("Successfully packaged", res)

        # Check .fpkg file exists in /home/Guest
        fpkg_node = fs_manager.get_node("/home/Guest/packdemo-1.0.0.fpkg")
        self.assertIsNotNone(fpkg_node)
        bundle = json.loads(fpkg_node["content"])
        self.assertEqual(bundle["format"], "fractalos-package-v1")
        self.assertEqual(bundle["name"], "packdemo")
        self.assertEqual(bundle["version"], "1.0.0")
        self.assertIn("sha256", bundle)
        self.assertIn("def run(", bundle["source"])

    def test_pkg_publish_dry_run(self):
        asyncio.run(pkg.run(["init", "drytool"], {}, self.context))
        res = asyncio.run(pkg.run(["publish", "/home/Guest/drytool.py"], {"dry_run": True}, self.context))
        self.assertIn("[DRY RUN]", res)
        self.assertIn("drytool", res)
        self.assertIn("0 files modified", res)

        # Ensure nothing was created in repo yet
        repo_node = fs_manager.get_node("/home/Guest/.pkg/repo/drytool.py")
        self.assertIsNone(repo_node)

    def test_pkg_publish_local_and_search(self):
        asyncio.run(pkg.run(["init", "pubtool"], {}, self.context))

        # Publish to local repository
        pub_res = asyncio.run(pkg.run(["publish", "/home/Guest/pubtool.py"], {}, self.context))
        self.assertTrue(pub_res["success"], f"Publish failed: {pub_res}")
        self.assertIn("Successfully published package 'pubtool'", pub_res["output"])

        # Check repository files
        repo_py = fs_manager.get_node("/home/Guest/.pkg/repo/pubtool.py")
        self.assertIsNotNone(repo_py)
        repo_fpkg = fs_manager.get_node("/home/Guest/.pkg/repo/pubtool-1.0.0.fpkg")
        self.assertIsNotNone(repo_fpkg)
        index_node = fs_manager.get_node("/home/Guest/.pkg/repo/index.json")
        self.assertIsNotNone(index_node)
        index_data = json.loads(index_node["content"])
        self.assertIn("pubtool", index_data["packages"])
        self.assertEqual(index_data["packages"]["pubtool"]["version"], "1.0.0")

        # Search for package
        search_res = asyncio.run(pkg.run(["search", "pubtool"], {}, self.context))
        self.assertIn("pubtool", search_res)
        self.assertIn("v1.0.0", search_res)

    def test_pkg_publish_mesh(self):
        asyncio.run(pkg.run(["init", "meshtool"], {}, self.context))
        res = asyncio.run(pkg.run(["publish", "/home/Guest/meshtool.py"], {"mesh": True}, self.context))
        self.assertTrue(res["success"])
        self.assertEqual(res["effect"], "pkg_mesh_publish")
        self.assertEqual(res["package"]["name"], "meshtool")

    def test_pkg_install_from_local_repo_and_remove(self):
        # 1. Init and publish package
        asyncio.run(pkg.run(["init", "greeter"], {}, self.root_context))
        pub_res = asyncio.run(pkg.run(["publish", "/home/root/greeter.py"], {}, self.root_context))
        self.assertTrue(pub_res["success"])

        # 2. Install greeter directly using package name (resolves from local repo!)
        inst_res = asyncio.run(pkg.run(["install", "greeter"], {}, self.root_context))
        self.assertTrue(inst_res["success"], f"Install failed: {inst_res}")
        self.assertIn("Successfully installed package 'greeter'", inst_res["output"])
        self.assertEqual(inst_res["effect"], "update_commands_manifest")

        # 3. Verify installed in /etc/packages/commands/greeter.py
        installed_node = fs_manager.get_node("/etc/packages/commands/greeter.py")
        self.assertIsNotNone(installed_node)

        # 4. Verify in /etc/pkg_manifest.json
        manifest_node = fs_manager.get_node("/etc/pkg_manifest.json")
        self.assertIsNotNone(manifest_node)
        manifest_data = json.loads(manifest_node["content"])
        self.assertIn("greeter", manifest_data)

        # 5. List packages
        list_res = asyncio.run(pkg.run(["list"], {}, self.root_context))
        self.assertIn("greeter", list_res)
        self.assertIn("v1.0.0", list_res)

        # 6. Remove package
        rm_res = asyncio.run(pkg.run(["remove", "greeter"], {}, self.root_context))
        self.assertTrue(rm_res["success"])
        self.assertIsNone(fs_manager.get_node("/etc/packages/commands/greeter.py"))

if __name__ == "__main__":
    unittest.main()
