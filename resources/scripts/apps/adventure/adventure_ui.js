window.TextAdventureModal = class TextAdventureModal {
  constructor(callbacks, dependencies, scriptingContext) {
    this.elements = {};
    this.callbacks = callbacks;
    this.dependencies = dependencies;

    this._boundHandleInput = this._handleInput.bind(this);

    this._buildLayout(scriptingContext);
  }

  getContainer() {
    return this.elements.container;
  }

  mountCompanion(controls, ask) {
    const { Utils } = this.dependencies;
    const input = Utils.createElement("input", {
      type: "text", className: "companion-field", placeholder: "Ask BoneAmanita", "aria-label": "Ask BoneAmanita",
    });
    const submit = Utils.createElement("button", { type: "submit", className: "btn btn--confirm", textContent: "Ask BoneAmanita" });
    const form = Utils.createElement("form", { className: "companion-controls" }, input, submit);
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message || submit.disabled) return;
      input.value = "";
      submit.disabled = true;
      this.appendOutput(message, "system");
      try {
        await ask(message);
      } finally {
        submit.disabled = false;
      }
    });
    this.elements.footer.append(controls, form);
  }

  _buildLayout(scriptingContext) {
    const { Utils } = this.dependencies;
    this._createElements();

    this.elements.input.addEventListener("keydown", this._boundHandleInput);

    if (scriptingContext?.isScripting) {
      this.elements.input.style.display = "none";
    }

    setTimeout(() => this.elements.input.focus(), 0);
  }

  hideAndReset() {
    if (this.elements.input) {
      this.elements.input.removeEventListener("keydown", this._boundHandleInput);
    }
    if (this.elements.container) {
      this.elements.container.remove();
    }
    this.elements = {};
    this.callbacks = {};
    this.dependencies = {};
  }

  _createElements() {
    const { Utils, UIComponents } = this.dependencies;
    const { container, header, main, footer } = UIComponents.createAppWindow("Adventure", this.callbacks.onExitRequest);
    container.id = "adventure-container";
    const roomNameSpan = Utils.createElement("span", { id: "adventure-room-name" });
    const scoreSpan = Utils.createElement("span", { id: "adventure-score" });
    const roomStatus = Utils.createElement("div", { id: "adventure-status" }, roomNameSpan, scoreSpan);
    const output = Utils.createElement("div", { id: "adventure-output" });
    const inputPrompt = Utils.createElement("span", { id: "adventure-prompt", textContent: ">" });
    const input = Utils.createElement("input", {
      id: "adventure-input",
      type: "text",
      spellcheck: "false",
      autocapitalize: "none",
      "aria-label": "Adventure command",
    });
    const inputContainer = Utils.createElement("div", { id: "adventure-input-container" }, inputPrompt, input);
    main.append(roomStatus, output);
    footer.append(inputContainer);
    this.elements = { container, header, footer, output, input, roomNameSpan, scoreSpan };
  }

  _handleInput(e) {
    if (e.key !== "Enter" || !this.callbacks.processCommand) return;
    e.preventDefault();
    const command = this.elements.input.value;
    this.elements.input.value = "";
    this.appendOutput(`> ${command}`, "system");
    this.callbacks.processCommand(command);
  }

  appendOutput(text, styleClass = "") {
    if (!this.elements.output) return;
    const { Utils } = this.dependencies;
    const p = Utils.createElement("p", { textContent: text });
    if (styleClass) {
      p.className = `adv-${styleClass}`;
    }
    this.elements.output.appendChild(p);
    this.elements.output.scrollTop = this.elements.output.scrollHeight;
  }

  updateStatusLine(roomName, score, moves) {
    if (this.elements.roomNameSpan) {
      this.elements.roomNameSpan.textContent = roomName;
    }
    if (this.elements.scoreSpan) {
      this.elements.scoreSpan.textContent = `Score: ${score}  Moves: ${moves}`;
    }
  }

  requestInput(_prompt) {
    return new Promise((resolve) => {
      if (this.callbacks.onScriptedInput) {
        const command = this.callbacks.onScriptedInput();
        resolve(command);
      } else {
        const handleOneTimeInput = (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            const command = this.elements.input.value;
            this.elements.input.value = '';
            this.appendOutput(`> ${command}`, 'system');
            this.elements.input.removeEventListener('keydown', handleOneTimeInput);
            this.elements.input.addEventListener('keydown', this._boundHandleInput);
            resolve(command);
          }
        };
        this.elements.input.removeEventListener('keydown', this._boundHandleInput);
        this.elements.input.addEventListener('keydown', handleOneTimeInput);
      }
    });
  }
}
