/**
 * tests/mesh_agent_unit.js - Unit tests for Distributed Agent Task Delegation (P7-07).
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

// Mock dependencies
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
            return { success: true, output: `[Simulated response for: ${cmd}]` };
        }
    }
};

// Load NetworkManager
const netManagerCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/network_manager.js'), 'utf8');
const nmFn = new Function(netManagerCode + '; return NetworkManager;');
const NetworkManager = nmFn();

async function runTests() {
    console.log("Running P7-07 Mesh Agent Task Delegation JS unit tests...");

    // Create node A
    const nodeA = new NetworkManager();
    nodeA.setDependencies(mockDependencies);
    nodeA.isNetworkingEnabled = true;

    // Create node B
    const nodeB = new NetworkManager();
    const nodeBDependencies = {
        ...mockDependencies,
        UserManager: { getCurrentUser: async () => ({ username: 'bob', name: 'bob' }) },
        EnvironmentManager: { get: () => 'node-beta' },
        CommandExecutor: {
            processSingleCommand: async (cmd) => {
                if (cmd.includes("failing")) {
                    return { success: false, output: "Command failed" };
                }
                return { success: true, output: `Bob handled: ${cmd}` };
            }
        }
    };
    nodeB.setDependencies(nodeBDependencies);
    nodeB.isNetworkingEnabled = true;

    // Register peers directly for test harness
    nodeA.remoteInstances.add(nodeB.instanceId);
    nodeB.remoteInstances.add(nodeA.instanceId);
    nodeA.peerMetadata.set(nodeB.instanceId, { user: 'bob@node-beta', hostname: 'node-beta', capabilities: ['mesh-agent'] });
    nodeB.peerMetadata.set(nodeA.instanceId, { user: 'alice@node-alpha', hostname: 'node-alpha', capabilities: ['mesh-agent'] });

    // Mock direct message transmission between nodeA and nodeB
    nodeA.sendMessage = async (targetId, type, data) => {
        if (targetId === nodeB.instanceId) {
            await nodeB._processIncomingMessage({ type, sourceId: nodeA.instanceId, targetId: nodeB.instanceId, data });
        }
    };
    nodeB.sendMessage = async (targetId, type, data) => {
        if (targetId === nodeA.instanceId) {
            await nodeA._processIncomingMessage({ type, sourceId: nodeB.instanceId, targetId: nodeA.instanceId, data });
        }
    };

    // Test 1: resolvePeerId
    const resolvedFull = nodeA.resolvePeerId(nodeB.instanceId);
    assert.strictEqual(resolvedFull, nodeB.instanceId, "resolvePeerId matches full ID");

    const resolvedPrefix = nodeA.resolvePeerId(nodeB.instanceId.substring(0, 6));
    assert.strictEqual(resolvedPrefix, nodeB.instanceId, "resolvePeerId matches prefix");

    const resolvedHostname = nodeA.resolvePeerId("bob@node-beta");
    assert.strictEqual(resolvedHostname, nodeB.instanceId, "resolvePeerId matches user/host metadata");
    console.log("ok 1 - resolvePeerId matches full ID, prefix, and host metadata");

    // Test 2: delegateAgentTask query
    const res1 = await nodeA.delegateAgentTask(nodeB.instanceId, "read pin 17", { isAutopilot: false });
    assert.strictEqual(res1.success, true, "Delegated query succeeded");
    assert(res1.data.includes("Bob handled: samwise \"read pin 17\""), "Remote node handled delegated task");
    console.log("ok 2 - delegateAgentTask executes read query on remote node");

    // Test 3: delegateAgentTask autopilot
    const res2 = await nodeA.delegateAgentTask("bob@node-beta", "turn on LED 18", { isAutopilot: true });
    assert.strictEqual(res2.success, true, "Autopilot delegation succeeded");
    assert(res2.data.includes("samwise --autopilot \"turn on LED 18\""), "Remote node invoked autopilot");
    console.log("ok 3 - delegateAgentTask delegates autopilot mode");

    // Test 4: delegateAgentTask timeout
    let timedOut = false;
    try {
        await nodeA.delegateAgentTask("unreachable-node", "hello", { timeout: 0.05 });
    } catch (e) {
        timedOut = true;
    }
    assert.strictEqual(timedOut, true, "Delegation to unreachable peer timed out as expected");
    console.log("ok 4 - delegateAgentTask times out on unreachable peer");

    // Test 5: capabilities include mesh-agent
    const nodeInfo = nodeA.getLocalNodeInfo();
    assert(nodeInfo.capabilities.includes('mesh-agent'), "Local capabilities include mesh-agent");
    console.log("ok 5 - getLocalNodeInfo reports mesh-agent capability");

    console.log("\nALL 5 MESH AGENT JS UNIT TESTS PASSED!");
    process.exit(0);
}

runTests().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
