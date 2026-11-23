class CompanionClient extends EventTarget {
    #connection = null;
    #pending = null;
    #busy = false;

    constructor(currentUser) {
        super();
        this.currentUser = currentUser;
    }

    async #run(operation) {
        if (this.#busy) throw new Error("A BoneAmanita request is already running.");
        this.#busy = true;
        try {
            const owner = await this.currentUser();
            if (this.#connection && this.#connection.owner !== owner) {
                this.#connection = null;
                this.#pending = null;
            }
            const result = await operation(owner);
            if (await this.currentUser() !== owner) {
                this.#connection = null;
                this.#pending = null;
                throw new Error("The FractalOS user changed. Pair again to continue.");
            }
            return result;
        } finally {
            this.#busy = false;
            this.dispatchEvent(new Event("statechange"));
        }
    }

    async #request(connection, path, body) {
        let response;
        try {
            response = await fetch(`http://127.0.0.1:${connection.port}${path}`, {
                method: body ? "POST" : "GET",
                headers: {
                    Authorization: `Bearer ${connection.code}`,
                    ...(body && { "Content-Type": "application/json" }),
                },
                body,
                cache: "no-store",
                credentials: "omit",
                redirect: "error",
                referrerPolicy: "no-referrer",
                signal: AbortSignal.timeout(body ? 120000 : 10000),
            });
            return { status: response.status, data: await response.json() };
        } catch {
            throw new Error(body
                ? "BoneAmanita did not return a result. Retry the turn to check its outcome."
                : "Could not pair. Check the port, service, and configured browser origin.");
        }
    }

    async pair(code, port) {
        return this.#run(async owner => {
            if (!code || !Number.isInteger(port) || port < 1 || port > 65535) {
                throw new Error("Enter the pairing code and a port between 1 and 65535.");
            }
            const connection = { code, port, owner };
            const { status, data } = await this.#request(connection, "/v1/session");
            if (status !== 200 || data?.version !== 1 || typeof data.session_id !== "string") {
                throw new Error(data?.error?.message || "BoneAmanita could not pair.");
            }
            const changed = this.#pending && (this.#connection?.id !== data.session_id || this.#connection.port !== port);
            if (changed) this.#pending = null;
            this.#connection = { ...connection, id: data.session_id };
            return changed ? "Paired. The previous turn has an unknown outcome." : "Paired with BoneAmanita.";
        });
    }

    async pairingState() {
        const owner = await this.currentUser();
        const paired = Boolean(this.#connection?.code && this.#connection.owner === owner);
        return { paired, canRetry: paired && Boolean(this.#pending), port: paired ? this.#connection.port : null };
    }

    async ask(message, scene = null) {
        return this.#run(async () => {
            if (!this.#connection?.code) throw new Error("Pair with BoneAmanita first.");
            if (this.#pending) throw new Error("Retry the pending BoneAmanita turn before sending another.");
            if (!message.trim() || message.length > 15000) throw new Error("Enter a message of 1 to 15,000 characters.");
            const turnId = crypto.randomUUID();
            const body = JSON.stringify({
                version: 1, session_id: this.#connection.id, turn_id: turnId, message, scene,
            });
            this.#pending = { turnId, body, scene };
            return this.#sendPending();
        });
    }

    async retry() {
        return this.#run(() => {
            if (!this.#connection?.code) throw new Error("Pair with BoneAmanita first.");
            if (!this.#pending) throw new Error("There is no pending BoneAmanita turn.");
            return this.#sendPending();
        });
    }

    async #sendPending() {
        const pending = this.#pending;
        const { status, data } = await this.#request(this.#connection, "/v1/turn", pending.body);
        const code = data?.error?.code;
        if (status === 401 || code === "pairing_required") {
            this.#connection.code = null;
            throw new Error(data?.error?.message || "Pair with BoneAmanita again.");
        }
        if (["turn_pending", "turn_busy"].includes(code)) {
            throw new Error(data?.error?.message || "The result is pending. Retry the turn.");
        }
        if (code === "session_changed") {
            this.#connection = null;
            this.#pending = null;
            throw new Error("The companion session changed. Pair again. The previous turn has an unknown outcome.");
        }
        if (data?.turn_id !== pending.turnId && !code) {
            throw new Error("BoneAmanita returned an unexpected turn ID. Retry to check the result.");
        }
        this.#pending = null;
        if (status !== 200 || typeof data.reply !== "string") {
            throw new Error(data?.error?.message || "BoneAmanita could not answer this turn.");
        }
        return { reply: data.reply, scene: pending.scene };
    }
}

function companionControls(client, Utils, onReply) {
    const code = Utils.createElement("input", {
        type: "password", className: "companion-field", placeholder: "Pairing code",
        "aria-label": "BoneAmanita pairing code", autocomplete: "off",
    });
    const port = Utils.createElement("input", {
        type: "number", className: "companion-field", value: 8765, min: 1, max: 65535, "aria-label": "BoneAmanita port",
    });
    const pair = Utils.createElement("button", { type: "submit", className: "btn btn--confirm", textContent: "Pair BoneAmanita" });
    const retry = Utils.createElement("button", { type: "button", className: "btn", textContent: "Retry turn", hidden: "" });
    const status = Utils.createElement("span", { className: "companion-controls__status", role: "status" });
    const element = Utils.createElement("form", { className: "companion-controls", autocomplete: "off" }, code, port, pair, retry, status);
    const lifecycle = new AbortController();

    async function run(operation) {
        try {
            return await operation();
        } catch (error) {
            status.textContent = error.message;
        }
    }

    function syncPairingControls() {
        run(async () => {
            const { paired, canRetry, port: pairedPort } = await client.pairingState();
            if (paired) {
                code.value = "";
                port.value = pairedPort;
            }
            for (const control of [code, port, pair]) control.classList.toggle("hidden", paired);
            retry.hidden = !canRetry;
        });
    }

    element.addEventListener("submit", event => {
        event.preventDefault();
        const value = code.value.trim();
        code.value = "";
        run(async () => { status.textContent = await client.pair(value, Number(port.value)); });
    });
    retry.addEventListener("click", () => run(async () => {
        const result = await client.retry();
        status.textContent = "";
        onReply(result);
    }));
    client.addEventListener("statechange", syncPairingControls, { signal: lifecycle.signal });
    syncPairingControls();
    return {
        element,
        dispose: () => lifecycle.abort(),
        ask: (message, scene) => run(async () => {
            status.textContent = "Waiting for BoneAmanita…";
            const result = await client.ask(message, scene);
            status.textContent = "";
            onReply(result);
        }),
        setStatus: message => { status.textContent = message; },
    };
}
