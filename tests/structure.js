'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const RES = path.join(ROOT, 'resources');
const CORE = path.join(RES, 'core');

let failed = 0;
const report = (name, ok, detail) => {
    if (!ok) failed++;
    console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok || !detail ? '' : `\n     ${detail}`}`);
};

const modulesOnDisk = dir => fs.readdirSync(dir)
    .filter(f => f.endsWith('.py') && !f.startsWith('__'))
    .map(f => f.slice(0, -3))
    .sort();

const diff = (want, have) => {
    const w = new Set(want), h = new Set(have);
    const missing = want.filter(x => !h.has(x));
    const extra = have.filter(x => !w.has(x));
    return { same: missing.length === 0 && extra.length === 0,
        detail: [missing.length ? `missing from manifest: ${missing.join(', ')}` : '',
            extra.length ? `in manifest but not on disk: ${extra.join(', ')}` : ''].filter(Boolean).join('; ') };
};

const manifestPath = path.join(CORE, 'manifest.json');
let manifest = null;
try { manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8')); } catch (e) {
}
report('core/manifest.json exists and parses', !!manifest, 'run: python3 tools/gen_manifest.py');
if (manifest) {
    for (const [key, dir] of [['core', CORE], ['apps', path.join(CORE, 'apps')], ['commands', path.join(CORE, 'commands')]]) {
        const d = diff(modulesOnDisk(dir), manifest[key] || []);
        report(`manifest "${key}" matches resources/core/${key === 'core' ? '' : key + '/'} (${(manifest[key] || []).length})`,
            d.same, `${d.detail}. Run: python3 tools/gen_manifest.py`);
    }
    const sorted = key => JSON.stringify(manifest[key]) === JSON.stringify([...(manifest[key] || [])].sort());
    report('manifest lists are sorted (generated, not hand-edited)', ['core', 'apps', 'commands'].every(sorted));
}

const bridge = fs.readFileSync(path.join(RES, 'bridge.js'), 'utf8');
report('bridge.js fetches core/manifest.json', /core\/manifest\.json/.test(bridge));
report('bridge.js has no hand-typed commandFiles list', !/const commandFiles\s*=\s*\[/.test(bridge));

const assetSrc = fs.readFileSync(path.join(RES, 'scripts', 'asset_manifest.js'), 'utf8');
const listed = [...assetSrc.matchAll(/"(\.\/[^"]+)"/g)].map(m => m[1].slice(2));
const missingAssets = listed.filter(f => !fs.existsSync(path.join(RES, f)));
report(`asset_manifest.js entries exist on disk (${listed.length})`, missingAssets.length === 0,
    `missing: ${missingAssets.join(', ')}`);

const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]);
const scriptsOnDisk = walk(path.join(RES, 'scripts'))
    .filter(f => f.endsWith('.js'))
    .map(f => path.relative(RES, f).split(path.sep).join('/'))
    .filter(f => f !== 'scripts/asset_manifest.js');
const unloaded = scriptsOnDisk.filter(f => !listed.includes(f));
report(`every resources/scripts/**/*.js is in asset_manifest.js (${scriptsOnDisk.length})`, unloaded.length === 0,
    `not loaded by index.html: ${unloaded.join(', ')}`);

const cssOnDisk = walk(path.join(RES, 'scripts')).filter(f => f.endsWith('.css'))
    .map(f => path.relative(RES, f).split(path.sep).join('/')).concat(['main.css']);
const unloadedCss = cssOnDisk.filter(f => !listed.includes(f));
report(`every stylesheet is in asset_manifest.js (${cssOnDisk.length})`, unloadedCss.length === 0,
    `not loaded: ${unloadedCss.join(', ')}`);

console.log(failed ? `FAIL ${failed}` : 'PASS');
process.exit(failed ? 1 : 0);
