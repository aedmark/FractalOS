/**
 * tests/swarm_safety_unit.js - Unit tests for P7-08 Swarm Safety & Voltage Policies in JS.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock browser globals
global.window = { addEventListener: () => {} };
global.document = {
    createElement: () => ({ setAttribute: () => {}, appendChild: () => {}, style: {} }),
};
global.performance = { now: () => 12345 };

if (typeof BroadcastChannel === 'undefined') {
    class MockBroadcastChannel {
        constructor(name) {
            this.name = name;
            if (!MockBroadcastChannel.channels.has(name)) {
                MockBroadcastChannel.channels.set(name, new Set());
            }
            MockBroadcastChannel.channels.get(name).add(this);
            this.onmessage = null;
        }
        postMessage(data) {
            const set = MockBroadcastChannel.channels.get(this.name) || new Set();
            for (const ch of set) {
                if (ch !== this && typeof ch.onmessage === 'function') {
                    setTimeout(() => ch.onmessage({ data }), 0);
                }
            }
        }
        close() {
            const set = MockBroadcastChannel.channels.get(this.name);
            if (set) set.delete(this);
        }
    }
    MockBroadcastChannel.channels = new Map();
    global.BroadcastChannel = MockBroadcastChannel;
}

const mockOutput = [];
const mockDependencies = {
    Config: {
        NETWORKING: { NETWORKING_ENABLED: true }
    },
    OutputManager: {
        appendToOutput: async (text) => {
            mockOutput.push(text);
        }
    },
    UserManager: {
        getCurrentUser: async () => ({ username: 'alice', name: 'alice' })
    },
    EnvironmentManager: {
        get: (key) => key === 'HOST' ? 'node-alpha' : ''
    },
    CommandExecutor: {
        processSingleCommand: async (cmd) => {
            return { success: true, output: `Executed fallback: ${cmd}` };
        }
    }
};

const netManagerPath = path.join(__dirname, '..', 'resources', 'scripts', 'network_manager.js');
const netManagerCode = fs.readFileSync(netManagerPath, 'utf8');

const NetworkManagerClass = new Function(
    'module', 'exports',
    `${netManagerCode}; return NetworkManager;`
)({}, {});

async function runTests() {
    console.log("Running P7-08 Swarm Safety & Voltage Policies JS unit tests...");

    // Test 1: Outgoing request carries voltage budget, dry-run, and force
    {
        const nodeA = new NetworkManagerClass();
        nodeA.setDependencies(mockDependencies);
        nodeA.isNetworkingEnabled = true;

        let sentMessage = null;
        nodeA.sendMessage = async (targetId, type, data) => {
            sentMessage = { targetId, type, data };
        };
        nodeA.remoteInstances.add('node-beta-1234');

        const delegatePromise = nodeA.delegateAgentTask('node-beta-1234', 'Turn on motor', {
            isAutopilot: true,
            maxVoltage: 4.5,
            isDryRun: true,
            isForce: false,
            timeout: 5
        });

        assert(sentMessage !== null, "Message should be sent");
        assert.strictEqual(sentMessage.type, 'mesh_agent_request');
        assert.strictEqual(sentMessage.data.prompt, 'Turn on motor');
        assert.strictEqual(sentMessage.data.isAutopilot, true);
        assert.strictEqual(sentMessage.data.maxVoltage, 4.5);
        assert.strictEqual(sentMessage.data.isDryRun, true);
        assert.strictEqual(sentMessage.data.isForce, false);

        // Simulate successful response with voltage
        nodeA._handleMeshAgentResponse({
            data: {
                reqId: sentMessage.data.reqId,
                success: true,
                data: "Plan evaluated successfully (4.0V).",
                voltage: 4.0,
                targetId: 'node-beta-1234'
            }
        });

        const res = await delegatePromise;
        assert.strictEqual(res.success, true);
        assert.strictEqual(res.voltage, 4.0);
        console.log("ok 1 - delegateAgentTask transmits voltage budget and handles response");
    }

    // Test 2: Handling incoming task through kernel swarm syscall
    {
        const nodeB = new NetworkManagerClass();
        nodeB.setDependencies(mockDependencies);
        nodeB.isNetworkingEnabled = true;

        let responseSent = null;
        nodeB.sendMessage = async (targetId, type, data) => {
            responseSent = { targetId, type, data };
        };

        // Mock FractalOS_Kernel with swarm syscall
        global.FractalOS_Kernel = {
            isReady: true,
            syscall: async (mod, func, args) => {
                assert.strictEqual(mod, 'swarm');
                assert.strictEqual(func, 'handle_remote_agent_request');
                const req = args[0];
                if (req.maxVoltage && req.maxVoltage < 5.0) {
                    return JSON.stringify({
                        success: false,
                        voltage: 7.0,
                        error: "🛑 SWARM VOLTAGE EXCEEDED: Plan voltage (7.0 V) exceeds budget (4.5 V)."
                    });
                }
                return JSON.stringify({
                    success: true,
                    data: "Task finished.",
                    voltage: 2.0
                });
            }
        };

        // Case A: Plan exceeds budget
        await nodeB._handleMeshAgentRequest({
            sourceId: 'node-alpha-5678',
            data: {
                reqId: 'req-1',
                prompt: 'Run high voltage task',
                isAutopilot: true,
                senderUser: 'alice',
                maxVoltage: 4.0
            }
        });

        assert(responseSent !== null, "Response message must be sent");
        assert.strictEqual(responseSent.data.success, false);
        assert(responseSent.data.error.includes("SWARM VOLTAGE EXCEEDED"), "Error should indicate voltage exceeded");
        assert.strictEqual(responseSent.data.voltage, 7.0);

        // Case B: Plan fits budget
        await nodeB._handleMeshAgentRequest({
            sourceId: 'node-alpha-5678',
            data: {
                reqId: 'req-2',
                prompt: 'Read sensors',
                isAutopilot: true,
                senderUser: 'alice',
                maxVoltage: 10.0
            }
        });

        assert.strictEqual(responseSent.data.success, true);
        assert.strictEqual(responseSent.data.data, "Task finished.");
        assert.strictEqual(responseSent.data.voltage, 2.0);
        console.log("ok 2 - _handleMeshAgentRequest enforces swarm voltage safety via kernel");
    }

    // Test 3: Delegator rejects when peer returns safety error
    {
        const nodeA = new NetworkManagerClass();
        nodeA.setDependencies(mockDependencies);
        nodeA.isNetworkingEnabled = true;

        let sentMessage = null;
        nodeA.sendMessage = async (targetId, type, data) => {
            sentMessage = { targetId, type, data };
        };
        nodeA.remoteInstances.add('node-beta-1234');

        const delegatePromise = nodeA.delegateAgentTask('node-beta-1234', 'Delete all files', {
            isAutopilot: true,
            timeout: 5
        });

        // Simulate rejection from remote
        nodeA._handleMeshAgentResponse({
            data: {
                reqId: sentMessage.data.reqId,
                success: false,
                error: "🛑 SWARM POLICY VIOLATION: Remote destructive commands prohibited.",
                targetId: 'node-beta-1234'
            }
        });

        await assert.rejects(
            async () => await delegatePromise,
            /SWARM POLICY VIOLATION/
        );
        console.log("ok 3 - delegateAgentTask rejects on remote swarm policy violation");
    }

    console.log("\nALL 3 SWARM SAFETY JS UNIT TESTS PASSED!\n");
    process.exit(0);
}

runTests().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
