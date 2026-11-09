'use strict';
// Runs every feature unit suite (tests/*_test.py, tests/*_unit.js) and grades each one by its exit code alone.
// No browser, no server, no model; seconds. P7-17: tests/window_manager_unit.js failed for a month because
// nothing ran it, and a shell loop that read exit codes inside a command substitution reported it as passing.
//
//     node tests/units.js            # all of them
//     node tests/units.js window     # only files whose name contains "window"

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const TESTS = __dirname;
const filter = process.argv[2] || '';
const suites = fs.readdirSync(TESTS)
    .filter(f => /_test\.py$|_unit\.js$/.test(f) && f.includes(filter))
    .sort();

let failed = 0;
for (const file of suites) {
    const [cmd, args] = file.endsWith('.py') ? ['python3', ['-B', file]] : [process.execPath, [file]];
    const started = Date.now();
    const run = spawnSync(cmd, args, { cwd: TESTS, encoding: 'utf8', timeout: 120000 });
    const seconds = ((Date.now() - started) / 1000).toFixed(1);
    const ok = run.status === 0 && !run.error;
    if (!ok) failed++;
    console.log(`${ok ? 'ok  ' : 'FAIL'} ${file} (${seconds} s)`);
    if (!ok) {
        const out = `${run.stdout || ''}${run.stderr || ''}${run.error ? run.error.message : ''}`.trim().split('\n');
        // The error line first (a stack trace's tail says little), then the end of the output.
        const errors = out.filter(l => /Error|^FAIL|^not ok|Traceback/.test(l)).slice(0, 3);
        console.log(`     exit ${run.status}${run.signal ? `, signal ${run.signal}` : ''}`);
        [...errors, '...', ...out.slice(-4)].forEach(line => console.log(`     ${line}`));
    }
}

if (!suites.length) {
    console.log(`FAIL no suite matches "${filter}"`);
    process.exit(1);
}
console.log(failed ? `FAIL ${failed} of ${suites.length}` : `PASS ${suites.length}/${suites.length}`);
process.exit(failed ? 1 : 0);
