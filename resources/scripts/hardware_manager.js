/**
 * hardware_manager.js - Background hardware sensor monitoring daemon & GPIO manager.
 * Supports physical GPIO (via Neutralino host bridge) and virtual simulation.
 */

window.HardwareManager = class HardwareManager {
    constructor(dependencies = {}) {
        this.dependencies = dependencies;
        this.virtualPins = new Map();
        this.monitors = new Map();
        console.log("HardwareManager initialized.");
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    async readPin(pin) {
        const pinStr = String(pin);
        // If Neutralino available in portable mode on Linux
        if (typeof Neutralino !== 'undefined' && Neutralino.os) {
            try {
                const res = await Neutralino.os.execCommand(`gpio read ${pinStr}`);
                if (res && res.exitCode === 0) {
                    const parsed = parseInt(res.stdOut.trim(), 10);
                    return isNaN(parsed) ? 0 : parsed;
                }
            } catch (_) {}
        }
        // Virtual pin fallback
        return this.virtualPins.get(pinStr) || 0;
    }

    async writePin(pin, val) {
        const pinStr = String(pin);
        const numVal = (val === 1 || val === "1" || val === true) ? 1 : 0;
        this.virtualPins.set(pinStr, numVal);

        if (typeof Neutralino !== 'undefined' && Neutralino.os) {
            try {
                await Neutralino.os.execCommand(`gpio write ${pinStr} ${numVal}`);
            } catch (_) {}
        }
        return numVal;
    }

    startMonitor(pin, options = {}) {
        const pinStr = String(pin);
        this.stopMonitor(pinStr);

        const trigger = options.trigger || 'change'; // 'change', 'rising', 'falling'
        const intervalMs = Math.max(50, options.interval || 500);
        const actionCmd = options.action || null;
        const meshNotify = !!options.mesh;

        const monitorData = {
            pin: pinStr,
            trigger,
            intervalMs,
            actionCmd,
            meshNotify,
            lastVal: this.virtualPins.get(pinStr) || 0,
            eventCount: 0,
            startTime: Date.now(),
            timer: null
        };

        monitorData.timer = setInterval(async () => {
            await this._checkMonitorTick(monitorData);
        }, intervalMs);

        this.monitors.set(pinStr, monitorData);
        return monitorData;
    }

    stopMonitor(pin) {
        const pinStr = String(pin);
        const existing = this.monitors.get(pinStr);
        if (existing) {
            if (existing.timer) clearInterval(existing.timer);
            this.monitors.delete(pinStr);
            return true;
        }
        return false;
    }

    listMonitors() {
        const list = [];
        for (const [pin, mon] of this.monitors) {
            list.push({
                pin: pin,
                trigger: mon.trigger,
                interval: mon.intervalMs,
                lastVal: mon.lastVal,
                eventCount: mon.eventCount,
                action: mon.actionCmd,
                mesh: mon.meshNotify,
                uptimeSec: Math.floor((Date.now() - mon.startTime) / 1000)
            });
        }
        return list;
    }

    async simulatePin(pin, val) {
        const pinStr = String(pin);
        const numVal = (val === 1 || val === "1" || val === true) ? 1 : 0;
        this.virtualPins.set(pinStr, numVal);

        // Check if an active monitor exists for immediate trigger evaluation
        const mon = this.monitors.get(pinStr);
        if (mon) {
            await this._checkMonitorTick(mon);
        }
        return numVal;
    }

    async _checkMonitorTick(mon) {
        const currentVal = await this.readPin(mon.pin);
        const lastVal = mon.lastVal;

        if (currentVal !== lastVal) {
            mon.lastVal = currentVal;
            let shouldFire = false;

            if (mon.trigger === 'change') {
                shouldFire = true;
            } else if (mon.trigger === 'rising' && lastVal === 0 && currentVal === 1) {
                shouldFire = true;
            } else if (mon.trigger === 'falling' && lastVal === 1 && currentVal === 0) {
                shouldFire = true;
            }

            if (shouldFire) {
                mon.eventCount++;
                await this._fireMonitorEvent(mon, currentVal, lastVal);
            }
        }
    }

    async _fireMonitorEvent(mon, currentVal, lastVal) {
        const transition = lastVal === 0 ? "0 -> 1 [RISING]" : "1 -> 0 [FALLING]";
        const alertMsg = `\x1b[1;33m[Hardware Event]\x1b[0m GPIO pin ${mon.pin} triggered (${mon.trigger}): ${transition}`;

        if (this.dependencies.OutputManager) {
            await this.dependencies.OutputManager.appendToOutput(alertMsg);
        }

        // Play audio beep/tone
        if (this.dependencies.SoundManager && this.dependencies.SoundManager.isInitialized) {
            try { this.dependencies.SoundManager.playTone('A5', '32n'); } catch (_) {}
        }

        // Broadcast over mesh if configured
        if (mon.meshNotify && this.dependencies.NetworkManager) {
            try {
                await this.dependencies.NetworkManager.sendMessage(
                    'broadcast',
                    'mesh_wall',
                    `[Hardware Sensor Alert] Node ${this.dependencies.NetworkManager.getInstanceId()} pin ${mon.pin} fired (${mon.trigger})`
                );
            } catch (_) {}
        }

        // Execute bound action command
        if (mon.actionCmd && this.dependencies.CommandExecutor) {
            try {
                const execResult = await this.dependencies.CommandExecutor.processSingleCommand(mon.actionCmd, { isInteractive: false });
                if (execResult && execResult.output && this.dependencies.OutputManager) {
                    await this.dependencies.OutputManager.appendToOutput(execResult.output);
                }
            } catch (err) {
                console.error(`GPIO monitor action failed for pin ${mon.pin}:`, err);
            }
        }
    }

    cleanup() {
        for (const [, mon] of this.monitors) {
            if (mon.timer) clearInterval(mon.timer);
        }
        this.monitors.clear();
    }
};
