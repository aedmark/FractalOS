window.StatusBarManager = class StatusBarManager {
    constructor() {
        this.dependencies = {};
        this.domElements = {};
        this.isVisible = true;
        this.notifications = [];
        this.unreadCount = 0;
        this.currentTicker = null;
        this.tickerTimer = null;
        this.isDrawerOpen = false;
        this.intervalTimer = null;
        this.agentStatus = "idle"; // "idle" | "planning" | "running" | "voltage"
    }

    initialize(domElements) {
        this.domElements = domElements;

        const terminalDiv = domElements.terminalDiv;
        if (!terminalDiv) return;

        // Create or find status-bar container
        let barEl = document.getElementById("status-bar");
        if (!barEl) {
            barEl = document.createElement("div");
            barEl.id = "status-bar";
            barEl.className = "status-bar";
            terminalDiv.insertBefore(barEl, terminalDiv.firstChild);
        }
        this.domElements.statusBar = barEl;

        // Build status bar sections: left, center, right
        barEl.innerHTML = `
            <div class="status-bar__left">
                <span class="status-bar__item status-bar__item--os" title="FractalOS">⬡ fractal</span>
                <span class="status-bar__item status-bar__item--user" id="status-bar-user">Guest@fractal</span>
                <span class="status-bar__item status-bar__item--cwd" id="status-bar-cwd">~</span>
                <span class="status-bar__item status-bar__item--panes hidden" id="status-bar-panes">[1 pane]</span>
                <span class="status-bar__item status-bar__item--jobs" id="status-bar-jobs" title="Background jobs">⚙ 0 jobs</span>
            </div>
            <div class="status-bar__center">
                <div class="status-bar__ticker" id="status-bar-ticker" title="Click to view notifications">
                    <span class="status-bar__ticker-icon">🔔</span>
                    <span class="status-bar__ticker-text">System ready</span>
                </div>
            </div>
            <div class="status-bar__right">
                <span class="status-bar__item status-bar__item--agent" id="status-bar-agent" title="Samwise AI Agent">🤖 idle</span>
                <span class="status-bar__item status-bar__item--mesh" id="status-bar-mesh" title="Mesh peers connected">🌐 0 peers</span>
                <button class="status-bar__btn status-bar__btn--audio" id="status-bar-audio" title="Toggle audio mute">🔊</button>
                <button class="status-bar__btn status-bar__btn--bell" id="status-bar-bell" title="Notification history">🔔 <span id="status-bar-badge" class="status-bar__badge hidden">0</span></button>
                <span class="status-bar__item status-bar__item--clock" id="status-bar-clock">00:00:00</span>
            </div>
            <div class="notification-drawer hidden" id="notification-drawer">
                <div class="notification-drawer__header">
                    <span class="notification-drawer__title">System Notifications</span>
                    <button class="notification-drawer__clear-btn" id="notification-drawer-clear">Clear</button>
                </div>
                <div class="notification-drawer__list" id="notification-drawer-list">
                    <div class="notification-drawer__empty">No notifications</div>
                </div>
            </div>
        `;

        // Wire event listeners
        const audioBtn = document.getElementById("status-bar-audio");
        audioBtn?.addEventListener("click", () => {
            if (this.dependencies.SoundManager) {
                const muted = this.dependencies.SoundManager.toggleMute();
                audioBtn.textContent = muted ? "🔇" : "🔊";
                audioBtn.classList.toggle("status-bar__btn--muted", muted);
            }
        });

        const bellBtn = document.getElementById("status-bar-bell");
        bellBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            this.toggleDrawer();
        });

        const ticker = document.getElementById("status-bar-ticker");
        ticker?.addEventListener("click", () => {
            this.toggleDrawer();
        });

        const clearBtn = document.getElementById("notification-drawer-clear");
        clearBtn?.addEventListener("click", (e) => {
            e.stopPropagation();
            this.clearNotifications();
        });

        const jobsItem = document.getElementById("status-bar-jobs");
        jobsItem?.addEventListener("click", () => {
            if (window.CommandExecutor) {
                window.CommandExecutor.processSingleCommand("jobs", { isInteractive: false });
            }
        });

        const meshItem = document.getElementById("status-bar-mesh");
        meshItem?.addEventListener("click", () => {
            if (window.CommandExecutor) {
                window.CommandExecutor.processSingleCommand("peers", { isInteractive: false });
            }
        });

        // Close notification drawer when clicking outside
        document.addEventListener("click", (e) => {
            if (this.isDrawerOpen && !e.target.closest("#notification-drawer, #status-bar-bell")) {
                this.closeDrawer();
            }
        });

        // Start 1-second update timer
        if (this.intervalTimer) clearInterval(this.intervalTimer);
        this.intervalTimer = setInterval(() => {
            this.update();
        }, 1000);

        this.update();
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    setAgentStatus(status) {
        this.agentStatus = status;
        const agentEl = document.getElementById("status-bar-agent");
        if (agentEl) {
            agentEl.textContent = `🤖 ${status}`;
            if (status.includes("run") || status.includes("plan")) {
                agentEl.classList.add("status-bar__item--pulse");
            } else {
                agentEl.classList.remove("status-bar__item--pulse");
            }
        }
    }

    notify(text, options = {}) {
        const level = options.level || "info"; // info | success | warn | error
        const timeout = options.timeout !== undefined ? options.timeout : 4500;
        const id = `notif-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        const timestamp = new Date();

        const item = {
            id,
            text,
            level,
            timestamp,
            read: false
        };

        this.notifications.unshift(item);
        if (this.notifications.length > 50) this.notifications.pop(); // Keep 50

        if (!this.isDrawerOpen) {
            this.unreadCount++;
        }

        // Update center ticker
        const ticker = document.getElementById("status-bar-ticker");
        if (ticker) {
            const iconMap = {
                info: "ℹ️",
                success: "✓",
                warn: "⚠️",
                error: "🛑"
            };
            const icon = options.icon || iconMap[level] || "🔔";

            const iconSpan = ticker.querySelector(".status-bar__ticker-icon");
            const textSpan = ticker.querySelector(".status-bar__ticker-text");
            if (iconSpan) iconSpan.textContent = icon;
            if (textSpan) textSpan.textContent = text;

            ticker.className = `status-bar__ticker status-bar__ticker--${level} status-bar__ticker--active`;

            if (this.tickerTimer) clearTimeout(this.tickerTimer);
            if (timeout > 0) {
                this.tickerTimer = setTimeout(() => {
                    ticker.classList.remove("status-bar__ticker--active");
                }, timeout);
            }
        }

        // Play subtle sound if unmuted and not silent
        if (!options.silent && this.dependencies.SoundManager && !this.dependencies.SoundManager.isMuted) {
            if (level === "error") {
                this.dependencies.SoundManager.playNote?.("C4", "16n");
            } else if (level === "success") {
                this.dependencies.SoundManager.playNote?.("G5", "32n");
            }
        }

        this._renderDrawerList();
        this._updateBadge();
        return item;
    }

    toggleDrawer() {
        if (this.isDrawerOpen) {
            this.closeDrawer();
        } else {
            this.openDrawer();
        }
    }

    openDrawer() {
        const drawer = document.getElementById("notification-drawer");
        if (drawer) {
            drawer.classList.remove("hidden");
            this.isDrawerOpen = true;
            this.unreadCount = 0;
            this.notifications.forEach(n => n.read = true);
            this._updateBadge();
            this._renderDrawerList();
        }
    }

    closeDrawer() {
        const drawer = document.getElementById("notification-drawer");
        if (drawer) {
            drawer.classList.add("hidden");
            this.isDrawerOpen = false;
        }
    }

    clearNotifications() {
        this.notifications = [];
        this.unreadCount = 0;
        this._updateBadge();
        this._renderDrawerList();
    }

    setVisible(val) {
        this.isVisible = !!val;
        const barEl = this.domElements.statusBar;
        if (barEl) {
            barEl.classList.toggle("hidden", !this.isVisible);
        }
    }

    toggleVisible() {
        this.setVisible(!this.isVisible);
        return this.isVisible;
    }

    _updateBadge() {
        const badge = document.getElementById("status-bar-badge");
        if (!badge) return;

        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 99 ? "99+" : String(this.unreadCount);
            badge.classList.remove("hidden");
        } else {
            badge.classList.add("hidden");
        }
    }

    _renderDrawerList() {
        const list = document.getElementById("notification-drawer-list");
        if (!list) return;

        if (this.notifications.length === 0) {
            list.innerHTML = `<div class="notification-drawer__empty">No notifications</div>`;
            return;
        }

        const iconMap = {
            info: "ℹ️",
            success: "✓",
            warn: "⚠️",
            error: "🛑"
        };

        list.innerHTML = this.notifications.map(n => {
            const timeStr = n.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const icon = iconMap[n.level] || "🔔";
            return `
                <div class="notification-drawer__item notification-drawer__item--${n.level}">
                    <span class="notification-drawer__item-icon">${icon}</span>
                    <div class="notification-drawer__item-body">
                        <div class="notification-drawer__item-text">${n.text}</div>
                        <div class="notification-drawer__item-time">${timeStr}</div>
                    </div>
                </div>
            `;
        }).join("");
    }

    update() {
        // Clock
        const clockEl = document.getElementById("status-bar-clock");
        if (clockEl) {
            const now = new Date();
            clockEl.textContent = now.toTimeString().slice(0, 8);
        }

        // User & CWD
        const { FileSystemManager, MultiplexerManager, NetworkManager, SoundManager } = this.dependencies;

        const cwdEl = document.getElementById("status-bar-cwd");
        if (cwdEl && FileSystemManager?.getCurrentPath) {
            const path = FileSystemManager.getCurrentPath();
            cwdEl.textContent = path === "/home/Guest" ? "~" : (path.replace("/home/Guest", "~") || "/");
        }

        // Panes count
        const panesEl = document.getElementById("status-bar-panes");
        if (panesEl && MultiplexerManager?.getPanes) {
            const count = MultiplexerManager.getPanes().length;
            if (count > 1) {
                panesEl.textContent = `[${count} panes]`;
                panesEl.classList.remove("hidden");
            } else {
                panesEl.classList.add("hidden");
            }
        }

        // Jobs count
        const jobsEl = document.getElementById("status-bar-jobs");
        if (jobsEl) {
            const jobCount = window.activeJobs ? Object.keys(window.activeJobs).length : 0;
            jobsEl.textContent = `⚙ ${jobCount} job${jobCount === 1 ? '' : 's'}`;
            if (jobCount > 0) {
                jobsEl.classList.add("status-bar__item--active-jobs");
            } else {
                jobsEl.classList.remove("status-bar__item--active-jobs");
            }
        }

        // Mesh Peers
        const meshEl = document.getElementById("status-bar-mesh");
        if (meshEl) {
            const peerCount = NetworkManager?.peers ? NetworkManager.peers.size : 0;
            meshEl.textContent = `🌐 ${peerCount} peer${peerCount === 1 ? '' : 's'}`;
            if (peerCount > 0) {
                meshEl.classList.add("status-bar__item--connected");
            } else {
                meshEl.classList.remove("status-bar__item--connected");
            }
        }

        // Audio mute icon
        const audioBtn = document.getElementById("status-bar-audio");
        if (audioBtn && SoundManager) {
            const isMuted = SoundManager.isMuted;
            audioBtn.textContent = isMuted ? "🔇" : "🔊";
            audioBtn.classList.toggle("status-bar__btn--muted", isMuted);
        }
    }

    getStatusSummary() {
        const { FileSystemManager, MultiplexerManager, NetworkManager, SoundManager } = this.dependencies;
        const peerCount = NetworkManager?.peers ? NetworkManager.peers.size : 0;
        const jobCount = window.activeJobs ? Object.keys(window.activeJobs).length : 0;
        const panesCount = MultiplexerManager?.getPanes ? MultiplexerManager.getPanes().length : 1;
        const cwd = FileSystemManager?.getCurrentPath ? FileSystemManager.getCurrentPath() : "/";
        const isMuted = SoundManager ? !!SoundManager.isMuted : false;

        return {
            isVisible: this.isVisible,
            agentStatus: this.agentStatus,
            peerCount,
            jobCount,
            panesCount,
            cwd,
            isMuted,
            unreadCount: this.unreadCount,
            totalNotifications: this.notifications.length
        };
    }
};
