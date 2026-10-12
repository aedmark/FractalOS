'use strict';
// P9-02: the deploy-time mesh switch (D-046). Needs a server on resources/ and Playwright, like smoke.js.
//   node tests/deploy_mesh.js http://127.0.0.1:8000/index.html
// deploy.json is faked with page.route, so nothing on disk changes. A page with no deploy.json must keep the
// mesh off; "auto" must aim the WebSocket at the page's own host; an explicit URL must win.
//   node tests/deploy_mesh.js <url> --live   also needs `python3 extras/signaling_server.py` running on the
//   page's host (port 8080): two browsers must then discover each other through the real relay.

const { chromium } = require('playwright');

const url = process.argv[2] || 'http://127.0.0.1:8000/index.html';
const host = new URL(url).hostname;
const live = process.argv.includes('--live');

const CASES = [
    { name: 'no deploy.json: mesh stays off', deploy: null, enabled: false, ws: null },
    { name: 'networking false: mesh stays off', deploy: { networking: false }, enabled: false, ws: null },
    { name: 'auto: signaling on the page host', deploy: { networking: true, signalingUrl: 'auto', signalingPort: 8080 },
        enabled: true, ws: `ws://${host}:8080/` },
    { name: 'auto with another port', deploy: { networking: true, signalingUrl: 'auto', signalingPort: 9191 },
        enabled: true, ws: `ws://${host}:9191/` },
    { name: 'explicit URL', deploy: { networking: true, signalingUrl: 'ws://relay.example:8080' },
        enabled: true, ws: 'ws://relay.example:8080/' },
    { name: 'junk deploy.json is ignored', deploy: '{not json', enabled: false, ws: null },
];

let failures = 0;
function report(name, ok, detail = '') {
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok || !detail ? '' : `  [${detail}]`}`);
    if (!ok) failures++;
}

async function bootedPage(context, deploy, seenSockets) {
    const page = await context.newPage();
    page.on('websocket', ws => seenSockets.push(ws.url()));
    await page.route('**/deploy.json', route => {
        if (deploy === null) return route.fulfill({ status: 404, body: 'nope' });
        const body = typeof deploy === 'string' ? deploy : JSON.stringify(deploy);
        return route.fulfill({ status: 200, contentType: 'application/json', body });
    });
    return page;
}

// First visit shows onboarding, which returns before networking starts. Mark it done, persist, reload.
async function openOnboarded(context, deploy, sockets) {
    const page = await bootedPage(context, deploy, sockets);
    await page.goto(url);
    await page.waitForFunction(() => typeof dependencies !== 'undefined' && dependencies.StorageManager, null, { timeout: 120000 });
    await page.evaluate(async () => {
        const { Config, StorageManager, StorageHAL } = dependencies;
        StorageManager.saveItem(Config.STORAGE_KEYS.ONBOARDING_COMPLETE, true, 'Onboarding Status');
        await StorageHAL.saveLocalStorage(StorageManager.exportLocalStorage());
    });
    sockets.length = 0;
    await page.reload();
    // The mesh is on or off by the time startNetworking() returns; wait for the end of onload.
    await page.waitForFunction(() => typeof CommandExecutor !== 'undefined' && document.querySelector('#output div'),
        null, { timeout: 120000 });
    await page.waitForTimeout(3000);
    return page;
}

(async () => {
    const launchOptions = process.env.CHROME ? { executablePath: process.env.CHROME } : {};
    const browser = await chromium.launch(launchOptions);
    try {
        for (const c of CASES) {
            const context = await browser.newContext();
            const sockets = [];
            const page = await openOnboarded(context, c.deploy, sockets);
            const enabled = await page.evaluate(() => dependencies.Config.NETWORKING.NETWORKING_ENABLED === true);
            report(`${c.name}: NETWORKING_ENABLED is ${c.enabled}`, enabled === c.enabled, `got ${enabled}`);
            const gotWs = sockets.length ? sockets[0] : null;
            report(`${c.name}: WebSocket ${c.ws}`, gotWs === c.ws, `got ${gotWs}`);
            await context.close();
        }
        if (live) {
            const auto = { networking: true, signalingUrl: 'auto', signalingPort: 8080 };
            const ctxA = await browser.newContext(), ctxB = await browser.newContext();
            const a = await openOnboarded(ctxA, auto, []);
            const b = await openOnboarded(ctxB, auto, []);
            // Separate contexts share no BroadcastChannel, so any peer seen here came through the relay.
            await a.waitForTimeout(5000);
            const idA = await a.evaluate(() => dependencies.NetworkManager.instanceId);
            const idB = await b.evaluate(() => dependencies.NetworkManager.instanceId);
            const seenByA = await a.evaluate(() => [...dependencies.NetworkManager.peerMetadata.keys()]);
            const seenByB = await b.evaluate(() => [...dependencies.NetworkManager.peerMetadata.keys()]);
            report('live relay: A discovers B', seenByA.includes(idB), JSON.stringify(seenByA));
            report('live relay: B discovers A', seenByB.includes(idA), JSON.stringify(seenByB));
            await ctxA.close(); await ctxB.close();
        }
    } finally {
        await browser.close();
    }
    console.log(failures ? `\n${failures} FAILED` : '\nAll deploy-mesh checks passed.');
    process.exit(failures ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
