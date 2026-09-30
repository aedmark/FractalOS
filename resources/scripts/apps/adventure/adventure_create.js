window.Adventure_create = {
    state: {
        isActive: false,
        commandContext: null,
    },
    dependencies: {},

    async enter(filename, initialData, commandContext) {
        if (this.state.isActive) return;

        this.dependencies = commandContext.dependencies;
        this.state = {
            isActive: true,
            commandContext: commandContext,
        };

        const resultJson = await FractalOS_Kernel.syscall('adventure', 'creator_initialize', [filename, JSON.stringify(initialData), JSON.stringify(commandContext.context)]);
        const result = JSON.parse(resultJson);

        this.dependencies.OutputManager.appendToOutput(result.data.message || result.error || "Initialization failed.", {
            typeClass: result.success ? "text-success" : "text-error"
        });

        if (result.success) {
            this._requestNextCommand();
        } else {
            this.state.isActive = false;
        }
    },

    async _requestNextCommand() {
        if (!this.state.isActive) return;

        const promptResultJson = await FractalOS_Kernel.syscall('adventure', 'creator_get_prompt', []);
        const promptResult = JSON.parse(promptResultJson);
        const prompt = promptResult.data?.prompt || "(creator)> ";

        this.dependencies.ModalManager.request({
            context: "terminal",
            type: "input",
            messageLines: [prompt],
            onConfirm: async (input) => {
                const resultJson = await FractalOS_Kernel.syscall('adventure', 'creator_process_command', [input]);
                const result = JSON.parse(resultJson);
                
                const data = result.data || {};

                if (data.output || result.error) {
                    await this.dependencies.OutputManager.appendToOutput(data.output || result.error, {
                        typeClass: result.success ? 'text-info' : 'text-error'
                    });
                }

                if (data.shouldExit || !result.success && result.error && result.error.includes("Exception")) {
                    this.state.isActive = false;
                }

                if (this.state.isActive) {
                    this._requestNextCommand();
                }
            },
            onCancel: () => {
                if (this.state.isActive) this._requestNextCommand();
            },
            options: this.state.commandContext.options,
        });
    },

    isActive: () => this.state.isActive,
};
