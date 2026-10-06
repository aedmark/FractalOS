/**
 * tests/netgame_unit.js - Unit tests for Netgame network coordination and UI app logic.
 */

const assert = require('assert');

// Mock browser globals for Node test environment
global.window = global;
global.window.addEventListener = () => {};
global.BroadcastChannel = class {
    constructor(name) { this.name = name; }
    postMessage() {}
    close() {}
};

// Minimal DOM mock
function createMockElement(tag, attrs = {}, children = []) {
    const el = {
        tagName: tag.toUpperCase(),
        className: attrs.className || '',
        id: attrs.id || '',
        textContent: attrs.textContent || '',
        style: attrs.style || {},
        children: [...children],
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
    createElement: (tag) => createMockElement(tag),
    createTextNode: (txt) => ({ text: txt })
};

// Mock App base class
global.App = class App {
    constructor() { this.isActive = false; }
    enter() {}
    exit() {}
};

// Load NetworkManager
const fs = require('fs');
const path = require('path');

const nmCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/network_manager.js'), 'utf8');
const netgameUiCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/apps/netgame/netgame_ui.js'), 'utf8');
const netgameMgrCode = fs.readFileSync(path.join(__dirname, '../resources/scripts/apps/netgame/netgame_manager.js'), 'utf8');

const nmFn = new Function(nmCode + '; return NetworkManager;');
const NetworkManagerClass = nmFn();
eval(netgameUiCode);
eval(netgameMgrCode);

async function runTests() {
    console.log("Running Netgame JS unit tests...");

    // Test 1: NetworkManager game message handling
    const nm = new NetworkManagerClass();
    let lastOutput = "";
    let tonesPlayed = [];

    nm.dependencies = {
        OutputManager: {
            appendToOutput: async (txt) => { lastOutput = txt; }
        },
        SoundManager: {
            isInitialized: true,
            playNote: (n) => { tonesPlayed.push(n); },
            playTone: (t) => { tonesPlayed.push(t); }
        }
    };
    nm.isNetworkingEnabled = true;

    // Receive invite
    await nm._handleMeshGame({
        sourceId: 'peer-alpha',
        data: { action: 'invite', gameType: 'c4' }
    });
    assert(lastOutput.includes("peer-alpha"), "Output should mention peer");
    assert(lastOutput.includes("Connect 4"), "Output should mention Connect 4");
    assert(tonesPlayed.length > 0, "Should have triggered audio cue");
    console.log("ok 1 - NetworkManager invite handling");

    // Receive accept
    await nm._handleMeshGame({
        sourceId: 'peer-alpha',
        data: { action: 'accept', guestName: 'Alice' }
    });
    assert(lastOutput.includes("accepted"), "Output should acknowledge accept");
    console.log("ok 2 - NetworkManager accept handling");

    // Receive remote move
    await nm._handleMeshGame({
        sourceId: 'peer-alpha',
        data: { action: 'move', gameType: 'c4', move: 4, board: [], turn: 'O', winner: null }
    });
    assert(lastOutput.includes("played:") && lastOutput.includes("4"), "Output should report move");
    console.log("ok 3 - NetworkManager move handling in terminal mode");

    // Receive resign
    await nm._handleMeshGame({
        sourceId: 'peer-alpha',
        data: { action: 'resign' }
    });
    assert(lastOutput.includes("resigned"), "Output should report resign");
    console.log("ok 4 - NetworkManager resign handling");

    // Test 2: NetgameUI and Manager
    const mockDeps = {
        Utils: {
            createElement: (tag, attrs, children) => createMockElement(tag, attrs, children)
        },
        UIComponents: {
            createAppWindow: (title, onExit) => {
                const header = createMockElement('header');
                const titleEl = createMockElement('h2', { className: 'app-header__title', textContent: title });
                header.appendChild(titleEl);
                const main = createMockElement('main');
                const footer = createMockElement('footer');
                const container = createMockElement('div', {}, [header, main, footer]);
                return { container, header, main, footer };
            }
        },
        SoundManager: {
            isMuted: false,
            playSequence: () => {},
            playTone: () => {}
        },
        AppLayerManager: {
            hide: () => {}
        },
        NetworkManager: nm,
        NetgameUI: global.NetgameUI
    };

    const mgr = new NetgameManager();
    const appLayer = createMockElement('div');
    await mgr.enter(appLayer, {
        dependencies: mockDeps,
        session: {
            gameType: 'c4',
            board: [
                ['.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.']
            ],
            turn: 'X',
            p1: 'Me',
            p2: 'Bob',
            my_symbol: 'X',
            winner: null,
            moves: []
        }
    });

    assert(mgr.isActive, "Manager should be active");
    assert.strictEqual(nm.activeGameApp, mgr, "NetworkManager should register activeGameApp");
    console.log("ok 5 - NetgameManager lifecycle and registration");

    // Test remote move delivered to active app
    mgr.handleRemoteMove({
        move: 4,
        turn: 'X',
        board: [
            ['.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', 'O', '.', '.', '.']
        ]
    });
    assert.strictEqual(mgr.session.turn, 'X');
    assert.strictEqual(mgr.session.moves.length, 1);
    console.log("ok 6 - NetgameManager receives and applies remote move");

    // Exit app
    mgr.exit();
    assert(!mgr.isActive, "Manager should be inactive after exit");
    assert.strictEqual(nm.activeGameApp, null, "NetworkManager activeGameApp cleared");
    console.log("ok 7 - NetgameManager cleanly unregisters on exit");

    console.log("\nALL 7 NETGAME JS UNIT TESTS PASSED!");
}

runTests().then(() => {
    process.exit(0);
}).catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
