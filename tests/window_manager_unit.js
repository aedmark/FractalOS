// tests/window_manager_unit.js
// Unit tests for P7-10: TUI Window Management & WindowManager

const assert = require('assert');

// Mock DOM elements
function createMockElement(tagName = 'div', className = '', id = '') {
    const el = {
        tagName: tagName.toUpperCase(),
        className,
        id,
        style: {},
        dataset: {},
        classList: {
            classes: new Set(className ? className.split(' ') : []),
            add(...tokens) { tokens.forEach(t => this.classes.add(t)); el.className = Array.from(this.classes).join(' '); },
            remove(...tokens) { tokens.forEach(t => this.classes.delete(t)); el.className = Array.from(this.classes).join(' '); },
            contains(c) { return this.classes.has(c); }
        },
        children: [],
        childNodes: [],
        parentNode: null,
        appendChild(child) {
            this.children.push(child);
            this.childNodes.push(child);
            child.parentNode = this;
            return child;
        },
        removeChild(child) {
            const idx = this.children.indexOf(child);
            if (idx !== -1) {
                this.children.splice(idx, 1);
                this.childNodes.splice(idx, 1);
                child.parentNode = null;
            }
            return child;
        },
        querySelector(sel) {
            if (sel.startsWith('.')) {
                const cls = sel.slice(1).split(',')[0].trim();
                for (const c of this.children) {
                    if (c.classList && c.classList.contains(cls)) return c;
                    const nested = c.querySelector?.(sel);
                    if (nested) return nested;
                }
            }
            return null;
        },
        querySelectorAll(sel) {
            const res = [];
            if (sel.startsWith('.')) {
                const cls = sel.slice(1);
                for (const c of this.children) {
                    if (c.classList && c.classList.contains(cls)) res.push(c);
                    if (c.querySelectorAll) res.push(...c.querySelectorAll(sel));
                }
            }
            return res;
        },
        addEventListener(evt, handler) {
            this._listeners = this._listeners || {};
            this._listeners[evt] = this._listeners[evt] || [];
            this._listeners[evt].push(handler);
        },
        dispatchEvent(evt) {
            if (this._listeners?.[evt.type]) {
                for (const h of this._listeners[evt.type]) h(evt);
            }
        },
        getBoundingClientRect() {
            return { top: 0, left: 0, width: 1000, height: 700 };
        },
        focus() { this._focused = true; }
    };
    return el;
}

// Global browser environment mocks
global.window = {
    innerWidth: 1024,
    innerHeight: 768,
    document: {
        createElement: (tag) => createMockElement(tag),
        getElementById: () => null,
        addEventListener: () => {},
        removeEventListener: () => {}
    }
};
global.document = global.window.document;

// Load WindowManager
require('../resources/scripts/window_manager.js');
const WindowManager = window.WindowManager;

console.log("Running P7-10 TUI Window Manager JS unit tests...");

// Setup DOM mocks
const terminalDiv = createMockElement('div', 'terminal', 'terminal');
const appLayer = createMockElement('div', 'hidden', 'app-layer');
const outputDiv = createMockElement('div', 'terminal__output', 'output');
const windowDock = createMockElement('div', 'window-dock hidden', 'window-dock');
terminalDiv.appendChild(outputDiv);
terminalDiv.appendChild(appLayer);
terminalDiv.appendChild(windowDock);

const domElements = {
    terminalDiv,
    appLayer,
    outputDiv,
    windowDock
};

const mockTerminalUI = {
    showInputLine: () => { mockTerminalUI.inputShown = true; },
    setInputState: (s) => { mockTerminalUI.inputState = s; },
    focusInput: () => { mockTerminalUI.inputFocused = true; }
};

const mockOutputManager = {
    setEditorActive: (s) => { mockOutputManager.editorActive = s; }
};

const wm = new WindowManager();
wm.initialize(domElements);
wm.setDependencies({
    TerminalUI: mockTerminalUI,
    OutputManager: mockOutputManager
});

// Test 1: WindowManager initialization
assert.strictEqual(wm.windows.size, 0, "No windows on init");
assert.strictEqual(wm.isTerminalFocused, true, "Terminal initially focused");
console.log("ok 1 - WindowManager initialized in clean state");

// Mock App class
class MockApp {
    constructor(title = "Test App") {
        this.title = title;
        this.isActive = false;
        this.container = null;
    }
    enter(layer, options = {}) {
        this.isActive = true;
        this.container = createMockElement('div', 'app-container', 'test-app-container');
        const header = createMockElement('header', 'app-header');
        const titleEl = createMockElement('h2', 'app-header__title');
        titleEl.textContent = this.title;
        header.appendChild(titleEl);
        this.container.appendChild(header);
        layer.appendChild(this.container);
    }
    exit() {
        this.isActive = false;
    }
}

// Test 2: openWindow creates floating window by default
const app1 = new MockApp("FractalOS Editor");
const win1 = wm.openWindow(app1);

assert.strictEqual(wm.windows.size, 1, "One window registered");
assert.strictEqual(win1.id, "win-1", "Window assigned win-1 ID");
assert.strictEqual(win1.mode, "floating", "Default mode is floating");
assert.strictEqual(appLayer.classList.contains("hidden"), false, "app-layer visible");
assert.strictEqual(appLayer.classList.contains("app-layer--floating"), true, "app-layer--floating active");
assert.strictEqual(win1.container.classList.contains("window--floating"), true, "window--floating applied");
assert.strictEqual(wm.isAppFocused(), true, "New window has focus");
console.log("ok 2 - openWindow creates floating window and activates focus");

// Test 3: Docking mode transitions (docked-right, docked-left, docked-bottom)
const dockRes = wm.setWindowMode(win1.id, "docked-right");
assert.strictEqual(dockRes.success, true, "setWindowMode succeeded");
assert.strictEqual(win1.mode, "docked-right", "Mode updated to docked-right");
assert.strictEqual(terminalDiv.classList.contains("terminal--docked-right"), true, "terminal--docked-right applied");
assert.strictEqual(appLayer.classList.contains("app-layer--docked-right"), true, "app-layer--docked-right applied");
assert.strictEqual(win1.container.classList.contains("window--docked-right"), true, "window--docked-right applied");

wm.setWindowMode(win1.id, "docked-left");
assert.strictEqual(terminalDiv.classList.contains("terminal--docked-left"), true, "terminal--docked-left applied");
assert.strictEqual(terminalDiv.classList.contains("terminal--docked-right"), false, "terminal--docked-right cleared");

wm.setWindowMode(win1.id, "docked-bottom");
assert.strictEqual(terminalDiv.classList.contains("terminal--docked-bottom"), true, "terminal--docked-bottom applied");
console.log("ok 3 - Docking modes split terminal and window viewports cleanly");

// Test 4: Switching back to floating restores bounds and removes terminal dock classes
wm.setWindowMode(win1.id, "floating");
assert.strictEqual(win1.mode, "floating", "Mode restored to floating");
assert.strictEqual(terminalDiv.classList.contains("terminal--docked-bottom"), false, "terminal docking classes cleared");
assert.strictEqual(appLayer.classList.contains("app-layer--floating"), true, "app-layer floating class restored");
console.log("ok 4 - Floating mode restores free window positioning");

// Test 5: Minimizing and restoring window
wm.minimizeWindow(win1.id);
assert.strictEqual(win1.isMinimized, true, "Window marked minimized");
assert.strictEqual(win1.container.style.display, "none", "Window hidden from display");
assert.strictEqual(wm.isTerminalFocused, true, "Focus reverted to terminal on minimize");

wm.restoreWindow(win1.id);
assert.strictEqual(win1.isMinimized, false, "Window unminimized");
assert.strictEqual(win1.container.style.display, "", "Window display restored");
assert.strictEqual(wm.isAppFocused(), true, "Window focused on restore");
console.log("ok 5 - Minimize and restore cycle works cleanly");

// Test 6: Multiple concurrent windows & tiling
const app2 = new MockApp("Process Viewer");
const win2 = wm.openWindow(app2, { windowMode: "floating" });

assert.strictEqual(wm.windows.size, 2, "Two open windows");
assert.strictEqual(wm.activeWindowId, win2.id, "Second window active");
assert.strictEqual(win2.container.classList.contains("window--active"), true, "win-2 active");
assert.strictEqual(win1.container.classList.contains("window--inactive"), true, "win-1 inactive");

// Focus win-1
wm.focusWindow(win1.id);
assert.strictEqual(wm.activeWindowId, win1.id, "win-1 active");
assert.strictEqual(win1.container.classList.contains("window--active"), true, "win-1 active");
assert.strictEqual(win2.container.classList.contains("window--inactive"), true, "win-2 inactive");

// Focus terminal
wm.focusTerminal();
assert.strictEqual(wm.isTerminalFocused, true, "Terminal focused");
assert.strictEqual(wm.isAppFocused(), false, "App not focused when terminal active");
assert.strictEqual(mockTerminalUI.inputFocused, true, "Terminal input focused");

// Tile both windows
wm.tileWindows();
assert.strictEqual(win1.mode, "floating", "win-1 tiled");
assert.strictEqual(win2.mode, "floating", "win-2 tiled");
assert.notStrictEqual(win1.bounds.left, win2.bounds.left, "Windows placed at separate columns");
console.log("ok 6 - Multiple windows, focus toggling, and tiling validated");

// Test 7: Closing windows cleans up DOM and resets state
wm.closeWindow(win2.id);
assert.strictEqual(wm.windows.size, 1, "One window remaining");
assert.strictEqual(wm.activeWindowId, win1.id, "Remaining window focused");

wm.closeWindow(win1.id);
assert.strictEqual(wm.windows.size, 0, "All windows closed");
assert.strictEqual(wm.activeWindowId, null, "Active window null");
assert.strictEqual(appLayer.classList.contains("hidden"), true, "appLayer hidden when all closed");
assert.strictEqual(wm.isTerminalFocused, true, "Terminal has sole focus");
console.log("ok 7 - Window closing cleans up state and DOM");

console.log("\nALL 7 TUI WINDOW MANAGER JS UNIT TESTS PASSED!\n");
