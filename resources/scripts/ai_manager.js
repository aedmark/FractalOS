class AIManager {
    constructor() {
        this.dependencies = {};
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }


    async getAvailableModels(provider) {
        const fallback = provider === "gemini"
            ? ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"]
            : ["gemma3:latest", "llama3.1:8b", "llama3.2:3b", "qwen2.5:7b"];
        if (!FractalOS_Kernel || !FractalOS_Kernel.isReady) return fallback;
        try {
            // The syscall answers {success, data}; the list is in data.
            const result = JSON.parse(await FractalOS_Kernel.syscall("ai", "get_available_models", [provider]));
            if (result.success && Array.isArray(result.data)) return result.data;
            console.error("Failed to fetch models:", result.error);
        } catch (e) {
            console.error("Failed to fetch models:", e);
        }
        return fallback;
    }

    async getApiKey(provider, options = {}) {
        const {StorageManager, ModalManager, OutputManager, Config} = this.dependencies;
        if (provider !== "gemini") {
            return {success: true, data: {key: null}};
        }

        const key = StorageManager.loadItem(Config.STORAGE_KEYS.GEMINI_API_KEY);
        if (key) {
            return {success: true, data: {key, fromStorage: true}};
        }

        if (!options.isInteractive) {
            return {
                success: false,
                error: "A Gemini API key is required. Please run `samwise` once in an interactive terminal to set it up.",
            };
        }

        return new Promise((resolve) => {
            ModalManager.request({
                context: "terminal",
                type: "input",
                messageLines: ["Please enter your Gemini API key:"],
                obscured: true,
                onConfirm: (providedKey) => {
                    if (!providedKey || providedKey.trim() === "") {
                        resolve({
                            success: false,
                            error: "API key entry cancelled or empty.",
                        });
                        return;
                    }
                    StorageManager.saveItem(
                        Config.STORAGE_KEYS.GEMINI_API_KEY,
                        providedKey,
                        "Gemini API Key"
                    );
                    OutputManager.appendToOutput("API Key saved.", {
                        typeClass: Config.CSS_CLASSES.SUCCESS_MSG,
                    });
                    resolve({
                        success: true,
                        data: {
                            key: providedKey,
                            fromStorage: false,
                        },
                    });
                },
                onCancel: () => {
                    resolve({success: false, error: "API key entry cancelled."});
                },
                options,
            });
        });
    }
}