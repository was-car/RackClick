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
try {
 const info = await poll(async () => (await fetch('http://127.0.0.1:' + port + '/json/version')).json(), 'Edge debugging endpoint');
 browser = await CDP.open(info.webSocketDebuggerUrl);
 async function session() {
  const context = await browser.send('Target.createBrowserContext');
  const target = await browser.send('Target.createTarget', { url: origin, browserContextId: context.browserContextId });
  const info = await poll(async () => (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.id === target.targetId), 'session target');
  const tab = await CDP.open(info.webSocketDebuggerUrl); lastTab = tab; await tab.send('Runtime.enable'); await tab.send('Log.enable'); await tab.send('Network.enable'); await tab.send('Page.enable'); await tab.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await tab.wait(`!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled`, 'login screen');
  await tab.field('select', 'es'); await tab.field('input[name=username]', username); await tab.field('input[name=password]', password); await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('.ir-nav')`, 'authenticated RC9 navigation'); return tab;
 }

 const first = await session(); await first.field('select', 'en');
 checks.push('Login GUI real y contexto de navegador aislado');
 async function button(tab, scope, text) {
  await tab.evaluate(`(()=>{const b=[...document.querySelector(${JSON.stringify(scope)}).querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!b||b.disabled)throw Error('Missing or disabled button');b.click()})()`);
 }
 async function form(tab, values) {
  await tab.wait(`!!document.querySelector('dialog[open]')`, 'operation dialog');
  for(const [key,value] of Object.entries(values)) await tab.field(`dialog [name="${key}"]`, value);
  await tab.evaluate(`document.querySelector('dialog form').requestSubmit()`);
  await tab.wait(`!document.querySelector('dialog[open]')`, 'confirmed form commit');
  await tab.wait(`!document.querySelector('.rc-inventory-toolbar button:disabled')`, 'inventory ready');
 }
 async function tap(tab, selector) {
  const p = await tab.evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center'});const b=e.getBoundingClientRect();return{x:b.x+b.width/2,y:b.y+b.height/2}})()`);
  await tab.send('Input.dispatchMouseEvent',{type:'mousePressed',...p,button:'left',clickCount:1});
  await tab.send('Input.dispatchMouseEvent',{type:'mouseReleased',...p,button:'left',clickCount:1});
 }
 const customerName = 'Inventory GUI '+run;
 await first.button('Create client'); await form(first,{name:customerName});
 const customerId=await first.evaluate(`[...document.querySelectorAll('.ir-client-card')].find(e=>e.querySelector('h2').textContent===${JSON.stringify(customerName)}).dataset.customerId`);
 await first.click(`[data-customer-id="${customerId}"]`);
 await first.wait(`!!document.querySelector('.rc-inventory-toolbar') && !document.querySelector('.rc-inventory-toolbar button:disabled')`, 'project loaded');
 const snapshot=tab=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Snapshot status '+r.status);return await r.json()})()`);
 await first.button('Create Site'); await form(first,{name:'Campus München 東京'});
 await button(first,'[data-site-id]','Create Building'); await form(first,{name:'Building A'});
 await button(first,'[data-building-id]','Create Room'); await form(first,{name:'Room 01'});
 let data=await snapshot(first); const roomId=data.rooms[0].id;
 assert.equal(data.sites[0].name,'Campus München 東京'); assert.equal(data.buildings[0].siteId,data.sites[0].id); assert.equal(data.rooms[0].buildingId,data.buildings[0].id);
 checks.push('Jerarquía sitio/edificio/sala creada mediante formularios y relaciones UUID persistidas');
 await first.button('Create Rack'); await form(first,{name:'Rack A',roomId,sizeU:'12'});
 data=await snapshot(first);const rackId=data.racks[0].id;
 assert.equal(data.racks[0].roomId,roomId);
 await first.click(`[data-rack-id="${rackId}"] .rc-rack-open`);
 await first.wait(`!!document.querySelector('#rack-detail-export')`, 'RC9 rack');
 await first.button('Add device'); await first.click('[data-create-mode="manual"]'); await form(first,{name:'Switch GUI',sizeU:'1'});
 await first.button('Add device'); await first.click('[data-create-mode="manual"]'); await form(first,{name:'Panel GUI',sizeU:'1'});
 data=await snapshot(first);const sw=data.devices.find(d=>d.name==='Switch GUI'),panel=data.devices.find(d=>d.name==='Panel GUI');
 const swPorts=data.ports.filter(p=>p.deviceId===sw.id), panelPorts=data.ports.filter(p=>p.deviceId===panel.id);
 assert.equal(swPorts.length,2); assert.equal(panelPorts.length,2);
 await first.wait(`document.querySelectorAll('[data-devid]').length===2`, 'persisted rack equipment');
 checks.push('Rack y dos equipos creados en GUI; renderer físico RC9 conserva UUID de puertos');
 await tap(first,`[data-vport="${swPorts[0].id}"]`);
 await first.wait(`!!document.querySelector('.ir-connect-hint')`, 'first Click-Click endpoint');
 await tap(first,`[data-vport="${panelPorts[0].id}"]`);
 await first.wait(`document.querySelectorAll('.rc-connections .ir-connection-card').length===1 && !document.querySelector('.ir-connect-hint')`, 'Click-Click confirmed');
 data=await snapshot(first);assert.equal(data.connections.length,1);
 assert.equal(data.connections[0].fromPortId,swPorts[0].id);assert.equal(data.connections[0].toPortId,panelPorts[0].id);
 checks.push('Click-Click con ratón real: conexión confirmada entre IDs exactos');
 await first.click('.rc-connections .ir-connection-card');await button(first,'.rc-connections .ir-inspector','Edit');
 await form(first,{note:'Cable geprüft 東京',patch:'tested',color:'#123456'});
 data=await snapshot(first);assert.equal(data.connections[0].note,'Cable geprüft 東京');assert.equal(data.connections[0].patch,'tested');assert.equal(data.connections[0].color,'#123456');
 checks.push('Nota Unicode, color y estado de patch escritos y leídos del servidor');
 await first.click('[data-face="rear"]');assert.equal(await first.evaluate(`document.querySelector('[data-face="rear"]').getAttribute('aria-pressed')`),'true');
 await first.click('[data-face="front"]');
 await writeFile(path.join(evidence,'rack-click-click-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 checks.push('Frontal/trasera RC9 y captura real del rack');
 await first.button('Manage infrastructure');
 await button(first,'[data-room-id]','Create Wall outlet');await form(first,{name:'Dose A'});
 await button(first,'[data-room-id]','Create End device');await form(first,{name:'Endpoint A'});
 data=await snapshot(first);const dose=data.devices.find(d=>d.name==='Dose A'),end=data.devices.find(d=>d.name==='Endpoint A');
 assert.equal(dose.kind,'dose');assert.equal(end.kind,'endDevice');assert.equal(dose.roomId,roomId);assert.equal(end.roomId,roomId);assert.equal(dose.rackId,null);assert.equal(end.rackId,null);
 const dosePort=data.ports.find(p=>p.deviceId===dose.id),endPort=data.ports.find(p=>p.deviceId===end.id);
 await first.click(`[data-room-port="${dosePort.id}"]`);await first.click(`[data-room-port="${endPort.id}"]`);
 await first.wait(`document.querySelectorAll('.rc-connections .ir-connection-card').length===2`, 'room connection committed');
 data=await snapshot(first);assert.equal(data.connections.length,2);
 checks.push('Dosen y dispositivos finales en sala sin rack; conexión explícita entre sus puertos');
 const expected=data;
 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`, 'reload customer');await first.click(`[data-customer-id="${customerId}"]`);
 await first.wait(`document.querySelectorAll('.rc-connections .ir-connection-card').length===2`, 'reloaded connections');
 assert.deepEqual(await snapshot(first),expected);
 checks.push('Recarga completa conserva jerarquía, equipos, puertos, cables y revisión');
 const second=await session();await second.field('select','en');await second.click(`[data-customer-id="${customerId}"]`);
 await second.wait(`document.querySelectorAll('.rc-connections .ir-connection-card').length===2`, 'independent session inventory');
 assert.deepEqual(await snapshot(second),expected);
 assert.deepEqual((await second.evaluate(`Object.keys(localStorage)`)).sort(),['rackclick_server_language','rackclick_server_theme']);
 checks.push('Segunda sesión con cookies independientes lee el mismo proyecto; localStorage solo preferencias');
 // Each fresh cookie context checks /me before login; exactly those 401s are expected.
 const unauthenticated=responses.filter(r=>r.path==='/api/v1/me'&&r.status===401);assert.ok(unauthenticated.length<=2);
 const materialErrors=errors.filter(error=>!/^\/api\/v1\/me: .*status of 401 |favicon\.ico/.test(error));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,customerId,revision:expected.revision,checks,browserErrors:materialErrors,limitations:['Recorrido principal de inventario; no certifica toda la paridad RC9 ni permisos de distintos usuarios.','Dos sesiones del mismo administrador; no se crean circuitos internos implícitos en Dosen.']};
 await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch (error) {
 let visibleText = '';
 if (lastTab) { try { visibleText = (await lastTab.evaluate(`document.body.innerText`)).replaceAll(password, '[redacted]').replaceAll(username, '[synthetic user]'); const shot = await lastTab.send('Page.captureScreenshot', { format: 'png' }); await writeFile(path.join(evidence, 'browser-failure.png'), Buffer.from(shot.data, 'base64')); } catch {} }
 await writeFile(path.join(evidence, 'browser-windows-failure.json'), JSON.stringify({ run, status: 'failed', checks, error: error.message, browserErrors: errors, responses, visibleText }, null, 2)); throw error;
} finally {
 if (browser) { try { await browser.send('Browser.close'); } catch {} }
 for (const client of clients) client.ws.close();
 if (child.exitCode === null) child.kill();
}
