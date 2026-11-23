window.AdventureManager = class AdventureManager extends App {
    constructor() {
        super();
        this.state = {};
        this.dependencies = {};
        this.callbacks = {};
        this.ui = null;
        this.companion = null;
    }

    async enter(appLayer, options = {}) {
        if (this.isActive) return;
        this.dependencies = options.dependencies;
        const { TextAdventureModal } = this.dependencies;
        this.callbacks = { processCommand: this.processCommand.bind(this), onExitRequest: this.exit.bind(this), };
        this.isActive = true;

        const initialStateResult = JSON.parse(
            await FractalOS_Kernel.syscall("adventure", "initialize_state", [
                JSON.stringify(options.adventureData),
                options.scriptingContext ? JSON.stringify(options.scriptingContext) : null
            ])
        );

        this.ui = new TextAdventureModal(this.callbacks, this.dependencies, options.scriptingContext);
        this.container = this.ui.getContainer();
        appLayer.appendChild(this.container);

        if (initialStateResult.success) this._applyUiUpdates(initialStateResult.updates);
        else this.ui.appendOutput("I couldn't start the adventure.", "error");
        if (options.companion && initialStateResult.success && !options.scriptingContext?.isScripting) {
            const ui = this.ui;
            const controls = companionControls(this.dependencies.CompanionClient, this.dependencies.Utils, result => {
                if (this.ui !== ui) return;
                const room = result.scene ? ` (${result.scene.room_name})` : "";
                ui.appendOutput(`BoneAmanita${room}: ${result.reply}`, "dialogue");
            });
            this.companion = controls;
            ui.mountCompanion(controls.element, async message => {
                try {
                    const packet = JSON.parse(await FractalOS_Kernel.syscall("adventure", "companion_scene", []));
                    if (this.ui !== ui) return;
                    if (!packet.success) {
                        controls.setStatus("Could not read the current adventure scene.");
                        return;
                    }
                    const scene = packet.data;
                    if (!scene) {
                        controls.setStatus("There is no current adventure scene.");
                        return;
                    }
                    await controls.ask(message, scene);
                } catch {
                    controls.setStatus("Could not read the current adventure scene.");
                }
            });
        }

        if (options.scriptingContext?.isScripting) await this._runScript(options.scriptingContext);
        else setTimeout(() => this.container.focus(), 0);
    }

    _applyUiUpdates(updates) {
        updates.forEach(update => {
            switch (update.type) {
                case "output":
                    this.ui.appendOutput(update.text, update.styleClass);
                    break;
                case "status":
                    this.ui.updateStatusLine(update.roomName, update.score, update.moves);
                    break;
            }
        });
    }

    async _runScript(scriptingContext) {
        while (
            scriptingContext.currentLineIndex < scriptingContext.lines.length - 1 &&
            this.isActive
            ) {
            let nextCommand = await this.ui.requestInput("");
            if (nextCommand === null) break;
            await this.processCommand(nextCommand);
        }
        if (this.isActive) {
            this.exit();
        }
    }

    exit() {
        if (!this.isActive) return;
        const { AppLayerManager } = this.dependencies;
        this.companion?.dispose();
        this.companion = null;
        if (this.ui) {
            this.ui.hideAndReset();
        }
        AppLayerManager.hide(this);
        this.isActive = false;
        this.state = {};
        this.ui = null;
    }

    handleKeyDown(event) {
        if (event.key === "Escape") {
            this.exit();
        }
    }


    async processCommand(command) {
        const result = JSON.parse(await FractalOS_Kernel.syscall("adventure", "process_command", [command]));
        if (result.success) {
            this._applyUiUpdates(result.updates);
            if (result.gameOver) {
                this.ui.elements.input.disabled = true;
                setTimeout(() => this.exit(), 1200);
            }
        } else {
            this.ui.appendOutput(result.error, "error");
        }
    }
};
