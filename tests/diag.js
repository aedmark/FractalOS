#!/usr/bin/env node
// tests/diag.js: run extras/diag.sh (the in-OS command test suite) headlessly and grade it.
//
//   cd resources && python3 -m http.server 8000 &
//   node tests/diag.js http://127.0.0.1:8000/index.html [path/to/script.sh]
//
// Boots the OS, completes onboarding as a real user, logs in as root, writes the
// script into the VFS, runs it with `run`, then counts its check_fail assertions
// and any error lines. The full transcript is written to tests/out/diag-transcript.txt.
// Exit code 0 = no CHECK_FAIL: FAILURE and no unexpected error lines. See docs/TESTING.md.

'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const url = process.argv[2] || 'http://127.0.0.1:8000/index.html';
const scriptPath = process.argv[3] || path.join(__dirname, '..', 'extras', 'diag.sh');
const BOOT_TIMEOUT_MS = 120000;
const RUN_TIMEOUT_MS = Number(process.env.DIAG_TIMEOUT_MS || 15 * 60 * 1000);
const OUT_DIR = path.join(__dirname, 'out');

const USER = { username: 'gordon', password: 'hunter2', rootPassword: 'rootpw' };

async function waitForKernel(page) {
    await page.waitForFunction(
        () => typeof OopisOS_Kernel !== 'undefined' && OopisOS_Kernel.isReady === true,
        null, { timeout: BOOT_TIMEOUT_MS });
}

(async () => {
    const script = fs.readFileSync(scriptPath, 'utf8');
    const launchOptions = process.env.CHROME ? { executablePath: process.env.CHROME } : {};
    const browser = await chromium.launch(launchOptions);
    const page = await browser.newPage();
    const consoleErrors = [];
    page.on('pageerror', e => consoleErrors.push(`[pageerror] ${e.message}`));
    // beep/play at the end of diag.sh need an AudioContext, which headless Chromium
    // never unlocks (no user gesture); that one console error is expected.
    page.on('console', m => { if (m.type() === 'error' && !m.text().includes('SoundManager not initialized')) consoleErrors.push(m.text()); });

    let exitCode = 1;
    try {
        // 1. Boot and complete onboarding the way OnboardingManager.onFinish does, then reload.
        await page.goto(url);
        await waitForKernel(page);
        const loaded = new Promise(resolve => {
            page.on('console', m => { if (m.text().includes('loaded successfully')) resolve(); });
        });
        await page.evaluate(async (u) => {
            const { UserManager, StorageManager, Config } = dependencies;
            const result = await UserManager.performFirstTimeSetup(u);
            if (!result.success) throw new Error('first_time_setup failed: ' + JSON.stringify(result));
            StorageManager.saveItem(Config.STORAGE_KEYS.USER_CREDENTIALS, result.data.users, 'User Credentials');
            StorageManager.saveItem(Config.STORAGE_KEYS.USER_GROUPS, result.data.groups, 'User Groups');
            StorageManager.saveItem(Config.STORAGE_KEYS.ONBOARDING_COMPLETE, true, 'Onboarding Status');
            StorageManager.saveItem(Config.STORAGE_KEYS.LAST_CREATED_USER, u.username, 'Last Created User');
        }, USER);
        await page.reload();
        await waitForKernel(page);
        await Promise.race([loaded, page.waitForTimeout(60000).then(() => { throw new Error('post-onboarding boot never finished'); })]);
        const who = await page.evaluate(() => dependencies.SessionManager.getCurrentUserFromStack());
        console.log(`booted; logged in as ${who}`);

        // 2. Put the script in root's home and become root.
        const vfsPath = '/home/root/' + path.basename(scriptPath);
        await page.evaluate(async ([p, content]) => {
            const r = JSON.parse(await OopisOS_Kernel.syscall('filesystem', 'write_file', [p, content, { name: 'root', group: 'root' }]));
            if (r.success === false) throw new Error('write_file failed: ' + JSON.stringify(r));
        }, [vfsPath, script]);
        for (const cmd of [`login root ${USER.rootPassword}`, `chmod 755 ${vfsPath}`, 'cd /home/root', 'whoami']) {
            const r = await page.evaluate(async c => await CommandExecutor.processSingleCommand(c, { isInteractive: false }), cmd);
            console.log(`${cmd} -> ${JSON.stringify(r).slice(0, 120)}`);
            if (!r.success) throw new Error(`setup command failed: ${cmd}`);
        }
        await page.evaluate(() => dependencies.OutputManager.clearOutput());

        // Record every line as it is printed: su/logout restore a user's saved terminal
        // state, which replaces the output div, so reading the DOM afterwards loses most of it.
        await page.evaluate(() => {
            const om = dependencies.OutputManager;
            const errClass = dependencies.Config.CSS_CLASSES.ERROR_MSG;
            window.__diagLog = [];
            const original = om.appendToOutput.bind(om);
            om.appendToOutput = async (text, options = {}) => {
                const isError = !!(options.typeClass && options.typeClass.split(' ').includes(errClass));
                window.__diagLog.push({ text: String(text), isError });
                return original(text, options);
            };
        });

        // 3. Run it. execute_script awaits every line, so this returns when the script is done.
        const started = Date.now();
        const runResult = await Promise.race([
            page.evaluate(async p => await CommandExecutor.processSingleCommand(`run ${p}`, { isInteractive: false }), vfsPath),
            page.waitForTimeout(RUN_TIMEOUT_MS).then(() => { throw new Error(`script still running after ${RUN_TIMEOUT_MS / 1000}s`); }),
        ]);
        const seconds = ((Date.now() - started) / 1000).toFixed(0);
        console.log(`run finished in ${seconds}s -> ${JSON.stringify(runResult).slice(0, 200)}`);

        // 4. Grade the transcript.
        const { text, errorLines } = await page.evaluate(() => ({
            text: window.__diagLog.map(e => e.text).join('\n'),
            errorLines: window.__diagLog.filter(e => e.isError).map(e => e.text),
        }));
        fs.mkdirSync(OUT_DIR, { recursive: true });
        const transcriptPath = path.join(OUT_DIR, 'diag-transcript.txt');
        fs.writeFileSync(transcriptPath, text);

        const lines = text.split('\n');
        const failures = lines.filter(l => l.includes('CHECK_FAIL: FAILURE'));
        const successes = lines.filter(l => l.includes('CHECK_FAIL: SUCCESS'));
        // Lines starting with check_fail in the file are a floor: the script also writes
        // child scripts that contain their own check_fail calls (38 in the file, 40 run).
        const expectedChecks = (script.match(/^\s*check_fail\b/gm) || []).length;
        const finished = /ALL SYSTEMS OPERATIONAL/.test(text); // the closing banner's last line

        console.log(`\ncheck_fail: ${successes.length} passed, ${failures.length} failed, ${expectedChecks} at top level in the script`);
        console.log(`script reached its completion banner: ${finished}`);
        if (failures.length) console.log(failures.map(l => '  FAIL ' + l).join('\n'));
        console.log(`error lines printed by commands: ${errorLines.length}`);
        if (errorLines.length) console.log(errorLines.map(l => '  ERR  ' + l.split('\n')[0]).join('\n'));
        if (consoleErrors.length) {
            console.log(`browser console errors: ${consoleErrors.length}`);
            console.log(consoleErrors.slice(0, 20).map(l => '  CON  ' + l.split('\n')[0]).join('\n'));
        }
        console.log(`transcript: ${transcriptPath} (${lines.length} lines)`);

        const ok = finished && failures.length === 0 && errorLines.length === 0 && successes.length >= expectedChecks;
        console.log(ok ? 'PASS' : 'FAIL');
        exitCode = ok ? 0 : 1;
    } catch (e) {
        console.error(`aborted: ${e.message}`);
        try {
            fs.mkdirSync(OUT_DIR, { recursive: true });
            fs.writeFileSync(path.join(OUT_DIR, 'diag-transcript.txt'),
                await page.evaluate(() => (window.__diagLog || []).map(e => e.text).join('\n')));
        } catch (_) { /* nothing to save */ }
    } finally {
        await browser.close();
    }
    process.exit(exitCode);
})();
