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
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if(data.method==='Network.requestWillBeSent' && /\/commands(?:\/preview)?$/.test(new URL(data.params.request.url).pathname)) { const r=data.params.request; (this.commands ||= []).push({path:new URL(r.url).pathname,body:JSON.parse(r.postData)}); } else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
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
  const target = await browser.send('Target.createTarget', { url: 'about:blank', browserContextId: context.browserContextId });
  const info = await poll(async () => (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.id === target.targetId), 'session target');
  const tab = await CDP.open(info.webSocketDebuggerUrl); lastTab = tab; await tab.send('Runtime.enable'); await tab.send('Log.enable'); await tab.send('Network.enable'); await tab.send('Page.enable'); await tab.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await tab.send('Page.navigate', {url:origin});
  await tab.wait(`!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled`, 'login screen');
  await tab.field('select', 'es'); await tab.field('input[name=username]', username); await tab.field('input[name=password]', password); await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('.ir-nav')`, 'authenticated RC9 navigation'); return tab;
 }

 const first=await session();await first.field('select','en');
 async function named(tab,button,name) {
  await tab.button(button);await tab.wait(`!!document.querySelector('dialog input[name=name]')`,'name dialog');
  await tab.field('dialog input[name=name]',name);await submit(tab);
 }
 async function submit(tab) {
  await tab.evaluate(`document.querySelector('dialog form').requestSubmit()`);
  await tab.wait(`!document.querySelector('dialog[open]')`,'commit confirmed');
  await tab.wait(`!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory ready');
 }
 async function tap(tab,selector) {
  const p=await tab.evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  for(const type of ['mousePressed','mouseReleased'])await tab.send('Input.dispatchMouseEvent',{type,...p,button:'left',clickCount:1});
 }
 await named(first,'Create client','Impact '+run);
 const customerId=await first.evaluate(`document.querySelector('[data-customer-id]').dataset.customerId`);
 async function enter(tab) {
  await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'customer loaded');await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory loaded');
 }
 const snapshot=tab=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Snapshot '+r.status);return r.json()})()`);
 await enter(first);await named(first,'Create Rack','Target rack');
 let data=await snapshot(first);const rackA=data.racks[0].id;
 async function openRack(id) {
  await first.button('Manage infrastructure');await first.click(`[data-rack-id="${id}"] .rc-rack-open`);
  await first.wait(`!!document.querySelector('#rack-detail-export')`,'physical rack');
 }
 await openRack(rackA);await named(first,'Add device','Device A');await named(first,'Add device','Device B');
 await named(first,'Create Rack','Protected rack');data=await snapshot(first);const rackB=data.racks.find(r=>r.name==='Protected rack').id;
 await openRack(rackB);await named(first,'Add device','Device C');await named(first,'Add device','Device D');
 data=await snapshot(first);
 const device=name=>data.devices.find(d=>d.name==='Device '+name);
 const ports=name=>data.ports.filter(p=>p.deviceId===device(name).id).sort((a,b)=>a.gn-b.gn);
 const a=ports('A'),b=ports('B'),c=ports('C'),d=ports('D'),deviceA=device('A');
 async function connect(from,to,count) {
  await tap(first,`[data-vport="${from}"]`);await first.wait(`!!document.querySelector('.ir-connect-hint')`,'first endpoint');
  await tap(first,`[data-vport="${to}"]`);
  await first.wait(`document.querySelectorAll('.rc-connections .ir-connection-card').length===${count}&&!document.querySelector('.ir-connect-hint')`,'connection committed');
 }
 await connect(c[0].id,d[0].id,1);await openRack(rackA);await connect(a[0].id,b[0].id,2);
 let before=await snapshot(first);const cable=before.connections.find(x=>x.fromPortId===a[0].id),protectedCable=before.connections.find(x=>x.fromPortId===c[0].id);
 assert.ok(cable&&protectedCable);assert.equal(cable.toPortId,b[0].id);assert.equal(protectedCable.toPortId,d[0].id);
 await first.evaluate(`(()=>{const b=[...document.querySelectorAll('.rc-connections .ir-connection-card')].find(b=>b.textContent.includes('Device A'));b.click()})()`);
 await first.evaluate(`(()=>{const b=[...document.querySelectorAll('.rc-connections .ir-inspector button')].find(b=>b.textContent.startsWith('Reconnect')&&b.textContent.includes('Device A'));b.click()})()`);
 await first.wait(`!!document.querySelector('.ir-connect-hint')`,'keep endpoint hint');await tap(first,`[data-vport="${b[1].id}"]`);
 await first.wait(`!document.querySelector('.ir-connect-hint')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'reconnected');
 let after=await snapshot(first);assert.equal(after.revision,before.revision+1);
 assert.deepEqual(after.connections.find(x=>x.id===cable.id),{...cable,toPortId:b[1].id});assert.deepEqual(after.connections.find(x=>x.id===protectedCable.id),protectedCable);
 for(const key of ['racks','devices','portGroups','ports'])assert.deepEqual(after[key],before[key]);
 const reconnection=first.commands.at(-1).body;
 assert.equal(reconnection.type,'connections.reconnect');assert.deepEqual(reconnection.payload,{connectionId:cable.id,keepPortId:a[0].id,newPortId:b[1].id,confirmedReservedPortIds:[]});
 checks.push('Reconexión GUI conserva UUID/extremo elegido y cable ajeno; solo cambia el extremo solicitado y la revisión');

 async function preview(expected) {
  const count=first.commands.length;
  await first.button('Review affected objects');await first.wait(`!!document.querySelector('dialog li details')`,'server impact shown');
  const shown=await first.evaluate(`Object.fromEntries([...document.querySelectorAll('dialog li')].map(li=>[li.dataset.impactKind,[...li.querySelectorAll('[data-impact-id]')].map(e=>e.dataset.impactId).sort()]))`);
  const filtered=Object.fromEntries(Object.entries(expected).filter(([,v])=>v.length).map(([k,v])=>[k,[...v].sort()]));
  assert.deepEqual(shown,filtered);
  const labels=await first.evaluate(`Object.fromEntries([...document.querySelectorAll('[data-impact-id]')].map(e=>[e.dataset.impactId,e.textContent]))`);
  const current=await snapshot(first);
  for(const id of expected.deviceIds)assert.ok(labels[id].includes(current.devices.find(d=>d.id===id).name));
  for(const id of expected.portIds){const p=current.ports.find(p=>p.id===id);assert.ok(labels[id].includes(current.devices.find(d=>d.id===p.deviceId).name));assert.ok(labels[id].includes('#'+p.gn));}
  for(const id of expected.connectionIds){const c=current.connections.find(c=>c.id===id);for(const pid of [c.fromPortId,c.toPortId]){const p=current.ports.find(p=>p.id===pid);assert.ok(labels[id].includes(current.devices.find(d=>d.id===p.deviceId).name));}}
  assert.ok(!await first.evaluate(`document.querySelector('dialog').textContent.includes('deviceIds:')`));
  assert.equal(first.commands.length,count+1);assert.ok(first.commands.at(-1).path.endsWith('/commands/preview'));
 }
 const impactDevice={rackIds:[],deviceIds:[deviceA.id],groupIds:before.portGroups.filter(g=>g.deviceId===deviceA.id).map(g=>g.id),portIds:a.map(p=>p.id),connectionIds:[cable.id]};
 before=after;
 await first.click(`[data-devid="${deviceA.id}"] .ir-device-actions button:last-child`);await preview(impactDevice);
 assert.deepEqual(await snapshot(first),before);
 await first.button('Cancel');await first.wait(`!document.querySelector('dialog[open]')`,'cancel preview');assert.deepEqual(await snapshot(first),before);
 checks.push('Vista previa de eliminar equipo muestra IDs exactos; revisar y cancelar no modifica datos');

 await first.click(`[data-devid="${deviceA.id}"] .ir-device-actions button:last-child`);await preview(impactDevice);
 const second=await session();await second.field('select','en');await enter(second);await named(second,'Create Site','Concurrent change');
 const concurrent=await snapshot(second);assert.equal(concurrent.revision,before.revision+1);
 await first.button('Confirm deletion');await first.wait(`!!document.querySelector('dialog [role=alert]')`,'stale preview conflict');
 assert.ok((await first.evaluate(`document.querySelector('dialog [role=alert]').textContent`)).includes('Another session'));
 assert.equal(await first.evaluate(`document.querySelector('dialog button[type=submit]').disabled`),true);
 assert.deepEqual(await snapshot(first),concurrent);
 const oldDelete=first.commands.at(-1).body;assert.equal(oldDelete.type,'device.delete');assert.ok(oldDelete.payload.confirmationToken);
 checks.push('Cambio concurrente invalida confirmación anterior con 412: equipo y conexiones siguen intactos');
 await first.button('Reload current data');await first.wait(`!document.querySelector('dialog [role=alert]')&&!document.querySelector('dialog li details')`,'refresh preview revision');
 await preview(impactDevice);assert.deepEqual(await snapshot(first),concurrent);
 await writeFile(path.join(evidence,'exact-impact-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await first.button('Confirm deletion');await first.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'delete device committed');
 after=await snapshot(first);assert.equal(after.revision,concurrent.revision+1);
 assert.notEqual(first.commands.at(-1).body.payload.confirmationToken,oldDelete.payload.confirmationToken);
 function assertRemoval(actual,previous,impact) {
  for(const [collection,key] of Object.entries({racks:'rackIds',devices:'deviceIds',portGroups:'groupIds',ports:'portIds',connections:'connectionIds'})) {
   assert.deepEqual(actual[collection],previous[collection].filter(x=>!impact[key].includes(x.id)),collection+' exact remaining objects');
  }
  for(const key of ['sites','buildings','rooms'])assert.deepEqual(actual[key],previous[key]);
 }
 assertRemoval(after,concurrent,impactDevice);
 checks.push('Nueva revisión y nueva confirmación eliminan solo equipo/puertos/cable previstos; objetos ajenos idénticos');

 before=after;await first.button('Manage infrastructure');
 await first.evaluate(`(()=>{const b=[...document.querySelector('[data-rack-id="${rackA}"]').querySelectorAll('button')].find(b=>b.textContent==='Delete');b.click()})()`);
 const rackDevices=before.devices.filter(x=>x.rackId===rackA).map(x=>x.id);
 const impactRack={rackIds:[rackA],deviceIds:rackDevices,groupIds:before.portGroups.filter(g=>rackDevices.includes(g.deviceId)).map(g=>g.id),portIds:before.ports.filter(p=>rackDevices.includes(p.deviceId)).map(p=>p.id),connectionIds:[]};
 await preview(impactRack);assert.deepEqual(await snapshot(first),before);
 await first.button('Confirm deletion');await first.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('[data-rack-id="${rackA}"]')`,'rack deleted');
 after=await snapshot(first);assert.equal(after.revision,before.revision+1);assertRemoval(after,before,impactRack);assert.deepEqual(after.connections,[protectedCable]);
 checks.push('Eliminación de rack aplica impacto exacto y conserva otro rack con su cable');
 await first.send('Page.reload');await first.wait(`!!document.querySelector('.ir-nav')`,'reload');await enter(first);assert.deepEqual(await snapshot(first),after);
 await second.send('Page.reload');await second.wait(`!!document.querySelector('.ir-nav')`,'second reload');await enter(second);assert.deepEqual(await snapshot(second),after);
 checks.push('Recarga y segunda sesión leen el mismo resultado persistido');
 const expectedError=e=>/^\/api\/v1\/me: .*status of 401 \(/.test(e)||/^\/favicon\.ico: .*status of 404 \(/.test(e)||e.startsWith('/api/v1/customers/'+customerId+'/commands: ')&&e.includes('status of 412 (');
 const materialErrors=errors.filter(e=>!expectedError(e));assert.deepEqual(materialErrors,[]);
 const failures=responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401));
 assert.deepEqual(failures,[{path:'/api/v1/customers/'+customerId+'/commands',status:412}]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,customerId,checks,browserErrors:materialErrors,limitations:['Dos sesiones del mismo administrador, no permisos de otros usuarios.','Eliminación de equipo y rack; no eliminación parcial de grupos ni todos los tipos de conectores.','Servidor activo durante recarga; no reinicio Windows ni servidor.']};
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
