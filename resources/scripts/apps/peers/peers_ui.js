/**
 * peers_ui.js - View and DOM layout for Mesh Network Monitor app.
 */

window.PeersUI = class PeersUI {
    constructor(callbacks, dependencies) {
        this.elements = {};
        this.callbacks = callbacks;
        this.dependencies = dependencies;
        this._buildLayout();
    }

    getContainer() {
        return this.elements.container;
    }

    _buildLayout() {
        const { Utils, UIComponents } = this.dependencies;

        const appWindow = UIComponents.createAppWindow('Mesh Network Monitor', this.callbacks.onExit);
        this.elements.container = appWindow.container;
        this.elements.container.id = 'peers-app-container';
        this.elements.main = appWindow.main;
        this.elements.main.className = 'app-main peers-main';

        // Summary Bar
        this.elements.summaryBar = Utils.createElement('div', { className: 'peers-summary-bar' });
        
        // Cards: Local Node, Signaling Status, Peer Count
        this.elements.cardLocalNode = this._createSummaryCard('Local Instance', 'Initializing...');
        this.elements.cardSignaling = this._createSummaryCard('Signaling Server', 'Checking...');
        this.elements.cardPeerCount = this._createSummaryCard('Mesh Peers', '0 Discovered');

        this.elements.summaryBar.appendChild(this.elements.cardLocalNode.card);
        this.elements.summaryBar.appendChild(this.elements.cardSignaling.card);
        this.elements.summaryBar.appendChild(this.elements.cardPeerCount.card);

        // Table container
        this.elements.tableContainer = Utils.createElement('div', { className: 'peers-table-container' });
        this.elements.tbody = Utils.createElement('tbody');

        const table = Utils.createElement('table', { className: 'peers-table' }, [
            Utils.createElement('thead', {},
                Utils.createElement('tr', {}, [
                    Utils.createElement('th', { textContent: 'NODE ID' }),
                    Utils.createElement('th', { textContent: 'USER @ HOST' }),
                    Utils.createElement('th', { textContent: 'TRANSPORT' }),
                    Utils.createElement('th', { textContent: 'LATENCY' }),
                    Utils.createElement('th', { textContent: 'CAPABILITIES' }),
                    Utils.createElement('th', { textContent: 'ACTIONS' })
                ])
            ),
            this.elements.tbody
        ]);
        this.elements.tableContainer.appendChild(table);

        // Footer controls
        this.elements.footerControls = Utils.createElement('div', { className: 'peers-footer-controls' });
        this.elements.btnRefresh = Utils.createElement('button', {
            className: 'btn',
            textContent: '↻ Refresh & Ping All',
            eventListeners: { click: () => this.callbacks.onRefresh() }
        });
        this.elements.statusNote = Utils.createElement('span', {
            style: { fontSize: '0.8rem', color: '#64748b' },
            textContent: 'Live monitoring active'
        });

        this.elements.footerControls.appendChild(this.elements.btnRefresh);
        this.elements.footerControls.appendChild(this.elements.statusNote);

        this.elements.main.appendChild(this.elements.summaryBar);
        this.elements.main.appendChild(this.elements.tableContainer);
        this.elements.main.appendChild(this.elements.footerControls);
    }

    _createSummaryCard(label, initialVal) {
        const { Utils } = this.dependencies;
        const card = Utils.createElement('div', { className: 'peers-summary-card' });
        const lblEl = Utils.createElement('div', { className: 'peers-summary-label', textContent: label });
        const valEl = Utils.createElement('div', { className: 'peers-summary-val', textContent: initialVal });
        card.appendChild(lblEl);
        card.appendChild(valEl);
        return { card, valEl };
    }

    render(localNode, peers) {
        const { Utils } = this.dependencies;

        // Update summary cards
        if (localNode) {
            this.elements.cardLocalNode.valEl.textContent = `${localNode.id} (${localNode.user})`;
            
            const isOnline = localNode.signalingConnected;
            this.elements.cardSignaling.valEl.innerHTML = '';
            const dot = Utils.createElement('span', {
                className: `peers-status-dot ${isOnline ? 'online' : 'standalone'}`
            });
            const text = document.createTextNode(` ${isOnline ? 'Connected' : 'Standalone'} (${localNode.signalingServerUrl})`);
            this.elements.cardSignaling.valEl.appendChild(dot);
            this.elements.cardSignaling.valEl.appendChild(text);

            this.elements.cardPeerCount.valEl.textContent = `${peers.length} Active Node${peers.length === 1 ? '' : 's'}`;
        }

        // Render Peers Table
        this.elements.tbody.innerHTML = '';

        if (!peers || peers.length === 0) {
            const emptyRow = Utils.createElement('tr', {},
                Utils.createElement('td', {
                    colSpan: 6,
                    className: 'peers-empty-msg',
                    textContent: 'No remote peers discovered on local mesh. Open another browser tab or start signaling server.'
                })
            );
            this.elements.tbody.appendChild(emptyRow);
            return;
        }

        peers.forEach(peer => {
            const row = Utils.createElement('tr');

            // 1. Node ID
            const tdId = Utils.createElement('td', {},
                Utils.createElement('span', { className: 'peer-node-id', textContent: peer.id })
            );

            // 2. User @ Host
            const tdUser = Utils.createElement('td', { textContent: peer.user || 'guest@fractal' });

            // 3. Transport
            const tdTrans = Utils.createElement('td', { textContent: peer.transport || 'BroadcastChannel' });

            // 4. Latency
            const tdLat = Utils.createElement('td');
            if (peer.latency !== null) {
                if (peer.latency >= 0) {
                    const badgeClass = peer.latency < 20 ? 'peer-latency-fast' : (peer.latency < 100 ? 'peer-latency-medium' : 'peer-latency-slow');
                    const badge = Utils.createElement('span', {
                        className: `peer-latency-badge ${badgeClass}`,
                        textContent: `${peer.latency} ms`
                    });
                    tdLat.appendChild(badge);
                } else {
                    tdLat.textContent = 'Timeout';
                }
            } else {
                tdLat.textContent = '—';
            }

            // 5. Capabilities
            const tdCaps = Utils.createElement('td');
            const capsList = Utils.createElement('div', { className: 'peer-caps-list' });
            (peer.capabilities || ['shell', 'mesh-cp', 'netgame']).forEach(cap => {
                const tag = Utils.createElement('span', { className: 'peer-cap-tag', textContent: cap });
                capsList.appendChild(tag);
            });
            tdCaps.appendChild(capsList);

            // 6. Actions
            const tdActions = Utils.createElement('td');
            const actionsDiv = Utils.createElement('div', { className: 'peer-actions-cell' });

            const btnPing = Utils.createElement('button', {
                className: 'peer-btn-action',
                textContent: 'Ping',
                title: 'Ping this peer',
                eventListeners: { click: () => this.callbacks.onPingPeer(peer.id) }
            });

            const btnAttach = Utils.createElement('button', {
                className: 'peer-btn-action',
                textContent: 'Attach',
                title: 'Attach to remote shell session',
                eventListeners: { click: () => this.callbacks.onAttachPeer(peer.id) }
            });

            actionsDiv.appendChild(btnPing);
            actionsDiv.appendChild(btnAttach);
            tdActions.appendChild(actionsDiv);

            row.appendChild(tdId);
            row.appendChild(tdUser);
            row.appendChild(tdTrans);
            row.appendChild(tdLat);
            row.appendChild(tdCaps);
            row.appendChild(tdActions);

            this.elements.tbody.appendChild(row);
        });
    }
};
