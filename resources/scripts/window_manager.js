window.WindowManager = class WindowManager {
    constructor() {
        this.dependencies = {};
        this.domElements = {};
        this.windows = new Map(); // id -> WindowRecord
        this.counter = 0;
        this.activeWindowId = null;
        this.isTerminalFocused = true;
        this.highestZIndex = 20;

        // Mouse drag and resize state
        this._dragState = null;
        this._resizeState = null;

        this._boundMouseMove = this._onMouseMove.bind(this);
        this._boundMouseUp = this._onMouseUp.bind(this);
    }

    initialize(domElements) {
        this.domElements = domElements;

        // Ensure window dock bar exists
        let dockEl = document.getElementById("window-dock");
        if (!dockEl && domElements.terminalDiv) {
            dockEl = document.createElement("div");
            dockEl.id = "window-dock";
            dockEl.className = "window-dock hidden";
            domElements.terminalDiv.appendChild(dockEl);
        }
        this.domElements.windowDock = dockEl;

        // Listen for global mouse events for dragging and resizing
        document.addEventListener("mousemove", this._boundMouseMove);
        document.addEventListener("mouseup", this._boundMouseUp);
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    /**
     * Determines if any currently visible window is modal/fullscreen blocking.
     */
    hasModalApp() {
        for (const win of this.windows.values()) {
            if (!win.isMinimized && win.mode === 'fullscreen') {
                return true;
            }
        }
        return false;
    }

    /**
     * Determines if an app window currently has keyboard focus.
     */
    isAppFocused() {
        if (this.isTerminalFocused) return false;
        if (!this.activeWindowId) return false;
        const win = this.windows.get(this.activeWindowId);
        return !!(win && !win.isMinimized);
    }

    /**
     * Returns the active App instance, if any has focus.
     */
    getActiveApp() {
        if (!this.activeWindowId) return null;
        const win = this.windows.get(this.activeWindowId);
        return win ? win.appInstance : null;
    }

    /**
     * Opens an app in a managed window.
     */
    async openWindow(appInstance, options = {}) {
        const { TerminalUI, OutputManager } = this.dependencies;
        const appLayer = this.domElements.appLayer;

        if (!appInstance) return null;

        const winId = `win-${++this.counter}`;
        const isModalApp = options.modal ||
            appInstance.constructor?.name === "OnboardingManager" ||
            appInstance.constructor?.name === "Pager";

        // A locked window is not the user's to dismiss: no controls, no minimize/dock/float, no close except by the app.
        const isLocked = !!options.locked || appInstance.constructor?.name === "OnboardingManager";

        let defaultMode = 'floating';
        if (isModalApp) {
            defaultMode = 'fullscreen';
        } else if (options.windowMode) {
            defaultMode = options.windowMode;
        }

        // enter() may be async (the editor loads its file first); the container only exists once it settles.
        await appInstance.enter(appLayer, options);

        const container = appInstance.container ||
            appInstance.ui?.elements?.container;

        if (!container) {
            console.error("WindowManager: Unable to find app container element.");
            return null;
        }

        container.dataset.windowId = winId;
        const titleEl = container.querySelector('.app-header__title, .window-title, h2');
        const title = options.title || (titleEl ? titleEl.textContent : (appInstance.constructor?.name || 'Application'));

        const count = this.windows.size;
        const bounds = {
            top: 25 + (count * 20) % 120,
            left: 25 + (count * 20) % 160,
            width: Math.min(780, Math.floor(window.innerWidth * 0.75)),
            height: Math.min(520, Math.floor(window.innerHeight * 0.70))
        };

        const winRecord = {
            id: winId,
            title,
            appInstance,
            container,
            mode: defaultMode,
            previousMode: defaultMode === 'fullscreen' ? 'floating' : defaultMode,
            isMinimized: false,
            locked: isLocked,
            bounds,
            zIndex: ++this.highestZIndex
        };

        this.windows.set(winId, winRecord);

        // Decorate container with window controls and resize handles if needed
        this._decorateWindow(winRecord);

        // Show appLayer
        appLayer.classList.remove("hidden");

        // Apply mode layout styles
        this.setWindowMode(winId, defaultMode);

        // Focus this new window
        this.focusWindow(winId);

        // If modal, obscure terminal; otherwise keep terminal visible & ready
        if (isModalApp) {
            TerminalUI?.setInputState(false);
            OutputManager?.setEditorActive(true);
        } else {
            TerminalUI?.showInputLine();
            TerminalUI?.setInputState(true);
            OutputManager?.setEditorActive(false);
        }

        this._updateDockBar();
        return winRecord;
    }

    /**
     * Decorates an app container with window controls (Min, Dock, Max/Float, Close) and drag handlers.
     */
    _decorateWindow(win) {
        const container = win.container;
        const header = container.querySelector('.app-header, .window-header, header');

        if (win.locked) {
            container.addEventListener('mousedown', () => this.focusWindow(win.id));
            return;
        }

        if (header) {
            header.style.cursor = 'grab';

            // Check if window-controls already exist
            let controls = header.querySelector('.window-controls');
            if (!controls) {
                controls = document.createElement('div');
                controls.className = 'window-controls';

                // Minimize button
                const minBtn = document.createElement('button');
                minBtn.className = 'window-btn window-btn--min';
                minBtn.textContent = '–';
                minBtn.title = 'Minimize (Alt+M)';
                minBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.minimizeWindow(win.id);
                });

                // Dock button
                const dockBtn = document.createElement('button');
                dockBtn.className = 'window-btn window-btn--dock';
                dockBtn.textContent = '◧';
                dockBtn.title = 'Dock Side-by-Side (Alt+D)';
                dockBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.cycleDockMode(win.id);
                });

                // Mode toggle button (Float / Fullscreen)
                const modeBtn = document.createElement('button');
                modeBtn.className = 'window-btn window-btn--mode';
                modeBtn.textContent = win.mode === 'fullscreen' ? '🗗' : '🗖';
                modeBtn.title = 'Maximize / Float (Alt+F)';
                modeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleMaximize(win.id);
                });

                // Close button (keep existing exit button if present, or add one)
                let exitBtn = header.querySelector('.app-header__exit-btn, .window-close-btn');
                if (!exitBtn) {
                    exitBtn = document.createElement('button');
                    exitBtn.className = 'window-btn window-btn--close';
                    exitBtn.textContent = '×';
                    exitBtn.title = 'Close (Esc)';
                    exitBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.closeWindow(win.id);
                    });
                } else {
                    exitBtn.classList.add('window-btn', 'window-btn--close');
                }

                controls.appendChild(minBtn);
                controls.appendChild(dockBtn);
                controls.appendChild(modeBtn);
                controls.appendChild(exitBtn);

                header.appendChild(controls);
            }

            // Header dragging listener
            header.addEventListener('mousedown', (e) => {
                if (e.target.closest('button, input, select, a, textarea')) return;
                if (win.mode !== 'floating') return;

                this.focusWindow(win.id);
                this._dragState = {
                    winId: win.id,
                    startX: e.clientX,
                    startY: e.clientY,
                    origLeft: container.offsetLeft,
                    origTop: container.offsetTop
                };
                header.style.cursor = 'grabbing';
                e.preventDefault();
            });
        }

        // Add resize handle for floating mode
        let resizeHandle = container.querySelector('.window-resize-handle');
        if (!resizeHandle) {
            resizeHandle = document.createElement('div');
            resizeHandle.className = 'window-resize-handle';
            resizeHandle.title = 'Drag to resize';
            resizeHandle.innerHTML = '⋰';
            resizeHandle.addEventListener('mousedown', (e) => {
                if (win.mode !== 'floating') return;
                this.focusWindow(win.id);
                this._resizeState = {
                    winId: win.id,
                    startX: e.clientX,
                    startY: e.clientY,
                    origWidth: container.offsetWidth,
                    origHeight: container.offsetHeight
                };
                e.preventDefault();
                e.stopPropagation();
            });
            container.appendChild(resizeHandle);
        }

        // Focus on click
        container.addEventListener('mousedown', () => {
            this.focusWindow(win.id);
        });
    }

    _onMouseMove(e) {
        if (this._dragState) {
            const win = this.windows.get(this._dragState.winId);
            if (!win) return;

            const dx = e.clientX - this._dragState.startX;
            const dy = e.clientY - this._dragState.startY;

            const terminalRect = this.domElements.terminalDiv?.getBoundingClientRect() || { width: window.innerWidth, height: window.innerHeight };
            const newLeft = Math.max(0, Math.min(terminalRect.width - 100, this._dragState.origLeft + dx));
            const newTop = Math.max(0, Math.min(terminalRect.height - 60, this._dragState.origTop + dy));

            win.bounds.left = newLeft;
            win.bounds.top = newTop;

            win.container.style.left = `${newLeft}px`;
            win.container.style.top = `${newTop}px`;
        } else if (this._resizeState) {
            const win = this.windows.get(this._resizeState.winId);
            if (!win) return;

            const dx = e.clientX - this._resizeState.startX;
            const dy = e.clientY - this._resizeState.startY;

            const newWidth = Math.max(340, this._resizeState.origWidth + dx);
            const newHeight = Math.max(220, this._resizeState.origHeight + dy);

            win.bounds.width = newWidth;
            win.bounds.height = newHeight;

            win.container.style.width = `${newWidth}px`;
            win.container.style.height = `${newHeight}px`;
        }
    }

    _onMouseUp() {
        if (this._dragState) {
            const win = this.windows.get(this._dragState.winId);
            if (win) {
                const header = win.container.querySelector('.app-header, .window-header, header');
                if (header) header.style.cursor = 'grab';
            }
            this._dragState = null;
        }
        if (this._resizeState) {
            this._resizeState = null;
        }
    }

    /**
     * Sets layout mode: 'floating', 'docked-right', 'docked-left', 'docked-bottom', 'fullscreen'.
     */
    setWindowMode(winId, mode) {
        const win = this.windows.get(winId);
        if (!win) return { success: false, error: `Window ${winId} not found` };
        if (win.locked && mode !== 'fullscreen') {
            return { success: false, error: `Window ${winId} is locked and cannot change layout` };
        }

        const validModes = ['floating', 'docked-right', 'docked-left', 'docked-bottom', 'fullscreen'];
        if (!validModes.includes(mode)) {
            return { success: false, error: `Invalid mode: ${mode}. Valid: ${validModes.join(', ')}` };
        }

        win.previousMode = win.mode;
        win.mode = mode;

        const container = win.container;
        const appLayer = this.domElements.appLayer;
        const terminalDiv = this.domElements.terminalDiv;

        // Clean up previous mode classes
        container.classList.remove(
            'window--floating',
            'window--docked',
            'window--docked-right',
            'window--docked-left',
            'window--docked-bottom',
            'window--fullscreen'
        );

        if (terminalDiv) {
            terminalDiv.classList.remove(
                'terminal--docked-right',
                'terminal--docked-left',
                'terminal--docked-bottom'
            );
        }

        if (appLayer) {
            appLayer.classList.remove(
                'app-layer--floating',
                'app-layer--docked-right',
                'app-layer--docked-left',
                'app-layer--docked-bottom',
                'app-layer--fullscreen'
            );
        }

        // Apply new mode
        if (mode === 'floating') {
            container.classList.add('window--floating');
            container.style.position = 'absolute';
            container.style.top = `${win.bounds.top}px`;
            container.style.left = `${win.bounds.left}px`;
            container.style.width = `${win.bounds.width}px`;
            container.style.height = `${win.bounds.height}px`;
            container.style.margin = '0';

            if (appLayer) appLayer.classList.add('app-layer--floating');
        } else if (mode.startsWith('docked-')) {
            container.classList.add('window--docked', `window--${mode}`);
            container.style.position = 'relative';
            container.style.top = '';
            container.style.left = '';
            container.style.width = '';
            container.style.height = '';
            container.style.margin = '0';

            if (terminalDiv) terminalDiv.classList.add(`terminal--${mode}`);
            if (appLayer) appLayer.classList.add(`app-layer--${mode}`);
        } else if (mode === 'fullscreen') {
            container.classList.add('window--fullscreen');
            container.style.position = 'relative';
            container.style.top = '';
            container.style.left = '';
            container.style.width = '';
            container.style.height = '';
            container.style.margin = 'auto';

            if (appLayer) appLayer.classList.add('app-layer--fullscreen');
        }

        // Update mode button icon
        const modeBtn = container.querySelector('.window-btn--mode');
        if (modeBtn) {
            modeBtn.textContent = mode === 'fullscreen' ? '🗗' : '🗖';
        }

        this._updateDockBar();
        return { success: true, mode };
    }

    cycleDockMode(winId) {
        const win = this.windows.get(winId);
        if (!win) return;
        const cycle = {
            'floating': 'docked-right',
            'docked-right': 'docked-left',
            'docked-left': 'docked-bottom',
            'docked-bottom': 'floating',
            'fullscreen': 'docked-right'
        };
        const nextMode = cycle[win.mode] || 'floating';
        this.setWindowMode(winId, nextMode);
    }

    toggleMaximize(winId) {
        const win = this.windows.get(winId);
        if (!win) return;
        if (win.mode === 'fullscreen') {
            this.setWindowMode(winId, win.previousMode || 'floating');
        } else {
            this.setWindowMode(winId, 'fullscreen');
        }
    }

    minimizeWindow(winId) {
        const win = this.windows.get(winId);
        if (!win) return { success: false, error: `Window ${winId} not found` };
        if (win.locked) return { success: false, error: `Window ${winId} is locked and cannot be minimized` };

        win.isMinimized = true;
        win.container.style.display = 'none';

        // If this was a docked window, remove terminal docking class while minimized
        if (win.mode.startsWith('docked-') && this.domElements.terminalDiv) {
            this.domElements.terminalDiv.classList.remove(
                'terminal--docked-right',
                'terminal--docked-left',
                'terminal--docked-bottom'
            );
        }

        // Switch focus to next open window or terminal
        if (this.activeWindowId === winId) {
            let nextWin = null;
            for (const other of this.windows.values()) {
                if (!other.isMinimized && other.id !== winId) {
                    nextWin = other;
                    break;
                }
            }
            if (nextWin) {
                this.focusWindow(nextWin.id);
            } else {
                this.focusTerminal();
            }
        }

        this._updateDockBar();
        return { success: true };
    }

    restoreWindow(winId) {
        const win = this.windows.get(winId);
        if (!win) return { success: false, error: `Window ${winId} not found` };

        win.isMinimized = false;
        win.container.style.display = '';

        // Reapply mode layout classes
        this.setWindowMode(winId, win.mode);
        this.focusWindow(winId);

        this._updateDockBar();
        return { success: true };
    }

    focusWindow(winId) {
        const win = this.windows.get(winId);
        if (!win) return { success: false, error: `Window ${winId} not found` };

        if (win.isMinimized) {
            this.restoreWindow(winId);
        }

        this.activeWindowId = winId;
        this.isTerminalFocused = false;
        win.zIndex = ++this.highestZIndex;
        win.container.style.zIndex = win.zIndex;

        // Visual active styling
        for (const other of this.windows.values()) {
            if (other.id === winId) {
                other.container.classList.add('window--active');
                other.container.classList.remove('window--inactive');
            } else {
                other.container.classList.remove('window--active');
                other.container.classList.add('window--inactive');
            }
        }

        if (win.container && typeof win.container.focus === "function") {
            win.container.focus();
        }

        this._updateDockBar();
        return { success: true };
    }

    focusTerminal() {
        this.isTerminalFocused = true;
        for (const other of this.windows.values()) {
            other.container.classList.remove('window--active');
            other.container.classList.add('window--inactive');
        }

        const { TerminalUI } = this.dependencies;
        if (TerminalUI) {
            TerminalUI.showInputLine();
            TerminalUI.setInputState(true);
            TerminalUI.focusInput();
        }

        this._updateDockBar();
    }

    cycleFocus() {
        const openWins = Array.from(this.windows.values()).filter(w => !w.isMinimized);
        if (openWins.length === 0) {
            this.focusTerminal();
            return;
        }

        if (this.isTerminalFocused) {
            this.focusWindow(openWins[0].id);
            return;
        }

        const curIdx = openWins.findIndex(w => w.id === this.activeWindowId);
        if (curIdx === -1 || curIdx === openWins.length - 1) {
            this.focusTerminal();
        } else {
            this.focusWindow(openWins[curIdx + 1].id);
        }
    }

    cycleDockModeForActive() {
        if (this.activeWindowId) {
            this.cycleDockMode(this.activeWindowId);
        }
    }

    toggleMaximizeForActive() {
        if (this.activeWindowId) {
            this.toggleMaximize(this.activeWindowId);
        }
    }

    minimizeActive() {
        if (this.activeWindowId) {
            this.minimizeWindow(this.activeWindowId);
        }
    }

    /**
     * Closes a window. A locked window refuses, unless the app itself is exiting (`force`, as closeApp passes).
     */
    closeWindow(winId, { force = false } = {}) {
        const win = this.windows.get(winId);
        if (!win) return { success: false, error: `Window ${winId} not found` };
        if (win.locked && !force) return { success: false, error: `Window ${winId} is locked and cannot be closed` };

        // Clean up DOM element
        if (win.container && win.container.parentNode) {
            win.container.parentNode.removeChild(win.container);
        }

        // Clean up dock layout on terminal if this was docked
        if (win.mode.startsWith('docked-') && this.domElements.terminalDiv) {
            this.domElements.terminalDiv.classList.remove(
                'terminal--docked-right',
                'terminal--docked-left',
                'terminal--docked-bottom'
            );
        }

        this.windows.delete(winId);

        // Notify app if not already exiting
        if (win.appInstance && typeof win.appInstance.exit === 'function') {
            try {
                win.appInstance.exit();
            } catch (e) {
                // Ignore if already exited
            }
        }

        // If no windows left, hide appLayer and restore terminal
        if (this.windows.size === 0) {
            this.activeWindowId = null;
            if (this.domElements.appLayer) {
                this.domElements.appLayer.classList.add("hidden");
                this.domElements.appLayer.className = "hidden";
            }
            this.focusTerminal();
        } else {
            // Focus next remaining window
            const remaining = Array.from(this.windows.values()).find(w => !w.isMinimized);
            if (remaining) {
                this.focusWindow(remaining.id);
            } else {
                this.focusTerminal();
            }
        }

        this._updateDockBar();
        return { success: true };
    }

    closeApp(appInstance) {
        for (const [id, win] of this.windows.entries()) {
            if (win.appInstance === appInstance) {
                return this.closeWindow(id, { force: true });
            }
        }
        return { success: false, error: "App instance not found in window manager" };
    }

    tileWindows() {
        const openWins = Array.from(this.windows.values()).filter(w => !w.isMinimized && !w.locked);
        if (openWins.length === 0) return;

        const terminalRect = this.domElements.terminalDiv?.getBoundingClientRect() || { width: 900, height: 600 };
        const W = terminalRect.width;
        const H = terminalRect.height;

        if (openWins.length === 1) {
            this.setWindowMode(openWins[0].id, 'docked-right');
        } else if (openWins.length === 2) {
            // Half and half floating
            openWins[0].mode = 'floating';
            openWins[0].bounds = { top: 10, left: 10, width: Math.floor(W * 0.48), height: Math.floor(H * 0.85) };
            this.setWindowMode(openWins[0].id, 'floating');

            openWins[1].mode = 'floating';
            openWins[1].bounds = { top: 10, left: Math.floor(W * 0.50), width: Math.floor(W * 0.48), height: Math.floor(H * 0.85) };
            this.setWindowMode(openWins[1].id, 'floating');
        } else {
            // Grid layout
            const cols = 2;
            const rows = Math.ceil(openWins.length / cols);
            const cellW = Math.floor(W / cols) - 20;
            const cellH = Math.floor(H / rows) - 20;

            openWins.forEach((win, i) => {
                const r = Math.floor(i / cols);
                const c = i % cols;
                win.mode = 'floating';
                win.bounds = { top: r * (cellH + 15) + 10, left: c * (cellW + 15) + 10, width: cellW, height: cellH };
                this.setWindowMode(win.id, 'floating');
            });
        }

        this.focusWindow(openWins[0].id);
    }

    getWindowsList() {
        const list = [];
        for (const win of this.windows.values()) {
            list.push({
                id: win.id,
                title: win.title,
                mode: win.mode,
                isMinimized: win.isMinimized,
                isFocused: this.activeWindowId === win.id && !this.isTerminalFocused
            });
        }
        return list;
    }

    _updateDockBar() {
        const dockEl = this.domElements.windowDock;
        if (!dockEl) return;

        if (![...this.windows.values()].some(w => !w.locked)) {
            dockEl.classList.add("hidden");
            dockEl.innerHTML = "";
            return;
        }

        dockEl.classList.remove("hidden");
        dockEl.innerHTML = "";

        for (const win of this.windows.values()) {
            if (win.locked) continue;
            const pill = document.createElement("div");
            pill.className = "window-dock__pill";
            if (this.activeWindowId === win.id && !this.isTerminalFocused) {
                pill.classList.add("window-dock__pill--active");
            }
            if (win.isMinimized) {
                pill.classList.add("window-dock__pill--minimized");
            }

            const iconSpan = document.createElement("span");
            iconSpan.className = "window-dock__icon";
            iconSpan.textContent = win.mode.startsWith("docked") ? "◧" : (win.mode === "fullscreen" ? "🗖" : "🗗");

            const titleSpan = document.createElement("span");
            titleSpan.className = "window-dock__title";
            titleSpan.textContent = win.title.length > 20 ? win.title.slice(0, 19) + "…" : win.title;

            const closeSpan = document.createElement("span");
            closeSpan.className = "window-dock__close";
            closeSpan.textContent = "×";
            closeSpan.title = "Close window";
            closeSpan.addEventListener("click", (e) => {
                e.stopPropagation();
                this.closeWindow(win.id);
            });

            pill.appendChild(iconSpan);
            pill.appendChild(titleSpan);
            pill.appendChild(closeSpan);

            pill.addEventListener("click", () => {
                if (win.isMinimized) {
                    this.restoreWindow(win.id);
                } else if (this.activeWindowId === win.id && !this.isTerminalFocused) {
                    this.minimizeWindow(win.id);
                } else {
                    this.focusWindow(win.id);
                }
            });

            dockEl.appendChild(pill);
        }
    }
};
