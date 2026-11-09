#!/usr/bin/env python3
"""
Unit tests for gpio.py (Hardware Sensor Monitoring Daemon & GPIO).
"""

import sys
import os
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources/core")))

import json

from commands import gpio
from host_api import host_api

class TestGPIOCommand(unittest.TestCase):
    def setUp(self):
        self.ctx = {"username": "root"}

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_gpio_mode_configuration(self):
        res = self.run_async(gpio.run(["mode", "17", "in"], {}, self.ctx))
        self.assertIn("mode set to in", str(res))

        res_out = self.run_async(gpio.run(["mode", "18", "out"], {}, self.ctx))
        self.assertIn("mode set to out", str(res_out))

    def test_gpio_virtual_write_and_read(self):
        res_write = self.run_async(gpio.run(["write", "18", "1"], {}, self.ctx))
        self.assertIsInstance(res_write, dict)
        self.assertIn("1", res_write.get("output", ""))
        self.assertEqual(res_write.get("effects", [])[0].get("effect"), "gpio_simulate")

        res_read = self.run_async(gpio.run(["read", "18"], {}, self.ctx))
        self.assertEqual(res_read, "1")

        self.run_async(gpio.run(["write", "18", "0"], {}, self.ctx))
        res_read2 = self.run_async(gpio.run(["read", "18"], {}, self.ctx))
        self.assertEqual(res_read2, "0")

    def test_gpio_monitor_daemon(self):
        flags = {"--trigger": "rising", "--interval": "100", "--action": "echo alert"}
        res = self.run_async(gpio.run(["monitor", "17"], flags, self.ctx))
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "gpio_monitor_start")
        self.assertEqual(res.get("pin"), "17")
        self.assertEqual(res.get("trigger"), "rising")
        self.assertEqual(res.get("interval"), 100)
        self.assertEqual(res.get("action"), "echo alert")

    def test_gpio_stop_monitor(self):
        res = self.run_async(gpio.run(["stop", "17"], {}, self.ctx))
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "gpio_monitor_stop")
        self.assertEqual(res.get("pin"), "17")

    def test_gpio_list_monitors(self):
        res = self.run_async(gpio.run(["monitors"], {}, self.ctx))
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "gpio_monitor_list")

    def test_gpio_simulate_input(self):
        res = self.run_async(gpio.run(["simulate", "17", "1"], {}, self.ctx))
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("effect"), "gpio_simulate")
        self.assertEqual(res.get("pin"), "17")
        self.assertEqual(res.get("value"), 1)

    def test_gpio_stream_telemetry(self):
        res = self.run_async(gpio.run(["stream", "17", "3"], {}, self.ctx))
        self.assertIn("Sensor Stream: GPIO Pin 17", res)
        self.assertIn("#1", res)
        self.assertIn("#3", res)

    def test_gpio_man_and_help(self):
        self.assertIn("interact with physical and virtual GPIO pins", gpio.man([], {}, self.ctx))
        self.assertIn("Usage: gpio", gpio.help([], {}, self.ctx))

class TestGPIOHostCommandSafety(unittest.TestCase):
    """P6-05: in portable mode the pin is interpolated into a host shell command."""

    def setUp(self):
        self.ctx = {"username": "Guest"}
        self.sent = []

        def record(command):
            self.sent.append(command)
            return json.dumps({"success": True, "stdout": "1", "stderr": "", "exitCode": 0})

        host_api.set_exec_callback(record)

    def tearDown(self):
        host_api.set_exec_callback(None)

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_injected_pins_are_refused_and_never_reach_the_host(self):
        hostile = ["1; touch /tmp/fractal-p6-05", "$(id)", "`id`", "17 && id", "17|id", "-1", "", "1\nid", "abc"]
        calls = [["mode", None, "out"], ["read", None], ["write", None, "1"], ["stream", None, "1"],
                 ["monitor", None], ["stop", None], ["simulate", None, "1"]]
        for pin in hostile:
            for call in calls:
                args = [pin if a is None else a for a in call]
                res = self.run_async(gpio.run(args, {}, self.ctx))
                self.assertIsInstance(res, dict, (args, res))
                self.assertFalse(res.get("success", True), (args, res))
                self.assertIn("is not a pin number", res["error"]["message"])
        self.assertEqual(self.sent, [])

    def test_a_numeric_pin_reaches_the_host_as_a_plain_command(self):
        self.run_async(gpio.run(["mode", "17", "out"], {}, self.ctx))
        self.run_async(gpio.run(["write", "017", "1"], {}, self.ctx))
        self.assertEqual(self.run_async(gpio.run(["read", "17"], {}, self.ctx)), "1")
        self.assertEqual(self.sent, ["gpio mode 17 out", "gpio write 17 1", "gpio read 17"])

    def test_mode_and_value_cannot_carry_text_to_the_host(self):
        res = self.run_async(gpio.run(["mode", "17", "out;id"], {}, self.ctx))
        self.assertFalse(res.get("success", True))
        self.run_async(gpio.run(["write", "17", "1; id"], {}, self.ctx))
        self.assertEqual(self.sent, ["gpio write 17 0"])


if __name__ == "__main__":
    unittest.main()
