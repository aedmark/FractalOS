"""
Tests for FractalOS Standard Library Community Packages (fortune, cowsay, cal, banner) (P7-15)
"""
import sys
import os
import unittest
import asyncio
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT, "resources", "core")
COMMANDS_DIR = os.path.join(CORE_DIR, "commands")
sys.path.insert(0, CORE_DIR)
sys.path.insert(0, COMMANDS_DIR)

from filesystem import fs_manager
import pkg

class TestStdlibPackages(unittest.TestCase):
    def setUp(self):
        fs_manager.reset()
        fs_manager.save_function = lambda x: None
        self.root_context = {"name": "root", "current_user": "root", "current_path": "/home/root"}
        self.user_context = {"name": "gordon", "current_user": "gordon", "current_path": "/home/gordon"}
        fs_manager.create_directory("/home/gordon", self.root_context, parents=True)

    def test_01_pkg_search_finds_standard_packages(self):
        async def _run():
            res = await pkg.run(["search"], {}, self.user_context)
            self.assertIn("fortune", res)
            self.assertIn("cowsay", res)
            self.assertIn("cal", res)
            self.assertIn("banner", res)

            # Targeted search
            res_cow = await pkg.run(["search", "cow"], {}, self.user_context)
            self.assertIn("cowsay", res_cow)
            self.assertNotIn("cal", res_cow)
        asyncio.run(_run())

    def test_02_pkg_install_standard_packages(self):
        async def _run():
            for name in ["fortune", "cowsay", "cal", "banner"]:
                res = await pkg.run(["install", name], {}, self.root_context)
                self.assertTrue(res.get("success"), f"Failed to install {name}: {res}")
                self.assertIn("Successfully installed", res.get("output", ""))
                self.assertIsNotNone(fs_manager.get_node(f"/etc/packages/commands/{name}.py"))

            # pkg list verification
            list_res = await pkg.run(["list"], {}, self.user_context)
            for name in ["fortune", "cowsay", "cal", "banner"]:
                self.assertIn(name, list_res)
        asyncio.run(_run())

    def test_03_fortune_command_execution(self):
        async def _run():
            await pkg.run(["install", "fortune"], {}, self.root_context)
            
            # Load installed command module
            code = fs_manager.get_node("/etc/packages/commands/fortune.py")["content"]
            env = {}
            exec(code, env)
            fortune_run = env["run"]
            
            # Default run
            out = await fortune_run([], {}, self.user_context)
            self.assertIsInstance(out, str)
            self.assertTrue(len(out) > 0)
            self.assertNotIn("\x1b[", out) # Default is plain text without ANSI (D-023)

            # Color run (-C)
            out_color = await fortune_run([], {"color": True}, self.user_context)
            self.assertIn("\x1b[1;36m", out_color)

            # Short run (-s)
            out_short = await fortune_run([], {"short": True}, self.user_context)
            self.assertLessEqual(len(out_short), 60)
        asyncio.run(_run())

    def test_04_cowsay_command_execution(self):
        async def _run():
            await pkg.run(["install", "cowsay"], {}, self.root_context)
            
            code = fs_manager.get_node("/etc/packages/commands/cowsay.py")["content"]
            env = {}
            exec(code, env)
            cowsay_run = env["run"]

            # Basic message
            out = await cowsay_run(["Hello", "FractalOS!"], {}, self.user_context)
            self.assertIn("< Hello FractalOS! >", out)
            self.assertIn("^__^", out)
            self.assertIn("(oo)", out)

            # Multi-line bubble wrapping
            long_msg = ["This", "is", "a", "longer", "message", "that", "will", "wrap", "into", "multiple", "lines", "cleanly"]
            out_multi = await cowsay_run(long_msg, {"width": 15}, self.user_context)
            self.assertIn("/", out_multi)
            self.assertIn("|", out_multi)
            self.assertIn("\\", out_multi)

            # Expression flags: Borg (-b), Dead (-d), Wired (-w)
            out_borg = await cowsay_run(["Borg"], {"borg": True}, self.user_context)
            self.assertIn("(==)", out_borg)

            out_dead = await cowsay_run(["Dead"], {"dead": True}, self.user_context)
            self.assertIn("(xx)", out_dead)
            self.assertIn("U ", out_dead)

            out_wired = await cowsay_run(["Wired"], {"wired": True}, self.user_context)
            self.assertIn("(OO)", out_wired)

            # Creature files: tux, duck, ghost
            out_tux = await cowsay_run(["Linux"], {"file": "tux"}, self.user_context)
            self.assertIn("o_o", out_tux)

            out_duck = await cowsay_run(["Quack"], {"file": "duck"}, self.user_context)
            self.assertIn(">()_", out_duck)

            out_ghost = await cowsay_run(["Boo"], {"file": "ghost"}, self.user_context)
            self.assertIn("(o o)", out_ghost)
        asyncio.run(_run())

    def test_05_cal_command_execution(self):
        async def _run():
            await pkg.run(["install", "cal"], {}, self.root_context)
            
            code = fs_manager.get_node("/etc/packages/commands/cal.py")["content"]
            env = {}
            exec(code, env)
            cal_run = env["run"]

            # Current month
            out = await cal_run([], {}, self.user_context)
            self.assertIn("Su Mo Tu We Th Fr Sa", out)

            # Monday start (-m)
            out_mon = await cal_run([], {"monday": True}, self.user_context)
            self.assertIn("Mo Tu We Th Fr Sa Su", out_mon)

            # Specific month/year: 12 2026
            out_spec = await cal_run(["12", "2026"], {}, self.user_context)
            self.assertIn("December 2026", out_spec)
            self.assertIn("31", out_spec)

            # Three-month view (-3)
            out_three = await cal_run([], {"three": True}, self.user_context)
            lines = out_three.strip().splitlines()
            self.assertTrue(len(lines) >= 7)

            # Full year view (-y)
            out_year = await cal_run(["2027"], {"year": True}, self.user_context)
            self.assertIn("January 2027", out_year)
            self.assertIn("December 2027", out_year)
        asyncio.run(_run())

    def test_06_banner_command_execution(self):
        async def _run():
            await pkg.run(["install", "banner"], {}, self.root_context)
            
            code = fs_manager.get_node("/etc/packages/commands/banner.py")["content"]
            env = {}
            exec(code, env)
            banner_run = env["run"]

            # Default char (#)
            out = await banner_run(["FRACTAL"], {}, self.user_context)
            lines = [l for l in out.splitlines() if l.strip()]
            self.assertEqual(len(lines), 5)
            self.assertIn("#", out)

            # Custom char (-c '*')
            out_star = await banner_run(["OS"], {"char": "*"}, self.user_context)
            self.assertIn("*", out_star)
            self.assertNotIn("#", out_star)
        asyncio.run(_run())

    def test_07_pipe_fortune_into_cowsay(self):
        async def _run():
            await pkg.run(["install", "fortune"], {}, self.root_context)
            await pkg.run(["install", "cowsay"], {}, self.root_context)

            f_code = fs_manager.get_node("/etc/packages/commands/fortune.py")["content"]
            f_env = {}
            exec(f_code, f_env)
            fortune_out = await f_env["run"]([], {}, self.user_context)

            c_code = fs_manager.get_node("/etc/packages/commands/cowsay.py")["content"]
            c_env = {}
            exec(c_code, c_env)
            cowsay_out = await c_env["run"]([], {}, self.user_context, stdin_data=fortune_out)

            self.assertIn("^__^", cowsay_out)
            self.assertTrue(len(cowsay_out.splitlines()) > 5)
        asyncio.run(_run())

    def test_08_pkg_deps_and_removal(self):
        async def _run():
            for name in ["fortune", "cowsay"]:
                await pkg.run(["install", name], {}, self.root_context)
                deps_res = await pkg.run(["deps", name], {}, self.user_context)
                self.assertIn(f"DEPENDENCY TREE: {name}", deps_res)

            # Remove fortune
            rem_res = await pkg.run(["remove", "fortune"], {}, self.root_context)
            self.assertTrue(rem_res.get("success"))
            self.assertIsNone(fs_manager.get_node("/etc/packages/commands/fortune.py"))

            # Confirm list only has cowsay
            list_res = await pkg.run(["list"], {}, self.user_context)
            self.assertNotIn("fortune", list_res)
            self.assertIn("cowsay", list_res)
        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
