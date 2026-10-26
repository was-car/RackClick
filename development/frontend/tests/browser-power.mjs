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

 await named(first,'Create client','Groups power '+run);
 const customerId=await first.evaluate(`document.querySelector('[data-customer-id]').dataset.customerId`);
 await first.click(`[data-customer-id="${customerId}"]`);await first.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory ready');
 const snapshot=()=>first.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Snapshot '+r.status);return r.json()})()`);
 await named(first,'Create Rack','Power rack');let data=await snapshot();const rackId=data.racks[0].id;
 await first.click(`[data-rack-id="${rackId}"] .rc-rack-open`);await first.wait(`!!document.querySelector('#rack-detail-export')`,'rack');
 async function createDevice(name,type='rj45') {
  await first.button('Add device');await first.wait(`!!document.querySelector('dialog input[name=name]')`,'device form');await first.field('dialog input[name=name]',name);
  await first.field('.rc-port-groups select',type);await submit(first);
 }
 await createDevice('Switch');await createDevice('Panel');await createDevice('Supply','power');await createDevice('Consumer','power');await createDevice('Optical','sfp');
 data=await snapshot();const device=name=>data.devices.find(d=>d.name===name),ports=name=>data.ports.filter(p=>p.deviceId===device(name).id).sort((a,b)=>a.gn-b.gn);
 const sw=ports('Switch'),panel=ports('Panel'),supply=ports('Supply'),consumer=ports('Consumer'),optical=ports('Optical');
 async function visiblePort(id) {
  const selector=`[data-vport="${id}"]`;
  if(!await first.evaluate(`!!document.querySelector('${selector}')`)) {
   const face=await first.evaluate(`document.querySelector('[data-face][aria-pressed=true]').dataset.face`);await first.click(`[data-face="${face==='front'?'rear':'front'}"]`);
  }
  await first.wait(`!!document.querySelector('${selector}')`,'visible port');return selector;
 }
 async function editor(id,field,value) {
  const selector=await visiblePort(id);await first.evaluate(`document.querySelector('${selector}').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))`);
  await first.wait(`!!document.querySelector('dialog .rc-port-selection')`,'port editor');
  await first.field('dialog section > label:nth-of-type(2) select',field);
  await first.field(`dialog section > label:last-child ${['poe','powerRole','face','status'].includes(field)?'select':'input'}`,value);
 }
 async function edit(id,field,value) {await editor(id,field,value);await submit(first);}
 async function connect(from,to,count) {
  await tap(first,await visiblePort(from));await first.wait(`!!document.querySelector('.ir-connect-hint')`,'first endpoint');await tap(first,await visiblePort(to));
  await first.wait(`document.querySelectorAll('.rc-connections .ir-connection-card').length===${count}&&!document.querySelector('.ir-connect-hint')`,'connection committed');
 }
 await connect(sw[0].id,panel[0].id,1);await connect(sw[1].id,panel[1].id,2);
 let before=await snapshot();await edit(sw[1].id,'poe','true');await edit(sw[1].id,'watts','90');
 let after=await snapshot(),p=after.ports.find(p=>p.id===sw[1].id);
 assert.equal(p.poe,true);assert.equal(p.type,'rj45_poe');assert.equal(p.watts,90);assert.deepEqual(after.connections,before.connections);
 for(const port of before.ports.filter(p=>p.id!==sw[1].id))assert.deepEqual(after.ports.find(p=>p.id===port.id),port);
 const command=first.commands.at(-1).body;assert.equal(command.type,'ports.update');assert.equal(command.payload.groupType,'rj45');assert.deepEqual(command.payload.portIds,[sw[1].id]);
 checks.push('PoE y 90 W documentados en UUID elegido; grupo sigue siendo RJ45, cables y demás puertos intactos');
 await edit(sw[1].id,'watts','0');assert.equal((await snapshot()).ports.find(p=>p.id===sw[1].id).watts,0);
 await edit(sw[1].id,'watts','');assert.equal((await snapshot()).ports.find(p=>p.id===sw[1].id).watts,null);
 before=await snapshot();await editor(optical[0].id,'poe','true');await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!!document.querySelector('dialog [role=alert]')`,'unsupported PoE rejected');assert.deepEqual(await snapshot(),before);
 await first.button('Cancel');await first.wait(`!document.querySelector('dialog[open]')`,'dismiss unsupported PoE');
 checks.push('Watts cero/desconocido preservados; servidor rechaza PoE en SFP sin cambiar inventario');

 await first.click('[data-face="front"]');before=await snapshot();
 const switchId=device('Switch').id,group=before.portGroups.find(g=>g.deviceId===switchId),removedCable=before.connections.find(c=>c.fromPortId===sw[0].id),keptCable=before.connections.find(c=>c.fromPortId===sw[1].id);
 await first.evaluate(`(()=>{const b=[...document.querySelectorAll('.ir-right button')].find(b=>b.textContent.startsWith('Edit port groups')&&b.textContent.includes('Switch'));b.click()})()`);
 await first.wait(`!!document.querySelector('dialog .rc-port-selection')`,'group editor');await first.click('dialog .rc-port-selection label:first-child input');
 await first.field('dialog .rc-port-groups input[type=number]','1');await first.button('Review affected objects');
 await first.wait(`!!document.querySelector('[data-impact-kind]')`,'partial removal impact');
 const shown=await first.evaluate(`Object.fromEntries([...document.querySelectorAll('[data-impact-kind]')].map(li=>[li.dataset.impactKind,[...li.querySelectorAll('[data-impact-id]')].map(e=>e.dataset.impactId)]))`);
 assert.deepEqual(shown,{portIds:[sw[0].id],connectionIds:[removedCable.id]});assert.deepEqual(await snapshot(),before);
 await writeFile(path.join(evidence,'partial-group-impact.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await first.button('Confirm deletion');await first.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'group edit committed');
 after=await snapshot();assert.equal(after.revision,before.revision+1);assert.ok(!after.ports.some(p=>p.id===sw[0].id));
 const retained=after.ports.find(p=>p.id===sw[1].id);assert.deepEqual(retained,{...before.ports.find(p=>p.id===sw[1].id),sortOrder:0});
 const added=after.ports.filter(p=>p.groupId===group.id&&p.id!==retained.id);assert.equal(added.length,1);assert.ok(!before.ports.some(p=>p.id===added[0].id));assert.equal(added[0].gn,3);
 assert.deepEqual(after.connections,[keptCable]);assert.deepEqual(after.portGroups,before.portGroups);
 for(const port of before.ports.filter(p=>p.deviceId!==switchId))assert.deepEqual(after.ports.find(p=>p.id===port.id),port);
 checks.push('Edición parcial quita solo puerto/cable previstos, conserva UUID/PoE del retenido y crea puerto nuevo sin reutilizar gn');

 await edit(supply[0].id,'powerRole','inlet');await edit(consumer[0].id,'powerRole','inlet');before=await snapshot();
 await tap(first,await visiblePort(supply[0].id));await tap(first,await visiblePort(consumer[0].id));
 await first.wait(`!!document.querySelector('.rc-inventory > [role=alert]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inlet-inlet rejected');assert.deepEqual(await snapshot(),before);
 await first.button('Clear selection');await edit(supply[0].id,'powerRole','outlet');
 await connect(supply[0].id,consumer[0].id,2);before=await snapshot();const powerCable=before.connections.find(c=>c.fromPortId===supply[0].id);
 assert.equal(powerCable.toPortId,consumer[0].id);assert.deepEqual(before.connections.find(c=>c.id===keptCable.id),keptCable);
 await editor(supply[0].id,'powerRole','inlet');await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!!document.querySelector('dialog [role=alert]')`,'invalid connected role rejected');assert.deepEqual(await snapshot(),before);
 await first.button('Cancel');await first.wait(`!document.querySelector('dialog[open]')`,'dismiss rejected role');
 checks.push('AC: servidor rechaza entrada–entrada; salida–entrada conecta; cambio incompatible conectado se revierte sin afectar cable PoE');
 const expected=await snapshot();await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'reload');await first.click(`[data-customer-id="${customerId}"]`);await first.wait(`!!document.querySelector('.rc-inventory-toolbar')`,'inventory');assert.deepEqual(await snapshot(),expected);
 checks.push('Recarga conserva grupos, puertos, PoE, roles AC y conexiones');
 const commandPath='/api/v1/customers/'+customerId+'/commands';
 const rejected=responses.filter(r=>r.path===commandPath&&r.status>=400);assert.deepEqual(rejected.map(r=>r.status),[422,409,409]);
 const materialErrors=errors.filter(e=>!/^\/api\/v1\/me: .*status of 401 \(|^\/favicon\.ico: .*status of 404 \(/.test(e)&&!(e.startsWith(commandPath+': ')&&/status of (422|409) \(/.test(e)));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&r.path!==commandPath&&!(r.path==='/api/v1/me'&&r.status===401)),[]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,customerId,checks,browserErrors:materialErrors,limitations:['Potencia documentada, no medida: no acredita suministro eléctrico ni cumplimiento de normas eléctricas.','Una sesión de administrador, sin permisos multiusuario ni reinicio servidor.','Tipos RJ45/SFP/power y casos descritos; no todas las combinaciones PoE/AC ni paridad completa.']};
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
