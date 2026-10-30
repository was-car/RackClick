import { build } from 'esbuild';
import { readFile, writeFile, mkdir, copyFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
const reference = 'rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28';
const hash = b => createHash('sha256').update(b).digest('hex');
const manifest = (await readFile(reference + '/SHA256SUMS-PACKAGE.txt', 'utf8')).split(/\r?\n/);
async function adopted(file) {
 const data = await readFile(reference + '/' + file);
 const expected = manifest.find(line => line.slice(66).replace(/^\.\//, '') === file)?.slice(0,64);
 if (!expected || hash(data) !== expected) throw Error('RC9 integrity mismatch: ' + file);
 return data;
}
await mkdir('dist/assets/fonts', { recursive: true }); await mkdir('dist/vendor', { recursive: true }); await mkdir('generated', { recursive: true });
// A failed build must not leave an old entry page that looks like a fresh candidate.
await rm('dist/index.html', { force: true });
const source = (await adopted('evidence/integrated-source.jsx')).toString();
const start = source.indexOf('function IRIcon('), end = source.indexOf('\nfunction irLocationKey', start);
if (start < 0 || end <= start) throw Error('RC9 IRIcon integration anchor missing');
function section(from, to) { const first = source.indexOf(from), last = source.indexOf(to, first + from.length); if (first < 0 || last <= first) throw Error('RC9 component anchor missing: ' + from); return source.slice(first, last); }
let physical = section('function irPortFace(', '/* Visible SVG equivalents');
const endpointAnchor = 'function irEndpointText(c,side,project,rack){';
if (physical.split(endpointAnchor).length !== 2) throw Error('RC9 endpoint adaptation anchor mismatch');
physical = physical.replace(endpointAnchor, endpointAnchor + "if(project?.serverEndpoints?.[c[side+'p']])return project.serverEndpoints[c[side+'p']];");
const exports = ['IRIcon', 'IR_WORDS', 'PT', 'PS', 'PRESETS', 'CATS', 'IntegratedPhysicalRack', 'IntegratedInspector', 'irPortFace', 'irPortTooltip', 'irDeviceTooltip', 'IRPortShape'];
const catalogue = section('const PRESETS =', 'const RSZ');
await writeFile('generated/rc9.jsx', section('const IR_WORDS=', 'const RC8_CATALOGUE=') + source.slice(start, end) + '\n' + section('const PT =', 'const ICONS =') + catalogue + '\n' + physical + '\n' + section('function IRPowerSummary(', 'function irPowerDemo(') + '\nexport {' + exports.join(',') + '};\n');
let css = '';
for (const font of JSON.parse((await adopted('assets/fonts/manifest.json')).toString())) {
 const bytes = await adopted(font.file);
 if (hash(bytes) !== font.sha256) throw Error('RC9 font digest mismatch');
 const name = path.basename(font.file); await writeFile('dist/assets/fonts/' + name, bytes);
 css += `@font-face{font-family:'${font.family}';font-style:normal;font-weight:${font.weight};font-display:swap;src:url(assets/fonts/${name}) format('woff2');unicode-range:${font.range}}\n`;
}
css += (await adopted('src/integrated.css')).toString() + '\n' + await readFile('src/server.css', 'utf8') + '\n' + await readFile('src/mfa-login.css', 'utf8');
if (/@import|url\(\s*['"]?https?:/i.test(css)) throw Error('Runtime remote CSS forbidden');
await writeFile('dist/app.css', css);
for (const name of ['react.production.min.js', 'react-dom.production.min.js']) await writeFile('dist/vendor/' + name, await adopted('vendor/' + name));
const qrPin = JSON.parse(await readFile('src/vendor/qrcodegen.sources.json', 'utf8'));
if (hash(await readFile('src/vendor/qrcodegen.source.ts')) !== qrPin.upstreamSourceSha256 || hash(await readFile('src/vendor/qrcodegen.mjs')) !== qrPin.moduleSha256) throw Error('QR vendor integrity mismatch');
await build({ entryPoints: ['src/ServerApp.jsx'], bundle: true, outfile: 'dist/app.js', target: 'es2020', minify: false, legalComments: 'inline' });
await writeFile('dist/index.html', '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light"><title>RackClick Server</title><link rel="stylesheet" href="/app.css"><script defer src="/vendor/react.production.min.js"></script><script defer src="/vendor/react-dom.production.min.js"></script><script defer src="/app.js"></script></head><body><div id="root"></div></body></html>');
await mkdir('dist/licenses', { recursive: true });
for (const name of ['react-LICENSE.txt', 'react-dom-LICENSE.txt', 'ibm-plex-mono-LICENSE.txt', 'ibm-plex-sans-LICENSE.txt', 'space-grotesk-LICENSE.txt']) await copyFile(reference + '/licenses/' + name, 'dist/licenses/' + name);
console.log(JSON.stringify({ status: 'built', source: 'RC9 adopted integrated-source', api: '/api/v1', dependencies: { esbuild: '0.25.10' }, appSHA256: hash(await readFile('dist/app.js')), cssSHA256: hash(css), runtimeCDN: false }));
