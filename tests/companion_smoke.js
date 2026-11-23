const assert = require("node:assert/strict");
const http = require("node:http");
const { chromium } = require("playwright");

const pageUrl = process.argv[2] || "http://127.0.0.1:8000/index.html";
const origin = new URL(pageUrl).origin;
const turns = [];
const sessionId = "companion-smoke";
let pairingCode = "fixture-code";
let releaseFirstReply;
let observeFirstTurn;
let offline = false;
const firstTurn = new Promise(resolve => { observeFirstTurn = resolve; });

const companion = http.createServer((request, response) => {
    if (offline) {
        response.destroy();
        return;
    }
    function send(status, payload) {
        response.writeHead(status, {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Content-Type": "application/json",
        });
        response.end(payload ? JSON.stringify(payload) : undefined);
    }
    if (request.method === "OPTIONS") return send(204);
    if (request.headers.authorization !== `Bearer ${pairingCode}`) {
        return send(401, { error: { code: "pairing_required", message: "Pair again." } });
    }
    if (request.url === "/v1/session") return send(200, { version: 1, session_id: sessionId });
    let body = "";
    request.setEncoding("utf8");
    request.on("data", chunk => { body += chunk; });
    request.on("end", () => {
        const turn = JSON.parse(body);
        turns.push(turn);
        if (turn.message === "Can you still hear me?" && pairingCode === "fixture-code") {
            pairingCode = "fresh-fixture-code";
            return send(401, { error: { code: "pairing_required", message: "Pair again." } });
        }
        const room = turn.scene?.room_name;
        const reply = turn.message === "What did I just take?"
            ? `You took the ${turn.scene.last_take.name}.`
            : room ? `From ${room}: old lantern.` : "You picked up the <b>old lantern</b>.";
        const answer = () => send(200, { turn_id: turn.turn_id, reply });
        if (turns.length === 1) {
            releaseFirstReply = answer;
            observeFirstTurn();
        } else if (turns.length === 4) {
            send(202, { turn_id: turn.turn_id, error: { code: "turn_pending", message: "Still running." } });
        } else {
            answer();
        }
    });
});

(async () => {
    await new Promise((resolve, reject) => {
        companion.once("error", reject);
        companion.listen(0, "127.0.0.1", resolve);
    });
    let browser;
    try {
        browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
        const page = await browser.newPage();
        await page.context().grantPermissions(["clipboard-read", "clipboard-write"], { origin });
        await page.goto(pageUrl);
        await page.waitForFunction(() => typeof FractalOS_Kernel !== "undefined" && FractalOS_Kernel.isReady, null, { timeout: 120000 });
        const launch = command => page.evaluate(text => CommandExecutor.processSingleCommand(text, { isInteractive: false }), command);
        assert.equal((await launch("samwise --chat --companion")).success, true);
        assert.equal((await launch("adventure --companion")).success, true);

        const adventure = page.locator("#adventure-container");
        const chat = page.locator("#boneamanita-app-container");
        const pairingCodeField = scope => scope.getByLabel("BoneAmanita pairing code");
        const pairingPortField = scope => scope.getByLabel("BoneAmanita port");
        const pairButton = scope => scope.getByRole("button", { name: "Pair BoneAmanita", includeHidden: true });
        const code = pairingCodeField(adventure);
        const port = pairingPortField(adventure);
        const pair = pairButton(adventure);
        const retry = page.getByRole("button", { name: "Retry turn", includeHidden: true });
        async function expectPairingHidden(scope) {
            const controls = [pairingCodeField(scope), pairingPortField(scope), pairButton(scope)];
            await Promise.all(controls.map(control => control.waitFor({ state: "hidden", timeout: 5000 })));
        }
        await port.fill(String(companion.address().port));
        await page.evaluate(value => navigator.clipboard.writeText(value), pairingCode);
        await code.press("Control+Shift+V");
        await page.waitForFunction(value => document.querySelector('#adventure-container [aria-label="BoneAmanita pairing code"]')?.value === value,
            pairingCode, { timeout: 5000 });
        assert.equal(await page.getByText(pairingCode, { exact: true }).count(), 0);
        assert.equal(await page.locator("#adventure-container > .app-header > .window-controls button").count(), 4);
        assert.equal(await pair.evaluate(el => el.classList.contains("btn")), true);
        await pair.click();
        await page.getByText("Paired with BoneAmanita.").waitFor();
        await expectPairingHidden(adventure);
        await expectPairingHidden(chat);
        const command = page.getByRole("textbox", { name: "Adventure command" });
        const adventureAsk = adventure.getByRole("textbox", { name: "Ask BoneAmanita" });
        const chatAsk = chat.getByRole("textbox", { name: "Ask BoneAmanita" });
        async function submit(input, text) {
            await input.fill(text);
            await input.press("Enter");
        }
        await submit(command, "go north");
        await page.getByText("Server Closet", { exact: true }).waitFor();
        await submit(command, "take lantern");
        await page.getByText("You take the old lantern.").waitFor();
        await submit(adventureAsk, "What am I carrying?");
        await Promise.race([
            firstTurn,
            page.getByText("Could not read the current adventure scene.").waitFor({ timeout: 10000 })
                .then(() => { throw new Error("Adventure scene missing"); }),
        ]);
        await submit(adventureAsk, "What am I carrying?");
        assert.equal(await adventure.getByText("What am I carrying?", { exact: true }).count(), 1);
        await submit(command, "go south");
        await page.getByText("Test Chamber", { exact: true }).waitFor();
        releaseFirstReply();
        releaseFirstReply = null;
        await page.getByText("BoneAmanita (Server Closet): From Server Closet: old lantern.").waitFor();
        await submit(adventureAsk, "Where am I now, and what did I bring?");
        await page.getByText("BoneAmanita (Test Chamber): From Test Chamber: old lantern.").waitFor();
        assert.deepEqual(turns.slice(0, 2).map(turn => turn.scene.room_id), ["server_closet", "test_chamber"]);
        assert.deepEqual(turns[0].scene.inventory, [{ id: "lantern", name: "old lantern" }]);
        assert.deepEqual(turns[0].scene.exits, ["south"]);
        assert.equal(turns[1].scene.world_id, turns[0].scene.world_id);
        assert.ok(turns[1].scene.revision > turns[0].scene.revision);

        await submit(command, "take brass key");
        await adventure.getByText("You take the brass key.", { exact: true }).waitFor({ timeout: 5000 });
        await submit(command, "take lantern");
        await adventure.getByText("You don't see that here.", { exact: true }).waitFor();
        await submit(command, "drop old lantern");
        await adventure.getByText("Dropped the old lantern.", { exact: true }).waitFor();
        const pickupIndex = turns.length;
        await submit(adventureAsk, "What did I just take?");
        await adventure.getByText("BoneAmanita (Test Chamber): You took the brass key.").waitFor();
        assert.deepEqual(turns[pickupIndex].scene.last_take, { id: "key", name: "brass key" });
        assert.deepEqual(turns[pickupIndex].scene.inventory.map(item => item.id), ["key"]);
        assert.deepEqual(turns[pickupIndex].scene.pickup_history, [
            { id: "lantern", name: "old lantern" },
            { id: "key", name: "brass key" },
        ]);
        assert.deepEqual(turns[pickupIndex].scene.pickup_locations, [
            { id: "lantern", name: "old lantern", room_id: "server_closet", room_name: "Server Closet" },
            { id: "key", name: "brass key", room_id: "test_chamber", room_name: "Test Chamber" },
        ]);

        await submit(command, "quit");
        await adventure.waitFor({ state: "hidden" });
        await submit(chatAsk, "What did I pick up in the closet?");
        await page.getByText("Still running.").waitFor();
        await retry.click();
        const reply = page.getByText("You picked up the <b>old lantern</b>.", { exact: true });
        await reply.waitFor();
        assert.equal(await reply.locator("b").count(), 0);
        assert.equal(turns[3].scene, null);
        assert.deepEqual(turns[3], turns[4]);
        assert.ok(turns.every(turn => turn.session_id === sessionId));
        assert.equal(new Set(turns.map(turn => turn.turn_id)).size, 4);

        await submit(chatAsk, "Can you still hear me?");
        await page.getByText("Pair again.").waitFor();
        const chatCode = pairingCodeField(chat);
        await chatCode.waitFor({ state: "visible" });
        await retry.waitFor({ state: "hidden" });
        assert.equal(await pairingPortField(chat).inputValue(), String(companion.address().port));
        await chatCode.fill(pairingCode);
        await pairButton(chat).click();
        await expectPairingHidden(chat);
        await retry.click();
        await reply.nth(1).waitFor();
        assert.deepEqual(turns[5], turns[6]);

        await page.keyboard.press("Escape");
        await page.locator("#boneamanita-app-container").waitFor({ state: "hidden" });
        offline = true;
        assert.equal((await launch("adventure --companion")).success, true);
        await expectPairingHidden(adventure);
        await submit(adventureAsk, "Is anyone there?");
        await page.getByText("BoneAmanita did not return a result. Retry the turn to check its outcome.").waitFor();
        await submit(command, "go north");
        await page.getByText("Server Closet", { exact: true }).waitFor();
        await submit(command, "inventory");
        await page.getByText("You are not carrying anything.", { exact: true }).waitFor();
        console.log("PASS companion browser playthrough: two rooms, carried inventory, shared pairing, re-pairing, plain chat, retry, and offline commands.");
    } finally {
        releaseFirstReply?.();
        await browser?.close();
        companion.closeAllConnections();
        await new Promise(resolve => companion.close(resolve));
    }
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
