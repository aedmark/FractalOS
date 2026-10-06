/**
 * tests/peers_unit.js - Unit tests for Mesh Node Presence, Discovery, and Peers UI app.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock browser globals for Node test environment
global.window = global;
global.window.addEventListener = () => {};
global.BroadcastChannel = class {
    constructor(name) { this.name = name; }
    postMessage() {}
    close() {}
};

function createMockElement(tag, attrs = {}, children = []) {
    const el = {
        tagName: tag.toUpperCase(),
        className: attrs.className || '',
        id: attrs.id || '',
        textContent: attrs.textContent || '',
        style: attrs.style || {},
        children: Array.isArray(children) ? [...children] : (children ? [children] : []),
        innerHTML: '',
        classList: {
            classes: new Set((attrs.className || '').split(' ').filter(Boolean)),
            add(c) { this.classes.add(c); el.className = Array.from(this.classes).join(' '); },
            remove(c) { this.classes.delete(c); el.className = Array.from(this.classes).join(' '); },
            contains(c) { return this.classes.has(c); }
        },
        appendChild(child) { this.children.push(child); return child; },
        querySelector(selector) {
            if (selector.startsWith('.')) {
                const cls = selector.substring(1);
                return this.children.find(c => c.classList && c.classList.contains(cls)) || null;
            }
            return null;
        },
        querySelectorAll() { return []; },
        focus() {}
    };
    return el;
}

global.document = {
    createElement: (tag, attrs, children) => createMockElement(tag, attrs, children),
    createTextNode: (txt) => ({ text: txt })
};

global.App = class App {
    constructor() { this.isActive = false; }
    enter() {}
    exit() {}
};

const nmCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/network_manager.js'), 'utf8');
const peersUiCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/apps/peers/peers_ui.js'), 'utf8');
const peersMgrCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/apps/peers/peers_manager.js'), 'utf8');

const nmFn = new Function(nmCode + '; return NetworkManager;');
const NetworkManagerClass = nmFn();
eval(peersUiCode);
eval(peersMgrCode);

async function runTests() {
    console.log("Running Peers & Mesh Presence JS unit tests...");

    // Test 1: Local node info and metadata
    const nm = new NetworkManagerClass();
    nm.dependencies = {
        UserManager: { getCurrentUser: () => ({ username: 'alice', name: 'Alice' }) },
        EnvironmentManager: { get: () => 'fractal-pi' }
    };
    nm.isNetworkingEnabled = true;

    const localInfo = nm.getLocalNodeInfo();
    assert.strictEqual(localInfo.id, nm.getInstanceId());
    assert(localInfo.user.includes('fractal-pi'), "User host string formatted");
    assert(localInfo.capabilities.includes('shell'), "Capabilities listed");
    assert(localInfo.capabilities.includes('netgame'), "Netgame capability listed");
    console.log("ok 1 - NetworkManager getLocalNodeInfo");

    // Test 2: Peer discovery and metadata tracking
    nm._handleDiscover({
        sourceId: 'node-beta',
        data: {
            user: 'bob@workstation',
            capabilities: ['shell', 'mesh-cp', 'netgame'],
            uptime: 120
        }
    });

    assert(nm.getRemoteInstances().includes('node-beta'), "Peer registered in remoteInstances");
    const peerMeta = nm.peerMetadata.get('node-beta');
    assert.strictEqual(peerMeta.user, 'bob@workstation');
    console.log("ok 2 - NetworkManager peer metadata caching");

    // Test 3: getPeersDetailed
    const peersList = await nm.getPeersDetailed({ doPing: false });
    assert.strictEqual(peersList.length, 1);
    assert.strictEqual(peersList[0].id, 'node-beta');
    assert.strictEqual(peersList[0].user, 'bob@workstation');
    assert.strictEqual(peersList[0].transport, 'BroadcastChannel');
    console.log("ok 3 - NetworkManager getPeersDetailed");

    // Test 4: getPeerInfo specific lookup
    const infoFound = await nm.getPeerInfo('node-beta');
    assert.notStrictEqual(infoFound, null);
    assert.strictEqual(infoFound.id, 'node-beta');

    const infoMissing = await nm.getPeerInfo('non-existent');
    assert.strictEqual(infoMissing, null);
    console.log("ok 4 - NetworkManager getPeerInfo");

    // Test 5: PeersUI rendering
    const mockDeps = {
        Utils: {
            createElement: (tag, attrs, children) => createMockElement(tag, attrs, children)
        },
        UIComponents: {
            createAppWindow: (title, onExit) => {
                const header = createMockElement('header');
                const main = createMockElement('main');
                const footer = createMockElement('footer');
                const container = createMockElement('div', {}, [header, main, footer]);
                return { container, header, main, footer };
            }
        },
        NetworkManager: nm,
        AppLayerManager: { hide: () => {} }
    };

    const ui = new global.PeersUI({ onExit: () => {}, onRefresh: () => {} }, mockDeps);
    ui.render(localInfo, peersList);

    assert(ui.elements.tbody.children.length === 1, "Renders 1 peer row");
    console.log("ok 5 - PeersUI table rendering");

    // Test 6: PeersManager lifecycle
    const mgr = new global.PeersManager();
    const appLayer = createMockElement('div');
    mockDeps.PeersUI = global.PeersUI;

    await mgr.enter(appLayer, { dependencies: mockDeps, doPing: false });
    assert(mgr.isActive, "PeersManager should be active");
    assert(mgr.pollInterval !== null, "Polling interval initialized");

    mgr.exit();
    assert(!mgr.isActive, "PeersManager should be inactive after exit");
    assert.strictEqual(mgr.pollInterval, null, "Polling interval cleared");
    console.log("ok 6 - PeersManager lifecycle and polling management");

    console.log("\nALL 6 PEERS & MESH PRESENCE JS UNIT TESTS PASSED!");
}

runTests().then(() => {
    process.exit(0);
}).catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
