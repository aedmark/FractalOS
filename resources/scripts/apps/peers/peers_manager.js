/**
 * peers_manager.js - App controller for Mesh Network Monitor app.
 */

window.PeersManager = class PeersManager extends App {
    constructor() {
        super();
        this.dependencies = {};
        this.callbacks = {};
        this.ui = null;
        this.pollInterval = null;
    }

    async enter(appLayer, options = {}) {
        if (this.isActive) return;

        this.dependencies = options.dependencies;
        this.callbacks = this._createCallbacks();
        this.isActive = true;

        this.ui = new this.dependencies.PeersUI(this.callbacks, this.dependencies);
        this.container = this.ui.getContainer();
        appLayer.appendChild(this.container);

        await this.refresh(options.doPing || false);

        // Auto poll every 3 seconds for new peers
        this.pollInterval = setInterval(() => this.refresh(false), 3000);
        this.container.focus();
    }

    exit() {
        if (!this.isActive) return;
        const { AppLayerManager } = this.dependencies;

        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }

        AppLayerManager.hide(this);
        this.isActive = false;
        this.ui = null;
    }

    handleKeyDown(event) {
        if (event.key === 'Escape' || event.key === 'q') {
            this.exit();
            return;
        }
        if (event.key === 'r') {
            this.refresh(true);
        }
    }

    _createCallbacks() {
        return {
            onExit: this.exit.bind(this),
            onRefresh: () => this.refresh(true),
            onPingPeer: (id) => this.pingPeer(id),
            onAttachPeer: (id) => this.attachPeer(id)
        };
    }

    async refresh(doPing = false) {
        if (!this.isActive || !this.dependencies.NetworkManager) return;
        const netMgr = this.dependencies.NetworkManager;

        const localNode = netMgr.getLocalNodeInfo();
        const peers = await netMgr.getPeersDetailed({ doPing });

        if (this.ui) {
            this.ui.render(localNode, peers);
        }
    }

    async pingPeer(peerId) {
        if (!this.dependencies.NetworkManager) return;
        try {
            await this.dependencies.NetworkManager.sendPing(peerId);
        } catch (_) {}
        await this.refresh(false);
    }

    async attachPeer(peerId) {
        this.exit();
        if (this.dependencies.CommandExecutor) {
            await this.dependencies.CommandExecutor.processSingleCommand(`attach ${peerId}`);
        }
    }
};
