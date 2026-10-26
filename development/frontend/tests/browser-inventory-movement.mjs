// Windows Edge/CDP integration. No Playwright or additional npm dependency.
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { createServer } from 'node:net';
import { once } from 'node:events';
import path from 'node:path';
import assert from 'node:assert/strict';
const origin = process.env.RACKCLICK_TEST_ORIGIN;
const username = process.env.RACKCLICK_TEST_USERNAME, password = process.env.RACKCLICK_TEST_PASSWORD;
if (!origin || !username || !password || !['127.0.0.1', 'localhost', '[::1]'].includes(new URL(origin).hostname)) throw Error('Explicit loopback laboratory origin and locally supplied test credentials required.');
const root = path.resolve('../..'), evidence = process.env.RACKCLICK_TEST_OUTPUT || path.join(root, 'evidence/s1-20260928/frontend');
const run = new Date().toISOString().replaceAll(/[:.]/g, '-');
const profile = path.join(root, '.local/browser-test', run);
await mkdir(profile, { recursive: true }); await mkdir(evidence, { recursive: true });
const portServer = createServer(); portServer.listen(0, '127.0.0.1'); await once(portServer, 'listening'); const port = portServer.address().port; await new Promise(r => portServer.close(r));
const edge = process.env.RACKCLICK_EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const child = spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + port, '--user-data-dir=' + profile, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const clients = [], checks = [], errors = [], responses = [];
let lastTab;
const delay = ms => new Promise(r => setTimeout(r, ms));
async function poll(fn, label, duration = 15000) { const end = Date.now() + duration; let last; do { try { const v = await fn(); if (v) return v; } catch (e) { last = e; } await delay(100); } while (Date.now() < end); throw Error('Timed out: ' + label + (last ? ': ' + last.message : '')); }
class CDP {
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
 static async open(url) { const ws = new WebSocket(url); await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); }); const c = new CDP(ws); clients.push(c); return c; }
 send(method, params = {}) { const id = ++this.sequence; return new Promise((resolve, reject) => { const timer = setTimeout(() => { this.pending.delete(id); reject(Error('CDP timeout: ' + method)); }, 15000); this.pending.set(id, { resolve, reject, timer }); this.ws.send(JSON.stringify({ id, method, params })); }); }
 async evaluate(expression) { const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error('Browser evaluation failed: ' + result.exceptionDetails.text); return result.result.value; }
 async wait(expression, label) { return poll(() => this.evaluate(expression), label); }
 async field(selector, value) { return this.evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});if(!el)throw Error('Field missing');const proto=el.tagName==='SELECT'?HTMLSelectElement.prototype:el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return true})()`); }
 async click(selector) { await this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
 async button(text) { await this.evaluate(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!button)throw Error('Button missing');button.click()})()`); }
}
let browser;
const ids=JSON.parse(process.env.RACKCLICK_FIXTURE);
const customerId=ids.customer;
function normalize(project) { const value=structuredClone(project); for(const key of ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']) value[key].sort((a,b)=>a.id.localeCompare(b.id)); return value; }
function changed(previous,patches) { const value=structuredClone(previous);value.revision++;for(const [id,patch] of Object.entries(patches))Object.assign(value.devices.find(x=>x.id===id),patch);return value; }
try {
 const info=await poll(async()=>(await fetch('http://127.0.0.1:'+port+'/json/version')).json(),'Edge endpoint');
 browser=await CDP.open(info.webSocketDebuggerUrl);
 async function session(user) {
  const context=await browser.send('Target.createBrowserContext');
  const target=await browser.send('Target.createTarget',{url:origin,browserContextId:context.browserContextId});
  const targetInfo=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(t=>t.id===target.targetId),'target');
  const tab=await CDP.open(targetInfo.webSocketDebuggerUrl);lastTab=tab;
  for(const domain of ['Runtime','Log','Network','Page'])await tab.send(domain+'.enable');
  await tab.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await tab.wait(`!!document.querySelector('input[name=username]')&&!document.querySelector('button[type=submit]').disabled`,'login form');
  await tab.field('select','es');await tab.field('input[name=username]',user);await tab.field('input[name=password]',password);
  await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'authenticated client');
  await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory loaded');
  return tab;
 }
 const snapshot=tab=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Snapshot status '+r.status);const value=await r.json();if(r.headers.get('etag')!=='"'+value.revision+'"')throw Error('Snapshot ETag mismatch');return value})()`);
 async function openRack(tab,id) {
  await tab.button('Gestionar infraestructura');await tab.wait(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`,'rack card');
  await tab.click(`[data-rack-id="${id}"] .rc-rack-open`);await tab.wait(`!!document.querySelector('#rack-detail-export')`,'rack view');
 }
 async function ready(tab,revision) {
  await tab.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')&&document.querySelector('.rc-inventory-toolbar [role=status]').textContent==='Guardado por el servidor'`,'server-confirmed save');
  await poll(async()=> (await snapshot(tab)).revision===revision,'revision persisted');
 }
 async function shot(tab,name) {await writeFile(path.join(evidence,name),Buffer.from((await tab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));}
 const first=await session(username),second=await session('move-second');
 let expected=await snapshot(first);assert.equal(expected.devices.length,3);assert.equal(expected.connections.length,1);assert.equal(expected.ports.length,6);assert.equal(expected.portGroups.length,3);
 assert.deepEqual(normalize(await snapshot(second)),normalize(expected));
 await openRack(first,ids.rackA);await openRack(second,ids.rackA);
 await first.wait(`!!document.querySelector('[data-wire="${ids.cable}"]')`,'local cable path');
 assert.equal(await first.evaluate(`document.querySelector('[data-wire="${ids.cable}"]').getAttribute('stroke-dasharray')`),null);
 const localCard=await first.evaluate(`document.querySelector('.rc-connections .ir-connection-card').textContent`);
 assert.equal(localCard.split('Rack origen').length-1,2);assert.ok(!localCard.includes('Rack destino'));
 checks.push('SQL fixture exact:2 racks,3 devices,3 groups,6 ports,1 cable; local cable drawn solid with both origin endpoints');
 // Open a real move draft at revision1. The other authorized user then commits a GUI reorder.
 await first.click(`[data-devid="${ids.a}"] button[title="Opciones del equipo"]`);
 await first.wait(`document.querySelector('dialog #operation-title')?.textContent==='Mover'`,'move dialog');
 await first.field('dialog select[name=rackId]',ids.rackB);
 await second.click(`[data-devid="${ids.a}"] button[title="Bajar"]`);
 expected=changed(expected,{[ids.a]:{sortOrder:1},[ids.b]:{sortOrder:0}});await ready(second,expected.revision);
 assert.deepEqual(normalize(await snapshot(second)),normalize(expected));
 await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!!document.querySelector('dialog [role=alert]')`,'real concurrent 412');
 assert.ok((await first.evaluate(`document.querySelector('dialog [role=alert]').textContent`)).includes('borrador'));
 assert.equal(await first.evaluate(`document.querySelector('dialog select[name=rackId]').value`),ids.rackB);
 assert.equal(await first.evaluate(`document.querySelector('dialog button[type=submit]').disabled`),true);
 assert.deepEqual(normalize(await snapshot(first)),normalize(expected));
 await shot(first,'move-conflict-draft-windows.png');
 checks.push('Distinct authorized user reordered using Bajar; stale move returned412, selected destination/draft retained, save disabled, entire server snapshot unchanged');
 await first.button('Cargar datos actuales');await first.wait(`!document.querySelector('dialog [role=alert]')&&!document.querySelector('dialog button[type=submit]').disabled`,'refresh stale revision');
 assert.equal(await first.evaluate(`document.querySelector('dialog select[name=rackId]').value`),ids.rackB);
 await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 expected=changed(expected,{[ids.a]:{rackId:ids.rackB,sortOrder:1}});await ready(first,expected.revision);
 assert.deepEqual(normalize(await snapshot(first)),normalize(expected));
 assert.equal(await first.evaluate(`!!document.querySelector('[data-devid="${ids.a}"]')`),false);
 await first.wait(`document.querySelector('[data-wire="${ids.cable}"]')?.getAttribute('stroke-dasharray')==='5 3'`,'cross-rack cable stub in origin');
 const crossCard=await first.evaluate(`document.querySelector('.rc-connections .ir-connection-card').textContent`);
 for(const text of ['Rack origen','Rack destino','Equipo móvil Ä','Equipo origen B','Cable literal <img> 東京'])assert.ok(crossCard.includes(text));
 checks.push('Opciones del equipo→Mover→Rack destino→Guardar after revision refresh: only mobile placement/order/revision changed; origin shows dashed cross-rack cable and literal endpoint labels');
 await openRack(first,ids.rackB);
 await first.wait(`document.querySelectorAll('[data-devid]').length===2&&document.querySelector('[data-wire="${ids.cable}"]')?.getAttribute('stroke-dasharray')==='5 3'`,'destination stub');
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('[data-devid]')].map(e=>e.dataset.devid)`),[ids.c,ids.a]);
 await first.click(`[data-devid="${ids.a}"] button[title="Subir"]`);
 expected=changed(expected,{[ids.a]:{sortOrder:0},[ids.c]:{sortOrder:1}});await ready(first,expected.revision);
 assert.deepEqual(normalize(await snapshot(first)),normalize(expected));
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('[data-devid]')].map(e=>e.dataset.devid)`),[ids.a,ids.c]);
 assert.equal(await first.evaluate(`document.querySelector('[data-devid="${ids.a}"] button[title="Subir"]').disabled`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-devid="${ids.c}"] button[title="Bajar"]').disabled`),true);
 for(const portId of [ids.pa,ids.pa2,ids.pc,ids.pc2])assert.ok(await first.evaluate(`!!document.querySelector('[data-vport="${portId}"]')`));
 await shot(first,'move-reorder-destination-windows.png');
 checks.push('Destination already contained C; Subir swaps only order, boundary arrows disabled, original port UUIDs and cross-rack cable retained');
 for(const tab of [first,second]) {
  await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'reload clients');await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'reloaded inventory');
  assert.deepEqual(normalize(await snapshot(tab)),normalize(expected));await openRack(tab,ids.rackB);
  assert.deepEqual(await tab.evaluate(`[...document.querySelectorAll('[data-devid]')].map(e=>e.dataset.devid)`),[ids.a,ids.c]);
  await tab.wait(`document.querySelector('[data-wire="${ids.cable}"]')?.getAttribute('stroke-dasharray')==='5 3'`,'reloaded cross cable');
 }
 assert.deepEqual((await second.evaluate(`Object.keys(localStorage)`)).sort(),['rackclick_server_language','rackclick_server_theme']);
 checks.push('Full reload in two different authorized users/cookie contexts preserves exact project, destination order and cross projection; localStorage only preferences');
 const allowedError=e=>/^\/api\/v1\/me: .*status of 401 |favicon\.ico/.test(e)||e.startsWith('/api/v1/customers/'+customerId+'/commands: ')&&e.includes('status of 412 (');
 const materialErrors=errors.filter(e=>!allowedError(e));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[{path:'/api/v1/customers/'+customerId+'/commands',status:412}]);
 await writeFile(path.join(evidence,'expected-project.json'),JSON.stringify(expected,null,2));
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,customerId,revision:expected.revision,checks,browserErrors:materialErrors,
  limits:['SQL-seeded inventory/accounts; does not test GUI creation.','Mouse/DOM buttons only: no drag, touch, Dosen, duplication or complete inventory parity.','Python harness separately checks real403/404 and server restart; no Windows reboot or real QA access.']};
 await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch(error) {
 let visibleText='';if(lastTab)try{visibleText=(await lastTab.evaluate(`document.body.innerText`)).replaceAll(password,'[redacted]').replaceAll(username,'[synthetic user]');await writeFile(path.join(evidence,'browser-failure.png'),Buffer.from((await lastTab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));}catch{}
 await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({status:'failed',checks,error:error.message,browserErrors:errors,responses,visibleText},null,2));throw error;
}finally{
 if(browser)try{await browser.send('Browser.close');}catch{}
 for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();
}
