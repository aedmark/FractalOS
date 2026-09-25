const dependencies = {};

window.onload = async () => {
    if (window.NL_PORT) {
        Neutralino.init();
    }
    const domElements = {
        terminalBezel: document.getElementById("terminal-bezel"),
        terminalDiv: document.getElementById("terminal"),
        outputDiv: document.getElementById("output"),
        inputLineContainerDiv: document.querySelector(".terminal__input-line"),
        promptContainer: document.getElementById("prompt-container"),
        editableInputContainer: document.getElementById("editable-input-container"),
        editableInputDiv: document.getElementById("editable-input"),
        appLayer: document.getElementById("app-layer"),
    };

    const configManager = new ConfigManager();
    const storageManager = new StorageManager();
    const storageHAL = new StorageHAL();
    const groupManager = new GroupManager();
    const fsManager = new FileSystemManager(configManager);
    const sessionManager = new SessionManager();
    const sudoManager = new SudoManager();
    const messageBusManager = new MessageBusManager();
    const outputManager = new OutputManager();
    const terminalUI = new TerminalUI();
    const modalManager = new ModalManager();
    const appLayerManager = new AppLayerManager();
    const aliasManager = new AliasManager();
    const historyManager = new HistoryManager();
    const tabCompletionManager = new TabCompletionManager();
    const uiComponents = new UIComponents();
    const aiManager = new AIManager();
    const networkManager = new NetworkManager();
    const soundManager = new SoundManager();
    const auditManager = new AuditManager();
    const environmentManager = new EnvironmentManager();
    const themeManager = new ThemeManager();
    const uiStateManager = new UIStateManager();

    Object.assign(dependencies, {
        Config: configManager, StorageManager: storageManager, FileSystemManager: fsManager,
        SessionManager: sessionManager, SudoManager: sudoManager, GroupManager: groupManager,
        MessageBusManager: messageBusManager, OutputManager: outputManager, TerminalUI: terminalUI,
        ModalManager: modalManager, AppLayerManager: appLayerManager, AliasManager: aliasManager,
        HistoryManager: historyManager, TabCompletionManager: tabCompletionManager, Utils: Utils,
        ErrorHandler: ErrorHandler, AIManager: aiManager, NetworkManager: networkManager,
        UIComponents: uiComponents, domElements: domElements, SoundManager: soundManager,
        AuditManager: auditManager,
        EnvironmentManager: environmentManager,
        ThemeManager: themeManager,
        UIStateManager: uiStateManager,
        StorageHAL: storageHAL,
        CommandExecutor: CommandExecutor,
        PagerManager: window.PagerManager,
        TextAdventureModal: window.TextAdventureModal, Adventure_create: window.Adventure_create,
        BasicUI: window.BasicUI, ChidiUI: window.ChidiUI, EditorUI: window.EditorUI,
        GeminiChatManager: window.GeminiChatManager,
        GeminiChatUI: window.GeminiChatUI,
        LogUI: window.LogUI,
        PaintUI: window.PaintUI, TopUI: window.TopUI,
    });

    const userManager = new UserManager(dependencies);
    dependencies.UserManager = userManager;

    Object.values(dependencies).forEach(dep => {
        if (dep && typeof dep.setDependencies === 'function') {
            dep.setDependencies(dependencies);
        }
    });
    userManager.setDependencies(sessionManager, sudoManager, CommandExecutor, modalManager);
    sudoManager.setDependencies(fsManager, groupManager, configManager);
    outputManager.initialize(domElements);
    terminalUI.initialize(domElements);
    modalManager.initialize(domElements);
    appLayerManager.initialize(domElements);
    outputManager.initializeConsoleOverrides();

    await storageHAL.init();

    const persistedLocalStorage = await storageHAL.loadLocalStorage();
    if (persistedLocalStorage) {
        storageManager.importLocalStorage(persistedLocalStorage);
    }

    if (window.NL_PORT && typeof Neutralino !== 'undefined' && Neutralino.app) {
        Neutralino.events.on("windowClose", async () => {
            await storageHAL.saveLocalStorage(storageManager.exportLocalStorage());
            Neutralino.app.exit();
        });
    }

    await FractalOS_Kernel.initialize(dependencies);

    const onboardingComplete = storageManager.loadItem(configManager.STORAGE_KEYS.ONBOARDING_COMPLETE, "Onboarding Status", false);
    if (!onboardingComplete) {
        startOnboardingProcess(dependencies);
        return;
    }

    try {
        const fsJsonFromStorage = await storageHAL.load();
        if (fsJsonFromStorage) {
            await FractalOS_Kernel.syscall("filesystem", "load_state_from_json", [JSON.stringify(fsJsonFromStorage)]);
            await fsManager.setFsData(fsJsonFromStorage);
        } else {
            await outputManager.appendToOutput("No file system found. Initializing new one.", { typeClass: configManager.CSS_CLASSES.CONSOLE_LOG_MSG });
            await fsManager.initialize(configManager.USER.DEFAULT_NAME);
            const initialFsData = await fsManager.getFsData();
            await FractalOS_Kernel.syscall("filesystem", "load_state_from_json", [JSON.stringify(initialFsData)]);
            await storageHAL.save(initialFsData);
        }

        await userManager.initializeDefaultUsers();
        await groupManager.initialize();
        await aliasManager.initialize();
        await sessionManager.initializeStack();

        let initialUser = storageManager.loadItem(configManager.STORAGE_KEYS.LAST_CREATED_USER, "Last Created User", configManager.USER.DEFAULT_NAME);

        if (initialUser !== configManager.USER.DEFAULT_NAME) {
            await sessionManager.pushUserToStack(initialUser);
        }

        const sessionStatus = await sessionManager.loadAutomaticState(initialUser);

        if (initialUser !== configManager.USER.DEFAULT_NAME) {
            storageManager.removeItem(configManager.STORAGE_KEYS.LAST_CREATED_USER);
        }

        if (sessionStatus.newStateCreated) {
        }

        outputManager.clearOutput();
        if (sessionStatus.newStateCreated) {
            const currentUser = await userManager.getCurrentUser();
            await outputManager.appendToOutput(`${configManager.MESSAGES.WELCOME_PREFIX} ${currentUser.name}${configManager.MESSAGES.WELCOME_SUFFIX}`);
        }

        initializeTerminalEventListeners(domElements, dependencies);

        await terminalUI.updatePrompt();
        terminalUI.focusInput();
        await themeManager.loadAndApplyInitialTheme();
        console.log(`${configManager.OS.NAME} v.${configManager.OS.VERSION} loaded successfully!`);

    } catch (error) {
        console.error("Failed to initialize FractalOS on window.onload:", error, error.stack);
        if (domElements.outputDiv) {
            domElements.outputDiv.innerHTML += `<div class="text-error">FATAL ERROR: ${error.message}. Check console for details.</div>`;
        }
    }
};