/**
 * netgame_manager.js - App controller for Netgame multiplayer arcade.
 */

window.NetgameManager = class NetgameManager extends App {
    constructor() {
        super();
        this.dependencies = {};
        this.session = null;
        this.callbacks = {};
        this.ui = null;
        this.mySymbol = 'X';
    }

    async enter(appLayer, options = {}) {
        if (this.isActive) return;

        this.dependencies = options.dependencies;
        this.callbacks = this._createCallbacks();
        this.isActive = true;

        this.session = options.session || {
            gameType: 'c4',
            board: Array(6).fill().map(() => Array(7).fill('.')),
            turn: 'X',
            p1: 'Player 1',
            p2: 'Bot',
            p2_display: 'Automated Bot',
            my_symbol: 'X',
            winner: null,
            moves: [],
            is_bot: true
        };
        this.mySymbol = this.session.my_symbol || 'X';

        this.ui = new this.dependencies.NetgameUI(this.callbacks, this.dependencies);
        this.container = this.ui.getContainer();
        appLayer.appendChild(this.container);

        if (this.dependencies.NetworkManager) {
            this.dependencies.NetworkManager.setActiveGameApp(this);
        }

        this.ui.render(this.session, this.mySymbol);
        this.ui.appendLog(`Game started: ${this.session.gameType.toUpperCase()}`);
        this.ui.appendLog(`You are Player [${this.mySymbol}]`);

        this.container.focus();
        this._playSound('start');
    }

    exit() {
        if (!this.isActive) return;
        const { AppLayerManager } = this.dependencies;

        if (this.dependencies.NetworkManager) {
            this.dependencies.NetworkManager.setActiveGameApp(null);
        }

        AppLayerManager.hide(this);
        this.isActive = false;
        this.session = null;
        this.ui = null;
    }

    handleKeyDown(event) {
        if (event.key === 'Escape' || event.key === 'q') {
            this.exit();
            return;
        }

        if (!this.session || this.session.winner) return;

        // Number keys 1-7 (C4) or 1-9 (TTT)
        const num = parseInt(event.key, 10);
        if (!isNaN(num)) {
            if (this.session.gameType === 'c4' && num >= 1 && num <= 7) {
                this.handleMove(num);
            } else if (this.session.gameType === 'ttt' && num >= 1 && num <= 9) {
                this.handleMove(num);
            }
        }
    }

    _createCallbacks() {
        return {
            onExit: this.exit.bind(this),
            onMove: (val) => this.handleMove(val),
            onResign: () => this.handleResign(),
            onNewGame: () => this.handleNewGame(),
        };
    }

    async handleMove(val) {
        if (!this.session || this.session.winner) return;

        const isMyTurn = this.session.turn === this.mySymbol;
        if (!isMyTurn && !this.session.is_bot) {
            this.ui.appendLog(`Wait! It's not your turn.`, 'player-o');
            return;
        }

        // Execute command in kernel to ensure source of truth and state sync
        const username = this.dependencies.UserManager?.getCurrentUser()?.username || 'guest';
        const cmd = `netgame move ${val}`;

        try {
            const result = await this.dependencies.CommandExecutor.processSingleCommand(cmd, { isInteractive: false });
            if (!result.success) {
                const errMsg = result.error?.message || 'Invalid move.';
                this.ui.appendLog(errMsg, 'player-o');
                return;
            }

            // Sync state from kernel
            await this.refreshStateFromKernel();
            this._playSound('drop');
        } catch (e) {
            console.error('Netgame move error:', e);
        }
    }

    async refreshStateFromKernel() {
        try {
            const raw = await FractalOS_Kernel.syscall('commands.netgame', '_get_active_session', [
                this.dependencies.UserManager?.getCurrentUser()?.username || 'guest'
            ]);
            // If python session available
            if (raw) {
                const pySession = typeof raw === 'string' ? JSON.parse(raw) : raw;
                if (pySession) {
                    this.session = pySession;
                    this.mySymbol = pySession.my_symbol || this.mySymbol;
                    this.ui.render(this.session, this.mySymbol);

                    const lastMove = this.session.moves[this.session.moves.length - 1];
                    if (lastMove) {
                        const playerLabel = lastMove.player === this.mySymbol ? 'You' : (this.session.is_bot ? 'Bot' : 'Opponent');
                        this.ui.appendLog(`${playerLabel} played: ${lastMove.move}`, lastMove.player === 'X' ? 'player-x' : 'player-o');
                    }

                    if (this.session.winner) {
                        this._handleGameOver(this.session.winner);
                    }
                }
            }
        } catch (_) {
            // Kernel syscall fallback: re-render with local session
            if (this.session && this.ui) {
                this.ui.render(this.session, this.mySymbol);
            }
        }
    }

    handleRemoteMove(data) {
        if (!this.isActive) return;

        if (data.board) {
            this.session.board = data.board;
        }
        if (data.turn) {
            this.session.turn = data.turn;
        }
        if (data.winner) {
            this.session.winner = data.winner;
        }
        if (data.move) {
            this.session.moves.push({ player: this.mySymbol === 'X' ? 'O' : 'X', move: data.move });
            this.ui.appendLog(`Opponent played: ${data.move}`, 'player-o');
        }

        this.ui.render(this.session, this.mySymbol);
        this._playSound('drop');

        if (this.session.winner) {
            this._handleGameOver(this.session.winner);
        }
    }

    handleRemoteResign() {
        if (!this.isActive) return;
        this.session.winner = this.mySymbol;
        this.ui.appendLog(`Opponent has resigned the match!`, 'player-x');
        this.ui.render(this.session, this.mySymbol);
        this._handleGameOver(this.mySymbol);
    }

    async handleResign() {
        if (!this.isActive || !this.session || this.session.winner) return;
        await this.dependencies.CommandExecutor.processSingleCommand('netgame resign', { isInteractive: false });
        await this.refreshStateFromKernel();
        this.ui.appendLog('You resigned.', 'player-o');
        this._playSound('loss');
    }

    async handleNewGame() {
        const gameType = this.session?.gameType || 'c4';
        const isBot = this.session?.is_bot ? '--bot' : '';
        const peer = this.session?.peer || '';
        this.ui.clearLog();

        const hostCmd = `netgame host ${gameType} ${peer} ${isBot}`.trim();
        await this.dependencies.CommandExecutor.processSingleCommand(hostCmd, { isInteractive: false });
        await this.refreshStateFromKernel();
        this.ui.appendLog(`New match started: ${gameType.toUpperCase()}`);
        this._playSound('start');
    }

    _handleGameOver(winner) {
        if (winner === 'draw') {
            this.ui.appendLog(`Match ended in a DRAW.`, 'player-x');
            this._playSound('draw');
        } else if (winner === this.mySymbol) {
            this.ui.appendLog(`VICTORY! You won the match!`, 'player-x');
            this._playSound('win');
        } else {
            this.ui.appendLog(`DEFEAT! Opponent won the match.`, 'player-o');
            this._playSound('loss');
        }
    }

    _playSound(type) {
        const soundMgr = this.dependencies.SoundManager;
        if (!soundMgr || soundMgr.isMuted) return;

        try {
            if (type === 'start') {
                soundMgr.playSequence(['C4', 'E4', 'G4'], '16n');
            } else if (type === 'drop') {
                soundMgr.playTone('E5', '32n');
            } else if (type === 'win') {
                soundMgr.playSequence(['C4', 'E4', 'G4', 'C5'], '8n');
            } else if (type === 'loss') {
                soundMgr.playSequence(['G4', 'E4', 'C4'], '8n');
            } else if (type === 'draw') {
                soundMgr.playSequence(['E4', 'E4'], '8n');
            }
        } catch (_) {}
    }
};
