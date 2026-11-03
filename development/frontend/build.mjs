import { build } from 'esbuild';
import { readFile, writeFile, mkdir, copyFile, rm, lstat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import {extendRc9ConnectorContract} from './src/connector-contract-l.mjs';
import {verifyHardwareCatalog,verifyCommercialHardwareCatalog,verifyArubaHardwareCatalog,verifyFortinetHardwareCatalog,verifySynologyHardwareCatalog,verifyDiskStationHardwareCatalog,verifyQnapHardwareCatalog,verifyBatch50HardwareCatalog,verifyBatch50BHardwareCatalog,verifyBatch100HardwareCatalog,verifyBatch100BHardwareCatalog,verifyBatch100CHardwareCatalog,verifySelected506AHardwareCatalog,verifySelected506BHardwareCatalog,verifySelected506CHardwareCatalog,verifySelected506DHardwareCatalog,verifySelected506EHardwareCatalog,verifySelected506FHardwareCatalog,verifySelected506GHardwareCatalog,verifySelected506HHardwareCatalog,verifySelected506IHardwareCatalog,verifySelected506JHardwareCatalog,verifySelected506KHardwareCatalog,verifySelected506LHardwareCatalog,verifyGermanCpeHardwareCatalog,verifyGermanRepeatersHardwareCatalog} from './verify-hardware-catalog.mjs';
// Check before touching generated/ or dist/. Python is only an authoring tool.
await verifyHardwareCatalog(path.resolve('../..'));
await verifyCommercialHardwareCatalog(path.resolve('../..'));
await verifyArubaHardwareCatalog(path.resolve('../..'));
await verifyFortinetHardwareCatalog(path.resolve('../..'));
await verifySynologyHardwareCatalog(path.resolve('../..'));
await verifyDiskStationHardwareCatalog(path.resolve('../..'));
await verifyQnapHardwareCatalog(path.resolve('../..'));
await verifyBatch50HardwareCatalog(path.resolve('../..'));
await verifyBatch50BHardwareCatalog(path.resolve('../..'));
await verifyBatch100HardwareCatalog(path.resolve('../..'));
await verifyBatch100BHardwareCatalog(path.resolve('../..'));
await verifyBatch100CHardwareCatalog(path.resolve('../..'));
await verifySelected506AHardwareCatalog(path.resolve('../..'));
await verifySelected506BHardwareCatalog(path.resolve('../..'));
await verifySelected506CHardwareCatalog(path.resolve('../..'));
await verifySelected506DHardwareCatalog(path.resolve('../..'));
await verifySelected506EHardwareCatalog(path.resolve('../..'));
await verifySelected506FHardwareCatalog(path.resolve('../..'));
await verifySelected506GHardwareCatalog(path.resolve('../..'));
await verifySelected506HHardwareCatalog(path.resolve('../..'));
await verifySelected506IHardwareCatalog(path.resolve('../..'));
await verifySelected506JHardwareCatalog(path.resolve('../..'));
await verifySelected506KHardwareCatalog(path.resolve('../..'));
await verifySelected506LHardwareCatalog(path.resolve('../..'));
await verifyGermanCpeHardwareCatalog(path.resolve('../..'));
await verifyGermanRepeatersHardwareCatalog(path.resolve('../..'));
// A normal/distributable build never adopts optional private manufacturer media.
try { await lstat('dist/hardware-media'); throw Error('private_hardware_media_present'); }
catch(error) { if(error.code!=='ENOENT')throw error; }
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
// Optional mounted-device row hook: legacy rows and all RC9 wire/face/interaction
// code remain intact. Only a bound hardware root delegates its own row rendering.
for (const [before,after] of [
 ['onFaces,onFace}){','onFaces,onFace,renderHardware}){'],
 ['const devices=rack.devs;','const devices=renderHardware?rack.devs.filter(d=>!d.mountParentId):rack.devs;'],
 ["window.addEventListener('resize',positions);return()=>{ro.disconnect();window.removeEventListener('resize',positions);", "window.addEventListener('resize',positions);const scrollRoot=root.current;if(renderHardware)scrollRoot?.addEventListener('scroll',positions,true);return()=>{ro.disconnect();window.removeEventListener('resize',positions);scrollRoot?.removeEventListener('scroll',positions,true);"],
 ["return <div className={'ir-device-row '","if(renderHardware&&d.hardwareProfileKey)return renderHardware(d,start);return <div className={'ir-device-row '"]
]) {
 if (physical.split(before).length !== 2) throw Error('RC9 mounted row hook anchor mismatch');
 physical=physical.replace(before,after);
}
const exports = ['IRIcon', 'IR_WORDS', 'PT', 'PS', 'PRESETS', 'CATS', 'IntegratedPhysicalRack', 'IntegratedInspector', 'irPortFace', 'irPortTooltip', 'irDeviceTooltip', 'IRPortShape'];
const catalogue = section('const PRESETS =', 'const RSZ');
const connectorContract=extendRc9ConnectorContract(section('const PT =','const ICONS ='),physical);
await writeFile('generated/rc9.jsx', section('const IR_WORDS=', 'const RC8_CATALOGUE=') + source.slice(start, end) + '\n' + connectorContract.metadataSource + catalogue + '\n' + connectorContract.physicalSource + '\n' + section('function IRPowerSummary(', 'function irPowerDemo(') + '\nexport {' + exports.join(',') + '};\n');
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
