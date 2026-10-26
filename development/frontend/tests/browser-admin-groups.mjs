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
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if (data.method === 'Fetch.requestPaused') this.paused=data.params; else if (data.method === 'Page.javascriptDialogOpening' && data.params.type==='beforeunload') this.send('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{}); else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
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
 async function session(user = username) {
  const context = await browser.send('Target.createBrowserContext');
  const target = await browser.send('Target.createTarget', { url: 'about:blank', browserContextId: context.browserContextId });
  const info = await poll(async () => (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.id === target.targetId), 'session target');
  const tab = await CDP.open(info.webSocketDebuggerUrl); lastTab = tab; await tab.send('Runtime.enable'); await tab.send('Log.enable'); await tab.send('Network.enable'); await tab.send('Page.enable'); await tab.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await tab.send('Page.navigate',{url:origin});
  await tab.wait(`!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled`, 'login screen');
  await tab.field('select', 'es'); await tab.field('input[name=username]', user); await tab.field('input[name=password]', password); await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('.ir-nav')`, 'authenticated RC9 navigation'); return tab;
 }

 async function reload(tab) {
  let loaded=false;
  const listener=e=>{if(JSON.parse(e.data).method==='Page.loadEventFired')loaded=true};
  tab.ws.addEventListener('message',listener);
  try {await tab.send('Page.reload');await poll(()=>loaded,'new document loaded');}
  finally {tab.ws.removeEventListener('message',listener);}
 }
 async function openGroups(tab) {
  await tab.wait(`!!document.querySelector('[data-admin-users]')`,'admin link');await tab.click('[data-admin-users]');
  await tab.wait(`!!document.querySelector('[data-admin-groups]')`,'groups link');await tab.click('[data-admin-groups]');
  await tab.wait(`!!document.querySelector('[data-create-group]')&&!document.querySelector('[data-create-group] button[type=submit]').disabled`,'group form ready');
 }
 const first=await session();await first.field('select','en');await openGroups(first);
 async function submit(tab,name,kind='userGroup') {
  await tab.field('select[name=groupKind]',kind);await tab.field('input[name=groupName]',name);
  await tab.evaluate(`document.querySelector('[data-create-group]').requestSubmit()`);
 }
 async function saved(tab,name,kind='userGroup') {
  const selector=kind==='userGroup'?'[data-user-group-id] h4':'[data-customer-group-id] h4';
  await tab.wait(`[...document.querySelectorAll(${JSON.stringify(selector)})].some(x=>x.textContent===${JSON.stringify(name)})&&!document.querySelector('[data-pending-group]')&&!document.querySelector('[data-create-group] button[type=submit]').disabled`,'group confirmed and reloaded');
 }
 const journal=()=>first.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminGroups.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
 const unicodeName='Techniker 東京 '+'🚀'.repeat(87);assert.equal([...unicodeName].length,100);
 await submit(first,'  '+unicodeName+'  ');await saved(first,unicodeName);
 await submit(first,'Kunden München 東京','customerGroup');await saved(first,'Kunden München 東京','customerGroup');
 const before=await first.evaluate(`Promise.all(['user-groups','customer-groups'].map(p=>fetch('/api/v1/admin/'+p).then(r=>r.json())))`);
 assert.equal(before[0].groups.length,2);assert.equal(before[1].groups.length,1);
 assert.deepEqual(before[0].groups.find(g=>g.name===unicodeName).members,[]);assert.deepEqual(before[0].groups.find(g=>g.name===unicodeName).grants,[]);assert.deepEqual(before[1].groups[0].customers,[]);
 checks.push('Ambos tipos desde GUI;100 escalares Unicode con trim y mayúsculas conservadas; grupos vacíos sin concesiones');
 await reload(first);await openGroups(first);await saved(first,unicodeName);
 const second=await session();await second.field('select','en');await openGroups(second);await saved(second,'Kunden München 東京','customerGroup');
 assert.deepEqual(await second.evaluate(`Promise.all(['user-groups','customer-groups'].map(p=>fetch('/api/v1/admin/'+p).then(r=>r.json())))`),before);
 checks.push('Recarga y otra sesión administrativa leen los mismos grupos persistidos');

 // Confirmed commit, but the browser never receives its response.
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/customer-groups',requestStage:'Response'}]});
 await submit(first,'Lost group response','customerGroup');const committed=await poll(()=>first.paused,'group response intercepted');assert.equal(committed.responseStatusCode,201);
 const original=await journal();assert.equal(original.length,1);assert.equal(Object.keys(original[0]).sort().join(),'actorId,kind,name,requestId,revision');assert.equal(original[0].kind,'customerGroup');
 await first.send('Fetch.failRequest',{requestId:committed.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('.rc-group-creation [role=alert]')`,'lost response pending');
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:300,y:120,button:'left',clickCount:1});
 await reload(first);await openGroups(first);assert.deepEqual(await journal(),original);
 assert.equal(await first.evaluate(`document.querySelector('select[name=groupKind]').value`),'customerGroup');assert.equal(await first.evaluate(`document.querySelector('input[name=groupName]').disabled`),true);
 await first.click('[data-check-group]');await saved(first,'Lost group response','customerGroup');assert.deepEqual(await journal(),[]);
 const after=await first.evaluate(`fetch('/api/v1/admin/customer-groups').then(r=>r.json())`);assert.equal(after.groups.filter(g=>g.name==='Lost group response').length,1);assert.equal(after.revision,before[1].revision+1);
 checks.push('Respuesta perdida tras commit: journal restaurado con tipo/actor/UUID/nombre/revisión y consulta confirma un único grupo');

 // Unsent intention, then another session advances the revision. No automatic rebasing.
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/user-groups',requestStage:'Request'}]});
 await submit(first,'Unsent old group');const unsent=await poll(()=>first.paused,'unsent group intercepted');
 await first.send('Fetch.failRequest',{requestId:unsent.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('.rc-group-creation [role=alert]')`,'unsent pending');const stale=await journal();assert.equal(stale.length,1);
 await second.button('Refresh groups');await second.wait(`!document.querySelector('[data-create-group] button[type=submit]').disabled`,'second fresh revision');
 await submit(second,'Another session group');await saved(second,'Another session group');
 await first.click('[data-check-group]');await first.wait(`document.querySelector('[data-group-result]')?.textContent.includes('No result is recorded yet')`,'absence is not cancellation');assert.deepEqual(await journal(),stale);
 await first.evaluate(`document.querySelector('[data-create-group]').requestSubmit()`);
 await first.wait(`document.querySelector('.rc-group-creation [role=alert]')?.textContent.includes('revision changed')`,'412 keeps original intention');assert.deepEqual(await journal(),stale);
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/user-groups/operations/*/cancel',requestStage:'Response'}]});
 await first.click('[data-cancel-group]');const cancelled=await poll(()=>first.paused,'cancellation intercepted');assert.equal(cancelled.responseStatusCode,200);
 await first.send('Fetch.failRequest',{requestId:cancelled.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('.rc-group-creation [role=alert]')`,'lost cancellation');assert.deepEqual(await journal(),stale);
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:300,y:120,button:'left',clickCount:1});
 await reload(first);await openGroups(first);await first.click('[data-check-group]');
 await first.wait(`!document.querySelector('[data-pending-group]')&&document.querySelector('[data-group-result]')?.textContent.includes('Cancellation confirmed')`,'authoritative cancellation');assert.deepEqual(await journal(),[]);
 const terminal=await first.evaluate(`fetch('/api/v1/admin/user-groups').then(r=>r.json())`);assert.equal(terminal.groups.some(g=>g.name==='Unsent old group'),false);
 await first.wait(`!document.querySelector('[data-create-group] button[type=submit]').disabled`,'revision after cancellation');
 await submit(first,'Unsent old group');await saved(first,'Unsent old group');
 checks.push('notRecorded y412 conservan intención; cancelación perdida se recupera tras recarga, sin grupo fantasma, y una nueva alta funciona');

 // Another tab's intention must not be overwritten or sent from this stale form.
 const other={...stale[0],requestId:crypto.randomUUID(),name:'Other tab intention',kind:'customerGroup'};
 await first.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminGroups.v1',1);r.onsuccess=()=>{const db=r.result,tx=db.transaction('pending','readwrite');tx.objectStore('pending').put(${JSON.stringify(other)});tx.oncomplete=()=>{db.close();resolve(true)};tx.onerror=()=>reject(Error('storage'))}})`);
 const postCount=responses.filter(r=>r.path==='/api/v1/admin/user-groups'&&r.status===201).length;
 await submit(first,'Must not send');await first.wait(`document.querySelector('.rc-group-creation [role=alert]')?.textContent.includes('journal is unavailable')`,'journal conflict blocks POST');
 assert.deepEqual(await journal(),[other]);assert.equal(responses.filter(r=>r.path==='/api/v1/admin/user-groups'&&r.status===201).length,postCount);
 await first.click('[data-admin-groups]');await first.click('[data-admin-groups]');
 await first.wait(`!!document.querySelector('[data-pending-group]')&&!document.querySelector('[data-check-group]').disabled`,'other tab intention recovered');
 assert.equal(await first.evaluate(`document.querySelector('input[name=groupName]').value`),other.name);await first.click('[data-cancel-group]');
 await first.wait(`!document.querySelector('[data-pending-group]')&&!document.querySelector('[data-create-group] button[type=submit]').disabled`,'other intention cancelled');assert.deepEqual(await journal(),[]);
 checks.push('Conflicto de journal conserva la intención de otra pestaña y bloquea el envío; reapertura permite cancelarla');
 await submit(first,'🚀'.repeat(101));await first.wait(`document.querySelector('.rc-group-creation [role=alert]')?.textContent.includes('1–100')`,'Unicode limit explained');
 assert.equal((await journal()).length,1);await first.click('[data-cancel-group]');await first.wait(`!document.querySelector('[data-pending-group]')`,'invalid name cancelled');
 checks.push('101 escalares rechazados por servidor, mensaje visible y cancelación confirmada libera la intención inválida');
 await first.wait(`!document.querySelector('[data-create-group] button[type=submit]').disabled`,'invalid cancellation refreshed');
 for(const [name,expected] of [['\u0085NEL group\u0085','NEL group'],['\ufeffBOM group\ufeff','\ufeffBOM group\ufeff']]) {
  await submit(first,name);await saved(first,expected);assert.deepEqual(await journal(),[]);
 }
 checks.push('GUI/PostgreSQL confirma NEL recortado y BOM conservado según .NET, sin journal bloqueado');
 await first.evaluate(`document.querySelector('.rc-group-creation').scrollIntoView({block:'start'})`);
 await writeFile(path.join(evidence,'groups-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const materialErrors=errors.filter(e=>!/^\/api\/v1\/me: .*status of 401 \(|^\/favicon\.ico: .*status of 404 \(/.test(e)&&!(e.startsWith('/api/v1/admin/')&&(/status of (412|422) \(/.test(e)||e.includes('net::ERR_FAILED'))));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)).map(r=>r.status),[412,422]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,checks,browserErrors:materialErrors,limitations:['Grupos vacíos; sin asignaciones ni edición.','Recarga de documento, no reinicio Windows. Conflicto de journal sembrado, no carrera real de dos pestañas.','No se ensayan todos los fallos IndexedDB ni todos los cambios de sesión.']};
 await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch(error) {
 let visibleText='';if(lastTab){try{visibleText=(await lastTab.evaluate(`document.body.innerText`)).replaceAll(password,'[redacted]').replaceAll(username,'[synthetic user]');await writeFile(path.join(evidence,'browser-failure.png'),Buffer.from((await lastTab.send('Page.captureScreenshot',{format:'png'})).data,'base64'))}catch{}}
 await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({run,status:'failed',checks,error:error.message,browserErrors:errors,responses,visibleText},null,2));throw error;
} finally {
 if(browser){try{await browser.send('Browser.close')}catch{}}
 for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();
}
