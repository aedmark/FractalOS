const FractalOS_Kernel = {
    isReady: false,
    pyodide: null,
    kernel: null,
    dependencies: null,
    _initPromise: null,
    _resolveInit: null,

    async syscall(module, func, args = [], kwargs = {}) {
        if (!this.isReady || !this.kernel) {
            if (this._initPromise) {
                try { await this._initPromise; } catch (_) {
                }
            }
        }
        if (!this.isReady || !this.kernel) {
            return JSON.stringify({ "success": false, "error": "Error: Python kernel is not ready for syscall." });
        }
        try {
            const request = { module, "function": func, args, kwargs };
            const resultPromise = this.kernel.syscall_handler(JSON.stringify(request));
            return await resultPromise;
        } catch (error) {
            return JSON.stringify({ "success": false, "error": `Syscall bridge error: ${error.message}` });
        }
    },
    
    async getKernelFileManifest() {
        const response = await fetch('./core/manifest.json');
        if (!response.ok) {
            throw new Error(`Could not load core/manifest.json (HTTP ${response.status}). Run: python3 tools/gen_manifest.py`);
        }
        const lists = await response.json();
        const manifest = {};

        for (const file of lists.core) {
            manifest[`/core/${file}.py`] = `./core/${file}.py`;
        }
        manifest['/core/commands/__init__.py'] = null;
        manifest['/core/apps/__init__.py'] = null;
        for (const file of lists.apps) {
            manifest[`/core/apps/${file}.py`] = `./core/apps/${file}.py`;
        }
        for (const file of lists.commands) {
            manifest[`/core/commands/${file}.py`] = `./core/commands/${file}.py`;
        }
        return manifest;
    },


    async initialize(dependencies) {
        this.dependencies = dependencies;
        const { OutputManager, Config } = this.dependencies;
        if (!this._initPromise) {
            this._initPromise = new Promise((resolve) => { this._resolveInit = resolve; });
        }
        try {
            await OutputManager.appendToOutput(`Initializing Python runtime via Pyodide (Browser Mode)...`, { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });

            let pyodideIndexURL = './dep/pyodide/';

            this.pyodide = await loadPyodide({
                indexURL: pyodideIndexURL
            });

            await this.pyodide.loadPackage(["cryptography"]);
            await OutputManager.appendToOutput("Python runtime loaded. Loading kernel...", { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });

            this.pyodide.FS.mkdir('/core');
            this.pyodide.FS.mkdir('/core/commands');
            this.pyodide.FS.mkdir('/core/apps');
            await this.pyodide.runPythonAsync(`import sys; sys.path.append('/core')`);

            const filesToLoad = await this.getKernelFileManifest();

            for (const [pyPath, jsPath] of Object.entries(filesToLoad)) {
                if (jsPath) {
                    let code;
                    code = await (await fetch(jsPath)).text();
                    this.pyodide.FS.writeFile(pyPath, code, { encoding: 'utf8' });
                } else {
                    this.pyodide.FS.writeFile(pyPath, '', { encoding: 'utf8' });
                }
            }

            this.kernel = this.pyodide.pyimport("kernel");
            this.kernel.initialize_kernel(this.saveFileSystemToDB.bind(this));

            const pythonCommands = this.kernel.MODULE_DISPATCHER["executor"].commands.toJs();
            Config.COMMANDS_MANIFEST.push(...pythonCommands);
            Config.COMMANDS_MANIFEST.sort();

            try {
                const request = { module: "executor", "function": "set_js_native_commands", args: [Config.JS_NATIVE_COMMANDS], kwargs: {} };
                await this.kernel.syscall_handler(JSON.stringify(request));
            } catch (e) {
                console.warn("Failed to set JS native commands during init:", e);
            }

            this.isReady = true;
            await OutputManager.appendToOutput("FractalOS Python Kernel is online.", { typeClass: Config.CSS_CLASSES.SUCCESS_MSG });
            if (this._resolveInit) { this._resolveInit(); this._resolveInit = null; }
        } catch (error) {
            this.isReady = false;
            console.error("Pyodide initialization failed:", error);
            await OutputManager.appendToOutput(`FATAL: Python Kernel failed to load: ${error.message}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            if (this._resolveInit) { this._resolveInit(); this._resolveInit = null; }
        }
    },

    async execute_command(commandString, jsContextJson, stdinContent = null) {
        if (!this.isReady || !this.kernel) {
            if (this._initPromise) {
                try { await this._initPromise; } catch (_) {
                }
            }
        }
        if (!this.isReady || !this.kernel) {
            return JSON.stringify({ "success": false, "error": "Kernel not ready." });
        }
        return await this.kernel.execute_command(commandString, jsContextJson, stdinContent);
    },

    async saveFileSystemToDB(fsJsonString) {
        const { StorageHAL } = FractalOS_Kernel.dependencies;
        try {
            const fsData = JSON.parse(fsJsonString);
            await StorageHAL.save(fsData);
        } catch (e) {
            console.error("JS Bridge: Failed to save filesystem state via kernel callback.", e);
        }
    }
};
