/**
 * tests/hardware_unit.js - Unit tests for HardwareManager background daemon & GPIO simulation.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock browser globals
global.window = global;
global.window.addEventListener = () => {};

const hwCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/hardware_manager.js'), 'utf8');
eval(hwCode);

async function runTests() {
    console.log("Running HardwareManager & GPIO Daemon JS unit tests...");

    const executedCommands = [];
    const outputMessages = [];

    const mockDeps = {
        OutputManager: {
            appendToOutput: async (txt) => { outputMessages.push(txt); }
        },
        SoundManager: {
            isInitialized: true,
            playTone: () => {}
        },
        CommandExecutor: {
            processSingleCommand: async (cmd) => {
                executedCommands.push(cmd);
                return { success: true, output: `Executed: ${cmd}` };
            }
        },
        NetworkManager: null
    };

    const hw = new window.HardwareManager(mockDeps);

    // Test 1: Virtual pin read & write
    assert.strictEqual(await hw.readPin(17), 0, "Default pin value is 0");
    await hw.writePin(17, 1);
    assert.strictEqual(await hw.readPin(17), 1, "Pin value updated to 1");
    await hw.writePin(17, 0);
    assert.strictEqual(await hw.readPin(17), 0, "Pin value updated to 0");
    console.log("ok 1 - HardwareManager virtual pin read & write");

    // Test 2: Background monitor registration
    const mon = hw.startMonitor(17, {
        trigger: 'rising',
        interval: 100,
        action: 'echo "Button Pressed!"'
    });
    assert.strictEqual(mon.pin, '17');
    assert.strictEqual(mon.trigger, 'rising');
    assert.strictEqual(hw.monitors.size, 1);
    console.log("ok 2 - HardwareManager monitor daemon registration");

    // Test 3: List monitors
    const list = hw.listMonitors();
    assert.strictEqual(list.length, 1);
    assert.strictEqual(list[0].pin, '17');
    assert.strictEqual(list[0].action, 'echo "Button Pressed!"');
    console.log("ok 3 - HardwareManager listMonitors");

    // Test 4: Simulation and rising trigger firing
    // Simulate pin 17 -> 1 (rising from 0)
    await hw.simulatePin(17, 1);
    assert.strictEqual(mon.eventCount, 1, "Rising transition fired event");
    assert(executedCommands.includes('echo "Button Pressed!"'), "Action command executed automatically");
    assert(outputMessages.some(m => m.includes("GPIO pin 17 triggered")), "Alert logged to output");
    console.log("ok 4 - HardwareManager rising trigger fires action command");

    // Test 5: Non-matching transition should not fire
    // Simulate pin 17 -> 0 (falling), while trigger is 'rising'
    const prevCount = mon.eventCount;
    await hw.simulatePin(17, 0);
    assert.strictEqual(mon.eventCount, prevCount, "Falling transition did NOT fire rising trigger");
    console.log("ok 5 - HardwareManager trigger condition filtering");

    // Test 6: Stop monitor & cleanup
    const stopped = hw.stopMonitor(17);
    assert.strictEqual(stopped, true, "Monitor stopped cleanly");
    assert.strictEqual(hw.monitors.size, 0, "Monitor map empty");
    hw.cleanup();
    console.log("ok 6 - HardwareManager stop and cleanup");

    console.log("\nALL 6 HARDWARE DAEMON JS UNIT TESTS PASSED!");
}

runTests().then(() => {
    process.exit(0);
}).catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
