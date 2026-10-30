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
const launch = () => spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + port, '--user-data-dir=' + profile, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
let child = launch();
const browserRestarts = [];
const clients = [], checks = [], errors = [], responses = [];
let lastTab;
const delay = ms => new Promise(r => setTimeout(r, ms));
async function poll(fn, label, duration = 15000) { const end = Date.now() + duration; let last; do { try { const v = await fn(); if (v) return v; } catch (e) { last = e; } await delay(100); } while (Date.now() < end); throw Error('Timed out: ' + label + (last ? ': ' + last.message : '')); }
class CDP {
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if(data.method === 'Fetch.requestPaused') this.paused = data.params; else if(data.method === 'Network.requestWillBeSent' && /\/commands$/.test(new URL(data.params.request.url).pathname)) { const r=data.params.request,h=Object.fromEntries(Object.entries(r.headers).map(([k,v])=>[k.toLowerCase(),v])); (this.commands ||= []).push({body:r.postData,requestId:h['idempotency-key'],etag:h['if-match'],actorId:h['x-rackclick-actor']}); } else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
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
 async function page(contextId) {
  const target = await browser.send('Target.createTarget', { url: 'about:blank', browserContextId: contextId });
  const ti = await poll(async () => (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.id === target.targetId), 'session target');
  const tab = await CDP.open(ti.webSocketDebuggerUrl);lastTab=tab;tab.contextId=contextId;tab.targetId=target.targetId;
  for(const domain of ['Runtime','Log','Network','Page']) await tab.send(domain+'.enable');
  await tab.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await tab.send('Page.navigate',{url:origin});return tab;
 }
 async function session() {
  const tab=await page();
  await tab.wait(`!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled`, 'login screen');
  await tab.field('select','en');await tab.field('input[name=username]',username);await tab.field('input[name=password]',password);await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('.ir-nav')`,'authenticated');return tab;
 }

 let tab=await session();
 async function submit() {
  await tab.evaluate(`document.querySelector('dialog form').requestSubmit()`);
  await tab.wait(`!document.querySelector('dialog[open]')`, 'confirmed dialog');
  await tab.wait(`!document.querySelector('.rc-inventory-toolbar button:disabled')`, 'ready');
 }
 async function named(button,name) {
  await tab.button(button);await tab.wait(`!!document.querySelector('dialog input[name=name]')`,'name dialog');
  await tab.field('dialog input[name=name]',name);await submit();
 }
 await named('Create client','Recovery '+run);
 const customerId=await tab.evaluate(`document.querySelector('[data-customer-id]').dataset.customerId`);
 const commandsPath='/api/v1/customers/'+customerId+'/commands';
 async function enter() {
  await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'customer');await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')`,'inventory');
 }
 const snapshot=()=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Project '+r.status);return r.json()})()`);
 const journal=()=>tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.PendingOperations.v1',1);r.onerror=()=>reject(Error('Journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)};q.onerror=()=>{db.close();reject(Error('Journal read'))}}})`);
 const operationState=id=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/operations/${id}');if(!r.ok)throw Error('Operation '+r.status);return r.json()})()`);
 await enter();await named('Create Rack','Batch rack');
 await tab.button('Add device');await tab.wait(`!!document.querySelector('dialog input[name=name]')`,'device');await tab.field('dialog input[name=name]','Three groups');
 await tab.button('Add group');await tab.button('Add group');
 for(let i=1;i<=3;i++) {
  const group=`.rc-port-groups > div:nth-of-type(${i})`;
  await tab.field(group+' select',i===3?'sfp':'rj45');
  await tab.field(group+' input[type=number]','2');
  await tab.field(group+' label:nth-of-type(3) input','Group '+i);
 }
 await submit();let before=await snapshot();const device=before.devices[0],group=before.portGroups.find(g=>g.name==='Group 1');
 assert.equal(before.ports.filter(p=>p.gn===1).length,3);
 const ids=before.ports.filter(p=>p.groupId===group.id).map(p=>p.id);
 const rackId=before.racks[0].id;await tab.click(`[data-rack-id="${rackId}"] .rc-rack-open`);
 await tab.wait(`!!document.querySelector('[data-vport="${ids[0]}"]')`,'rack ports');
 await tab.evaluate(`document.querySelector('[data-vport="${ids[0]}"]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))`);
 await tab.wait(`!!document.querySelector('dialog .rc-port-selection')`,'port editor');
 await tab.click('dialog .rc-port-selection label:nth-child(2) input');
 // Group, field, value are the three selects in the scoped port editor.
 await tab.field('dialog section > label:last-child select','reserved');
 await submit();let after=await snapshot();
 assert.equal(after.revision,before.revision+1);
 for(const p of before.ports) assert.deepEqual(after.ports.find(x=>x.id===p.id),ids.includes(p.id)?{...p,status:'reserved'}:p);
 const sent=tab.commands.at(-1),body=JSON.parse(sent.body);
 assert.equal(body.type,'ports.update');assert.equal(body.payload.groupId,group.id);assert.equal(body.payload.groupType,'rj45');assert.deepEqual(body.payload.portIds.sort(),[...ids].sort());
 checks.push('Lote GUI por dos UUID y grupo/tipo: solo cambia el grupo elegido entre tres grupos con gn repetido');
 assert.deepEqual(await journal(),[]);

 async function pause(stage) {
  tab.paused=null;await tab.send('Fetch.enable',{patterns:[{urlPattern:origin+commandsPath,requestStage:stage}]});
 }
 async function lose() {
  const p=await poll(()=>tab.paused,'intercepted command');
  await tab.send('Fetch.failRequest',{requestId:p.requestId,errorReason:'Failed'});await tab.send('Fetch.disable');
  await tab.wait(`!!document.querySelector('dialog [role=alert]')`,'visible uncertainty');
  assert.equal(await tab.evaluate(`document.querySelector('dialog input[name=name]').disabled`),true);
  return p;
 }
 async function reopen() {
  const previous=child;
  await browser.send('Browser.close');
  await poll(()=>previous.exitCode!==null,'previous Edge process exited');
  child=launch();
  const nextInfo=await poll(async()=>(await fetch('http://127.0.0.1:'+port+'/json/version')).json(),'restarted Edge');
  browser=await CDP.open(nextInfo.webSocketDebuggerUrl);tab=await page();
  assert.notEqual(child.pid,previous.pid);browserRestarts.push({previousPid:previous.pid,newPid:child.pid,previousExited:true});
  await tab.wait(`!!document.querySelector('.ir-nav') || (!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled)`,'reopened profile');
  if(await tab.evaluate(`!!document.querySelector('input[name=username]')`)) {
   await tab.field('input[name=username]',username);await tab.field('input[name=password]',password);await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  }
  await tab.wait(`!!document.querySelector('.ir-nav')`,'original actor authenticated');await enter();
  await tab.wait(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Recover pending operation')`,'durable pending banner');
  assert.equal(await tab.evaluate(`document.querySelector('.rc-inventory-toolbar button:nth-child(2)').disabled`),true);
 }
 await tab.button('Manage infrastructure');before=await snapshot();
 await tab.button('Create Site');await tab.field('dialog input[name=name]','Committed with lost response');
 await pause('Response');await tab.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 const paused=await poll(()=>tab.paused,'response after server');assert.equal(paused.responseStatusCode,200);
 const records=await journal();assert.equal(records.length,1);const original=records[0];
 const committed=await operationState(original.requestId);assert.equal(committed.state,'committed');
 await lose();await reopen();assert.deepEqual(await journal(),records);
 await tab.button('Recover pending operation');await tab.button('Retry confirmation');
 await tab.wait(`!document.querySelector('dialog[open]') && !document.querySelector('.rc-inventory-toolbar button:disabled')`,'recovered original commit');
 after=await snapshot();assert.equal(after.revision,before.revision+1);assert.equal(after.sites.filter(x=>x.name==='Committed with lost response').length,1);
 const replay=tab.commands.at(-1);assert.deepEqual(replay,{body:original.operation.body,requestId:original.requestId,etag:original.operation.etag,actorId:original.actorId});
 assert.deepEqual(await journal(),[]);assert.deepEqual(await operationState(original.requestId),committed);
 checks.push('Respuesta perdida después del commit: diario sobrevive reinicio de Edge, reintento conserva UUID/cuerpo/revisión/actor y no duplica');

 before=after;await tab.button('Create Site');await tab.field('dialog input[name=name]','Cancelled before send');
 await pause('Request');await tab.evaluate(`document.querySelector('dialog form').requestSubmit()`);await lose();
 const cancelRecords=await journal(),cancelId=cancelRecords[0].requestId;
 assert.equal((await operationState(cancelId)).state,'notRecorded');await reopen();assert.deepEqual(await journal(),cancelRecords);
 await tab.button('Recover pending operation');
 const confirm=new Promise(resolve=>{const fn=e=>{const d=JSON.parse(e.data);if(d.method==='Page.javascriptDialogOpening'){tab.ws.removeEventListener('message',fn);resolve(d.params)}};tab.ws.addEventListener('message',fn)});
 const clickCancel=tab.button('Cancel pending operation');const dialog=await confirm;assert.equal(dialog.type,'confirm');await tab.send('Page.handleJavaScriptDialog',{accept:true});await clickCancel;
 await tab.wait(`!document.querySelector('dialog[open]') && !document.querySelector('.rc-inventory-toolbar button:disabled')`,'server cancellation fence');
 assert.equal((await operationState(cancelId)).state,'cancelled');assert.deepEqual(await snapshot(),before);assert.deepEqual(await journal(),[]);
 checks.push('Petición interrumpida antes del envío: recuperación y cancelación confirmada por servidor sin escribir inventario');
 await writeFile(path.join(evidence,'recovered-windows.png'),Buffer.from((await tab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const expectedError=error=>/^\/api\/v1\/me: .*status of 401 \(/.test(error)||/^\/favicon\.ico: .*status of 404 \(/.test(error)||error.startsWith(commandsPath+': ')&&error.includes('net::ERR_FAILED');
 const materialErrors=errors.filter(e=>!expectedError(e));assert.deepEqual(materialErrors,[]);
 assert.ok(responses.filter(r=>r.path==='/api/v1/me'&&r.status===401).length<=3);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,customerId,checks,browserRestarts,browserErrors:materialErrors,limitations:['Reinicio de procesos Edge sobre perfil de laboratorio propio; no apagado abrupto ni reinicio Windows.','Mismo administrador; permisos de distintos usuarios no forman parte de este escenario.','Interrupciones controladas por CDP antes del envío y después del commit; no caída del servidor.']};
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
