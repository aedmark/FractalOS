"""
gpio.py - Interact with and monitor physical or simulated GPIO pins and hardware sensors.
"""

import asyncio
from host_api import host_api

# In-memory virtual pin storage (fallback and simulation)
VIRTUAL_PINS = {}
VIRTUAL_MODES = {}
ACTIVE_MONITORS = {}

def define_flags():
    return {
        "flags": ["--trigger", "-t", "--interval", "-i", "--action", "-a", "--mesh", "-m", "--simulate", "-s", "--help", "-h"],
        "metadata": {
            "--trigger": {"type": "string", "choices": ["change", "rising", "falling"]},
            "--interval": {"type": "integer"},
            "--action": {"type": "string"}
        }
    }

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if not args:
        return {
            "success": False,
            "error": {
                "message": "gpio: missing arguments",
                "suggestion": "Usage: gpio [mode|read|write|monitor|stop|monitors|simulate|stream] <pin> [args]"
            }
        }

    cmd = args[0].lower()

    # --- Mode Configuration ---
    if cmd == "mode":
        if len(args) != 3:
            return {"success": False, "error": {"message": "gpio mode: requires pin and mode (in/out)", "suggestion": "Usage: gpio mode <pin> <in|out>"}}
        pin = str(args[1])
        mode = args[2].lower()
        if mode not in ("in", "out", "op", "ip"):
            return {"success": False, "error": {"message": f"gpio mode: unknown mode '{mode}'", "suggestion": "Use 'in' or 'out'."}}

        VIRTUAL_MODES[pin] = mode

        # Try host execution if available
        res = await host_api.exec_command(f"gpio mode {pin} {mode}")
        if res.get("success") and res.get("exitCode") == 0:
            return res.get("stdout", "").strip() or f"Pin {pin} mode set to {mode}."

        return f"Pin {pin} mode set to {mode} (virtual mode)."

    # --- Read Pin ---
    elif cmd == "read":
        if len(args) != 2:
            return {"success": False, "error": {"message": "gpio read: requires pin", "suggestion": "Usage: gpio read <pin>"}}
        pin = str(args[1])

        res = await host_api.exec_command(f"gpio read {pin}")
        if res.get("success") and res.get("exitCode") == 0:
            return res.get("stdout", "").strip()

        # Fall back to virtual pin
        return str(VIRTUAL_PINS.get(pin, 0))

    # --- Write Pin ---
    elif cmd == "write":
        if len(args) != 3:
            return {"success": False, "error": {"message": "gpio write: requires pin and value (0/1)", "suggestion": "Usage: gpio write <pin> <0|1>"}}
        pin = str(args[1])
        val = 1 if str(args[2]) in ("1", "high", "true") else 0

        VIRTUAL_PINS[pin] = val

        effects = [{
            "effect": "gpio_simulate",
            "pin": pin,
            "value": val
        }]

        res = await host_api.exec_command(f"gpio write {pin} {val}")
        if res.get("success") and res.get("exitCode") == 0:
            out = res.get("stdout", "").strip() or f"Pin {pin} -> {val}"
            return {"effects": effects, "output": out}

        return {"effects": effects, "output": f"Pin {pin} -> {val} (virtual bus)"}

    # --- Sensor Monitoring Daemon ---
    elif cmd in ("monitor", "watch"):
        if len(args) < 2:
            return {"success": False, "error": {"message": "gpio monitor: requires pin", "suggestion": "Usage: gpio monitor <pin> [--trigger <change|rising|falling>] [--action <cmd>] [--interval <ms>] [--mesh]"}}
        pin = str(args[1])

        # Parse flags
        trigger = "change"
        if "--trigger" in flags:
            trigger = flags["--trigger"]
        elif "-t" in flags:
            trigger = flags["-t"]

        interval = 500
        if "--interval" in flags:
            try: interval = int(flags["--interval"])
            except ValueError: pass
        elif "-i" in flags:
            try: interval = int(flags["-i"])
            except ValueError: pass

        action_cmd = flags.get("--action") or flags.get("-a") or None
        wants_mesh = "--mesh" in flags or "-m" in flags

        ACTIVE_MONITORS[pin] = {
            "pin": pin,
            "trigger": trigger,
            "interval": interval,
            "action": action_cmd,
            "mesh": wants_mesh
        }

        return {
            "effect": "gpio_monitor_start",
            "pin": pin,
            "trigger": trigger,
            "interval": interval,
            "action": action_cmd,
            "mesh": wants_mesh
        }

    # --- Stop Monitoring ---
    elif cmd in ("unmonitor", "stop", "unwatch"):
        if len(args) < 2:
            return {"success": False, "error": {"message": "gpio stop: requires pin", "suggestion": "Usage: gpio stop <pin>"}}
        pin = str(args[1])
        if pin in ACTIVE_MONITORS:
            del ACTIVE_MONITORS[pin]

        return {
            "effect": "gpio_monitor_stop",
            "pin": pin
        }

    # --- List Monitors ---
    elif cmd in ("monitors", "list-monitors", "status"):
        return {
            "effect": "gpio_monitor_list"
        }

    # --- Simulate Pin Input ---
    elif cmd in ("simulate", "mock"):
        if len(args) != 3:
            return {"success": False, "error": {"message": "gpio simulate: requires pin and value (0/1)", "suggestion": "Usage: gpio simulate <pin> <0|1>"}}
        pin = str(args[1])
        val = 1 if str(args[2]) in ("1", "high", "true") else 0
        VIRTUAL_PINS[pin] = val

        return {
            "effect": "gpio_simulate",
            "pin": pin,
            "value": val
        }

    # --- Stream Readings ---
    elif cmd in ("stream", "telemetry"):
        if len(args) < 2:
            return {"success": False, "error": {"message": "gpio stream: requires pin", "suggestion": "Usage: gpio stream <pin> [sample_count]"}}
        pin = str(args[1])
        count = 5
        if len(args) > 2:
            try: count = max(1, min(20, int(args[2])))
            except ValueError: pass

        lines = [
            f"\x1b[1;36m=== Sensor Stream: GPIO Pin {pin} ({count} samples) ===\x1b[0m",
            "Sample   Value   State",
            "─────────────────────────"
        ]

        for i in range(1, count + 1):
            res = await host_api.exec_command(f"gpio read {pin}")
            if res.get("success") and res.get("exitCode") == 0:
                v = int(res.get("stdout", "0").strip())
            else:
                v = VIRTUAL_PINS.get(pin, 0)
            state_label = "\x1b[1;32mHIGH (1)\x1b[0m" if v == 1 else "\x1b[2mLOW (0)\x1b[0m"
            lines.append(f"  #{i:<6} {v:<7} {state_label}")
            if i < count:
                await asyncio.sleep(0.1)

        return "\n".join(lines)

    else:
        return {"success": False, "error": {"message": f"gpio: unknown subcommand '{cmd}'", "suggestion": "Run 'man gpio' for supported commands."}}


def man(args, flags, user_context, **kwargs):
    return """
NAME
    gpio - interact with physical and virtual GPIO pins, sensors, and daemons

SYNOPSIS
    gpio mode <pin> <in|out>
    gpio read <pin>
    gpio write <pin> <0|1>
    gpio monitor <pin> [--trigger <change|rising|falling>] [--interval <ms>] [--action <cmd>] [--mesh]
    gpio stop <pin>
    gpio monitors
    gpio simulate <pin> <0|1>
    gpio stream <pin> [count]

DESCRIPTION
    Interacts with hardware sensors, buttons, and actuators.
    In Portable Mode on a Raspberry Pi, communicates with physical hardware via
    Neutralino's OS bridge. In browser or virtual mode, provides a virtual bus with
    full sensor simulation and background monitoring.

    Background monitors watch pins for state changes or button transitions
    (rising: 0->1, falling: 1->0, change) and automatically execute bound shell
    actions or broadcast alerts across the mesh network.

OPTIONS
    --trigger, -t
        Trigger condition for monitoring: 'change' (default), 'rising' (button press / low-to-high),
        or 'falling' (button release / high-to-low).
    --interval, -i
        Polling interval in milliseconds (default: 500ms).
    --action, -a
        Shell command string executed automatically when trigger condition fires.
    --mesh, -m
        Broadcast alert across the mesh network via 'mesh_wall' on event.

EXAMPLES
    gpio mode 17 in
        Configures pin 17 as an input.
    gpio write 18 1
        Sets pin 18 (e.g. LED) HIGH.
    gpio monitor 17 --trigger rising --action "wall 'Button pressed!'"
        Starts a background daemon monitoring pin 17 for button presses, broadcasting
        an alert whenever the button is pressed.
    gpio simulate 17 1
        Simulates an input transition to test callbacks and monitoring daemons.
    gpio monitors
        Lists active background hardware monitors.
    gpio stream 17 5
        Reads 5 live sensor samples from pin 17.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: gpio [mode | read | write | monitor | stop | monitors | simulate | stream] <pin> [args]"
