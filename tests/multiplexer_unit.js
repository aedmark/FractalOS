/**
 * tests/multiplexer_unit.js - Unit tests for Terminal Multiplexer & Split Panes (P7-09).
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock DOM element factory
function createMockElement(tag, className = '') {
    const classSet = new Set(className.split(' ').filter(Boolean));
    const children = [];
    const listeners = {};
    const attrs = {};

    const el = {
        tagName: tag.toUpperCase(),
        className: className,
        classList: {
            add: (c) => { classSet.add(c); el.className = Array.from(classSet).join(' '); },
            remove: (c) => { classSet.delete(c); el.className = Array.from(classSet).join(' '); },
            contains: (c) => classSet.has(c),
            toggle: (c) => {
                if (classSet.has(c)) classSet.delete(c); else classSet.add(c);
                el.className = Array.from(classSet).join(' ');
            }
        },
        children,
        style: {},
        textContent: '',
        innerHTML: '',
        contentEditable: 'false',
        setAttribute: (k, v) => { attrs[k] = v; },
        getAttribute: (k) => attrs[k] || null,
        appendChild: (child) => {
            children.push(child);
            child.parentElement = el;
            return child;
        },
        insertBefore: (newNode, refNode) => {
            const idx = children.indexOf(refNode);
            if (idx >= 0) children.splice(idx, 0, newNode);
            else children.push(newNode);
            newNode.parentElement = el;
            return newNode;
        },
        remove: () => {
            if (el.parentElement) {
                const idx = el.parentElement.children.indexOf(el);
                if (idx >= 0) el.parentElement.children.splice(idx, 1);
                el.parentElement = null;
            }
        },
        querySelector: (sel) => {
            if (sel.startsWith('.')) {
                const targetClass = sel.substring(1);
                const findIn = (node) => {
                    if (node.classList?.contains(targetClass)) return node;
                    for (const c of node.children) {
                        const found = findIn(c);
                        if (found) return found;
                    }
                    return null;
                };
                return findIn(el);
            }
            return null;
        },
        querySelectorAll: () => [],
        addEventListener: (evt, handler) => {
            if (!listeners[evt]) listeners[evt] = [];
            listeners[evt].push(handler);
        },
        dispatchEvent: (evt) => {
            const list = listeners[evt.type] || [];
            list.forEach(h => h(evt));
        },
        focus: () => {},
        blur: () => {},
        scrollTop: 0,
        scrollHeight: 100
    };
    return el;
}

global.document = {
    createElement: (tag) => createMockElement(tag),
    getElementById: (id) => createMockElement('div')
};
global.window = {};

const muxCode = fs.readFileSync(path.join(__dirname, '..', 'resources', 'scripts', 'multiplexer_manager.js'), 'utf8');
const MultiplexerManager = new Function(
    'module', 'exports',
    `${muxCode}; return MultiplexerManager;`
)({}, {});

async function runTests() {
    console.log("Running P7-09 Terminal Multiplexer JS unit tests...");

    // Setup initial DOM
    const terminalDiv = createMockElement('div', 'terminal');
    const outputDiv = createMockElement('div', 'terminal__output');
    const inputLineContainerDiv = createMockElement('div', 'terminal__input-line');
    const promptContainer = createMockElement('div', 'terminal__prompt');
    const editableInputDiv = createMockElement('div', 'terminal__input');
    editableInputDiv.contentEditable = 'true';
    const appLayer = createMockElement('div', 'app-layer');

    terminalDiv.appendChild(outputDiv);
    inputLineContainerDiv.appendChild(promptContainer);
    inputLineContainerDiv.appendChild(editableInputDiv);
    terminalDiv.appendChild(inputLineContainerDiv);
    terminalDiv.appendChild(appLayer);

    const domElements = {
        terminalDiv,
        outputDiv,
        inputLineContainerDiv,
        promptContainer,
        editableInputDiv,
        appLayer
    };

    let currentPath = '/home/Guest';
    const mockFsManager = {
        getCurrentPath: () => currentPath,
        setCurrentPath: (p) => { currentPath = p; }
    };

    const mockTerminalUI = {
        elements: { ...domElements },
        updatePrompt: async () => {},
        focusInput: () => {},
        scrollOutputToEnd: () => {}
    };

    const mockOutputManager = {
        cachedOutputDiv: outputDiv,
        appendToOutput: async () => {}
    };

    const dependencies = {
        FileSystemManager: mockFsManager,
        TerminalUI: mockTerminalUI,
        OutputManager: mockOutputManager,
        UserManager: { getCurrentUser: () => ({ username: 'Guest' }) },
        Config: {
            USER: { DEFAULT_NAME: 'Guest' },
            OS: { DEFAULT_HOST_NAME: 'fractal' }
        }
    };

    const mux = new MultiplexerManager();
    mux.setDependencies(dependencies);
    mux.initialize(domElements);

    // Test 1: Initial state has 1 pane
    assert.strictEqual(mux.panes.size, 1);
    assert.strictEqual(mux.activePaneId, 'pane-1');
    assert.strictEqual(mux.isMultiplexing, false);
    console.log("ok 1 - Multiplexer initialized in single-pane mode");

    // Test 2: Split vertical creates pane-2
    const splitRes = await mux.split('vertical');
    assert.strictEqual(splitRes.success, true);
    assert.strictEqual(splitRes.paneId, 'pane-2');
    assert.strictEqual(mux.panes.size, 2);
    assert.strictEqual(mux.activePaneId, 'pane-2');
    assert.strictEqual(mux.isMultiplexing, true);

    const panesList = mux.listPanes();
    assert.strictEqual(panesList.length, 2);
    assert.strictEqual(panesList[0].id, 'pane-1');
    assert.strictEqual(panesList[1].id, 'pane-2');
    assert.strictEqual(panesList[1].active, true);
    console.log("ok 2 - Vertical split creates second pane and sets focus");

    // Test 3: Independent CWDs per pane
    // Set pane-2's CWD to /etc
    mockFsManager.setCurrentPath('/etc');
    await mux.focusPane('pane-1');
    // Switching back to pane-1 should save /etc in pane-2 and restore /home/Guest in pane-1
    assert.strictEqual(mux.getPane('pane-2').cwd, '/etc');
    assert.strictEqual(mockFsManager.getCurrentPath(), '/home/Guest');

    // Switch back to pane-2
    await mux.focusPane('pane-2');
    assert.strictEqual(mockFsManager.getCurrentPath(), '/etc');
    console.log("ok 3 - Independent working directories maintained across panes");

    // Test 4: Focus next and previous
    await mux.focusNext();
    assert.strictEqual(mux.activePaneId, 'pane-1');
    await mux.focusPrev();
    assert.strictEqual(mux.activePaneId, 'pane-2');
    console.log("ok 4 - focusNext and focusPrev cycle active panes");

    // Test 5: Horizontal split creates pane-3
    const splitHRes = await mux.split('horizontal');
    assert.strictEqual(splitHRes.success, true);
    assert.strictEqual(splitHRes.paneId, 'pane-3');
    assert.strictEqual(mux.panes.size, 3);
    assert.strictEqual(mux.activePaneId, 'pane-3');
    console.log("ok 5 - Horizontal split creates third pane");

    // Test 6: Toggle Zoom
    const zoomRes = mux.toggleZoom();
    assert.strictEqual(zoomRes.isZoomed, true);
    assert.strictEqual(mux.isZoomed, true);
    assert.strictEqual(mux.getPane('pane-3').paneElement.classList.contains('terminal-pane--zoomed'), true);

    const unzoomRes = mux.toggleZoom();
    assert.strictEqual(unzoomRes.isZoomed, false);
    assert.strictEqual(mux.isZoomed, false);
    console.log("ok 6 - toggleZoom zooms active pane and unzooms cleanly");

    // Test 7: Close pane
    const closeRes = await mux.closePane('pane-3');
    assert.strictEqual(closeRes.success, true);
    assert.strictEqual(mux.panes.size, 2);

    // Close pane-2
    const closeRes2 = await mux.closePane('pane-2');
    assert.strictEqual(closeRes2.success, true);
    assert.strictEqual(mux.panes.size, 1);
    assert.strictEqual(mux.activePaneId, 'pane-1');

    // Cannot close only remaining pane
    const closeLastRes = await mux.closePane('pane-1');
    assert.strictEqual(closeLastRes.success, false);
    assert.strictEqual(mux.panes.size, 1);
    console.log("ok 7 - closePane removes panes and preserves single remaining pane");

    console.log("\nALL 7 MULTIPLEXER JS UNIT TESTS PASSED!\n");
    process.exit(0);
}

runTests().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
