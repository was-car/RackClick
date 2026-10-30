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
 const second=await session();await second.field('select','en');await openGroups(second);
 const groups=await first.evaluate(`fetch('/api/v1/admin/user-groups').then(r=>r.json())`);
 const adminGroup=groups.groups[0].id;
 const actor=groups.groups[0].members[0].id;
 // Create a second account from the existing API, without adding implicit privileges.
 const userName='member-test';
 const created=await first.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json());const r=await fetch('/api/v1/admin/users',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':${JSON.stringify(actor)},'If-Match':'"'+${groups.revision}+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({username:${JSON.stringify(userName)},password:${JSON.stringify(password)}})});return {status:r.status,data:await r.json()}})()`);
 assert.equal(created.status,201);const user=created.data.resource.id;
 async function refresh(tab){await tab.button('Refresh groups');await tab.wait(`!!document.querySelector('select[name=memberUser] option[value="${user}"]')`,'member targets');}
 async function submit(tab,assigned=true,target=user){await tab.field('select[name=memberGroup]',adminGroup);await tab.field('select[name=memberUser]',target);await tab.field('select[name=memberAction]',assigned?'add':'remove');await tab.evaluate(`document.querySelector('[data-assign-member]').requestSubmit()`);}
 async function saved(tab){await tab.wait(`!document.querySelector('[data-pending-member]')&&document.querySelector('[data-member-result]')?.textContent.includes('Assignment confirmed')`,'assignment confirmed');await tab.wait(`!document.querySelector('select[name=memberGroup]').disabled`,'target reload');}
 const journal=()=>first.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminGroupMembers.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
 await refresh(first);await submit(first,true);await saved(first);
 await refresh(second);assert.equal(await second.evaluate(`document.querySelector('[data-user-group-id="${adminGroup}"]').innerText.includes('member-test')`),true);
 await submit(second,false);await saved(second);await reload(first);await openGroups(first);
 assert.equal(await first.evaluate(`document.querySelector('[data-user-group-id="${adminGroup}"]').innerText.includes('member-test')`),false);
 checks.push('Añadir y retirar por GUI; IDs y membresía persistidos tras recarga y leídos desde otra sesión');
 // Lose a response after commit and recover the exact intention from IndexedDB.
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/user-groups/'+adminGroup+'/members',requestStage:'Response'}]});
 await submit(first,true);const response=await poll(()=>first.paused,'committed assignment');assert.equal(response.responseStatusCode,200);
 const original=await journal();assert.equal(original.length,1);assert.equal(Object.keys(original[0]).sort().join(),'actorId,assigned,groupId,requestId,revision,userId');
 await first.send('Fetch.failRequest',{requestId:response.requestId,errorReason:'Failed'});await first.send('Fetch.disable');await first.wait(`!!document.querySelector('.rc-group-members [role=alert]')`,'lost response');
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:300,y:120,button:'left',clickCount:1});
 await reload(first);await openGroups(first);assert.deepEqual(await journal(),original);assert.equal(await first.evaluate(`document.querySelector('select[name=memberAction]').disabled`),true);
 await first.click('[data-check-member]');await saved(first);assert.deepEqual(await journal(),[]);
 const restored=await first.evaluate(`fetch('/api/v1/admin/user-groups').then(r=>r.json())`);assert.equal(restored.revision,original[0].revision+1);
 checks.push('Respuesta perdida tras commit y recarga conserva IDs/acción/actor/clave/revisión; consulta confirma sin duplicar');
 // Unsent removal, advance revision from other session, then verify 412 and authoritative cancellation.
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/user-groups/'+adminGroup+'/members',requestStage:'Request'}]});
 await submit(first,false);const unsent=await poll(()=>first.paused,'unsent assignment');await first.send('Fetch.failRequest',{requestId:unsent.requestId,errorReason:'Failed'});await first.send('Fetch.disable');await first.wait(`!!document.querySelector('.rc-group-members [role=alert]')`,'pending original');const stale=(await journal())[0];
 await refresh(second);await submit(second,true);await saved(second);
 await first.click('[data-check-member]');await first.wait(`document.querySelector('[data-member-result]')?.textContent.includes('No result is recorded')`,'notRecorded');assert.deepEqual(await journal(),[stale]);
 await first.evaluate(`document.querySelector('[data-assign-member]').requestSubmit()`);await first.wait(`document.querySelector('.rc-group-members [role=alert]')?.textContent.includes('revision changed')`,'412');assert.deepEqual(await journal(),[stale]);
 await first.click('[data-cancel-member]');await first.wait(`!document.querySelector('[data-pending-member]')&&document.querySelector('[data-member-result]')?.textContent.includes('Cancellation confirmed')`,'cancelled');assert.deepEqual(await journal(),[]);
 checks.push('notRecorded y412 conservan intención sin rebase; cancelar confirma y libera journal sin retirar al usuario');
 const late=await first.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json());const r=await fetch('/api/v1/admin/user-groups/${adminGroup}/members',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':${JSON.stringify(actor)},'If-Match':'"${stale.revision}"','Idempotency-Key':${JSON.stringify(stale.requestId)}},body:JSON.stringify({userId:${JSON.stringify(user)},assigned:false})});return{status:r.status,data:await r.json()}})()`);
 assert.equal(late.status,409);assert.equal(late.data.error,'operation_cancelled');checks.push('Reintento tardío con clave cancelada rechazado por servidor');
 // Remove second administrator, then protect the last active global administrator.
 await first.wait(`!document.querySelector('select[name=memberGroup]').disabled`,'post cancellation reload');await submit(first,false);await saved(first);
 await submit(first,false,actor);await first.wait(`document.querySelector('.rc-group-members [role=alert]')?.textContent.includes('last active administrator')`,'last administrator');assert.equal((await journal()).length,1);await first.click('[data-cancel-member]');await first.wait(`!document.querySelector('[data-pending-member]')`,'blocked request cancelled');
 checks.push('Último administrador protegido; error claro y cancelación no cambia membresías');
 const restricted=await session(userName);assert.equal(await restricted.evaluate(`!!document.querySelector('[data-admin-users]')||!!document.querySelector('[data-assign-member]')`),false);
 const denied=await restricted.evaluate(`fetch('/api/v1/admin/user-groups').then(r=>r.status)`);assert.equal(denied,403);checks.push('Usuario sin security.manage no ve administración y GET administrativo denegado en servidor');
 await first.evaluate(`document.querySelector('.rc-group-members').scrollIntoView({block:'start'})`);
 await writeFile(path.join(evidence,'members-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const materialErrors=errors.filter(e=>!/^\/api\/v1\/me: .*status of 401 \(|^\/favicon\.ico: .*status of 404 \(/.test(e)&&!(e.startsWith('/api/v1/admin/')&&(/status of (412|409|403) \(/.test(e)||e.includes('net::ERR_FAILED'))));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)).map(r=>r.status),[412,409,409,403]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,checks,browserErrors:materialErrors,limitations:['No se ejecutan todos los fallos IndexedDB ni cambios de actor en navegador; adaptador sí rechaza cambios de actor.','Recarga de documento, no reinicio Windows. Sin matriz de permisos efectivos.']};
 await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch(error) {
 await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({run,status:'failed',checks,error:error.message,browserErrors:errors,responses,diagnostic:lastTab?await lastTab.evaluate(`(async()=>({alerts:[...document.querySelectorAll('[role=alert]')].map(x=>x.textContent),targets:await Promise.all(['/api/v1/admin/users','/api/v1/admin/user-groups','/api/v1/admin/customer-groups'].map(async p=>{const r=await fetch(p);return {status:r.status,etag:r.headers.get('ETag'),body:await r.json()}}))}))()`).catch(()=>null):null},null,2));throw error;
} finally {
 if(browser){try{await browser.send('Browser.close')}catch{}}
 for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();
}
