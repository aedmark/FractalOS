// tests/status_bar_unit.js
// Unit tests for P7-11: Persistent Status & Notification Bar (StatusBarManager)

const assert = require('assert');

// Mock DOM elements
function createMockElement(tagName = 'div', className = '', id = '') {
    const el = {
        tagName: tagName.toUpperCase(),
        className,
        id,
        style: {},
        innerHTML: '',
        textContent: '',
        classList: {
            classes: new Set(className ? className.split(' ') : []),
            add(...tokens) { tokens.forEach(t => this.classes.add(t)); el.className = Array.from(this.classes).join(' '); },
            remove(...tokens) { tokens.forEach(t => this.classes.delete(t)); el.className = Array.from(this.classes).join(' '); },
            toggle(c, force) {
                if (force !== undefined) {
                    if (force) this.add(c); else this.remove(c);
                    return force;
                }
                if (this.classes.has(c)) { this.remove(c); return false; }
                this.add(c); return true;
            },
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
        insertBefore(newNode, refNode) {
            const idx = this.children.indexOf(refNode);
            if (idx === -1) {
                return this.appendChild(newNode);
            }
            this.children.splice(idx, 0, newNode);
            this.childNodes.splice(idx, 0, newNode);
            newNode.parentNode = this;
            return newNode;
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
            if (sel.startsWith('#')) {
                const targetId = sel.slice(1);
                return findById(this, targetId);
            }
            if (sel.startsWith('.')) {
                const cls = sel.slice(1).split(',')[0].trim();
                return findByClass(this, cls);
            }
            return null;
        },
        querySelectorAll(sel) {
            const res = [];
            if (sel.startsWith('.')) {
                const cls = sel.slice(1);
                findAllByClass(this, cls, res);
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
        }
    };
    return el;
}

function findById(root, id) {
    if (root.id === id) return root;
    for (const c of root.children) {
        const found = findById(c, id);
        if (found) return found;
    }
    return null;
}

function findByClass(root, cls) {
    for (const c of root.children) {
        if (c.classList && c.classList.contains(cls)) return c;
        const found = findByClass(c, cls);
        if (found) return found;
    }
    return null;
}

function findAllByClass(root, cls, acc) {
    for (const c of root.children) {
        if (c.classList && c.classList.contains(cls)) acc.push(c);
        findAllByClass(c, cls, acc);
    }
}

// Global browser environment mocks
const allElements = new Map();
global.window = {
    innerWidth: 1024,
    innerHeight: 768,
    document: {
        createElement: (tag) => {
            const el = createMockElement(tag);
            return el;
        },
        getElementById: (id) => allElements.get(id) || null,
        addEventListener: () => {},
        removeEventListener: () => {}
    }
};
global.document = global.window.document;

// Load StatusBarManager
require('../resources/scripts/status_bar_manager.js');
const StatusBarManager = window.StatusBarManager;

console.log("Running P7-11 Status & Notification Bar JS unit tests...");

// Setup DOM mocks
const terminalDiv = createMockElement('div', 'terminal', 'terminal');
allElements.set('terminal', terminalDiv);

const mockSoundManager = {
    isMuted: false,
    toggleMute() { this.isMuted = !this.isMuted; return this.isMuted; },
    setMute(val) { this.isMuted = !!val; return this.isMuted; },
    playNote(note, dur) { mockSoundManager.playedNote = { note, dur }; }
};

const mockFileSystemManager = {
    getCurrentPath: () => "/home/Guest/projects"
};

const mockMultiplexerManager = {
    getPanes: () => [{ id: "pane-1" }, { id: "pane-2" }]
};

const mockNetworkManager = {
    peers: new Map([["peer-1", {}], ["peer-2", {}]])
};

const sbm = new StatusBarManager();
sbm.setDependencies({
    SoundManager: mockSoundManager,
    FileSystemManager: mockFileSystemManager,
    MultiplexerManager: mockMultiplexerManager,
    NetworkManager: mockNetworkManager
});

// Helper to register inner elements created via innerHTML
const origInit = sbm.initialize.bind(sbm);
sbm.initialize = function(dom) {
    const bar = createMockElement('div', 'status-bar', 'status-bar');
    dom.terminalDiv.appendChild(bar);
    dom.statusBar = bar;
    allElements.set('status-bar', bar);

    const ids = [
        'status-bar-user', 'status-bar-cwd', 'status-bar-panes', 'status-bar-jobs',
        'status-bar-ticker', 'status-bar-agent', 'status-bar-mesh', 'status-bar-audio',
        'status-bar-bell', 'status-bar-badge', 'status-bar-clock',
        'notification-drawer', 'notification-drawer-clear', 'notification-drawer-list'
    ];
    for (const id of ids) {
        const el = createMockElement('span', '', id);
        bar.appendChild(el);
        allElements.set(id, el);
    }

    const ticker = allElements.get('status-bar-ticker');
    ticker.appendChild(createMockElement('span', 'status-bar__ticker-icon'));
    ticker.appendChild(createMockElement('span', 'status-bar__ticker-text'));

    this.domElements = dom;
    this.update();
};

sbm.initialize({ terminalDiv });

// Test 1: Initialization
assert.strictEqual(sbm.isVisible, true, "StatusBarManager initially visible");
assert.strictEqual(sbm.notifications.length, 0, "No notifications on init");
assert.strictEqual(sbm.unreadCount, 0, "0 unread count on init");
console.log("ok 1 - StatusBarManager initialized cleanly");

// Test 2: Notification delivery
const n1 = sbm.notify("Connection established", { level: "success" });
assert.strictEqual(sbm.notifications.length, 1, "Notification added to queue");
assert.strictEqual(sbm.unreadCount, 1, "Unread count incremented");
assert.strictEqual(n1.text, "Connection established");
assert.strictEqual(n1.level, "success");
assert.strictEqual(mockSoundManager.playedNote.note, "G5", "Success tone triggered");
console.log("ok 2 - Notification logged and sound emitted");

// Test 3: Multiple notifications and unread tracking
sbm.notify("Warning: high voltage", { level: "warn" });
sbm.notify("Critical swarm alert", { level: "error" });
assert.strictEqual(sbm.notifications.length, 3, "3 notifications in history");
assert.strictEqual(sbm.unreadCount, 3, "3 unread notifications");
console.log("ok 3 - Multiple notification levels and counters tracked");

// Test 4: Notification drawer open and mark as read
sbm.openDrawer();
assert.strictEqual(sbm.isDrawerOpen, true, "Drawer is open");
assert.strictEqual(sbm.unreadCount, 0, "Unread count reset on drawer open");
assert.strictEqual(sbm.notifications[0].read, true, "Notifications marked read");

sbm.closeDrawer();
assert.strictEqual(sbm.isDrawerOpen, false, "Drawer closed");
console.log("ok 4 - Notification drawer open/close and read receipt functioning");

// Test 5: Sound mute toggle and status bar integration
assert.strictEqual(mockSoundManager.isMuted, false, "Initially unmuted");
mockSoundManager.toggleMute();
assert.strictEqual(mockSoundManager.isMuted, true, "Muted after toggle");
sbm.update();
assert.strictEqual(allElements.get('status-bar-audio').textContent, "🔇", "Audio button displays muted icon");

mockSoundManager.toggleMute();
assert.strictEqual(mockSoundManager.isMuted, false, "Unmuted after second toggle");
sbm.update();
assert.strictEqual(allElements.get('status-bar-audio').textContent, "🔊", "Audio button displays unmuted icon");
console.log("ok 5 - Audio mute toggle and UI indicator verified");

// Test 6: Status summary reporting
const summary = sbm.getStatusSummary();
assert.strictEqual(summary.isVisible, true, "Summary reports visibility");
assert.strictEqual(summary.cwd, "/home/Guest/projects", "Summary reports cwd");
assert.strictEqual(summary.panesCount, 2, "Summary reports 2 panes");
assert.strictEqual(summary.peerCount, 2, "Summary reports 2 peers");
assert.strictEqual(summary.isMuted, false, "Summary reports audio unmuted");
assert.strictEqual(summary.totalNotifications, 3, "Summary reports 3 total notifications");
console.log("ok 6 - getStatusSummary accurately reports system metrics");

// Test 7: Visibility toggle and notification clearing
sbm.setVisible(false);
assert.strictEqual(sbm.isVisible, false, "Status bar hidden");

sbm.setVisible(true);
assert.strictEqual(sbm.isVisible, true, "Status bar shown");

sbm.clearNotifications();
assert.strictEqual(sbm.notifications.length, 0, "Notifications cleared");
assert.strictEqual(sbm.unreadCount, 0, "Unread count 0 after clear");
console.log("ok 7 - Visibility and clearNotifications verified");

console.log("\nALL 7 STATUS BAR & NOTIFICATION JS UNIT TESTS PASSED!\n");
