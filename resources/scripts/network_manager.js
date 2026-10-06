// scripts/network_manager.js

class NetworkManager {
    constructor() {
        this.instanceId = `oos-${Date.now()}-${Math.floor(Math.random() * 100)}`;
        this.channel = new BroadcastChannel('fractal-network');
        this.dependencies = {};
        this.isNetworkingEnabled = false;
        this.listenCallback = null;
        this.messageQueue = [];
        this.pingCallbacks = new Map();
        this.signalingServerUrl = 'ws://localhost:8080';
        this.websocket = null;
        this.peers = new Map();
        this.remoteInstances = new Set();
        this.attachedSession = null;
        this.attachedClients = new Set();
        this.pendingAttachRequests = new Map();
        this.pendingExecRequests = new Map();
        this.pendingFileSendRequests = new Map();
        this.pendingFilePullRequests = new Map();
        this.pendingAgentDelegations = new Map();
        this.activeGameApp = null;
        this.peerMetadata = new Map();

        this.channel.onmessage = this._handleBroadcastMessage.bind(this);

        if (typeof window !== 'undefined') {
            window.addEventListener('beforeunload', () => {
                if (this.isNetworkingEnabled) {
                    try {
                        this.sendMessage('broadcast', 'goodbye', { sourceId: this.instanceId });
                    } catch (_) {}
                }
            });
        }

        console.log(`NetworkManager initialized with ID: ${this.instanceId}`);
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    async startNetworking() {
        if (this.dependencies.Config?.NETWORKING?.NETWORKING_ENABLED) {
            this.isNetworkingEnabled = true;
            this.signalingServerUrl = this.dependencies.Config.NETWORKING.SIGNALING_SERVER_URL;
            
            try {
                const netConfNode = await this.dependencies.FileSystemManager.getNodeByPath('/etc/network.conf');
                if (netConfNode && netConfNode.content) {
                    const netConf = JSON.parse(netConfNode.content);
                    if (netConf.runSignalingServer) {
                        if (typeof Neutralino !== 'undefined' && Neutralino.os) {
                            console.log('Starting local signaling server via Neutralino...');
                            Neutralino.os.spawnProcess('python3 extras/signaling_server.py');
                            this.signalingServerUrl = 'ws://localhost:8765';
                        } else {
                            console.warn('Cannot run signaling server: not in Portable mode.');
                        }
                    }
                }
            } catch (e) {
                console.warn('Could not read /etc/network.conf', e);
            }

            // Announce presence across local browser tabs
            try {
                this.channel.postMessage({ type: 'discover', sourceId: this.instanceId, targetId: 'broadcast' });
            } catch (_) {}

            this._initializeSignaling();
        } else {
            console.log("Networking is disabled by default. Set NETWORKING.NETWORKING_ENABLED to true in config.js to enable it.");
        }
    }

    getInstanceId() {
        return this.instanceId;
    }

    getRemoteInstances() {
        return Array.from(this.remoteInstances);
    }

    getPeers() {
        return this.peers;
    }

    isAttached() {
        return !!this.attachedSession;
    }

    getAttachedSession() {
        return this.attachedSession;
    }

    getAttachedClients() {
        return Array.from(this.attachedClients);
    }

    setListenCallback(callback) {
        this.listenCallback = callback;
    }

    _handleBroadcastMessage(event) {
        if (!this.isNetworkingEnabled) return;
        this._processIncomingMessage(event.data);
    }

    _handleDiscover(payload) {
        if (!payload.sourceId || payload.sourceId === this.instanceId) return;
        const isNew = !this.remoteInstances.has(payload.sourceId);
        this.remoteInstances.add(payload.sourceId);

        if (payload.data) {
            this.peerMetadata.set(payload.sourceId, {
                ...payload.data,
                lastSeen: Date.now()
            });
        } else if (!this.peerMetadata.has(payload.sourceId)) {
            this.peerMetadata.set(payload.sourceId, {
                user: 'user@fractal',
                capabilities: ['shell', 'mesh-cp', 'netgame'],
                lastSeen: Date.now()
            });
        }

        if (isNew) {
            console.log(`Discovered remote peer: ${payload.sourceId}`);
            // If peer announced itself to broadcast or to us, acknowledge with our discovery info
            if (payload.targetId === 'broadcast' || !payload.targetId) {
                const presencePayload = {
                    type: 'discover',
                    sourceId: this.instanceId,
                    targetId: payload.sourceId,
                    data: this.getLocalMetadata()
                };
                try { this.channel.postMessage(presencePayload); } catch (_) {}
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    this.websocket.send(JSON.stringify(presencePayload));
                }
            }
        }
    }

    _initializeSignaling() {
        if (!this.isNetworkingEnabled) return;
        this.websocket = new WebSocket(this.signalingServerUrl);

        this.websocket.onopen = () => {
            console.log('Connected to signaling server.');
            const presencePayload = {
                type: 'discover',
                sourceId: this.instanceId,
                targetId: 'broadcast',
                data: this.getLocalMetadata()
            };
            this.websocket.send(JSON.stringify(presencePayload));
        };

        this.websocket.onmessage = async (event) => {
            try {
                let messageData = event.data;
                if (messageData instanceof Blob) {
                    messageData = await messageData.text();
                }
                const payload = JSON.parse(messageData);
                if (payload.sourceId === this.instanceId) return;

                switch (payload.type) {
                    case 'discover':
                        this._handleDiscover(payload);
                        break;
                    case 'offer': await this._handleOffer(payload); break;
                    case 'answer': await this._handleAnswer(payload); break;
                    case 'candidate': await this._handleCandidate(payload); break;
                    default:
                        await this._processIncomingMessage(payload);
                        break;
                }
            } catch (error) {
                console.error('Error parsing signaling message:', error);
            }
        };

        this.websocket.onclose = () => {
            console.log('Disconnected from signaling server. Reconnecting in 5s...');
            setTimeout(() => this._initializeSignaling(), 5000);
        };

        this.websocket.onerror = (error) => console.error('Signaling server error:', error);
    }

    _sendSignalingMessage(payload) {
        if (!this.isNetworkingEnabled) return;
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(payload));
        }
    }

    async _createPeerConnection(targetId) {
        if (!this.isNetworkingEnabled) return null;
        if (this.peers.has(targetId)) return this.peers.get(targetId);

        const peerConnection = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this._sendSignalingMessage({ type: 'candidate', targetId, sourceId: this.instanceId, candidate: event.candidate });
            }
        };
        peerConnection.ondatachannel = (event) => this._setupDataChannel(event.channel, targetId);
        this.peers.set(targetId, peerConnection);
        return peerConnection;
    }

    _setupDataChannel(dataChannel, peerId) {
        dataChannel.onopen = () => console.log(`Data channel with ${peerId} is open.`);
        dataChannel.onmessage = (event) => this._processIncomingMessage(JSON.parse(event.data));
        dataChannel.onclose = () => {
            console.log(`Data channel with ${peerId} closed.`);
            this.peers.delete(peerId);
            this.remoteInstances.delete(peerId);
        };
    }

    async _handleOffer({ sourceId, offer }) {
        if (!this.isNetworkingEnabled) return;
        const peerConnection = await this._createPeerConnection(sourceId);
        await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        this._sendSignalingMessage({ type: 'answer', targetId: sourceId, sourceId: this.instanceId, answer });
    }

    async _handleAnswer({ sourceId, answer }) {
        if (!this.isNetworkingEnabled) return;
        const peerConnection = this.peers.get(sourceId);
        if (peerConnection) await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    }

    async _handleCandidate({ sourceId, candidate }) {
        if (!this.isNetworkingEnabled) return;
        const peerConnection = this.peers.get(sourceId);
        if (peerConnection?.remoteDescription && candidate) {
            try {
                await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            } catch (e) {
                console.error('Error adding ICE candidate', e);
            }
        }
    }

    async sendMessage(targetId, type, data) {
        if (!this.isNetworkingEnabled) return;
        const payload = { sourceId: this.instanceId, targetId, type, data, timestamp: Date.now() };

        try {
            this.channel.postMessage(payload);
        } catch (_) {}

        if (this.remoteInstances.has(targetId) && typeof RTCPeerConnection !== 'undefined') {
            let peerConnection = this.peers.get(targetId);
            if (!peerConnection || peerConnection.connectionState !== 'connected') {
                peerConnection = await this._createPeerConnection(targetId);
                const dataChannel = peerConnection.createDataChannel('fractal-datachannel');
                this._setupDataChannel(dataChannel, targetId);

                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                this._sendSignalingMessage({ type: 'offer', targetId, sourceId: this.instanceId, offer });
            }

            const getDataChannel = () => {
                for (const [, pc] of this.peers) {
                    if (pc.sctp) {
                        const transport = pc.sctp.transport;
                        if (transport && transport.transport) {
                            const dataChannels = transport.transport.dataChannels;
                            if (dataChannels) {
                                const dc = Array.from(dataChannels).find(c => c.label === 'fractal-datachannel');
                                if (dc) return dc;
                            }
                        }
                    }
                }
                return null;
            };

            const waitForDataChannel = new Promise((resolve, reject) => {
                const check = () => {
                    const dc = getDataChannel();
                    if (dc && dc.readyState === 'open') {
                        resolve(dc);
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
                setTimeout(() => reject(new Error('Data channel timeout')), 5000);
            });

            try {
                const dc = await waitForDataChannel;
                dc.send(JSON.stringify(payload));
            } catch (error) {
                console.error(`WebRTC send failed to ${targetId}:`, error);
                this._sendSignalingMessage(payload);
            }
        } else if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this._sendSignalingMessage(payload);
        }
    }

    async _processIncomingMessage(payload) {
        if (!this.isNetworkingEnabled || !payload) return;
        const { sourceId, targetId, type, data, timestamp } = payload;
        if (targetId !== this.instanceId && targetId !== 'broadcast') return;

        switch (type) {
            case 'discover':
                this._handleDiscover(payload);
                break;

            case 'goodbye':
                this.remoteInstances.delete(sourceId);
                this.peers.delete(sourceId);
                this.attachedClients.delete(sourceId);
                if (this.attachedSession && this.attachedSession.targetId === sourceId) {
                    this.attachedSession = null;
                    if (this.dependencies.OutputManager) {
                        await this.dependencies.OutputManager.appendToOutput(`\x1b[1;33m[Mesh] Remote host ${sourceId} disconnected. Session detached.\x1b[0m`);
                    }
                    if (this.dependencies.TerminalUI) {
                        await this.dependencies.TerminalUI.updatePrompt();
                    }
                }
                break;

            case 'pong':
                const callback = this.pingCallbacks.get(sourceId);
                if (callback) {
                    callback(Date.now() - timestamp);
                    this.pingCallbacks.delete(sourceId);
                }
                break;

            case 'ping':
                await this.sendMessage(sourceId, 'pong', 'PONG');
                break;

            case 'mesh_wall': {
                const wallData = typeof data === 'object' && data !== null ? data : { message: data, sender: 'user' };
                const sender = wallData.sender || 'user';
                const msg = wallData.message || '';
                const time = wallData.timestamp || new Date().toLocaleTimeString();
                const formatted = `\n\x1b[1;33mBroadcast message from ${sender}@${sourceId} (${time}):\x1b[0m\n${msg}\n`;
                if (this.dependencies.OutputManager) {
                    await this.dependencies.OutputManager.appendToOutput(formatted);
                }
                if (this.dependencies.SoundManager && this.dependencies.SoundManager.isInitialized) {
                    try { this.dependencies.SoundManager.playNote(['E5', 'G5'], '16n'); } catch (_) {}
                }
                break;
            }

            case 'mesh_talk': {
                const talkData = typeof data === 'object' && data !== null ? data : { message: data, sender: 'user' };
                const sender = talkData.sender || 'user';
                const msg = talkData.message || '';
                const time = talkData.timestamp || new Date().toLocaleTimeString();
                const formatted = `\n\x1b[1;36m[Message from ${sender}@${sourceId} (${time})]:\x1b[0m ${msg}\n`;
                if (this.dependencies.OutputManager) {
                    await this.dependencies.OutputManager.appendToOutput(formatted);
                }
                if (this.dependencies.SoundManager && this.dependencies.SoundManager.isInitialized) {
                    try { this.dependencies.SoundManager.playNote(['C5', 'E5'], '16n'); } catch (_) {}
                }
                break;
            }

            case 'attach_request':
                await this._handleAttachRequest(payload);
                break;

            case 'attach_accept':
                this._handleAttachAccept(payload);
                break;

            case 'detach_notify':
                await this._handleDetachNotify(payload);
                break;

            case 'mesh_exec':
                await this._handleMeshExec(payload);
                break;

            case 'mesh_exec_result':
                this._handleMeshExecResult(payload);
                break;

            case 'mesh_file_push':
                await this._handleMeshFilePush(payload);
                break;

            case 'mesh_file_push_ack':
                this._handleMeshFilePushAck(payload);
                break;

            case 'mesh_file_pull':
                await this._handleMeshFilePull(payload);
                break;

            case 'mesh_file_pull_reply':
                await this._handleMeshFilePullReply(payload);
                break;

            case 'mesh_game':
                await this._handleMeshGame(payload);
                break;

            case 'mesh_agent_request':
                await this._handleMeshAgentRequest(payload);
                break;

            case 'mesh_agent_response':
                this._handleMeshAgentResponse(payload);
                break;

            default:
                if (this.listenCallback) {
                    this.listenCallback(payload);
                } else {
                    this.messageQueue.push(payload);
                }
                break;
        }
    }

    async _handleAttachRequest(payload) {
        const { sourceId } = payload;
        const { OutputManager, FileSystemManager, UserManager, EnvironmentManager, Config } = this.dependencies;
        this.attachedClients.add(sourceId);

        if (OutputManager) {
            await OutputManager.appendToOutput(`\x1b[1;32m[Client ${sourceId} attached to your session]\x1b[0m`);
        }

        const currentPath = FileSystemManager ? FileSystemManager.getCurrentPath() : '/';
        const currentUser = UserManager ? (await UserManager.getCurrentUser())?.name || 'Guest' : 'Guest';
        const host = EnvironmentManager ? (await EnvironmentManager.get('HOST')) || Config?.OS?.DEFAULT_HOST_NAME || 'fractal' : 'fractal';

        await this.sendMessage(sourceId, 'attach_accept', {
            hostId: this.instanceId,
            user: currentUser,
            host: host,
            path: currentPath
        });
    }

    _handleAttachAccept(payload) {
        const { sourceId, data } = payload;
        const pending = this.pendingAttachRequests.get(sourceId);
        if (pending) {
            this.pendingAttachRequests.delete(sourceId);
            pending.resolve(data);
        }
    }

    async _handleDetachNotify(payload) {
        const { sourceId } = payload;
        if (this.attachedClients.has(sourceId)) {
            this.attachedClients.delete(sourceId);
            if (this.dependencies.OutputManager) {
                await this.dependencies.OutputManager.appendToOutput(`\x1b[1;33m[Client ${sourceId} detached from your session]\x1b[0m`);
            }
        }
        if (this.attachedSession && this.attachedSession.targetId === sourceId) {
            this.attachedSession = null;
            if (this.dependencies.OutputManager) {
                await this.dependencies.OutputManager.appendToOutput(`\x1b[1;33mRemote host detached session.\x1b[0m`);
            }
            if (this.dependencies.TerminalUI) {
                await this.dependencies.TerminalUI.updatePrompt();
            }
        }
    }

    async _handleMeshExec(payload) {
        const { sourceId, data } = payload;
        const { reqId, command } = data || {};
        const { OutputManager, FileSystemManager, UserManager, EnvironmentManager, Config } = this.dependencies;

        if (OutputManager) {
            await OutputManager.appendToOutput(`\x1b[1;35m[remote@${sourceId.substring(0, 8)}]\x1b[0m ${command}`);
        }

        let success = true;
        let output = "";
        let error = null;

        try {
            const kernelContextJson = typeof createKernelContext === 'function' ? await createKernelContext() : "{}";
            const jsonResult = await FractalOS_Kernel.execute_command(command, kernelContextJson);
            const pyResult = JSON.parse(jsonResult);

            success = pyResult.success;
            if (pyResult.success) {
                if (Array.isArray(pyResult.effects)) {
                    for (const eff of pyResult.effects) {
                        if (typeof handleEffect === 'function') await handleEffect(eff, { isInteractive: false });
                    }
                } else if (pyResult.effect) {
                    if (typeof handleEffect === 'function') await handleEffect(pyResult, { isInteractive: false });
                }
                output = pyResult.output || "";
                if (FileSystemManager && typeof FileSystemManager.getFsData === 'function' && typeof FileSystemManager.setFsData === 'function') {
                    const updatedFsData = await FileSystemManager.getFsData();
                    FileSystemManager.setFsData(updatedFsData);
                }
            } else {
                error = pyResult.error?.message || pyResult.error || "Execution failed";
            }
        } catch (e) {
            success = false;
            error = e.message || "Failed to execute command";
        }

        if (OutputManager && output) {
            await OutputManager.appendToOutput(output);
        }

        const currentPath = FileSystemManager ? FileSystemManager.getCurrentPath() : '/';
        const currentUser = UserManager ? (await UserManager.getCurrentUser())?.name || 'Guest' : 'Guest';
        const host = EnvironmentManager ? (await EnvironmentManager.get('HOST')) || Config?.OS?.DEFAULT_HOST_NAME || 'fractal' : 'fractal';

        await this.sendMessage(sourceId, 'mesh_exec_result', {
            reqId,
            success,
            output,
            error,
            newPath: currentPath,
            user: currentUser,
            host
        });
    }

    _handleMeshExecResult(payload) {
        const { data } = payload;
        const reqId = data?.reqId;
        if (reqId && this.pendingExecRequests.has(reqId)) {
            const pending = this.pendingExecRequests.get(reqId);
            this.pendingExecRequests.delete(reqId);
            pending.resolve(data);
        }
    }

    async requestAttach(targetId, options = {}) {
        if (!this.isNetworkingEnabled) throw new Error("Networking is disabled.");
        const timeoutMs = options.timeoutMs || 5000;

        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingAttachRequests.delete(targetId);
                reject(new Error(`Connection to ${targetId} timed out.`));
            }, timeoutMs);

            this.pendingAttachRequests.set(targetId, {
                resolve: (data) => {
                    clearTimeout(timer);
                    this.attachedSession = {
                        targetId,
                        host: data.host,
                        user: data.user,
                        path: data.path
                    };
                    resolve(data);
                },
                reject: (err) => {
                    clearTimeout(timer);
                    reject(err);
                }
            });

            this.sendMessage(targetId, 'attach_request', {
                sourceId: this.instanceId,
                targetId
            });
        });
    }

    async detachSession() {
        if (!this.attachedSession) return;
        const targetId = this.attachedSession.targetId;
        this.attachedSession = null;
        try {
            await this.sendMessage(targetId, 'detach_notify', { sourceId: this.instanceId });
        } catch (_) {}
        if (this.dependencies.TerminalUI) {
            await this.dependencies.TerminalUI.updatePrompt();
        }
    }

    async sendRemoteCommand(command, options = {}) {
        if (!this.attachedSession) throw new Error("Not attached to any remote session.");
        const targetId = this.attachedSession.targetId;
        const timeoutMs = options.timeoutMs || 30000;
        const reqId = `req-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingExecRequests.delete(reqId);
                reject(new Error("Remote command timed out after 30 seconds."));
            }, timeoutMs);

            this.pendingExecRequests.set(reqId, {
                resolve: (result) => {
                    clearTimeout(timer);
                    if (this.attachedSession) {
                        if (result.newPath) this.attachedSession.path = result.newPath;
                        if (result.user) this.attachedSession.user = result.user;
                        if (result.host) this.attachedSession.host = result.host;
                    }
                    resolve(result);
                },
                reject: (err) => {
                    clearTimeout(timer);
                    reject(err);
                }
            });

            this.sendMessage(targetId, 'mesh_exec', { reqId, command });
        });
    }

    async _handleMeshFilePush(payload) {
        const { sourceId, data } = payload;
        const { reqId, path, content } = data || {};
        const { OutputManager, FileSystemManager, UserManager } = this.dependencies;

        try {
            const currentUser = (await UserManager?.getCurrentUser()) || { name: 'Guest' };
            const primaryGroup = (typeof UserManager?.getPrimaryGroupForUser === 'function' ? await UserManager.getPrimaryGroupForUser(currentUser.name) : currentUser.primaryGroup) || 'Guest';
            const context = { currentUser: currentUser.name, primaryGroup };

            let resolvedPath = path || 'unnamed_file';
            if (!resolvedPath.startsWith('/')) {
                resolvedPath = `/home/${currentUser.name}/${resolvedPath}`;
            }

            if (FileSystemManager && typeof FileSystemManager.createOrUpdateFile === 'function') {
                const result = await FileSystemManager.createOrUpdateFile(resolvedPath, content, context);
                if (result.success) {
                    if (typeof FileSystemManager.getFsData === 'function' && typeof FileSystemManager.setFsData === 'function') {
                        const updatedFsData = await FileSystemManager.getFsData();
                        FileSystemManager.setFsData(updatedFsData);
                    }
                    if (typeof FileSystemManager.save === 'function') {
                        await FileSystemManager.save();
                    }

                    if (OutputManager) {
                        await OutputManager.appendToOutput(`\x1b[1;32m[Received file from ${sourceId.substring(0, 8)}]: ${resolvedPath} (${content.length} bytes)\x1b[0m`);
                    }

                    await this.sendMessage(sourceId, 'mesh_file_push_ack', {
                        reqId,
                        success: true,
                        path: resolvedPath,
                        bytes: content.length
                    });
                } else {
                    await this.sendMessage(sourceId, 'mesh_file_push_ack', {
                        reqId,
                        success: false,
                        error: result.error?.message || "Permission denied or failed to write file."
                    });
                }
            } else {
                throw new Error("Filesystem manager unavailable.");
            }
        } catch (err) {
            await this.sendMessage(sourceId, 'mesh_file_push_ack', {
                reqId,
                success: false,
                error: err.message
            });
        }
    }

    _handleMeshFilePushAck(payload) {
        const { data } = payload;
        const reqId = data?.reqId;
        if (reqId && this.pendingFileSendRequests.has(reqId)) {
            const pending = this.pendingFileSendRequests.get(reqId);
            this.pendingFileSendRequests.delete(reqId);
            if (data.success) {
                pending.resolve(data);
            } else {
                pending.reject(new Error(data.error || "Remote failed to receive file."));
            }
        }
    }

    async _handleMeshFilePull(payload) {
        const { sourceId, data } = payload;
        const { reqId, path } = data || {};
        const { OutputManager, FileSystemManager, UserManager } = this.dependencies;

        try {
            const currentUser = (await UserManager?.getCurrentUser()) || { name: 'Guest' };
            let resolvedPath = path || '';
            if (!resolvedPath.startsWith('/')) {
                resolvedPath = `/home/${currentUser.name}/${resolvedPath}`;
            }

            if (FileSystemManager && typeof FileSystemManager.getNodeByPath === 'function') {
                const node = await FileSystemManager.getNodeByPath(resolvedPath);
                if (!node) {
                    await this.sendMessage(sourceId, 'mesh_file_pull_reply', {
                        reqId,
                        success: false,
                        error: `File not found on remote: ${resolvedPath}`
                    });
                    return;
                }
                if (node.type !== 'file') {
                    await this.sendMessage(sourceId, 'mesh_file_pull_reply', {
                        reqId,
                        success: false,
                        error: `Remote path is a directory, not a file: ${resolvedPath}`
                    });
                    return;
                }

                if (OutputManager) {
                    await OutputManager.appendToOutput(`\x1b[1;36m[Sent file to ${sourceId.substring(0, 8)}]: ${resolvedPath} (${(node.content || '').length} bytes)\x1b[0m`);
                }

                await this.sendMessage(sourceId, 'mesh_file_pull_reply', {
                    reqId,
                    success: true,
                    content: node.content || '',
                    path: resolvedPath,
                    bytes: (node.content || '').length
                });
            } else {
                throw new Error("Filesystem manager unavailable.");
            }
        } catch (err) {
            await this.sendMessage(sourceId, 'mesh_file_pull_reply', {
                reqId,
                success: false,
                error: err.message
            });
        }
    }

    async _handleMeshFilePullReply(payload) {
        const { data } = payload;
        const reqId = data?.reqId;
        if (reqId && this.pendingFilePullRequests.has(reqId)) {
            const pending = this.pendingFilePullRequests.get(reqId);
            this.pendingFilePullRequests.delete(reqId);

            if (!data.success) {
                pending.reject(new Error(data.error || "Remote node failed to read requested file."));
                return;
            }

            const { FileSystemManager, UserManager } = this.dependencies;
            try {
                const currentUser = (await UserManager?.getCurrentUser()) || { name: 'Guest' };
                const primaryGroup = (typeof UserManager?.getPrimaryGroupForUser === 'function' ? await UserManager.getPrimaryGroupForUser(currentUser.name) : currentUser.primaryGroup) || 'Guest';
                const context = { currentUser: currentUser.name, primaryGroup };

                if (FileSystemManager && typeof FileSystemManager.createOrUpdateFile === 'function') {
                    const result = await FileSystemManager.createOrUpdateFile(pending.localPath, data.content, context);
                    if (result.success) {
                        if (typeof FileSystemManager.getFsData === 'function' && typeof FileSystemManager.setFsData === 'function') {
                            const updatedFsData = await FileSystemManager.getFsData();
                            FileSystemManager.setFsData(updatedFsData);
                        }
                        if (typeof FileSystemManager.save === 'function') {
                            await FileSystemManager.save();
                        }
                        pending.resolve({ success: true, localPath: pending.localPath, bytes: data.bytes });
                    } else {
                        pending.reject(new Error(result.error?.message || "Failed to write pulled file to local disk."));
                    }
                } else {
                    pending.resolve({ success: true, localPath: pending.localPath, bytes: data.bytes, content: data.content });
                }
            } catch (err) {
                pending.reject(err);
            }
        }
    }

    async sendFile(targetId, remotePath, content, options = {}) {
        if (!this.isNetworkingEnabled) throw new Error("Networking is disabled.");
        const timeoutMs = options.timeoutMs || 15000;
        const reqId = `fsend-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingFileSendRequests.delete(reqId);
                reject(new Error(`Sending file to ${targetId} timed out.`));
            }, timeoutMs);

            this.pendingFileSendRequests.set(reqId, {
                resolve: (data) => {
                    clearTimeout(timer);
                    resolve(data);
                },
                reject: (err) => {
                    clearTimeout(timer);
                    reject(err);
                }
            });

            this.sendMessage(targetId, 'mesh_file_push', {
                reqId,
                path: remotePath,
                content,
                size: content.length,
                sender: this.instanceId
            });
        });
    }

    async pullFile(targetId, remotePath, localPath, options = {}) {
        if (!this.isNetworkingEnabled) throw new Error("Networking is disabled.");
        const timeoutMs = options.timeoutMs || 15000;
        const reqId = `fpull-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingFilePullRequests.delete(reqId);
                reject(new Error(`Pulling file from ${targetId} timed out.`));
            }, timeoutMs);

            this.pendingFilePullRequests.set(reqId, {
                localPath,
                resolve: (data) => {
                    clearTimeout(timer);
                    resolve(data);
                },
                reject: (err) => {
                    clearTimeout(timer);
                    reject(err);
                }
            });

            this.sendMessage(targetId, 'mesh_file_pull', {
                reqId,
                path: remotePath,
                sender: this.instanceId
            });
        });
    }

    sendPing(targetId) {
        if (!this.isNetworkingEnabled) return Promise.reject(new Error("Networking is disabled."));
        return new Promise((resolve, reject) => {
            this.pingCallbacks.set(targetId, resolve);
            this.sendMessage(targetId, 'ping', 'PING');
            setTimeout(() => {
                if (this.pingCallbacks.has(targetId)) {
                    this.pingCallbacks.delete(targetId);
                    reject(new Error('Ping timed out'));
                }
            }, 5000);
        });
    }

    getNextMessage() {
        return this.messageQueue.shift() || null;
    }

    setActiveGameApp(app) {
        this.activeGameApp = app;
    }

    async sendGameAction(targetId, actionData) {
        if (!this.isNetworkingEnabled) return;
        const payloadData = {
            ...actionData,
            sender: this.instanceId
        };
        await this.sendMessage(targetId, 'mesh_game', payloadData);
    }

    async _handleMeshGame(payload) {
        const { sourceId, data } = payload;
        if (!data) return;

        const { action, gameType, move, board, turn, winner, guestName } = data;
        const gameName = gameType === 'c4' ? 'Connect 4' : (gameType === 'ttt' ? 'Tic-Tac-Toe' : 'Game');

        switch (action) {
            case 'invite': {
                if (this.dependencies.OutputManager) {
                    await this.dependencies.OutputManager.appendToOutput(
                        `\n\x1b[1;36m[Netgame]\x1b[0m Peer \x1b[1;35m@${sourceId}\x1b[0m invited you to a game of \x1b[1;33m${gameName}\x1b[0m!\n` +
                        `Type \x1b[1;32m'netgame accept ${sourceId}'\x1b[0m or \x1b[1;32m'${gameType || "c4"} accept ${sourceId}'\x1b[0m to play.\n`
                    );
                }
                if (this.dependencies.SoundManager && this.dependencies.SoundManager.isInitialized) {
                    try { this.dependencies.SoundManager.playNote(['E5', 'G5'], '16n'); } catch (_) {}
                }
                break;
            }

            case 'accept': {
                if (this.activeGameApp) {
                    this.activeGameApp.session.peer = sourceId;
                    this.activeGameApp.session.p2 = guestName || sourceId;
                    this.activeGameApp.session.p2_display = guestName || sourceId;
                    this.activeGameApp.ui?.render(this.activeGameApp.session, this.activeGameApp.mySymbol);
                    this.activeGameApp.ui?.appendLog(`Peer @${sourceId} joined the match!`, 'player-o');
                } else if (this.dependencies.OutputManager) {
                    await this.dependencies.OutputManager.appendToOutput(
                        `\n\x1b[1;32m[Netgame]\x1b[0m Peer \x1b[1;35m@${sourceId}\x1b[0m accepted your invitation! Match is live.\n` +
                        `Make your move with \x1b[1;32m'netgame move <col>'\x1b[0m or open graphical TUI with \x1b[1;32m'netgame play'\x1b[0m.\n`
                    );
                }
                if (this.dependencies.SoundManager && this.dependencies.SoundManager.isInitialized) {
                    try { this.dependencies.SoundManager.playNote(['C5', 'G5'], '16n'); } catch (_) {}
                }
                break;
            }

            case 'move': {
                if (this.activeGameApp) {
                    this.activeGameApp.handleRemoteMove(data);
                } else {
                    if (this.dependencies.OutputManager) {
                        const movePrompt = gameType === 'c4' ? '1-7' : '1-9';
                        await this.dependencies.OutputManager.appendToOutput(
                            `\n\x1b[1;36m[Netgame]\x1b[0m Opponent \x1b[1;35m@${sourceId}\x1b[0m played: \x1b[1;33m${move}\x1b[0m. It is your turn!\n` +
                            `Enter \x1b[1;32m'netgame move <${movePrompt}>'\x1b[0m or \x1b[1;32m'netgame board'\x1b[0m to view.\n`
                        );
                    }
                    if (this.dependencies.SoundManager && this.dependencies.SoundManager.isInitialized) {
                        try { this.dependencies.SoundManager.playTone('E5', '32n'); } catch (_) {}
                    }
                }

                // Sync session in Python kernel if available
                try {
                    if (typeof FractalOS_Kernel !== 'undefined' && FractalOS_Kernel.isReady) {
                        const user = this.dependencies.UserManager?.getCurrentUser()?.username || 'guest';
                        const pyCmd = `import json; from commands import netgame; s = netgame._get_active_session('${user}');\n` +
                            `if s:\n    s['board'] = ${JSON.stringify(board)}; s['turn'] = '${turn}'; s['winner'] = ${winner ? `'${winner}'` : 'None'};\n` +
                            `    s['moves'].append({'player': 'O' if s['my_symbol'] == 'X' else 'X', 'move': ${move}})`;
                        await FractalOS_Kernel.execute_command(`python -c "${pyCmd.replace(/"/g, '\\"')}"`);
                    }
                } catch (_) {}
                break;
            }

            case 'resign': {
                if (this.activeGameApp) {
                    this.activeGameApp.handleRemoteResign();
                } else if (this.dependencies.OutputManager) {
                    await this.dependencies.OutputManager.appendToOutput(
                        `\n\x1b[1;32m[Netgame]\x1b[0m Opponent \x1b[1;35m@${sourceId}\x1b[0m resigned! You win!\n`
                    );
                }
                break;
            }
        }
    }

    getLocalMetadata() {
        const user = this.dependencies.UserManager?.getCurrentUser()?.username || 'Guest';
        const host = this.dependencies.EnvironmentManager?.get('HOST') || 'fractal';
        return {
            user: `${user}@${host}`,
            capabilities: ['shell', 'mesh-cp', 'netgame', 'gpio', 'mesh-agent'],
            uptime: Math.floor(typeof performance !== 'undefined' ? performance.now() / 1000 : 0)
        };
    }

    getLocalNodeInfo() {
        const meta = this.getLocalMetadata();
        return {
            id: this.instanceId,
            user: meta.user,
            networkingEnabled: this.isNetworkingEnabled,
            signalingServerUrl: this.signalingServerUrl,
            signalingConnected: !!(this.websocket && this.websocket.readyState === WebSocket.OPEN),
            peerCount: this.remoteInstances.size,
            capabilities: meta.capabilities
        };
    }

    async getPeersDetailed({ doPing = false } = {}) {
        const list = [];
        for (const peerId of this.remoteInstances) {
            const meta = this.peerMetadata.get(peerId) || {
                user: 'guest@fractal',
                capabilities: ['shell', 'mesh-cp', 'netgame', 'mesh-agent']
            };
            const pc = this.peers.get(peerId);
            let transport = 'BroadcastChannel';
            if (pc && pc.connectionState === 'connected') {
                transport = 'WebRTC DataChannel';
            } else if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                transport = 'WebSocket Signaling';
            }

            let latency = meta.latency !== undefined ? meta.latency : null;
            if (doPing) {
                try {
                    latency = await this.sendPing(peerId);
                    meta.latency = latency;
                    this.peerMetadata.set(peerId, meta);
                } catch (_) {
                    latency = -1;
                }
            }

            list.push({
                id: peerId,
                user: meta.user || 'guest@fractal',
                transport: transport,
                capabilities: meta.capabilities || ['shell', 'mesh-cp', 'netgame', 'mesh-agent'],
                latency: latency,
                lastSeen: meta.lastSeen || Date.now(),
                attached: this.attachedClients.has(peerId) || (this.attachedSession?.targetId === peerId)
            });
        }
        return list;
    }

    async getPeerInfo(peerId, { doPing = false } = {}) {
        if (!this.remoteInstances.has(peerId)) return null;
        const peers = await this.getPeersDetailed({ doPing });
        return peers.find(p => p.id === peerId) || null;
    }

    resolvePeerId(query) {
        if (!query) return null;
        if (this.remoteInstances.has(query)) return query;
        const matching = Array.from(this.remoteInstances).filter(id => id.startsWith(query));
        if (matching.length === 1) return matching[0];
        for (const [id, meta] of this.peerMetadata.entries()) {
            if (meta.user === query || (meta.user && meta.user.startsWith(query)) || id.startsWith(query)) {
                return id;
            }
        }
        return matching.length > 0 ? matching[0] : query;
    }

    async delegateAgentTask(targetPeerId, prompt, options = {}) {
        if (!this.isNetworkingEnabled) throw new Error("Networking is disabled.");
        const resolvedId = this.resolvePeerId(targetPeerId);
        if (!resolvedId) throw new Error(`Target peer '${targetPeerId}' not found.`);

        const timeoutSec = options.timeout || 30;
        const timeoutMs = timeoutSec * 1000;
        const reqId = `agent-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingAgentDelegations.delete(reqId);
                reject(new Error(`Delegated agent task to ${targetPeerId} timed out after ${timeoutSec}s.`));
            }, timeoutMs);

            this.pendingAgentDelegations.set(reqId, {
                resolve: (data) => {
                    clearTimeout(timer);
                    resolve(data);
                },
                reject: (err) => {
                    clearTimeout(timer);
                    reject(err);
                }
            });

            this.sendMessage(resolvedId, 'mesh_agent_request', {
                reqId,
                prompt,
                isAutopilot: !!options.isAutopilot,
                maxVoltage: options.maxVoltage !== undefined ? options.maxVoltage : null,
                isDryRun: !!options.isDryRun,
                isForce: !!options.isForce,
                sourceId: this.instanceId,
                senderUser: options.senderUser || 'Guest'
            });
        });
    }

    async _handleMeshAgentRequest(payload) {
        const sourceId = payload?.sourceId || payload?.data?.sourceId;
        const msgData = payload?.data || payload || {};
        const { reqId, prompt, isAutopilot, senderUser, maxVoltage, isDryRun, isForce } = msgData;
        const { OutputManager } = this.dependencies;

        const voltageInfo = maxVoltage !== undefined && maxVoltage !== null ? ` [Budget: ${maxVoltage}V]` : '';
        const modeInfo = isDryRun ? ' (dry-run)' : (isAutopilot ? ' (autopilot)' : '');
        if (OutputManager && sourceId) {
            await OutputManager.appendToOutput(
                `\n\x1b[1;35m[Mesh Swarm]\x1b[0m Incoming task from \x1b[1m${sourceId.substring(0, 8)}\x1b[0m (${senderUser || 'Guest'})${modeInfo}${voltageInfo}: "${prompt}"\n`
            );
        }

        try {
            let resultData = "";
            let isSuccess = true;
            let errorDetails = null;
            let resultVoltage = null;

            if (typeof FractalOS_Kernel !== 'undefined' && FractalOS_Kernel.isReady && FractalOS_Kernel.syscall) {
                const requestPayload = {
                    reqId,
                    prompt,
                    isAutopilot: !!isAutopilot,
                    senderUser: senderUser || 'Guest',
                    sourceId: sourceId,
                    maxVoltage: maxVoltage !== undefined ? maxVoltage : null,
                    isDryRun: !!isDryRun,
                    isForce: !!isForce
                };
                const rawResult = await FractalOS_Kernel.syscall("swarm", "handle_remote_agent_request", [requestPayload]);
                const pyResult = JSON.parse(rawResult);

                isSuccess = !!pyResult.success;
                resultData = pyResult.data || "";
                resultVoltage = pyResult.voltage !== undefined ? pyResult.voltage : null;
                if (!isSuccess) {
                    errorDetails = pyResult.error?.message || pyResult.error || "Remote task execution failed.";
                }
            } else if (this.dependencies.CommandExecutor) {
                const escaped = (prompt || '').replace(/"/g, '\\"');
                const cmd = isAutopilot ? `samwise --autopilot "${escaped}"` : `samwise "${escaped}"`;
                const execResult = await this.dependencies.CommandExecutor.processSingleCommand(cmd, { isInteractive: false });
                isSuccess = execResult?.success !== false;
                resultData = execResult?.output || "Task executed.";
            }

            if (sourceId) {
                await this.sendMessage(sourceId, 'mesh_agent_response', {
                    reqId,
                    success: isSuccess,
                    data: resultData,
                    error: errorDetails,
                    voltage: resultVoltage,
                    targetId: this.instanceId
                });
            }
        } catch (err) {
            if (sourceId) {
                await this.sendMessage(sourceId, 'mesh_agent_response', {
                    reqId,
                    success: false,
                    data: "",
                    error: err.message,
                    targetId: this.instanceId
                });
            }
        }
    }

    _handleMeshAgentResponse(payload) {
        const msgData = payload?.data || payload || {};
        const reqId = msgData?.reqId;
        if (reqId && this.pendingAgentDelegations.has(reqId)) {
            const pending = this.pendingAgentDelegations.get(reqId);
            this.pendingAgentDelegations.delete(reqId);
            if (msgData.success) {
                pending.resolve(msgData);
            } else {
                pending.reject(new Error(msgData.error || "Remote agent failed to complete task."));
            }
        }
    }
}