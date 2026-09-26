'use strict';

const { chromium } = require('playwright');

const url = process.argv[2] || 'http://127.0.0.1:8000/index.html';
const BOOT_TIMEOUT_MS = 120000;

const CHECKS = [
    { cmd: 'echo hello', expect: r => r.success && r.output === 'hello' },
    { cmd: 'date', expect: r => r.success && /\d{4}/.test(r.output || '') },
    { cmd: 'whoami', expect: r => r.success && r.output === 'Guest' },
    { cmd: 'ls -la /home', expect: r => r.success && ['gordon', 'Guest', 'root'].every(n => (r.output || '').includes(n)) },
    { cmd: 'help | head -3', expect: r => r.success && (r.output || '').startsWith('FractalOS - Powered by Python') },
    { cmd: 'mkdir /home/t', expect: r => !r.success && /Permission denied/.test(errorMessage(r)) },
    { cmd: 'cat /nonexistent', expect: r => !r.success && /No such file/.test(errorMessage(r)) },
    { cmd: 'python -c "print(2 ** 10)"', expect: r => r.success && r.output === '1024' },
    { cmd: 'python -c "import sys; print(sys.argv[1:])" one two', expect: r => r.success && r.output === "['one', 'two']" },
    { cmd: 'echo 21 | python -c "print(int(input()) * 2)"', expect: r => r.success && r.output === '42' },
    { cmd: 'echo hello > /home/Guest/hello.txt', expect: r => r.success },
    { cmd: 'echo "print(open(\'/home/Guest/hello.txt\').read().upper())" > /home/Guest/shout.py', expect: r => r.success },
    { cmd: 'python /home/Guest/shout.py', expect: r => r.success && r.output === 'HELLO' },
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
    { cmd: String.raw`forge /home/Guest/nested.py 'print("first\\nsecond")\nprint("done")'`, expect: r => r.success },
    { cmd: 'python /home/Guest/nested.py', expect: r => r.success && r.output === 'first\nsecond\ndone' },
    { cmd: String.raw`forge --literal /home/Guest/literal.txt 'keep \n café'`, expect: r => r.success },
    { cmd: 'cat /home/Guest/literal.txt', expect: r => r.success && r.output === String.raw`keep \n café` },
    { cmd: 'cat', expect: r => r.success && (r.output || '') === '' },
    { cmd: 'wc', expect: r => r.success && (r.output || '') === '' },
    { cmd: 'find /home -name "*.txt"', expect: r => r.success && (r.output || '').split('\n').length >= 2 && !/\\n/.test(r.output) },
];

function errorMessage(r) {
    if (!r || !r.error) return '';
    return typeof r.error === 'string' ? r.error : (r.error.message || '');
}

(async () => {
    const launchOptions = process.env.CHROME ? { executablePath: process.env.CHROME } : {};
    const browser = await chromium.launch(launchOptions);
    const page = await browser.newPage();
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
                () => typeof FractalOS_Kernel !== 'undefined' && FractalOS_Kernel.isReady === true,
                null, { timeout: BOOT_TIMEOUT_MS });
            report('kernel boots', true);
        } catch (e) {
            report('kernel boots', false, `not ready after ${BOOT_TIMEOUT_MS / 1000}s`);
            throw e;
        }

        const runtime = await page.evaluate(async () => {
            const py = FractalOS_Kernel.pyodide;
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
            const names = Object.keys(FractalOS_Kernel.pyodide.loadedPackages).sort().join(',');
            return names === 'cffi,cryptography,pycparser,six';
        }));

        const setup = JSON.parse(await page.evaluate(() =>
            FractalOS_Kernel.syscall('users', 'first_time_setup', ['gordon', 'hunter2', 'rootpw'])));
        report('first_time_setup creates root, Guest and the user', setup.success === true
            && setup.data && setup.data.users && ['root', 'Guest', 'gordon'].every(u => u in setup.data.users),
            JSON.stringify(setup).slice(0, 200));
        const okPw = JSON.parse(await page.evaluate(() => FractalOS_Kernel.syscall('users', 'verify_password', ['gordon', 'hunter2'])));
        const badPw = JSON.parse(await page.evaluate(() => FractalOS_Kernel.syscall('users', 'verify_password', ['gordon', 'wrong'])));
        report('verify_password accepts the right password', okPw.success && okPw.data === true, JSON.stringify(okPw));
        report('verify_password rejects the wrong password', badPw.success && badPw.data === false, JSON.stringify(badPw));

        const wire = JSON.parse(await page.evaluate(async () => FractalOS_Kernel.pyodide.runPythonAsync(`
import json, kernel, ai_manager
saved_fetch = ai_manager.pyodide_http.pyfetch
bodies = []
class Reply:
    status = 200
    async def json(self):
        return Reply.data
async def fake_fetch(url, **kwargs):
    bodies.append(json.loads(kwargs["body"]))
    return Reply()
ai_manager.pyodide_http.pyfetch = fake_fetch
results = {}
try:
    for value in ["", "   ", None, "hello"]:
        Reply.data = {"response": value, "done_reason": "length"}
        r = await kernel.ai_manager._call_llm_api("ollama", "test", [], None)
        results[str(value)] = r
    results["thinking_disabled"] = all(b.get("think") is False for b in bodies)
finally:
    ai_manager.pyodide_http.pyfetch = saved_fetch
json.dumps(results)
`)));
        report('Ollama requests disable thinking', wire.thinking_disabled === true);
        report('Ollama empty replies report done_reason', ['', '   ', 'None'].every(k =>
            wire[k].success === false && wire[k].error.includes('done_reason: length')));
        report('Ollama nonempty replies survive the adapter', wire.hello.success === true && wire.hello.answer === 'hello');

        // P2-06: a real timeout on model calls, and errors that name the provider and say what to do.
        // The hang, refusal and HTTP errors go through the real pyfetch with a fake JS fetcher, so the
        // AbortSignal plumbing is exercised, not just our except branch.
        const net = JSON.parse(await page.evaluate(async () => FractalOS_Kernel.pyodide.runPythonAsync(`
import json, time, kernel, ai_manager
from pyodide.code import run_js
am = kernel.ai_manager
real_fetch = ai_manager.pyodide_http.pyfetch
hang = run_js("(req, init) => new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(init.signal.reason)))")
refuse = run_js("(req, init) => Promise.reject(new TypeError('Failed to fetch'))")
def respond(status, body):
    return run_js(f"(req, init) => Promise.resolve(new Response({json.dumps(body)}, {{status: {status}}}))")
def use(fetcher):
    async def fetch(url, **kw):
        return await real_fetch(url, fetcher=fetcher, **kw)
    ai_manager.pyodide_http.pyfetch = fetch
out = {}
saved_timeout = am._request_timeout
try:
    am._request_timeout = lambda: 0.3
    use(hang)
    t0 = time.time()
    r = await am._call_llm_api("ollama", "m", [], None)
    out["timeout"] = {"error": r.get("error", ""), "seconds": round(time.time() - t0, 2)}
    am._request_timeout = saved_timeout
    use(refuse)
    out["refused"] = (await am._call_llm_api("ollama", "m", [], None)).get("error", "")
    use(respond(404, json.dumps({"error": 'model "nope:1b" not found, try pulling it first'})))
    out["missing_model"] = (await am._call_llm_api("ollama", "nope:1b", [], None)).get("error", "")
    use(respond(429, json.dumps({"error": {"message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}})))
    out["rate_limited"] = (await am._call_llm_api("gemini", None, [], "k")).get("error", "")
    use(respond(200, json.dumps({"response": "fine"})))
    out["ok_through_signal"] = await am._call_llm_api("ollama", "m", [], None)
finally:
    am._request_timeout = saved_timeout
    ai_manager.pyodide_http.pyfetch = real_fetch
saved_get = am.fs_manager.get_node
def conf(content):
    am.fs_manager.get_node = lambda path, *a, **k: {"type": "file", "content": content} if path == "/etc/ai.conf" else saved_get(path, *a, **k)
try:
    out["timeout_default"] = am._request_timeout()
    conf('{"timeout_seconds": 5}'); out["timeout_conf"] = am._request_timeout()
    bad = []
    for c in ['{"timeout_seconds": -1}', '{"timeout_seconds": "9"}', '{"timeout_seconds": true}', 'not json']:
        conf(c); bad.append(am._request_timeout())
    out["timeout_bad"] = bad
finally:
    am.fs_manager.get_node = saved_get
json.dumps(out)
`)));
        report('LLM calls time out instead of hanging (P2-06)', net.timeout.error.includes("didn't answer within 0.3 seconds") && net.timeout.seconds < 5,
            JSON.stringify(net.timeout));
        report('an unreachable provider is named with a hint (P2-06)', net.refused.includes("Can't reach Ollama at http://localhost:11434") && net.refused.includes('ollama serve'), net.refused);
        report('a missing Ollama model says how to pull it (P2-06)', net.missing_model.includes('ollama pull nope:1b'), net.missing_model);
        report('HTTP 429 names the provider (P2-06)', net.rate_limited.startsWith('Gemini says') && net.rate_limited.includes('Resource exhausted'), net.rate_limited);
        report('a normal reply still arrives through the timeout signal', net.ok_through_signal.success === true && net.ok_through_signal.answer === 'fine',
            JSON.stringify(net.ok_through_signal));
        report('timeout_seconds in /etc/ai.conf is honoured, bad values ignored', net.timeout_default === 120 && net.timeout_conf === 5
            && net.timeout_bad.every(v => v === 120), JSON.stringify([net.timeout_default, net.timeout_conf, net.timeout_bad]));

        const agent = JSON.parse(await page.evaluate(async () => {
            const py = FractalOS_Kernel.pyodide;
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
results["autopilot_refuses_steps"] = r.get("success") is False and "the agent may not change python" in r.get("error", "")
fake_llm.plan = '1. python -c "print(6 * 7)"'
r = await am.perform_agentic_search("six times seven", [], "ollama", None, {"apiKey": None})
results["agent_asks_first"] = r.get("effect") == "confirm_ai_command" and r.get("command") == 'python -c "print(6 * 7)"'
fake_llm.plan = '1. python --steps 0 -c "print(1)"'
r = await am.perform_agentic_search("x", [], "ollama", None, {"apiKey": None})
results["agent_halts_steps"] = r.get("success") is False and "step budget" in r.get("error", "")
fake_llm.plan = '1. echo probe'
r = await am.perform_agentic_search("x", [], "ollama", None, {"apiKey": None})
results["agent_readonly_ok"] = r.get("success") and "probe" in r.get("data", "")
# D-014: the context probe must not reset the cwd to "/", and a confirm effect must pass through samwise.py.
saved_path = am.fs_manager.current_path
am.fs_manager.current_path = "/etc"
ctx = await am._get_terminal_context()
results["context_keeps_cwd"] = "Current Directory:\\n/etc" in ctx and am.fs_manager.current_path == "/etc"
am.fs_manager.current_path = saved_path
import commands.samwise as samwise_cmd
fake_llm.plan = '1. python -c "print(6 * 7)"'
r = await samwise_cmd.run(["x"], {"provider": "ollama"}, {"name": "gordon", "group": "gordon"}, ai_manager=am)
results["samwise_passes_confirm_effect"] = r.get("effect") == "confirm_ai_command"
# P2-02: verify the stored pre-write contents, not just a checkpoint message.
user = am.command_executor.user_context
home = f"/home/{user['name']}"
probe = f"{home}/checkpoint_probe.txt"
am.fs_manager.write_file(probe, "before", user)
fake_llm.plan = f'1. forge {probe} "after"'
r = await am.perform_autopilot("overwrite probe", [], "ollama", None, {"apiKey": None})
from story_manager import story_manager
chapter = story_manager.read_log(f"{home}/.story")["data"][0]["snapshot"]
stored = am.fs_manager.get_node(f"{home}/.story/snapshots/{chapter}/checkpoint_probe.txt")
results["checkpoint_before_write"] = r.get("success") and stored["content"] == "before" and am.fs_manager.get_node(probe)["content"] == "after"
# P2-16: --dry-run plans and reports, and runs nothing, in agent mode and in autopilot (even with --force).
def story_count():
    log = story_manager.read_log(f"{home}/.story")
    return len(log.get("data") or []) if log.get("success") else 0
am.fs_manager.write_file(f"{home}/dry_keep.txt", "keep", user)
chapters_before = story_count()
fake_llm.plan = f"1. mkdir {home}/dry_made\\n2. mv {home}/dry_keep.txt {home}/dry_moved.txt"
r = await samwise_cmd.run(["x"], {"provider": "ollama", "dry-run": True}, user, ai_manager=am)
results["dry_agent_reports"] = r.get("effect") == "display_prose" and "asks you first" in r.get("content", "") and "Nothing was executed" in r.get("content", "")
fake_llm.plan = f"1. rm -r {home}/dry_keep.txt"
r2 = await samwise_cmd.run(["x"], {"provider": "ollama", "dry-run": True, "autopilot": True, "force": True}, user, ai_manager=am)
results["dry_autopilot_reports"] = r2.get("effect") == "display_prose" and "Voltage" in r2.get("content", "") and "Nothing was executed" in r2.get("content", "")
results["dry_run_changes_nothing"] = (am.fs_manager.get_node(f"{home}/dry_made") is None
    and am.fs_manager.get_node(f"{home}/dry_moved.txt") is None
    and am.fs_manager.get_node(f"{home}/dry_keep.txt") is not None
    and story_count() == chapters_before)
fake_llm.plan = "1. ls | wc"
r3 = await samwise_cmd.run(["x"], {"provider": "ollama", "dry-run": True}, user, ai_manager=am)
results["dry_reports_refusal"] = "Would halt" in r3.get("content", "")
# P2-17: a rejected plan goes back to the model with the reason, and the corrected plan runs.
replies = ["1. ls | wc", "1. echo retried-ok", "1. ls | wc", "1. echo retried-ok"]
async def seq_llm(provider, model, conversation, api_key, system_prompt=None):
    return {"success": True, "answer": replies.pop(0)}
am._call_llm_api = seq_llm
r = await am.perform_autopilot("x", [], "ollama", None, {"apiKey": None})
r4 = await samwise_cmd.run(["x"], {"provider": "ollama", "dry-run": True, "autopilot": True}, user, ai_manager=am)
results["retry_runs_corrected_plan"] = r.get("success") and "retried-ok" in r.get("data", "")
results["retry_shown_in_dry_run"] = "rejected 1 earlier plan" in r4.get("content", "")
am._call_llm_api = fake_llm

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
        report('samwise passes the confirm effect through (D-014)', agent.samwise_passes_confirm_effect === true);
        report('autopilot stores a real checkpoint before writing', agent.checkpoint_before_write === true);
        report('samwise --dry-run shows the plan and who would be asked (P2-16)', agent.dry_agent_reports === true);
        report('samwise --autopilot --force --dry-run shows voltage (P2-16)', agent.dry_autopilot_reports === true);
        report('--dry-run creates, moves, deletes and checkpoints nothing (P2-16)', agent.dry_run_changes_nothing === true);
        report('--dry-run reports a plan that would halt (P2-16)', agent.dry_reports_refusal === true);
        report('a rejected plan is retried and the corrected one runs (P2-17)', agent.retry_runs_corrected_plan === true);
        report('--dry-run shows the rejected attempts (P2-17)', agent.retry_shown_in_dry_run === true);

        for (const { cmd, expect } of CHECKS) {
            const r = await page.evaluate(async c => await CommandExecutor.processSingleCommand(c, { isInteractive: false }), cmd);
            let ok = false;
            try { ok = !!expect(r); } catch (_) { ok = false; }
            report(`command: ${cmd}`, ok, JSON.stringify(r).slice(0, 300));
        }

        // P2-20: Samwise Chat must hand the message to the model verbatim. It used to be spliced into a
        // double-quoted command line, so the shell ate quotes, expanded $VARS and ran $(...).
        await page.evaluate(async () => FractalOS_Kernel.pyodide.runPythonAsync(`
import kernel
chat_seen = []
async def _fake_chat(prompt, history, provider, model, api_key):
    chat_seen.append({"prompt": prompt, "history": len(history), "engine": f"{provider}/{model}"})
    return {"success": True, "answer": "ok"}
kernel.ai_manager.continue_chat_conversation = _fake_chat
`));
        const launched = await page.evaluate(async () => await CommandExecutor.processSingleCommand('samwise -c -p ollama -m stub', { isInteractive: false }));
        await page.waitForSelector('#samwise-chat-app-container', { timeout: 10000 });
        const chatMessages = ['she said "hi"', 'a lone " quote', 'cost $HOME and $(echo expanded) and `x`'];
        for (const msg of chatMessages) {
            const before = await page.$$eval('.samwise-chat-message.ai', els => els.length);
            await page.fill('.samwise-chat-input', msg);
            await page.press('.samwise-chat-input', 'Enter');
            await page.waitForFunction(n => document.querySelectorAll('.samwise-chat-message.ai').length > n, before, { timeout: 20000 });
        }
        const seen = JSON.parse(await page.evaluate(async () => FractalOS_Kernel.pyodide.runPythonAsync('import json; json.dumps(chat_seen)')));
        report('Samwise Chat opens with samwise -c', launched.success === true, JSON.stringify(launched));
        report('Samwise Chat passes messages verbatim (P2-20)', seen.length === chatMessages.length && seen.every((c, i) => c.prompt === chatMessages[i]),
            JSON.stringify(seen.map(c => c.prompt)));
        report('Samwise Chat keeps history and the chosen model', seen.every((c, i) => c.history === 2 * i && c.engine === 'ollama/stub'),
            JSON.stringify(seen.map(c => [c.history, c.engine])));
        const direct = await page.evaluate(async () => await CommandExecutor.processSingleCommand('samwise --chat-internal', { isInteractive: false }));
        report('samwise --chat-internal without a JSON message fails cleanly', direct.success === false, JSON.stringify(direct).slice(0, 200));
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
