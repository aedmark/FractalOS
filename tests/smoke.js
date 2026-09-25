#!/usr/bin/env node
// tests/smoke.js: boot FractalOS in headless Chromium and check the kernel works.
//
//   cd resources && python3 -m http.server 8000 &
//   node tests/smoke.js http://127.0.0.1:8000/index.html
//
// Needs Node 18+ and Playwright with a Chromium (or CHROME=/path/to/chrome).
// Exit code 0 = every check passed. See docs/TESTING.md.

'use strict';

const { chromium } = require('playwright');

const url = process.argv[2] || 'http://127.0.0.1:8000/index.html';
const BOOT_TIMEOUT_MS = 120000;

// Shell commands run through CommandExecutor as the default user (Guest), in
// this order. `expect` gets the result object and returns true on pass.
const CHECKS = [
    { cmd: 'echo hello', expect: r => r.success && r.output === 'hello' },
    { cmd: 'date', expect: r => r.success && /\d{4}/.test(r.output || '') },
    { cmd: 'whoami', expect: r => r.success && r.output === 'Guest' },
    { cmd: 'ls -la /home', expect: r => r.success && ['gordon', 'Guest', 'root'].every(n => (r.output || '').includes(n)) },
    { cmd: 'help | head -3', expect: r => r.success && (r.output || '').startsWith('FractalOS - Powered by Python') },
    // Guest may not write to /home: a denial is the correct answer.
    { cmd: 'mkdir /home/t', expect: r => !r.success && /Permission denied/.test(errorMessage(r)) },
    { cmd: 'cat /nonexistent', expect: r => !r.success && /No such file/.test(errorMessage(r)) },
    // python (D-011): the kernel's own interpreter, VFS-aware open()/input(), a step budget.
    { cmd: 'python -c "print(2 ** 10)"', expect: r => r.success && r.output === '1024' },
    { cmd: 'python -c "import sys; print(sys.argv[1:])" one two', expect: r => r.success && r.output === "['one', 'two']" },
    { cmd: 'echo 21 | python -c "print(int(input()) * 2)"', expect: r => r.success && r.output === '42' },
    { cmd: 'echo hello > /home/Guest/hello.txt', expect: r => r.success },
    { cmd: 'echo "print(open(\'/home/Guest/hello.txt\').read().upper())" > /home/Guest/shout.py', expect: r => r.success },
    { cmd: 'python /home/Guest/shout.py', expect: r => r.success && r.output === 'HELLO' },
    // cd is an effect applied after the line finishes, so it gets its own command (D-002).
    { cmd: 'cd /home/Guest', expect: r => r.success },
    { cmd: 'python -c "open(\'out.txt\', \'w\').write(\'written\')"', expect: r => r.success },
    { cmd: 'cd /', expect: r => r.success },
    { cmd: 'cat /home/Guest/out.txt', expect: r => r.success && r.output === 'written' },
    { cmd: 'python -c "with open(\'/home/Guest/out.txt\', \'a\') as f: f.write(\' twice\')"', expect: r => r.success },
    { cmd: 'cat /home/Guest/out.txt', expect: r => r.success && r.output === 'written twice' },
    { cmd: 'python -c "open(\'/etc/sudoers\', \'w\')"', expect: r => !r.success && /PermissionError/.test(errorMessage(r)) },
    { cmd: 'python -c "print(1); 1/0"', expect: r => !r.success && /^1\n[\s\S]*ZeroDivisionError/.test(errorMessage(r)) },
    { cmd: 'python -c "import sys; sys.exit(3)"', expect: r => !r.success && /exit status 3/.test(errorMessage(r)) },
    { cmd: 'python -c "print(("', expect: r => !r.success && /SyntaxError/.test(errorMessage(r)) },
    { cmd: 'python --steps 5000 -c "while True: pass"', expect: r => !r.success && /stopped after 5,000 steps/.test(errorMessage(r)) },
    { cmd: 'python -c "print(1)" | python -c "print(int(input()) + 1)"', expect: r => r.success && r.output === '2' },
    { cmd: 'python', expect: r => !r.success && /nothing to run/.test(errorMessage(r)) },
    // No pipe means no stdin: JS null must reach Python as None, not as Pyodide's jsnull (D-011).
    { cmd: 'cat', expect: r => r.success && (r.output || '') === '' },
    { cmd: 'wc', expect: r => r.success && (r.output || '') === '' }, // crashed on JsNull before the fix
    // find used to join its results with a literal backslash-n (one long line).
    { cmd: 'find /home -name "*.txt"', expect: r => r.success && (r.output || '').split('\n').length >= 2 && !/\\n/.test(r.output) },
];

function errorMessage(r) {
    if (!r || !r.error) return '';
    return typeof r.error === 'string' ? r.error : (r.error.message || '');
}

(async () => {
    const launchOptions = process.env.CHROME ? { executablePath: process.env.CHROME } : {};
    const browser = await chromium.launch(launchOptions);
    const page = await browser.newPage(); // fresh context: no real profile is touched
    const logs = [];
    page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`));
    page.on('console', m => { if (['error', 'warning'].includes(m.type())) logs.push(`[${m.type()}] ${m.text()}`); });
    page.on('requestfailed', r => logs.push(`[reqfail] ${r.url()} ${r.failure() && r.failure().errorText}`));
    page.on('response', r => { if (r.status() >= 400) logs.push(`[http ${r.status()}] ${r.url()}`); });

    let passed = 0, failed = 0;
    const report = (name, ok, detail) => {
        if (ok) passed++; else failed++;
        console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok || !detail ? '' : `\n     ${detail}`}`);
    };

    try {
        await page.goto(url);
        try {
            await page.waitForFunction(
                () => typeof OopisOS_Kernel !== 'undefined' && OopisOS_Kernel.isReady === true,
                null, { timeout: BOOT_TIMEOUT_MS });
            report('kernel boots', true);
        } catch (e) {
            report('kernel boots', false, `not ready after ${BOOT_TIMEOUT_MS / 1000}s`);
            throw e;
        }

        // 1. Runtime and the vendored wheels agree (D-004, D-007).
        const runtime = await page.evaluate(async () => {
            const py = OopisOS_Kernel.pyodide;
            return await py.runPythonAsync(`
import sys, ssl, hashlib, zipfile, zlib, json
import cryptography, pyodide
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
k = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'salt', iterations=1000).derive(b'pw')
json.dumps({"python": sys.version.split()[0], "pyodide": pyodide.__version__,
            "cryptography": cryptography.__version__, "pbkdf2": k.hex()[:16],
            "sha1": hashlib.sha1(b'x').hexdigest()[:8]})
`);
        });
        const rt = JSON.parse(runtime);
        console.log(`     python ${rt.python}, pyodide ${rt.pyodide}, cryptography ${rt.cryptography}`);
        report('cryptography PBKDF2 derives a key', rt.pbkdf2 === '0a38253555ce37f5', `got ${rt.pbkdf2}`);
        report('hashlib sha1 works without the OpenSSL wheel', rt.sha1 === '11f6ad8e', `got ${rt.sha1}`);
        report('loaded packages are exactly the cryptography chain', await page.evaluate(() => {
            const names = Object.keys(OopisOS_Kernel.pyodide.loadedPackages).sort().join(',');
            return names === 'cffi,cryptography,pycparser,six';
        }));

        // 2. Accounts through the syscall bridge.
        const setup = JSON.parse(await page.evaluate(() =>
            OopisOS_Kernel.syscall('users', 'first_time_setup', ['gordon', 'hunter2', 'rootpw'])));
        report('first_time_setup creates root, Guest and the user', setup.success === true
            && setup.data && setup.data.users && ['root', 'Guest', 'gordon'].every(u => u in setup.data.users),
            JSON.stringify(setup).slice(0, 200));
        const okPw = JSON.parse(await page.evaluate(() => OopisOS_Kernel.syscall('users', 'verify_password', ['gordon', 'hunter2'])));
        const badPw = JSON.parse(await page.evaluate(() => OopisOS_Kernel.syscall('users', 'verify_password', ['gordon', 'wrong'])));
        report('verify_password accepts the right password', okPw.success && okPw.data === true, JSON.stringify(okPw));
        report('verify_password rejects the wrong password', badPw.success && badPw.data === false, JSON.stringify(badPw));

        // 2b. The agent and python (P2-03, D-013), with the LLM replaced by a fake that returns a fixed plan.
        const agent = JSON.parse(await page.evaluate(async () => {
            const py = OopisOS_Kernel.pyodide;
            return await py.runPythonAsync(`
import json, kernel
from bone_driver import BoneDriver
am = kernel.ai_manager
results = {}
prompt = BoneDriver.get_system_prompt({"name": "gordon"})
results["persona_mentions_python"] = "python script.py" in prompt and "DOES NOT RUN PYTHON" not in prompt
results["python_whitelisted"] = "python" in am.COMMAND_WHITELIST
results["python_dangerous"] = "python" in am.DANGEROUS_COMMANDS
results["refuse_steps"] = am.agent_refusal('python --steps 0 -c "while True: pass"')
results["refuse_steps_eq"] = am.agent_refusal('python --steps=0 -c "pass"')
results["allow_plain"] = am.agent_refusal('python -c "print(1)"')

async def fake_llm(provider, model, conversation, api_key, system_prompt=None):
    text = conversation[-1]["parts"][0]["text"]
    if "USER REQUEST:" in text:            # autopilot plan
        return {"success": True, "answer": fake_llm.plan}
    if "Original user question" in text:   # synthesizer
        return {"success": True, "answer": "SYNTH:" + text.split("Context from file system:")[1].strip()[:80]}
    return {"success": True, "answer": fake_llm.plan}   # planner
am._call_llm_api = fake_llm

fake_llm.plan = '1. python -c "print(6 * 7)"'
r = await am.perform_autopilot("six times seven", [], "ollama", None, {"apiKey": None})
results["autopilot_python"] = r.get("success") and "42" in r.get("data", "")
fake_llm.plan = '1. python --steps 0 -c "print(1)"'
r = await am.perform_autopilot("x", [], "ollama", None, {"apiKey": None})
results["autopilot_refuses_steps"] = r.get("success") and "Refused: the agent may not change python" in r.get("data", "") and "\\n1\\n" not in r.get("data", "")
fake_llm.plan = '1. python -c "print(6 * 7)"'
r = await am.perform_agentic_search("six times seven", [], "ollama", None, {"apiKey": None})
results["agent_asks_first"] = r.get("effect") == "confirm_ai_command" and r.get("command") == 'python -c "print(6 * 7)"'
fake_llm.plan = '1. python --steps 0 -c "print(1)"'
r = await am.perform_agentic_search("x", [], "ollama", None, {"apiKey": None})
results["agent_halts_steps"] = r.get("success") is False and "step budget" in r.get("error", "")
fake_llm.plan = '1. echo probe'
r = await am.perform_agentic_search("x", [], "ollama", None, {"apiKey": None})
results["agent_readonly_ok"] = r.get("success") and "probe" in r.get("data", "")
# D-014: the context probe must not reset the cwd to "/", and a confirm effect must pass through gemini.py.
saved_path = am.fs_manager.current_path
am.fs_manager.current_path = "/etc"
ctx = await am._get_terminal_context()
results["context_keeps_cwd"] = "Current Directory:\\n/etc" in ctx and am.fs_manager.current_path == "/etc"
am.fs_manager.current_path = saved_path
import commands.gemini as gemini_cmd
fake_llm.plan = '1. python -c "print(6 * 7)"'
r = await gemini_cmd.run(["x"], {"provider": "ollama"}, {"name": "gordon", "group": "gordon"}, ai_manager=am)
results["gemini_passes_confirm_effect"] = r.get("effect") == "confirm_ai_command"
json.dumps(results)
`);
        }));
        report('autopilot persona knows about python', agent.persona_mentions_python === true);
        report('python is whitelisted for the agent', agent.python_whitelisted === true);
        report('python counts as dangerous (agent asks first)', agent.python_dangerous === true);
        report('agent_refusal blocks --steps and --steps=', !!agent.refuse_steps && !!agent.refuse_steps_eq && agent.allow_plain === null,
            JSON.stringify([agent.refuse_steps, agent.refuse_steps_eq, agent.allow_plain]));
        report('autopilot runs a python plan line', agent.autopilot_python === true);
        report('autopilot refuses a python --steps line', agent.autopilot_refuses_steps === true);
        report('agent mode asks before running python', agent.agent_asks_first === true);
        report('agent mode halts on python --steps', agent.agent_halts_steps === true);
        report('agent mode still runs a read-only plan', agent.agent_readonly_ok === true);
        report('agent context probe keeps the shell cwd (D-014)', agent.context_keeps_cwd === true);
        report('gemini passes the confirm effect through (D-014)', agent.gemini_passes_confirm_effect === true);

        // 3. Shell commands through the executor.
        for (const { cmd, expect } of CHECKS) {
            const r = await page.evaluate(async c => await CommandExecutor.processSingleCommand(c, { isInteractive: false }), cmd);
            let ok = false;
            try { ok = !!expect(r); } catch (_) { ok = false; }
            report(`command: ${cmd}`, ok, JSON.stringify(r).slice(0, 300));
        }
    } catch (e) {
        console.error(`aborted: ${e.message}`);
        failed++;
    } finally {
        const noise = logs.filter(l => !l.includes('AudioContext') && !l.includes('Python Execution Error'));
        if (noise.length) console.log('--- page console ---\n' + noise.join('\n'));
        await browser.close();
    }

    const total = passed + failed;
    console.log(failed ? `FAIL ${failed} of ${total}` : `PASS ${passed}/${total}`);
    process.exit(failed ? 1 : 0);
})();
