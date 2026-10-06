// scripts/multiplexer_manager.js

/**
 * MultiplexerManager - Terminal Multiplexer & Split Panes for FractalOS (P7-09).
 * Manages vertical and horizontal pane splits, independent working directories,
 * per-pane output buffering, zoom toggling, and keyboard navigation.
 */
class MultiplexerManager {
    constructor() {
        this.dependencies = {};
        this.panes = new Map();
        this.activePaneId = 'pane-1';
        this.counter = 1;
        this.isZoomed = false;
        this.isMultiplexing = false;
        this.container = null;
        this.originalDom = null;
        this.currentOrientation = 'vertical';
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    initialize(domElements) {
        this.originalDom = domElements;
        const defaultPane = {
            id: 'pane-1',
            index: 1,
            cwd: '/home/Guest',
            title: '1: Guest@fractal:~',
            outputDiv: domElements.outputDiv,
            promptContainer: domElements.promptContainer,
            editableInputDiv: domElements.editableInputDiv,
            inputLineContainerDiv: domElements.inputLineContainerDiv,
            paneElement: null,
            bodyElement: null,
            headerElement: null,
            titleElement: null
        };
        this.panes.set('pane-1', defaultPane);
    }

    getActivePane() {
        return this.panes.get(this.activePaneId) || this.panes.get('pane-1') || null;
    }

    getActivePaneId() {
        return this.activePaneId;
    }

    getPane(paneId) {
        if (!paneId) return this.getActivePane();
        if (this.panes.has(paneId)) return this.panes.get(paneId);
        // Match by index (e.g. "1" or "2")
        for (const [id, pane] of this.panes) {
            if (String(pane.index) === String(paneId) || id.endsWith(paneId)) {
                return pane;
            }
        }
        return null;
    }

    listPanes() {
        return Array.from(this.panes.values()).map(p => ({
            id: p.id,
            index: p.index,
            cwd: p.cwd || '/',
            active: p.id === this.activePaneId,
            isZoomed: this.isZoomed && p.id === this.activePaneId
        }));
    }

    updatePaneTitle(pane) {
        if (!pane || !pane.titleElement) return;
        const { UserManager, Config } = this.dependencies;
        const user = UserManager?.getCurrentUser()?.username || Config?.USER?.DEFAULT_NAME || 'Guest';
        const host = Config?.OS?.DEFAULT_HOST_NAME || 'fractal';
        const displayCwd = pane.cwd.startsWith('/home/' + user)
            ? '~' + pane.cwd.substring(('/home/' + user).length)
            : pane.cwd;
        const titleText = `${pane.index}: ${user}@${host}:${displayCwd}`;
        pane.title = titleText;
        pane.titleElement.textContent = titleText;
    }

    _setupPaneEventListeners(pane) {
        if (!pane.paneElement) return;

        // Click on pane body focuses it
        pane.paneElement.addEventListener('click', (e) => {
            if (this.dependencies.AppLayerManager?.isActive()) return;
            if (e.target.closest('.terminal-pane__btn')) return;
            this.focusPane(pane.id);
        });

        // Close button
        const closeBtn = pane.paneElement.querySelector('.terminal-pane__btn--close');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closePane(pane.id);
            });
        }

        // Zoom button
        const zoomBtn = pane.paneElement.querySelector('.terminal-pane__btn--zoom');
        if (zoomBtn) {
            zoomBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleZoom(pane.id);
            });
        }
    }

    _createPaneElement(id, index, cwd, isOriginal = false) {
        const paneEl = document.createElement('div');
        paneEl.className = 'terminal-pane';
        paneEl.setAttribute('data-pane-id', id);

        const header = document.createElement('div');
        header.className = 'terminal-pane__header';

        const title = document.createElement('span');
        title.className = 'terminal-pane__title';
        title.textContent = `${index}: Guest@fractal:~`;
        header.appendChild(title);

        const controls = document.createElement('div');
        controls.className = 'terminal-pane__controls';

        const zoomBtn = document.createElement('span');
        zoomBtn.className = 'terminal-pane__btn terminal-pane__btn--zoom';
        zoomBtn.title = 'Toggle Zoom (Alt+Z)';
        zoomBtn.textContent = '⤢';
        controls.appendChild(zoomBtn);

        const closeBtn = document.createElement('span');
        closeBtn.className = 'terminal-pane__btn terminal-pane__btn--close';
        closeBtn.title = 'Close Pane (Alt+W)';
        closeBtn.textContent = '×';
        controls.appendChild(closeBtn);

        header.appendChild(controls);
        paneEl.appendChild(header);

        const body = document.createElement('div');
        body.className = 'terminal-pane__body';
        paneEl.appendChild(body);

        let outputDiv, inputLine, promptContainer, editableInputDiv;

        if (isOriginal && this.originalDom) {
            outputDiv = this.originalDom.outputDiv;
            inputLine = this.originalDom.inputLineContainerDiv;
            promptContainer = this.originalDom.promptContainer;
            editableInputDiv = this.originalDom.editableInputDiv;
            body.appendChild(outputDiv);
            body.appendChild(inputLine);
        } else {
            outputDiv = document.createElement('div');
            outputDiv.className = 'terminal__output';
            outputDiv.id = `output-${id}`;
            body.appendChild(outputDiv);

            inputLine = document.createElement('div');
            inputLine.className = 'terminal__input-line';

            promptContainer = document.createElement('div');
            promptContainer.className = 'terminal__prompt';
            promptContainer.textContent = 'Guest@fractal:~$ ';
            inputLine.appendChild(promptContainer);

            const inputWrapper = document.createElement('div');
            inputWrapper.className = 'terminal__input-wrapper';

            editableInputDiv = document.createElement('div');
            editableInputDiv.className = 'terminal__input';
            editableInputDiv.contentEditable = 'true';
            editableInputDiv.spellcheck = false;
            editableInputDiv.autocapitalize = 'none';
            inputWrapper.appendChild(editableInputDiv);
            inputLine.appendChild(inputWrapper);
            body.appendChild(inputLine);

            // Wire input events for the new pane
            this._wirePaneInput(editableInputDiv, paneEl, id);
        }

        return {
            paneEl,
            header,
            title,
            body,
            outputDiv,
            inputLine,
            promptContainer,
            editableInputDiv
        };
    }

    _wirePaneInput(editableInputDiv, paneEl, paneId) {
        editableInputDiv.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text/plain').replace(/\r?\n|\r/g, ' ');
            if (this.dependencies.TerminalUI) {
                this.dependencies.TerminalUI.handlePaste(text);
            }
        });
    }

    async split(orientation = 'vertical', options = {}) {
        const { FileSystemManager, OutputManager, SoundManager } = this.dependencies;
        const activePane = this.getActivePane();
        const activeCwd = activePane?.cwd || FileSystemManager?.getCurrentPath() || '/home/Guest';

        if (typeof document === 'undefined') {
            // Headless / mock environment
            const newIndex = ++this.counter;
            const newId = `pane-${newIndex}`;
            this.panes.set(newId, {
                id: newId,
                index: newIndex,
                cwd: activeCwd,
                title: `${newIndex}: Guest@fractal:~`
            });
            this.activePaneId = newId;
            this.isMultiplexing = true;
            return { success: true, paneId: newId, index: newIndex };
        }

        const terminalDiv = this.originalDom?.terminalDiv || document.getElementById('terminal');
        if (!terminalDiv) return { success: false, error: 'Terminal container not found.' };

        // Initialize multiplexer container on first split
        if (!this.isMultiplexing) {
            this.isMultiplexing = true;
            this.currentOrientation = orientation;

            this.container = document.createElement('div');
            this.container.id = 'multiplexer-container';
            this.container.className = `multiplexer-container multiplexer-split--${orientation}`;

            // Wrap original Pane 1
            const pane1Data = this._createPaneElement('pane-1', 1, activeCwd, true);
            const p1 = this.panes.get('pane-1');
            p1.paneElement = pane1Data.paneEl;
            p1.bodyElement = pane1Data.body;
            p1.headerElement = pane1Data.header;
            p1.titleElement = pane1Data.title;
            this._setupPaneEventListeners(p1);
            this.updatePaneTitle(p1);

            this.container.appendChild(pane1Data.paneEl);

            const appLayer = this.originalDom?.appLayer || document.getElementById('app-layer');
            terminalDiv.insertBefore(this.container, appLayer);
        } else if (this.container) {
            // Already multiplexing; update orientation class if container orientation changed
            if (this.container.children.length === 1) {
                this.currentOrientation = orientation;
                this.container.className = `multiplexer-container multiplexer-split--${orientation}`;
            }
        }

        // Create new pane
        const newIndex = ++this.counter;
        const newId = `pane-${newIndex}`;
        const newPaneData = this._createPaneElement(newId, newIndex, activeCwd, false);

        const newPaneObj = {
            id: newId,
            index: newIndex,
            cwd: activeCwd,
            title: `${newIndex}: Guest@fractal:~`,
            outputDiv: newPaneData.outputDiv,
            promptContainer: newPaneData.promptContainer,
            editableInputDiv: newPaneData.editableInputDiv,
            inputLineContainerDiv: newPaneData.inputLine,
            paneElement: newPaneData.paneEl,
            bodyElement: newPaneData.body,
            headerElement: newPaneData.header,
            titleElement: newPaneData.title
        };

        this.panes.set(newId, newPaneObj);
        this._setupPaneEventListeners(newPaneObj);
        this.updatePaneTitle(newPaneObj);

        if (this.container) {
            this.container.appendChild(newPaneData.paneEl);
        }

        // Focus new pane
        await this.focusPane(newId);

        if (SoundManager && SoundManager.isInitialized) {
            try { SoundManager.playTone('E4', '32n'); } catch (_) {}
        }

        // Run initial command in new pane if requested
        if (options.command && typeof executePythonCommand === 'function') {
            setTimeout(async () => {
                await executePythonCommand(options.command, { isInteractive: true });
            }, 50);
        }

        return { success: true, paneId: newId, index: newIndex };
    }

    async closePane(paneId = null) {
        const targetId = paneId || this.activePaneId;
        if (!this.panes.has(targetId)) {
            return { success: false, error: `Pane '${targetId}' not found.` };
        }

        if (this.panes.size <= 1) {
            return { success: false, error: "Cannot close the only remaining terminal pane." };
        }

        const paneToClose = this.panes.get(targetId);
        if (paneToClose.paneElement) {
            paneToClose.paneElement.remove();
        }
        this.panes.delete(targetId);

        // If closed active pane, focus next available pane
        if (targetId === this.activePaneId) {
            const nextPane = this.panes.values().next().value;
            if (nextPane) {
                await this.focusPane(nextPane.id);
            }
        }

        // If only 1 pane remains, we can either keep container or restore layout
        if (this.panes.size === 1) {
            if (this.isZoomed) this.toggleZoom();
        }

        return { success: true, closedId: targetId };
    }

    async focusPane(paneId) {
        const targetPane = this.getPane(paneId);
        if (!targetPane) return { success: false, error: `Pane '${paneId}' not found.` };

        // Save active pane's current directory from FileSystemManager before switching
        const currentActive = this.panes.get(this.activePaneId);
        if (currentActive && this.dependencies.FileSystemManager) {
            currentActive.cwd = this.dependencies.FileSystemManager.getCurrentPath() || currentActive.cwd;
            this.updatePaneTitle(currentActive);
        }

        this.activePaneId = targetPane.id;

        // Update active class on DOM elements
        for (const [id, pane] of this.panes) {
            if (pane.paneElement) {
                if (id === targetPane.id) {
                    pane.paneElement.classList.add('terminal-pane--active');
                } else {
                    pane.paneElement.classList.remove('terminal-pane--active');
                }
            }
        }

        // Redirect TerminalUI and OutputManager to target pane's DOM
        const { TerminalUI, OutputManager, FileSystemManager } = this.dependencies;
        if (TerminalUI) {
            TerminalUI.elements.outputDiv = targetPane.outputDiv;
            TerminalUI.elements.promptContainer = targetPane.promptContainer;
            TerminalUI.elements.editableInputDiv = targetPane.editableInputDiv;
            TerminalUI.elements.inputLineContainerDiv = targetPane.inputLineContainerDiv;
        }

        if (OutputManager) {
            OutputManager.cachedOutputDiv = targetPane.outputDiv;
        }

        if (FileSystemManager && targetPane.cwd) {
            FileSystemManager.setCurrentPath(targetPane.cwd);
        }

        if (TerminalUI) {
            await TerminalUI.updatePrompt();
            TerminalUI.focusInput();
            TerminalUI.scrollOutputToEnd();
        }

        this.updatePaneTitle(targetPane);
        return { success: true, activePaneId: targetPane.id };
    }

    async focusNext() {
        const paneList = Array.from(this.panes.keys());
        if (paneList.length <= 1) return;
        const currentIndex = paneList.indexOf(this.activePaneId);
        const nextIndex = (currentIndex + 1) % paneList.length;
        await this.focusPane(paneList[nextIndex]);
    }

    async focusPrev() {
        const paneList = Array.from(this.panes.keys());
        if (paneList.length <= 1) return;
        const currentIndex = paneList.indexOf(this.activePaneId);
        const prevIndex = (currentIndex - 1 + paneList.length) % paneList.length;
        await this.focusPane(paneList[prevIndex]);
    }

    toggleZoom(paneId = null) {
        const targetId = paneId || this.activePaneId;
        const pane = this.getPane(targetId);
        if (!pane || !pane.paneElement) return { success: false };

        this.isZoomed = !this.isZoomed;
        if (this.isZoomed) {
            pane.paneElement.classList.add('terminal-pane--zoomed');
        } else {
            for (const [, p] of this.panes) {
                p.paneElement?.classList.remove('terminal-pane--zoomed');
            }
        }
        return { success: true, isZoomed: this.isZoomed };
    }
}

if (typeof window !== 'undefined') {
    window.MultiplexerManager = MultiplexerManager;
}
