// /scripts/boot.js

window.sessionStartTime = new Date();

// --- Onboarding Process ---
function startOnboardingProcess(dependencies) {
    const { AppLayerManager, OutputManager, TerminalUI } = dependencies;
    OutputManager.clearOutput();
    TerminalUI.hideInputLine();

    const OnboardingApp = window.OnboardingManager;
    if (OnboardingApp) {
        const appInstance = new OnboardingApp();
        AppLayerManager.show(appInstance, { dependencies });
    } else {
        console.error("OnboardingManager app not found!");
        OutputManager.appendToOutput("CRITICAL ERROR: Onboarding process could not be started.");
    }
}

// --- Asynchronous Python Command Execution ---
async function executePythonCommand(rawCommandText, options = {}) {
    const { isInteractive = true, scriptingContext = null, stdinContent = null, asUser = null } = options;
    const { ModalManager, OutputManager, TerminalUI, AppLayerManager, HistoryManager, Config, ErrorHandler, Utils, FileSystemManager } = dependencies;

    if (isInteractive && !scriptingContext) {
        TerminalUI.hideInputLine();
        const prompt = TerminalUI.getPromptText();
        await OutputManager.appendToOutput(`${prompt}${rawCommandText.trim()}`, { noCinematic: true });
        if (!options.isSudoContinuation) {
            await HistoryManager.add(rawCommandText.trim());
        }
    }

    if (rawCommandText.trim() === "") {
        if (isInteractive) await finalizeInteractiveModeUI(rawCommandText);
        return { success: true, output: "" };
    }

    const commandName = rawCommandText.trim().split(/\s+/)[0];
    const aiCommands = ['gemini', 'storyboard', 'remix', 'forge', 'planner'];
    let thinkingMessageDiv = null;

    if (aiCommands.includes(commandName) && isInteractive && !scriptingContext) {
        const randomMessage = Config.MESSAGES.AI_LOADING_MESSAGES[Math.floor(Math.random() * Config.MESSAGES.AI_LOADING_MESSAGES.length)];
        thinkingMessageDiv = Utils.createElement('div', {
            className: `${Config.CSS_CLASSES.OUTPUT_LINE} ${Config.CSS_CLASSES.CONSOLE_LOG_MSG}`,
            textContent: `🧠 ${randomMessage}`
        });
        OutputManager.cachedOutputDiv.appendChild(thinkingMessageDiv);
        TerminalUI.scrollOutputToEnd();
    }

    let result;
    try {
        const kernelContextJson = await createKernelContext({ asUser });
        const jsonResult = await OopisOS_Kernel.execute_command(rawCommandText, kernelContextJson, stdinContent);
        const pyResult = JSON.parse(jsonResult);

        if (pyResult.success) {
            if (Array.isArray(pyResult.effects)) {
                for (const eff of pyResult.effects) {
                    await handleEffect(eff, options);
                }
                result = { success: true };
            } else if (pyResult.effect) {
                result = await handleEffect(pyResult, options);
            } else if (pyResult.output !== undefined) {
                if (isInteractive) {
                    if (pyResult.output) {
                        await OutputManager.appendToOutput(pyResult.output);
                    }
                } else {
                    return { success: true, output: pyResult.output };
                }
            }
            const updatedFsData = await FileSystemManager.getFsData();
            FileSystemManager.setFsData(updatedFsData);

        } else {
            // This is the new, improved error handling logic!
            const errorObject = ErrorHandler.createError(pyResult.error);
            let fullErrorMessage = errorObject.error.message;
            if (errorObject.error.suggestion) {
                fullErrorMessage += `\nSuggestion: ${errorObject.error.suggestion}`;
            }

            // Still log the raw error to the dev console for us engineers!
            console.error("Python Execution Error:", pyResult.error);

            await OutputManager.appendToOutput(fullErrorMessage, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            result = errorObject;
        }
    } catch (e) {
        const errorMsg = e.message || "An unknown JavaScript error occurred.";
        await OutputManager.appendToOutput(errorMsg, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
        result = { success: false, error: errorMsg };
    } finally {
        if (thinkingMessageDiv) {
            thinkingMessageDiv.remove();
        }
    }

    if (isInteractive) {
        await finalizeInteractiveModeUI(rawCommandText);
    }

    return result || { success: true, output: "" };
}

// --- Command Execution Wrapper ---
const CommandExecutor = {
    processSingleCommand: executePythonCommand,
    getActiveJobs: () => activeJobs,
};

// --- Kernel Context Creation ---
async function createKernelContext(options = {}) {
    const { asUser = null } = options;
    const { FileSystemManager, UserManager, GroupManager, StorageManager, Config, SessionManager, AliasManager, HistoryManager } = dependencies;

    let user;
    let primaryGroup;

    if (asUser) {
        user = { name: asUser.name };
        primaryGroup = asUser.primaryGroup;
    } else {
        user = await UserManager.getCurrentUser();
        primaryGroup = await UserManager.getPrimaryGroupForUser(user.name);
    }

    const allUsers = StorageManager.loadItem(Config.STORAGE_KEYS.USER_CREDENTIALS, "User list", {});
    const allUsernames = Object.keys(allUsers);
    const userGroupsMap = {};
    for (const username of allUsernames) {
        userGroupsMap[username] = await GroupManager.getGroupsForUser(username);
    }
    if (!userGroupsMap['Guest']) {
        userGroupsMap['Guest'] = await GroupManager.getGroupsForUser('Guest');
    }
    const apiKey = StorageManager.loadItem(Config.STORAGE_KEYS.GEMINI_API_KEY);

    // This syncs the JS-side session state to Python before execution
    await OopisOS_Kernel.syscall("alias", "load_aliases", [await AliasManager.getAllAliases()]);
    await OopisOS_Kernel.syscall("history", "set_history", [await HistoryManager.getFullHistory()]);

    return JSON.stringify({
        current_path: FileSystemManager.getCurrentPath(),
        user_context: { name: user.name, group: primaryGroup },
        users: allUsers,
        user_groups: userGroupsMap,
        groups: await GroupManager.getAllGroups(),
        jobs: activeJobs,
        config: {
            MAX_VFS_SIZE: Config.FILESYSTEM.MAX_VFS_SIZE,
            NETWORKING_ENABLED: Config.NETWORKING.NETWORKING_ENABLED, // Pass the flag
        },
        api_key: apiKey,
        session_start_time: window.sessionStartTime.toISOString(),
        session_stack: await SessionManager.getStack()
    });
}

// --- Terminal UI State Initialization ---
async function finalizeInteractiveModeUI(originalCommandText) {
    const { TerminalUI, AppLayerManager, HistoryManager } = dependencies;
    if (!TerminalUI.isSearchingHistory) {
        TerminalUI.clearInput();
        await TerminalUI.updatePrompt();
    }
    if (!AppLayerManager.isActive()) {
        TerminalUI.showInputLine();
        TerminalUI.setInputState(true);
        TerminalUI.focusInput();
    }
    TerminalUI.scrollOutputToEnd();
    if (!TerminalUI.getIsNavigatingHistory() && originalCommandText.trim()) {
        await HistoryManager.resetIndex();
    }
    TerminalUI.setIsNavigatingHistory(false);
}
function initializeTerminalEventListeners(domElements, dependencies) {
    const { AppLayerManager, ModalManager, TerminalUI, TabCompletionManager, HistoryManager, SoundManager } = dependencies;

    domElements.terminalDiv.addEventListener("click", (e) => {
        if (AppLayerManager.isActive()) return;

        // If text has been selected, don't steal focus.
        // This allows the user to copy text from the output.
        const selection = window.getSelection();
        if (selection && selection.toString().length > 0) {
            return;
        }

        if (!e.target.closest("button, a")) TerminalUI.focusInput();
    });

    document.addEventListener("keydown", async (e) => {
        if (ModalManager.isAwaiting()) {
            if (TerminalUI.isObscured()) {
                e.preventDefault();
                if (e.key === "Enter") {
                    await ModalManager.handleTerminalInput(TerminalUI.getCurrentInputValue());
                } else if (e.key === "Escape") {
                    await ModalManager.handleTerminalInput(null);
                } else if (e.key === "Backspace" || e.key === "Delete" || (e.key.length === 1 && !e.ctrlKey && !e.metaKey)) {
                    TerminalUI.updateInputForObscure(e.key);
                }
                return;
            }
            if (e.key === "Enter") {
                e.preventDefault();
                await ModalManager.handleTerminalInput(TerminalUI.getCurrentInputValue());
            } else if (e.key === "Escape") {
                e.preventDefault();
                await ModalManager.handleTerminalInput(null);
            }
            return;
        }


        if (AppLayerManager.isActive()) {
            const activeApp = AppLayerManager.activeApp;
            if (activeApp?.handleKeyDown) activeApp.handleKeyDown(e);
            return;
        }

        if (e.target !== domElements.editableInputDiv && !TerminalUI.isSearchingHistory) return;

        // --- History Search Logic ---
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            await TerminalUI.startHistorySearch();
            return;
        }

        if (TerminalUI.isSearchingHistory) {
            e.preventDefault();
            if (e.key === 'Enter') {
                await TerminalUI.endHistorySearch();
                await executePythonCommand(TerminalUI.getCurrentInputValue(), { isInteractive: true });
            } else if (e.key === 'Escape') {
                await TerminalUI.cancelHistorySearch();
            } else {
                await TerminalUI.updateHistorySearch(e);
            }
            return;
        }
        // --- End History Search Logic ---

        switch (e.key) {
            case "Enter":
                e.preventDefault();
                if (!SoundManager.isInitialized) await SoundManager.initialize();
                TabCompletionManager.resetCycle();
                await executePythonCommand(TerminalUI.getCurrentInputValue(), { isInteractive: true });
                break;
            case "ArrowUp":
                e.preventDefault();
                const prevCmd = await HistoryManager.getPrevious();
                if (prevCmd !== null) TerminalUI.setCurrentInputValue(prevCmd, true);
                break;
            case "ArrowDown":
                e.preventDefault();
                const nextCmd = await HistoryManager.getNext();
                if (nextCmd !== null) TerminalUI.setCurrentInputValue(nextCmd, true);
                break;
            case "Tab":
                e.preventDefault();
                const currentInput = TerminalUI.getCurrentInputValue();
                const result = await TabCompletionManager.handleTab(currentInput, TerminalUI.getSelection().start);
                if (result?.textToInsert !== null) {
                    TerminalUI.setCurrentInputValue(result.textToInsert, false);
                    TerminalUI.setCaretPosition(domElements.editableInputDiv, result.newCursorPos);
                }
                break;
        }
    });

    domElements.editableInputDiv.addEventListener("paste", (e) => {
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData).getData("text/plain").replace(/\r?\n|\r/g, " ");
        TerminalUI.handlePaste(text);
    });
}