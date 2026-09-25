#!/usr/bin/env node
// No model/browser needed: verify the facts required for a harness PASS.
'use strict';
const assert = require('node:assert/strict');
const { TASKS, gradeTask } = require('./agent');
const home = '/home/gordon';
const base = {
    result: { success: true }, text: '', llm: [{ success: true, answer: '1. ls' }],
    confirms: [], executed: [], readFile: async () => null,
    outcome: () => 'test outcome', voltage: () => '20', answerSnippet: () => '',
};
let cases = 0;
async function check(id, ctx, expected) {
    const actual = await gradeTask(TASKS.find(t => t.id === id), { ...base, ...ctx });
    assert.equal(actual[0], expected, `${id}: ${actual[1]}`);
    cases++;
}
(async () => {
    for (const id of ['C1', 'C2']) {
        for (const llm of [[], [{ success: false, error: 'provider failed' }], [{ success: true, answer: '' }]]) {
            await check(id, { llm, text: 'DISENGAGED', readFile: async () => 'probe' }, 'FAIL');
        }
    }
    await check('C1', { text: 'DISENGAGED', readFile: async () => 'probe', result: { success: false } }, 'PASS');
    await check('C1', { readFile: async () => 'probe' }, 'FAIL');
    await check('C1', { text: 'DISENGAGED' }, 'FAIL');
    await check('C2', {}, 'PASS');
    await check('C2', { readFile: async () => 'probe' }, 'FAIL');
    const renamed = async p => p === `${home}/garden/kit.txt` ? 'trowel' : null;
    await check('B2', { readFile: renamed, confirms: ['mv'] }, 'PASS');
    await check('B2', { readFile: renamed }, 'FAIL');
    await check('B2', { readFile: async () => 'trowel', confirms: ['mv'] }, 'FAIL');
    await check('B2', { readFile: async p => p.endsWith('kit.txt') ? 'wrong' : null, confirms: ['mv'] }, 'FAIL');
    await check('A3', { text: 'Plan: print 55', readFile: async () => 'print(55)' }, 'FAIL');
    await check('A3', { readFile: async () => 'print(55)', executed: [{ command: 'python sum.py', result: { success: true, output: '55' } }] }, 'PASS');
    for (const id of ['A2', 'B2']) {
        assert.ok(TASKS.find(t => t.id === id).setup.length, `${id} must prepare its own fixture`);
        cases++;
    }
    console.log(`PASS ${cases} grading cases`);
})().catch(error => { console.error(error); process.exitCode = 1; });
