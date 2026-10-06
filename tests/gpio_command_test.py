#!/usr/bin/env python3
"""
Unit tests for gpio.py (Hardware Sensor Monitoring Daemon & GPIO).
"""

import sys
import os
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources/core")))

from commands import gpio

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

if __name__ == "__main__":
    unittest.main()
