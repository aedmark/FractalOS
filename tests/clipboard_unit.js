const assert = require("assert");
const fs = require("fs");
const path = require("path");

// Load ClipboardManager code into global scope
const clipboardCode = fs.readFileSync(path.join(__dirname, "../resources/scripts/clipboard_manager.js"), "utf8");
global.window = global;
eval(clipboardCode);

async function runTests() {
    console.log("Running clipboard_unit.js...");

    const cm = new global.ClipboardManager();

    // 1. Initial status
    let status = cm.getStatus();
    assert.strictEqual(status.hasMemoryBuffer, false);
    assert.strictEqual(status.bufferLength, 0);
    console.log("ok   initial status is empty");

    // 2. Copy and Paste via fallback buffer
    const copyRes = await cm.copy("Hello FractalOS Clipboard!");
    assert.strictEqual(copyRes.success, true);
    assert.strictEqual(copyRes.length, 26);
    assert.strictEqual(copyRes.text, "Hello FractalOS Clipboard!");

    status = cm.getStatus();
    assert.strictEqual(status.hasMemoryBuffer, true);
    assert.strictEqual(status.bufferLength, 26);

    const pasted = await cm.paste();
    assert.strictEqual(pasted, "Hello FractalOS Clipboard!");
    console.log("ok   copy and paste works via fallback buffer");

    // 3. Clear buffer
    cm.clear();
    status = cm.getStatus();
    assert.strictEqual(status.hasMemoryBuffer, false);
    assert.strictEqual(status.bufferLength, 0);
    const pastedEmpty = await cm.paste();
    assert.strictEqual(pastedEmpty, "");
    console.log("ok   clear resets clipboard buffer");

    // 4. File import simulation
    const mockFiles = [
        { name: "test1.txt", size: 12, content: "hello test 1" },
        { name: "data.json", size: 20, content: '{"status":"ok"}' }
    ];

    const vfsStore = {};
    const mockFsManager = {
        getCurrentPath: () => "/home/Guest",
        createOrUpdateFile: async (filePath, content) => {
            vfsStore[filePath] = content;
            return { success: true };
        },
        getFsData: async () => ({ vfs: vfsStore })
    };

    const mockOutput = [];
    const mockOutputManager = {
        appendToOutput: async (txt) => { mockOutput.push(txt); }
    };

    const mockNotifications = [];
    const mockStatusBar = {
        notify: (txt, opts) => { mockNotifications.push({ txt, opts }); }
    };

    cm.setDependencies({
        FileSystemManager: mockFsManager,
        OutputManager: mockOutputManager,
        StatusBarManager: mockStatusBar,
        SoundManager: { isMuted: true }
    });

    // Mock FileReader on global
    global.FileReader = class {
        readAsText(file) {
            setTimeout(() => {
                this.result = file.content;
                if (this.onload) this.onload();
            }, 0);
        }
    };

    const importRes = await cm.importFiles(mockFiles);
    assert.strictEqual(importRes.success, true);
    assert.strictEqual(importRes.imported.length, 2);
    assert.strictEqual(vfsStore["/home/Guest/test1.txt"], "hello test 1");
    assert.strictEqual(vfsStore["/home/Guest/data.json"], '{"status":"ok"}');
    assert.strictEqual(mockNotifications.length, 1);
    assert(mockNotifications[0].txt.includes("Imported 2 files"));
    console.log("ok   drag-and-drop file import into VFS works");

    console.log("ALL CLIPBOARD UNIT TESTS PASSED");
}

runTests().catch(err => {
    console.error("FAIL:", err);
    process.exit(1);
});
