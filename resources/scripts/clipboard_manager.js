window.ClipboardManager = class ClipboardManager {
    constructor() {
        this.dependencies = {};
        this.domElements = {};
        this._memoryBuffer = "";
        this.isInitialized = false;
        this.overlayEl = null;
    }

    initialize(domElements) {
        this.domElements = domElements;
        const target = domElements.terminalBezel || domElements.terminalDiv || document.body;

        this.setupTerminalClipboard();
        this.setupDragAndDrop(target);
        this.isInitialized = true;
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    /**
     * Copy text to clipboard.
     * Tries Neutralino, then navigator.clipboard, then fallback memory buffer.
     */
    async copy(text) {
        this._memoryBuffer = String(text || "");

        let success = false;
        if (window.NL_PORT && typeof Neutralino !== "undefined" && Neutralino.clipboard?.writeText) {
            try {
                await Neutralino.clipboard.writeText(this._memoryBuffer);
                success = true;
            } catch (e) {
                // fallback
            }
        }

        if (!success && navigator.clipboard?.writeText) {
            try {
                await navigator.clipboard.writeText(this._memoryBuffer);
                success = true;
            } catch (e) {
                // fallback
            }
        }

        const len = this._memoryBuffer.length;
        if (this.dependencies?.StatusBarManager) {
            this.dependencies.StatusBarManager.notify(
                `✓ Copied ${len} character${len === 1 ? '' : 's'} to clipboard`,
                { level: "success", timeout: 3000 }
            );
        }

        return { success: true, length: len, text: this._memoryBuffer };
    }

    /**
     * Read text from clipboard.
     * Tries Neutralino, then navigator.clipboard, then fallback memory buffer.
     */
    async paste() {
        let text = null;

        if (window.NL_PORT && typeof Neutralino !== "undefined" && Neutralino.clipboard?.readText) {
            try {
                text = await Neutralino.clipboard.readText();
            } catch (e) {
                // fallback
            }
        }

        if (text === null && navigator.clipboard?.readText) {
            try {
                text = await navigator.clipboard.readText();
            } catch (e) {
                // fallback
            }
        }

        if (text === null) {
            text = this._memoryBuffer;
        }

        return text || "";
    }

    clear() {
        this._memoryBuffer = "";
        if (window.NL_PORT && typeof Neutralino !== "undefined" && Neutralino.clipboard?.writeText) {
            Neutralino.clipboard.writeText("");
        } else if (navigator.clipboard?.writeText) {
            navigator.clipboard.writeText("");
        }
        return true;
    }

    getStatus() {
        return {
            hasMemoryBuffer: this._memoryBuffer.length > 0,
            bufferLength: this._memoryBuffer.length,
            preview: this._memoryBuffer.slice(0, 40)
        };
    }

    /**
     * Set up terminal shortcuts:
     * - Ctrl+Shift+C: copy selection
     * - Ctrl+Shift+V: paste clipboard
     */
    setupTerminalClipboard() {
        document.addEventListener("keydown", async (e) => {
            // Ctrl+Shift+C -> Copy selection
            if (e.ctrlKey && e.shiftKey && (e.key === "C" || e.key === "c")) {
                const sel = window.getSelection();
                if (sel && sel.toString().length > 0) {
                    e.preventDefault();
                    await this.copy(sel.toString());
                }
            }

            // Ctrl+Shift+V -> Paste into active terminal input
            if (e.ctrlKey && e.shiftKey && (e.key === "V" || e.key === "v")) {
                const { TerminalUI } = this.dependencies;
                if (TerminalUI) {
                    e.preventDefault();
                    const text = await this.paste();
                    if (text) {
                        TerminalUI.handlePaste(text.replace(/\r?\n|\r/g, " "));
                    }
                }
            }
        });
    }

    /**
     * Set up drag and drop file import from host OS into the virtual file system.
     */
    setupDragAndDrop(targetElement) {
        if (!targetElement) return;

        // Build drag-drop overlay element
        let overlay = document.getElementById("drag-drop-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "drag-drop-overlay";
            overlay.className = "drag-drop-overlay hidden";
            overlay.innerHTML = `
                <div class="drag-drop-overlay__card">
                    <div class="drag-drop-overlay__icon">📥</div>
                    <div class="drag-drop-overlay__title">Drop files to import into FractalOS</div>
                    <div class="drag-drop-overlay__dest" id="drag-drop-dest">Destination: /home/Guest</div>
                    <div class="drag-drop-overlay__hint">Files will be saved into the current working directory</div>
                </div>
            `;
            targetElement.appendChild(overlay);
        }
        this.overlayEl = overlay;

        let dragCounter = 0;

        targetElement.addEventListener("dragenter", (e) => {
            e.preventDefault();
            dragCounter++;
            const { FileSystemManager } = this.dependencies;
            const destPath = FileSystemManager?.getCurrentPath ? FileSystemManager.getCurrentPath() : "/home/Guest";
            const destEl = document.getElementById("drag-drop-dest");
            if (destEl) destEl.textContent = `Destination: ${destPath}`;
            overlay.classList.remove("hidden");
        });

        targetElement.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
        });

        targetElement.addEventListener("dragleave", (e) => {
            e.preventDefault();
            dragCounter--;
            if (dragCounter <= 0) {
                dragCounter = 0;
                overlay.classList.add("hidden");
            }
        });

        targetElement.addEventListener("drop", async (e) => {
            e.preventDefault();
            dragCounter = 0;
            overlay.classList.add("hidden");

            const files = e.dataTransfer?.files;
            if (files && files.length > 0) {
                await this.importFiles(files);
            }
        });
    }

    /**
     * Import a FileList or array of File objects into the current VFS directory.
     */
    async importFiles(files, targetDirectory = null) {
        const { FileSystemManager, OutputManager, StatusBarManager, SoundManager } = this.dependencies;
        if (!FileSystemManager) return { success: false, error: "FileSystemManager not available" };

        const cwd = targetDirectory || (FileSystemManager.getCurrentPath ? FileSystemManager.getCurrentPath() : "/home/Guest");
        const imported = [];
        const errors = [];

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const cleanName = file.name.replace(/[^a-zA-Z0-9._\-]/g, "_");
            const destPath = cwd === "/" ? `/${cleanName}` : `${cwd}/${cleanName}`;

            try {
                const content = await this._readFileAsText(file);
                const writeRes = await FileSystemManager.createOrUpdateFile(destPath, content, {});

                if (writeRes?.success !== false) {
                    imported.push({ name: file.name, path: destPath, size: file.size });
                } else {
                    errors.push({ name: file.name, error: writeRes?.error?.message || "Write failed" });
                }
            } catch (err) {
                errors.push({ name: file.name, error: err.message });
            }
        }

        // Refresh VFS data
        if (FileSystemManager.getFsData) {
            await FileSystemManager.getFsData();
        }

        // Output and alert
        if (imported.length > 0) {
            const countStr = `${imported.length} file${imported.length === 1 ? '' : 's'}`;
            if (StatusBarManager) {
                StatusBarManager.notify(`✓ Imported ${countStr} into ${cwd}`, { level: "success" });
            }
            if (SoundManager && !SoundManager.isMuted) {
                SoundManager.playNote?.("G5", "16n");
            }
            if (OutputManager) {
                let report = `\x1b[1;32m[Import Bridge]\x1b[0m Successfully imported ${countStr} into \x1b[34m${cwd}\x1b[0m:\n`;
                for (const item of imported) {
                    report += `  + ${item.name} (${item.size} bytes) -> ${item.path}\n`;
                }
                await OutputManager.appendToOutput(report);
            }
        }

        if (errors.length > 0) {
            if (StatusBarManager) {
                StatusBarManager.notify(`Import errors on ${errors.length} file(s)`, { level: "error" });
            }
            if (OutputManager) {
                let errReport = `\x1b[1;31m[Import Bridge Errors]\x1b[0m Failed to import:\n`;
                for (const err of errors) {
                    errReport += `  - ${err.name}: ${err.error}\n`;
                }
                await OutputManager.appendToOutput(errReport);
            }
        }

        return { success: true, imported, errors };
    }

    _readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error(`Failed to read file ${file.name}`));
            reader.readAsText(file);
        });
    }
};
