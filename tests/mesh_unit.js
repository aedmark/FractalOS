// tests/mesh_unit.js
// Node-based unit test for Phase 7 Milestone 7.1 (P7-01: Remote Shell & Session Attachment)

const assert = require('assert');

// Mock browser globals for Node testing if needed
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

// Load NetworkManager
const fs = require('fs');
const path = require('path');
const nmCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/network_manager.js'), 'utf8');

// Evaluate NetworkManager in global scope
const nmFn = new Function(nmCode + '; return NetworkManager;');
const NetworkManagerClass = nmFn();

async function runTests() {
    console.log("Running P7-01 Mesh Unit Tests...");

    // Create two network managers (simulating two FractalOS nodes)
    const nodeA = new NetworkManagerClass();
    const nodeB = new NetworkManagerClass();

    const outputA = [];
    const outputB = [];

    const mockDepsA = {
        Config: { NETWORKING: { NETWORKING_ENABLED: true, SIGNALING_SERVER_URL: 'ws://mock:8080' } },
        OutputManager: { appendToOutput: async (msg) => outputA.push(msg) },
        TerminalUI: { updatePrompt: async () => {} },
        FileSystemManager: { getCurrentPath: () => '/home/userA', getFsData: async () => ({}) },
        UserManager: { getCurrentUser: async () => ({ name: 'userA' }) },
        EnvironmentManager: { get: async () => 'node-a-host' }
    };

    const mockDepsB = {
        Config: { NETWORKING: { NETWORKING_ENABLED: true, SIGNALING_SERVER_URL: 'ws://mock:8080' } },
        OutputManager: { appendToOutput: async (msg) => outputB.push(msg) },
        TerminalUI: { updatePrompt: async () => {} },
        FileSystemManager: { getCurrentPath: () => '/home/userB', getFsData: async () => ({}) },
        UserManager: { getCurrentUser: async () => ({ name: 'userB' }) },
        EnvironmentManager: { get: async () => 'node-b-host' }
    };

    nodeA.setDependencies(mockDepsA);
    nodeB.setDependencies(mockDepsB);

    nodeA.isNetworkingEnabled = true;
    nodeB.isNetworkingEnabled = true;

    // Test 1: Peer Discovery over BroadcastChannel
    nodeA.channel.postMessage({ type: 'discover', sourceId: nodeA.getInstanceId(), targetId: 'broadcast' });
    await new Promise(r => setTimeout(r, 50));

    assert.ok(nodeB.getRemoteInstances().includes(nodeA.getInstanceId()), "Node B should discover Node A");
    assert.ok(nodeA.getRemoteInstances().includes(nodeB.getInstanceId()), "Node A should discover Node B");
    console.log("ok   peer discovery over broadcast channel");

    // Test 2: Mesh Wall (Broadcast)
    await nodeA.sendMessage('broadcast', 'mesh_wall', {
        sender: 'userA',
        message: 'Maintenance in 10 minutes',
        timestamp: '12:00:00'
    });
    await new Promise(r => setTimeout(r, 50));

    assert.ok(outputB.some(o => o.includes('Maintenance in 10 minutes')), "Node B should receive wall broadcast");
    console.log("ok   mesh wall broadcast received on peer");

    // Test 3: Mesh Talk (Direct 2-way peer message)
    await nodeA.sendMessage(nodeB.getInstanceId(), 'mesh_talk', {
        sender: 'userA',
        message: 'Hello Node B',
        timestamp: '12:00:01'
    });
    await new Promise(r => setTimeout(r, 50));

    assert.ok(outputB.some(o => o.includes('Hello Node B')), "Node B should receive talk direct message");
    console.log("ok   mesh talk direct message received on target");

    // Test 4: Remote Session Attachment (Attach Node A -> Node B)
    assert.strictEqual(nodeA.isAttached(), false, "Node A should initially not be attached");
    assert.strictEqual(nodeB.getAttachedClients().length, 0, "Node B should have 0 attached clients");

    const attachPromise = nodeA.requestAttach(nodeB.getInstanceId(), { timeoutMs: 2000 });
    await new Promise(r => setTimeout(r, 50));
    await attachPromise;

    assert.strictEqual(nodeA.isAttached(), true, "Node A should now be attached");
    assert.strictEqual(nodeA.getAttachedSession().targetId, nodeB.getInstanceId());
    assert.strictEqual(nodeA.getAttachedSession().user, 'userB');
    assert.strictEqual(nodeA.getAttachedSession().path, '/home/userB');
    assert.ok(nodeB.getAttachedClients().includes(nodeA.getInstanceId()), "Node B should record attached client");
    console.log("ok   remote session attachment (handshake, context transfer, state tracking)");

    // Test 5: Remote Execution over Attached Session
    // Mock kernel on Node B
    global.createKernelContext = async () => "{}";
    global.FractalOS_Kernel = {
        execute_command: async (cmd) => JSON.stringify({ success: true, output: `Echo from B: ${cmd}` })
    };

    const execPromise = nodeA.sendRemoteCommand('whoami');
    await new Promise(r => setTimeout(r, 50));
    const result = await execPromise;

    assert.strictEqual(result.success, true);
    assert.strictEqual(result.output, 'Echo from B: whoami');
    console.log("ok   remote command execution over attached session");

    // Test 6: Detach Session
    await nodeA.detachSession();
    await new Promise(r => setTimeout(r, 50));

    assert.strictEqual(nodeA.isAttached(), false, "Node A should be detached");
    assert.strictEqual(nodeB.getAttachedClients().includes(nodeA.getInstanceId()), false, "Node B should clear client");
    console.log("ok   clean session detach and notification");

    // Test 7: Peer-to-Peer File Send (P7-02)
    const filesOnB = {};
    mockDepsB.FileSystemManager.createOrUpdateFile = async (path, content) => {
        filesOnB[path] = content;
        return { success: true };
    };
    mockDepsB.FileSystemManager.save = async () => true;

    const sendPromise = nodeA.sendFile(nodeB.getInstanceId(), '/home/userB/transferred.txt', 'Hello from Node A');
    await new Promise(r => setTimeout(r, 50));
    const sendAck = await sendPromise;

    assert.strictEqual(sendAck.success, true);
    assert.strictEqual(filesOnB['/home/userB/transferred.txt'], 'Hello from Node A');
    console.log("ok   p2p file send (push) across mesh");

    // Test 8: Peer-to-Peer File Pull (P7-02)
    const filesOnA = {};
    mockDepsA.FileSystemManager.createOrUpdateFile = async (path, content) => {
        filesOnA[path] = content;
        return { success: true };
    };
    mockDepsA.FileSystemManager.save = async () => true;

    mockDepsB.FileSystemManager.getNodeByPath = async (path) => {
        if (path === '/home/userB/data.json') {
            return { type: 'file', content: '{"answer": 42}' };
        }
        return null;
    };

    const pullPromise = nodeA.pullFile(nodeB.getInstanceId(), '/home/userB/data.json', '/home/userA/pulled.json');
    await new Promise(r => setTimeout(r, 50));
    const pullReply = await pullPromise;

    assert.strictEqual(pullReply.success, true);
    assert.strictEqual(filesOnA['/home/userA/pulled.json'], '{"answer": 42}');
    console.log("ok   p2p file pull across mesh");

    console.log("ALL P7-01 AND P7-02 MESH TESTS PASSED");
}

runTests().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
