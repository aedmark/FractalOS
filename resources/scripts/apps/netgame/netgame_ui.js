/**
 * netgame_ui.js - View and DOM layout for Netgame multiplayer terminal app.
 */

window.NetgameUI = class NetgameUI {
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

        const appWindow = UIComponents.createAppWindow('Netgame Arcade', this.callbacks.onExit);
        this.elements.container = appWindow.container;
        this.elements.container.id = 'netgame-app-container';
        this.elements.headerTitle = appWindow.header.querySelector('.app-header__title');
        this.elements.main = appWindow.main;
        this.elements.main.className = 'app-main netgame-main';

        // Arena (Left/Center)
        this.elements.arena = Utils.createElement('div', { className: 'netgame-arena' });
        this.elements.statusBanner = Utils.createElement('div', {
            className: 'netgame-status-banner turn-my',
            textContent: 'Initializing match...'
        });
        this.elements.boardArea = Utils.createElement('div', { className: 'netgame-board-area' });

        this.elements.arena.appendChild(this.elements.statusBanner);
        this.elements.arena.appendChild(this.elements.boardArea);

        // Sidebar (Right)
        this.elements.sidebar = Utils.createElement('div', { className: 'netgame-sidebar' });
        this.elements.sidebarTitle = Utils.createElement('div', {
            className: 'netgame-sidebar-title',
            textContent: 'Match Log'
        });
        this.elements.moveLog = Utils.createElement('div', { className: 'netgame-move-log' });

        // Controls
        this.elements.controls = Utils.createElement('div', { className: 'netgame-controls' });
        this.elements.btnNew = Utils.createElement('button', {
            className: 'netgame-btn',
            textContent: 'Restart / New Match',
            eventListeners: { click: () => this.callbacks.onNewGame() }
        });
        this.elements.btnResign = Utils.createElement('button', {
            className: 'netgame-btn netgame-btn-danger',
            textContent: 'Resign Match',
            eventListeners: { click: () => this.callbacks.onResign() }
        });

        this.elements.controls.appendChild(this.elements.btnNew);
        this.elements.controls.appendChild(this.elements.btnResign);

        this.elements.sidebar.appendChild(this.elements.sidebarTitle);
        this.elements.sidebar.appendChild(this.elements.moveLog);
        this.elements.sidebar.appendChild(this.elements.controls);

        this.elements.main.appendChild(this.elements.arena);
        this.elements.main.appendChild(this.elements.sidebar);
    }

    render(session, mySymbol) {
        if (!session) return;
        const { gameType, board, turn, winner, p1, p2_display, is_bot } = session;

        // Title
        const titleStr = gameType === 'c4' ? 'Netgame: Connect 4' : 'Netgame: Tic-Tac-Toe';
        if (this.elements.headerTitle) {
            this.elements.headerTitle.textContent = titleStr;
        }

        // Status banner
        const isMyTurn = turn === mySymbol;
        this.elements.statusBanner.className = 'netgame-status-banner';

        if (winner) {
            if (winner === 'draw') {
                this.elements.statusBanner.textContent = 'Match Result: Draw!';
                this.elements.statusBanner.classList.add('turn-my');
            } else if (winner === mySymbol) {
                this.elements.statusBanner.textContent = '🎉 Victory! You Won!';
                this.elements.statusBanner.classList.add('game-win');
            } else {
                this.elements.statusBanner.textContent = 'Defeat! Opponent Won!';
                this.elements.statusBanner.classList.add('turn-opp');
            }
        } else {
            if (isMyTurn) {
                this.elements.statusBanner.textContent = `Your Turn (${mySymbol}) — Make a move!`;
                this.elements.statusBanner.classList.add('turn-my');
            } else {
                const oppName = is_bot ? 'Automated Bot' : (p2_display || 'Opponent');
                this.elements.statusBanner.textContent = `Waiting for ${oppName} (${turn})...`;
                this.elements.statusBanner.classList.add('turn-opp');
            }
        }

        // Render Board
        this.elements.boardArea.innerHTML = '';
        if (gameType === 'c4') {
            this._renderC4Board(board, isMyTurn && !winner);
        } else if (gameType === 'ttt') {
            this._renderTTTBoard(board, isMyTurn && !winner);
        }
    }

    _renderC4Board(board, canMove) {
        const { Utils } = this.dependencies;
        const wrapper = Utils.createElement('div', { className: 'netgame-c4-wrapper' });

        // Column drop buttons (1 to 7)
        const colButtons = Utils.createElement('div', { className: 'netgame-c4-col-buttons' });
        for (let c = 0; c < 7; c++) {
            const isColFull = board[0][c] !== '.';
            const btn = Utils.createElement('button', {
                className: 'netgame-col-btn',
                textContent: `↓ ${c + 1}`,
                title: `Drop in column ${c + 1} (or press '${c + 1}')`,
                eventListeners: { click: () => this.callbacks.onMove(c + 1) }
            });
            if (!canMove || isColFull) {
                btn.disabled = true;
            }
            colButtons.appendChild(btn);
        }
        wrapper.appendChild(colButtons);

        // 7x6 board
        const grid = Utils.createElement('div', { className: 'netgame-c4-board' });
        for (let r = 0; r < 6; r++) {
            for (let c = 0; c < 7; c++) {
                const cellVal = board[r][c];
                const slot = Utils.createElement('div', { className: 'netgame-c4-slot' });
                if (cellVal === 'X') {
                    const piece = Utils.createElement('div', { className: 'netgame-piece netgame-piece-x' });
                    slot.appendChild(piece);
                } else if (cellVal === 'O') {
                    const piece = Utils.createElement('div', { className: 'netgame-piece netgame-piece-o' });
                    slot.appendChild(piece);
                }
                grid.appendChild(slot);
            }
        }
        wrapper.appendChild(grid);
        this.elements.boardArea.appendChild(wrapper);
    }

    _renderTTTBoard(board, canMove) {
        const { Utils } = this.dependencies;
        const grid = Utils.createElement('div', { className: 'netgame-ttt-board' });

        for (let i = 0; i < 9; i++) {
            const cellVal = board[i];
            const isTaken = cellVal !== '.';
            const slot = Utils.createElement('div', {
                className: `netgame-ttt-slot ${isTaken ? 'taken' : ''}`,
                textContent: isTaken ? cellVal : (i + 1),
                eventListeners: {
                    click: () => {
                        if (canMove && !isTaken) {
                            this.callbacks.onMove(i + 1);
                        }
                    }
                }
            });

            if (cellVal === 'X') {
                slot.classList.add('netgame-piece-x');
            } else if (cellVal === 'O') {
                slot.classList.add('netgame-piece-o');
            }

            if (!canMove || isTaken) {
                slot.style.cursor = 'default';
            }
            grid.appendChild(slot);
        }
        this.elements.boardArea.appendChild(grid);
    }

    appendLog(message, type = 'info') {
        const { Utils } = this.dependencies;
        const entry = Utils.createElement('div', {
            className: `netgame-log-entry ${type}`,
            textContent: message
        });
        this.elements.moveLog.appendChild(entry);
        this.elements.moveLog.scrollTop = this.elements.moveLog.scrollHeight;
    }

    clearLog() {
        this.elements.moveLog.innerHTML = '';
    }
};
