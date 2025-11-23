// --- Effect Handler ---
async function handleEffect(result, options) {
    const {
        FileSystemManager, TerminalUI, SoundManager, SessionManager, AppLayerManager,
        UserManager, ErrorHandler, Config, OutputManager, PagerManager, Utils, domElements,
        GroupManager, NetworkManager, MessageBusManager, ModalManager, StorageManager,
        AuditManager, StorageHAL, SudoManager, ThemeManager, UIStateManager
    } = dependencies;

    switch (result.effect) {
        case 'sudo_exec': {
            const currentUser = await UserManager.getCurrentUser();
            const executeAsRoot = async () => {
                SudoManager.updateUserTimestamp(currentUser.name);
                await AuditManager.log(currentUser.name, 'SUDO_SUCCESS', `Command: ${result.command}`);
                const execOptions = { ...options, isInteractive: false, asUser: { name: 'root', primaryGroup: 'root' }, isSudoContinuation: true };
                await CommandExecutor.processSingleCommand(result.command, execOptions);
            };

            if (SudoManager.isUserTimestampValid(currentUser.name)) {
                await executeAsRoot();
                break;
            }

            let passwordToTry = result.password;
            if (passwordToTry === null) {
                passwordToTry = await new Promise((resolve) => {
                    ModalManager.request({
                        context: 'terminal', type: 'input',
                        messageLines: [`[sudo] password for ${currentUser.name}:`],
                        obscured: true,
                        onConfirm: (pwd) => resolve(pwd),
                        onCancel: () => resolve(null),
                        options
                    });
                });
            }

            if (passwordToTry === null) {
                await AuditManager.log(currentUser.name, 'SUDO_FAILURE', `Command: ${result.command} (Reason: Password prompt cancelled)`);
                await OutputManager.appendToOutput("sudo: authentication cancelled", { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                break;
            }

            const verifyResultJson = await OopisOS_Kernel.syscall("users", "verify_password", [currentUser.name, passwordToTry]);
            const verifyResult = JSON.parse(verifyResultJson);

            if (verifyResult.success && verifyResult.data) {
                await executeAsRoot();
            } else {
                await AuditManager.log(currentUser.name, 'SUDO_FAILURE', `Command: ${result.command} (Reason: Incorrect password)`);
                await OutputManager.appendToOutput("sudo: incorrect password", { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            }
            break;
        }
        case 'full_reset':
            await OutputManager.appendToOutput("Performing factory reset... The system will reboot.", { typeClass: Config.CSS_CLASSES.WARNING_MSG });
            await StorageHAL.clear(); // Clears IndexedDB
            localStorage.clear(); // Clears all local storage for this origin
            setTimeout(() => window.location.reload(), 2000); // Give user time to read message
            break;

        case 'confirm':
            ModalManager.request({
                context: 'terminal',
                type: 'confirm',
                messageLines: result.message,
                onConfirm: async () => {
                    if (result.on_confirm_command) {
                        await CommandExecutor.processSingleCommand(result.on_confirm_command, { isInteractive: false });
                    } else if (result.on_confirm) {
                        await handleEffect(result.on_confirm, options);
                    }
                },
                onCancel: () => {
                    OutputManager.appendToOutput('Operation cancelled.', { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
                },
                options,
            });
            break;
        case 'confirm_ai_command':
            ModalManager.request({
                context: 'terminal',
                type: 'confirm',
                messageLines: [
                    "The AI agent wants to run the following command:",
                    `  ${result.command}`,
                    "Do you want to allow this action?"
                ],
                onConfirm: async () => {
                    await CommandExecutor.processSingleCommand(result.command, { isInteractive: false });
                },
                onCancel: () => {
                    OutputManager.appendToOutput('Execution cancelled by user.', { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
                },
                options,
            });
            break;
        case 'execute_script':
        case 'execute_commands': {
            const commandsToRun = result.lines || result.commands;
            const scriptArgs = result.args || [];
            const envMgr = dependencies.EnvironmentManager;
            await envMgr.push();

            const scriptingContext = {
                isScripting: true,
                lines: commandsToRun.map(item => (typeof item === 'string' ? item : item.command)),
                currentLineIndex: -1
            };

            try {
                for (const item of commandsToRun) {
                    scriptingContext.currentLineIndex++;
                    let commandText;
                    let passwordPipe = null;

                    if (typeof item === 'string') {
                        commandText = item;
                    } else {
                        commandText = item.command;
                        passwordPipe = item.password_pipe;
                    }

                    commandText = commandText.replace(/\$@/g, scriptArgs.map(arg => `'${arg.replace(/'/g, "'\\''")}'`).join(' '));
                    commandText = commandText.replace(/\$#/g, scriptArgs.length);
                    for (let i = 0; i < scriptArgs.length; i++) {
                        commandText = commandText.replace(new RegExp(`\\$${i + 1}`, 'g'), scriptArgs[i]);
                    }

                    const execOptions = {
                        isInteractive: false,
                        scriptingContext: scriptingContext,
                        stdinContent: passwordPipe ? passwordPipe.join('\n') : null
                    };
                    const commandResult = await CommandExecutor.processSingleCommand(commandText, execOptions);

                    if (commandResult.success) {
                        if (commandResult.output) {
                            await OutputManager.appendToOutput(commandResult.output);
                        }
                    } else {
                        await OutputManager.appendToOutput(`run: error on line ${scriptingContext.currentLineIndex + 1}: ${commandText}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                        if (commandResult.error) {
                            let errorMessage = commandResult.error.message || commandResult.error;
                            if (commandResult.error.suggestion) {
                                errorMessage += `\nSuggestion: ${commandResult.error.suggestion}`;
                            }
                            await OutputManager.appendToOutput(errorMessage, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                        }
                        break;
                    }
                }
            } finally {
                await envMgr.pop();
            }
            break;
        }

        case 'useradd': {
            const newPassword = await new Promise((resolve) => {
                ModalManager.request({
                    context: 'terminal', type: 'input', messageLines: [`Enter new password for ${result.username}:`],
                    obscured: true, onConfirm: (pwd) => resolve(pwd), onCancel: () => resolve(null)
                });
            });
            if (newPassword === null) {
                await OutputManager.appendToOutput("User creation cancelled.", { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
                break;
            }
            const confirmPassword = await new Promise((resolve) => {
                ModalManager.request({
                    context: 'terminal', type: 'input', messageLines: [`Confirm new password for ${result.username}:`],
                    obscured: true, onConfirm: (pwd) => resolve(pwd), onCancel: () => resolve(null)
                });
            });
            if (confirmPassword === null) {
                await OutputManager.appendToOutput("User creation cancelled.", { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
                break;
            }
            if (newPassword !== confirmPassword) {
                await OutputManager.appendToOutput(Config.MESSAGES.PASSWORD_MISMATCH, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                break;
            }
            const command = `useradd ${result.username}`;
            const stdin = `${newPassword}\n${confirmPassword}`;
            await CommandExecutor.processSingleCommand(command, { isInteractive: false, stdinContent: stdin });
            break;
        }

        case 'removeuser': {
            const { username, remove_home } = result;
            const message = [`Are you sure you want to permanently delete user '${username}'?`];
            if (remove_home) {
                message.push("This will also delete their home directory and all its contents.");
            }
            message.push("This action cannot be undone.");

            ModalManager.request({
                context: 'terminal', type: 'confirm', messageLines: message,
                onConfirm: async () => {
                    const deleteResultJson = await OopisOS_Kernel.syscall("users", "delete_user_and_data", [username, remove_home]);
                    const deleteResult = JSON.parse(deleteResultJson);
                    if (deleteResult.success) {
                        await UserManager.syncUsersFromKernel();
                        const allGroups = await GroupManager.getAllGroups();
                        await GroupManager.syncAndSave(allGroups);
                        await OutputManager.appendToOutput(`User '${username}' removed successfully.`);
                    } else {
                        await OutputManager.appendToOutput(`Error: ${deleteResult.error}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                    }
                },
            });
            break;
        }

        case 'background_job':
            const newJobId = ++backgroundProcessIdCounter;
            const abortController = new AbortController();
            const jobUser = (await UserManager.getCurrentUser()).name;

            activeJobs[newJobId] = {
                command: result.command_string, status: 'running', user: jobUser,
                startTime: new Date().toISOString(), abortController: abortController
            };
            MessageBusManager.registerJob(newJobId);

            (async () => {
                const bgOptions = { ...options, isInteractive: false, suppressOutput: true, signal: abortController.signal };
                await executePythonCommand(result.command_string, bgOptions);
                if (activeJobs[newJobId]) {
                    delete activeJobs[newJobId];
                    MessageBusManager.unregisterJob(newJobId);
                }
            })();
            await OutputManager.appendToOutput(`[${newJobId}] ${result.command_string}`);
            break;

        case 'login':

        case 'su': { // 'su' and 'login' effects are functionally identical
            const loginResult = await UserManager.loginUser(result.username, result.password);
            if (!loginResult.success) {
                await OutputManager.appendToOutput(loginResult.error.message || loginResult.error, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            }
            break;
        }

        case 'logout': {
            const poppedUser = await SessionManager.popUserFromStack();
            if (poppedUser) {
                const newCurrentUser = await SessionManager.getCurrentUserFromStack();
                await OutputManager.appendToOutput(`Logged out of ${poppedUser}. Current user is now ${newCurrentUser}.`);
                await SessionManager.loadAutomaticState(newCurrentUser);
            } else {
                await OutputManager.appendToOutput("Not logged in to any additional user sessions.", { typeClass: Config.CSS_CLASSES.WARNING_MSG });
            }
            break;
        }

        case 'passwd': {
            const newPassword = await new Promise((resolve) => {
                ModalManager.request({
                    context: 'terminal', type: 'input',
                    messageLines: [`Enter new password for ${result.username}:`],
                    obscured: true, onConfirm: (pwd) => resolve(pwd), onCancel: () => resolve(null)
                });
            });
            if (newPassword === null) {
                await OutputManager.appendToOutput("Password change cancelled.", { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
                break;
            }
            const confirmPassword = await new Promise((resolve) => {
                ModalManager.request({
                    context: 'terminal', type: 'input',
                    messageLines: [`Confirm new password for ${result.username}:`],
                    obscured: true, onConfirm: (pwd) => resolve(pwd), onCancel: () => resolve(null)
                });
            });
            if (confirmPassword === null) {
                await OutputManager.appendToOutput("Password change cancelled.", { typeClass: Config.CSS_CLASSES.CONSOLE_LOG_MSG });
                break;
            }
            if (newPassword !== confirmPassword) {
                await OutputManager.appendToOutput(Config.MESSAGES.PASSWORD_MISMATCH, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                break;
            }

            const changeResultJson = await OopisOS_Kernel.syscall("users", "change_password", [result.username, newPassword]);
            const changeResult = JSON.parse(changeResultJson);

            if (changeResult.success) {
                await UserManager.syncUsersFromKernel();
                await OutputManager.appendToOutput(`Password for ${result.username} changed successfully.`);
            } else {
                await OutputManager.appendToOutput(`Error: ${changeResult.error}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            }
            break;
        }

        case 'signal_job':
            const signalResult = sendSignalToJob(result.job_id, result.signal);
            if (!signalResult.success) {
                await OutputManager.appendToOutput(signalResult.error, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            }
            break;

        case 'change_directory':
            await FileSystemManager.setCurrentPath(result.path);
            await TerminalUI.updatePrompt();
            break;

        case 'clear_screen':
            await OutputManager.clearOutput();
            break;

        case 'beep':
            SoundManager.beep();
            break;

        case 'reboot':
            await OutputManager.appendToOutput("Rebooting...");
            setTimeout(() => window.location.reload(), 1000);
            break;

        case 'delay':
            await Utils.safeDelay(result.milliseconds);
            break;

        case 'launch_app':
            const App = window[result.app_name + "Manager"];
            if (App) {
                const appInstance = new App();
                AppLayerManager.show(appInstance, { ...options, dependencies, ...result.options });
            } else {
                console.error(`Attempted to launch unknown app: ${result.app_name}`);
            }
            break;

        case 'page_output':
            const lineCount = result.content.split('\n').length;
            const outputDiv = domElements.outputDiv;
            const computedStyle = window.getComputedStyle(outputDiv);
            const { height: lineHeight } = Utils.getCharacterDimensions(computedStyle.font);
            const terminalRows = lineHeight > 0 ? Math.floor(outputDiv.clientHeight / lineHeight) - 2 : 24;
            if (lineCount <= terminalRows) {
                await OutputManager.appendToOutput(result.content);
            } else {
                const pagerApp = new dependencies.PagerManager();
                AppLayerManager.show(pagerApp, {
                    dependencies,
                    content: result.content,
                    mode: result.mode
                });
            }
            break;

        case 'trigger_upload_flow':
            return new Promise(async (resolve) => {
                const input = Utils.createElement("input", { type: "file", multiple: true, style: { display: 'none' } });
                let fileSelected = false;

                const cleanup = () => {
                    window.removeEventListener('focus', onFocus);
                    if (input.parentNode) {
                        document.body.removeChild(input);
                    }
                };

                input.onchange = async (e) => {
                    fileSelected = true;
                    cleanup();
                    const files = e.target.files;
                    if (!files || files.length === 0) {
                        resolve({ success: true, output: "Upload cancelled." });
                        return;
                    }
                    const filesForPython = await Promise.all(Array.from(files).map(file => {
                        return new Promise((res, rej) => {
                            const reader = new FileReader();
                            reader.onload = (event) => res({ name: file.name, path: FileSystemManager.getAbsolutePath(file.name), content: event.target.result });
                            reader.onerror = () => rej(new Error(`Could not read file: ${file.name}`));
                            reader.readAsText(file);
                        });
                    }));
                    const userContext = await createKernelContext();
                    const uploadResult = JSON.parse(await OopisOS_Kernel.execute_command("_upload_handler", userContext, JSON.stringify(filesForPython)));
                    await OutputManager.appendToOutput(uploadResult.output || uploadResult.error, { typeClass: uploadResult.success ? null : 'text-error' });
                    resolve({ success: uploadResult.success });
                };

                const onFocus = () => {
                    window.removeEventListener('focus', onFocus);
                    setTimeout(() => {
                        if (!fileSelected) {
                            cleanup();
                            resolve({ success: true, output: "Upload cancelled." });
                        }
                    }, 500);
                };

                window.addEventListener('focus', onFocus);
                document.body.appendChild(input);
                input.click();
            });

        case 'netcat_listen':
            await OutputManager.appendToOutput(`Listening on instance ${NetworkManager.getInstanceId()} in '${result.execute ? 'execute' : 'print'}' mode...`);
            NetworkManager.setListenCallback((payload) => {
                const { sourceId, data } = payload;
                if (result.execute) {
                    OutputManager.appendToOutput(`[NET EXEC from ${sourceId}]> ${data}`);
                    executePythonCommand(data, { isInteractive: false });
                } else {
                    OutputManager.appendToOutput(`[NET] From ${sourceId}: ${data}`);
                }
            });
            break;

        case 'netcat_send':
            await NetworkManager.sendMessage(result.targetId, 'direct_message', result.message);
            break;

        case 'netstat_display':
            const output = [`Your Instance ID: ${NetworkManager.getInstanceId()}`, "\nDiscovered Remote Instances:"];
            const instances = NetworkManager.getRemoteInstances();
            if (instances.length === 0) output.push("  (None)");
            else instances.forEach(id => {
                const peer = NetworkManager.getPeers().get(id);
                output.push(`  - ${id} (Status: ${peer ? peer.connectionState : 'Disconnected'})`);
            });
            await OutputManager.appendToOutput(output.join('\n'));
            break;

        case 'read_messages':
            const messages = MessageBusManager.getMessages(result.job_id);
            // This implicitly becomes the command's output
            await OutputManager.appendToOutput(messages.join(" "));
            break;

        case 'post_message':
            MessageBusManager.postMessage(result.job_id, result.message);
            break;

        case 'play_sound':
            if (!SoundManager.isInitialized) { await SoundManager.initialize(); }
            SoundManager.playNote(result.notes, result.duration);
            const durationInSeconds = new Tone.Time(result.duration).toSeconds();
            await new Promise(resolve => setTimeout(resolve, Math.ceil(durationInSeconds * 1000)));
            break;

        case 'sync_session_state':
            if (result.aliases) {
                await OopisOS_Kernel.syscall("alias", "load_aliases", [result.aliases]);
                StorageManager.saveItem(Config.STORAGE_KEYS.ALIAS_DEFINITIONS, result.aliases, "Aliases");
            }
            if (result.env) {
                await OopisOS_Kernel.syscall("env", "load", [result.env]);
                await SessionManager.saveAutomaticState((await UserManager.getCurrentUser()).name);
            }
            break;

        case 'sync_group_state':
            if (result.groups) {
                await GroupManager.syncAndSave(result.groups);
            }
            break;

        case 'sync_user_and_group_state':
            if (result.users) {
                await UserManager.syncUsersFromKernel(); // This fetches from Python kernel's memory
                // After syncing, save the new state to JS localStorage
                const allUsers = await OopisOS_Kernel.syscall("users", "get_all_users");
                const parsedUsers = JSON.parse(allUsers);
                if (parsedUsers.success) {
                    StorageManager.saveItem(Config.STORAGE_KEYS.USER_CREDENTIALS, parsedUsers.data, "User Credentials");
                }
            }
            if (result.groups) {
                await GroupManager.syncAndSave(result.groups);
            }
            break;

        case 'display_prose':
            await OutputManager.appendToOutput(
                DOMPurify.sanitize(marked.parse(`### ${result.header}\n\n${result.content}`)),
                { asBlock: true, typeClass: 'prose-output' }
            );
            break;

        case 'apply_theme':
            await ThemeManager.applyTheme(result.themeName);
            await OutputManager.appendToOutput(`Theme '${result.themeName}' applied.`);
            break;

        case 'dump_screen_text': {
            try {
                const textSource = document.getElementById('output');
                const innerText = textSource ? textSource.innerText : '';
                const destPathArg = result.path || 'screen.txt';
                const absPath = FileSystemManager.getAbsolutePath(destPathArg, FileSystemManager.getCurrentPath());
                const currentUser = await UserManager.getCurrentUser();
                const primaryGroup = await UserManager.getPrimaryGroupForUser(currentUser.name);
                const writeRes = await FileSystemManager.createOrUpdateFile(absPath, innerText, { currentUser: currentUser.name, primaryGroup });
                if (!writeRes.success) {
                    await OutputManager.appendToOutput(writeRes.error || 'Failed to write screen text.', { typeClass: Config.CSS_CLASSES.ERROR_MSG });
                }
            } catch (e) {
                await OutputManager.appendToOutput(`printscreen error: ${e.message}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            }
            break;
        }

        case 'capture_screenshot_png': {
            try {
                const target = document.getElementById('terminal') || document.body;
                const canvas = await html2canvas(target);
                const dataUrl = canvas.toDataURL('image/png');
                const link = document.createElement('a');
                link.href = dataUrl;
                link.download = result.filename || 'FractalOS_Screenshot.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } catch (e) {
                await OutputManager.appendToOutput(`screenshot error: ${e.message}`, { typeClass: Config.CSS_CLASSES.ERROR_MSG });
            }
            break;
        }

        case 'toggle_cinematic_mode':
            UIStateManager.toggleCinematicMode(result.mode);
            break;

        default:
            await OutputManager.appendToOutput(`Unknown effect from Python: ${result.effect}`, { typeClass: 'text-warning' });
            break;
    }
}