class OutputManager {
    constructor() {
        this.isEditorActive = false;
        this.cachedOutputDiv = null;
        this.cachedInputLineContainerDiv = null;
        this.dependencies = {};
        this.originalConsoleLog = console.log;
        this.originalConsoleWarn = console.warn;
        this.originalConsoleError = console.error;
        this.isTyping = false;
        this.typingQueue = [];
        this.cinematicSkip = false;
    }

    initialize(dom) {
        this.cachedOutputDiv = dom.outputDiv;
        this.cachedInputLineContainerDiv = dom.inputLineContainerDiv;
    }

    setDependencies(injectedDependencies) {
        this.dependencies = injectedDependencies;
    }

    setEditorActive(status) {
        this.isEditorActive = status;
    }

    async appendToOutput(text, options = {}) {
        const { UIStateManager } = this.dependencies;

        if (UIStateManager && UIStateManager.isCinematic() && !options.isCompletionSuggestion && !this.isEditorActive && !options.noCinematic) {
            return new Promise(resolve => {
                this.typingQueue.push({ text, options, resolve });
                if (!this.isTyping) {
                    this._processTypingQueue();
                }
            });
        } else {
            this._appendDirectly(text, options);
        }
    }

    _appendDirectly(text, options = {}) {
        const { Config, TerminalUI, Utils } = this.dependencies;
        if (
            this.isEditorActive &&
            options.typeClass !== Config.CSS_CLASSES.EDITOR_MSG &&
            !options.isCompletionSuggestion
        )
            return;
        if (!this.cachedOutputDiv) {
            this.originalConsoleError(
                "OutputManager.appendToOutput: cachedOutputDiv is not defined. Message:",
                text
            );
            return;
        }
        const { typeClass = options.messageType || null, isBackground = false, asBlock = false } = options;

        if (
            isBackground &&
            this.cachedInputLineContainerDiv &&
            !this.cachedInputLineContainerDiv.classList.contains(Config.CSS_CLASSES.HIDDEN)
        ) {
            const promptText = TerminalUI.getPromptText() || "> ";
            const currentInputVal = TerminalUI.getCurrentInputValue();
            const echoLine = Utils.createElement("div", {
                className: Config.CSS_CLASSES.OUTPUT_LINE,
                textContent: `${promptText}${currentInputVal}`,
            });
            this.cachedOutputDiv.appendChild(echoLine);
        }

        if (asBlock) {
            const blockWrapper = Utils.createElement("div", {
                className: typeClass || "",
                innerHTML: text,
            });
            this.cachedOutputDiv.appendChild(blockWrapper);
            this.cachedOutputDiv.scrollTop = this.cachedOutputDiv.scrollHeight;
            return;
        }

        const lines = String(text).split("\n");
        const fragment = document.createDocumentFragment();

        for (const line of lines) {
            const lineClasses = Config.CSS_CLASSES.OUTPUT_LINE.split(" ");
            const hasAnsi = line.includes("\x1b[");
            const lineAttributes = {
                classList: [...lineClasses],
                textContent: hasAnsi ? "" : line,
            };

            if (typeClass) {
                typeClass.split(" ").forEach((cls) => {
                    if (cls) lineAttributes.classList.push(cls);
                });
            }

            const lineDiv = Utils.createElement("div", lineAttributes);
            if (hasAnsi) this._renderAnsi(lineDiv, line);
            fragment.appendChild(lineDiv);
        }

        this.cachedOutputDiv.appendChild(fragment);
        this.cachedOutputDiv.scrollTop = this.cachedOutputDiv.scrollHeight;
    }

    /**
     * Appends `line` to `el`, turning ANSI SGR sequences (ESC[...m) into styled spans.
     * Supports reset (0), bold (1, 22), and foreground colours (30-37, 90-97, 39).
     * Everything else is dropped. Text goes in as text nodes, never as HTML.
     */
    _renderAnsi(el, line) {
        const sgr = /\x1b\[([0-9;]*)m/g;
        let last = 0, fg = null, bold = false, match;
        const push = (text) => {
            if (!text) return;
            if (!fg && !bold) {
                el.appendChild(document.createTextNode(text));
                return;
            }
            const span = document.createElement("span");
            if (fg) span.classList.add(`ansi-fg-${fg}`);
            if (bold) span.classList.add("ansi-bold");
            span.textContent = text;
            el.appendChild(span);
        };
        while ((match = sgr.exec(line)) !== null) {
            push(line.slice(last, match.index));
            for (const code of (match[1] || "0").split(";").map(Number)) {
                if (code === 0) { fg = null; bold = false; }
                else if (code === 1) bold = true;
                else if (code === 22) bold = false;
                else if (code === 39) fg = null;
                else if ((code >= 30 && code <= 37) || (code >= 90 && code <= 97)) fg = code;
            }
            last = sgr.lastIndex;
        }
        push(line.slice(last));
    }

    async _processTypingQueue() {
        if (this.typingQueue.length === 0) {
            this.isTyping = false;
            return;
        }

        this.isTyping = true;
        const { text, options, resolve } = this.typingQueue.shift();
        await this._typewriterEffect(text, options);
        resolve();

        this._processTypingQueue();
    }

    _typewriterEffect(text, options) {
        return new Promise(async (resolve) => {
            const { Config, Utils } = this.dependencies;
            const lines = String(text).replace(/\x1b\[[0-9;]*m/g, "").split("\n");
            const characterDelay = 12;

            const skipHandler = (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.cinematicSkip = true;
                document.removeEventListener('keydown', skipHandler, true);
                document.removeEventListener('mousedown', skipHandler, true);
            };
            document.addEventListener('keydown', skipHandler, true);
            document.addEventListener('mousedown', skipHandler, true);

            for (const line of lines) {
                const lineClasses = Config.CSS_CLASSES.OUTPUT_LINE.split(" ");
                const lineAttributes = { classList: [...lineClasses] };
                if (options.typeClass) {
                    options.typeClass.split(" ").forEach(cls => { if (cls) lineAttributes.classList.push(cls); });
                }
                const lineDiv = Utils.createElement("div", lineAttributes);
                this.cachedOutputDiv.appendChild(lineDiv);

                for (let i = 0; i < line.length; i++) {
                    if (this.cinematicSkip) {
                        lineDiv.textContent = line;
                        this.cachedOutputDiv.scrollTop = this.cachedOutputDiv.scrollHeight;
                        break;
                    }
                    lineDiv.textContent += line[i];
                    this.cachedOutputDiv.scrollTop = this.cachedOutputDiv.scrollHeight;
                    await Utils.safeDelay(characterDelay);
                }
                if (this.cinematicSkip) {
                    continue;
                }
            }

            this.cinematicSkip = false;
            document.removeEventListener('keydown', skipHandler, true);
            document.removeEventListener('mousedown', skipHandler, true);
            resolve();
        });
    }

    clearOutput() {
        if (!this.isEditorActive && this.cachedOutputDiv) {
            while (this.cachedOutputDiv.firstChild) {
                this.cachedOutputDiv.removeChild(this.cachedOutputDiv.firstChild);
            }
        }
    }

    _consoleLogOverride(...args) {
        const { Config, Utils } = this.dependencies;
        if (this.cachedOutputDiv && typeof Utils !== "undefined" && typeof Utils.formatConsoleArgs === "function") {
            this._appendDirectly(`LOG: ${Utils.formatConsoleArgs(args)}`, { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
        }
        this.originalConsoleLog.apply(console, args);
    }

    _consoleWarnOverride(...args) {
        const { Config, Utils } = this.dependencies;
        if (this.cachedOutputDiv && typeof Utils !== "undefined" && typeof Utils.formatConsoleArgs === "function") {
            this._appendDirectly(`WARN: ${Utils.formatConsoleArgs(args)}`, { typeClass: Config.CSS_CLASSES.WARNING_MSG });
        }
        this.originalConsoleWarn.apply(console, args);
    }

    _consoleErrorOverride(...args) {
        const { Config, Utils } = this.dependencies;
        if (this.cachedOutputDiv && typeof Utils !== "undefined" && typeof Utils.formatConsoleArgs === "function") {
            this._appendDirectly(`ERROR: ${Utils.formatConsoleArgs(args)}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
        }
        this.originalConsoleError.apply(console, args);
    }

    initializeConsoleOverrides() {
        if (typeof this.dependencies.Utils === "undefined" || typeof this.dependencies.Utils.formatConsoleArgs !== "function") {
            this.originalConsoleError("OutputManager: Cannot initialize console overrides, Utils or Utils.formatConsoleArgs is not defined.");
            return;
        }
        console.log = this._consoleLogOverride.bind(this);
        console.warn = this._consoleWarnOverride.bind(this);
        console.error = this._consoleErrorOverride.bind(this);
    }
}