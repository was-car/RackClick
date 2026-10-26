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
  for(const type of ['mousePressed','mouseReleased'])await tab.send('Input.dispatchMouseEvent',{type,x:300,y:120,button:'left',clickCount:1});
  let loaded=false;
  const listener=e=>{if(JSON.parse(e.data).method==='Page.loadEventFired')loaded=true};
  tab.ws.addEventListener('message',listener);
  try {await tab.send('Page.reload');await poll(()=>loaded,'new document loaded');}
  finally {tab.ws.removeEventListener('message',listener);}
 }
 async function openUsers(tab){await tab.wait(`!!document.querySelector('[data-admin-users]')`,'admin link');await tab.click('[data-admin-users]');await tab.wait(`!!document.querySelector('[data-set-state]')&&(!document.querySelector('select[name=stateUser]').disabled||!!document.querySelector('[data-pending-state]'))`,'state form ready')}
 const first=await session();await first.field('select','en');await openUsers(first);
 const second=await session('second-admin');await second.field('select','en');await openUsers(second);
 const target=process.env.RACKCLICK_FIXTURE_TARGET,admin=process.env.RACKCLICK_FIXTURE_ADMIN;
 const reader=await session('state-reader'),reader2=await session('state-reader');
 const journal=tab=>tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminUserState.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
 async function refresh(tab){await tab.click('[data-refresh-state]');await tab.wait(`!document.querySelector('select[name=stateUser]').disabled`,'accounts ready')}
 async function submit(tab,id,active){await tab.field('select[name=stateUser]',id);await tab.field('select[name=stateActive]',String(active));await tab.evaluate(`document.querySelector('[data-set-state]').requestSubmit()`)}
 async function saved(tab){await tab.wait(`!document.querySelector('[data-pending-state]')&&document.querySelector('[data-state-result]')?.textContent.includes('confirmed by the server')`,'state confirmed')}
 const me=tab=>tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`);
 const state=tab=>tab.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json()).then(x=>x.users.find(u=>u.id==='${target}').active)`);
 await submit(first,target,false);await saved(first);assert.equal(await me(reader),401);assert.equal(await me(reader2),401);assert.equal(await state(second),false);
 assert.equal(await reader.evaluate(`fetch('/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'state-reader',password:${JSON.stringify(password)}})}).then(r=>r.status)`),401);
 await refresh(second);await submit(second,target,true);await saved(second);assert.equal(await me(reader),401);const fresh=await session('state-reader');assert.equal(await me(fresh),200);
 await reload(first);await openUsers(first);assert.equal(await state(first),true);checks.push('Desactivar GUI revoca dos sesiones y login; reactivar permite NUEVA sesión sin restituir viejas, recarga/otra sesión leen estado');
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users/'+target+'/state',requestStage:'Response'}]});await submit(first,target,false);const lost=await poll(()=>first.paused,'committed state');assert.equal(lost.responseStatusCode,200);const original=await journal(first);assert.equal(Object.keys(original[0]).sort().join(),'active,actorId,requestId,revision,userId');await first.send('Fetch.failRequest',{requestId:lost.requestId,errorReason:'Failed'});await first.send('Fetch.disable');await first.wait(`!!document.querySelector('.rc-admin-state [role=alert]')`,'lost response');await reload(first);await openUsers(first);assert.deepEqual(await journal(first),original);await first.click('[data-check-state]');await saved(first);assert.deepEqual(await journal(first),[]);checks.push('Respuesta perdida tras commit/recarga: journal exacto y consulta confirman una sola intención');
 first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users/'+target+'/state',requestStage:'Request'}]});await submit(first,target,true);const unsent=await poll(()=>first.paused,'unsent state');await first.send('Fetch.failRequest',{requestId:unsent.requestId,errorReason:'Failed'});await first.send('Fetch.disable');await first.wait(`!!document.querySelector('.rc-admin-state [role=alert]')`,'unsent pending');const stale=(await journal(first))[0];await refresh(second);await submit(second,target,false);await saved(second);await first.click('[data-check-state]');await first.wait(`document.querySelector('[data-state-result]')?.textContent.includes('No result is recorded')`,'notRecorded');assert.deepEqual(await journal(first),[stale]);await first.evaluate(`document.querySelector('[data-set-state]').requestSubmit()`);await first.wait(`document.querySelector('.rc-admin-state [role=alert]')?.textContent.includes('Revision changed')`,'stale conflict');assert.deepEqual(await journal(first),[stale]);await first.click('[data-cancel-state]');await first.wait(`!document.querySelector('[data-pending-state]')&&document.querySelector('[data-state-result]')?.textContent.includes('Cancellation confirmed')`,'cancel confirmed');checks.push('notRecorded y 412 conservan ID/cuerpo/revisión; cancelación confirmada elimina solo journal propio');
 // Own deactivation after a lost response, restored by another administrator.
 await refresh(first);await first.field('select[name=stateUser]',admin);await first.field('select[name=stateActive]','false');assert.equal(await first.evaluate(`!!document.querySelector('[data-own-state-warning]')&&document.querySelector('[data-set-state] button[type=submit]').disabled`),true);
 await first.click('input[name=stateSelfConfirm]');first.paused=null;await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users/'+admin+'/state',requestStage:'Response'}]});await first.evaluate(`document.querySelector('[data-set-state]').requestSubmit()`);const ownlost=await poll(()=>first.paused,'self committed');assert.equal(ownlost.responseStatusCode,200);const ownOriginal=await journal(first);await first.send('Fetch.failRequest',{requestId:ownlost.requestId,errorReason:'Failed'});await first.send('Fetch.disable');await first.click('[data-check-state]');await first.wait(`!!document.querySelector('[data-state-login]')`,'reauth original actor');assert.equal(await me(first),401);assert.deepEqual(await journal(first),ownOriginal);
 await refresh(second);await submit(second,admin,true);await saved(second);assert.equal(await me(first),401);await first.field('input[name=statePassword]',password);await first.evaluate(`document.querySelector('[data-state-login]').requestSubmit()`);await first.wait(`!document.querySelector('[data-state-login]')&&!document.querySelector('[data-check-state]').disabled`,'new session original actor');assert.equal(await me(first),200);assert.deepEqual(await journal(first),ownOriginal);await first.click('[data-check-state]');await saved(first);assert.equal(await me(first),200);assert.deepEqual(await journal(first),[]);assert.equal(await first.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json()).then(x=>x.users.find(u=>u.id==='${admin}').active)`),true);
 checks.push('Autodesactivación requiere aviso/checkbox; respuesta perdida revoca sesión; otro admin reactiva, login NUEVO mismo actor recupera committed sin redesactivar ni revocar sesión nueva');
 // Journal isolation: invalid data or a changed intention cannot silently replace a sibling journal.
 const journalGuard=await first.evaluate(`(async()=>{const db=await new Promise(resolve=>{const r=indexedDB.open('RackClick.AdminUserState.v1',1);r.onsuccess=()=>resolve(r.result)});const foreign={actorId:crypto.randomUUID(),requestId:crypto.randomUUID(),userId:crypto.randomUUID(),active:true,revision:1};await new Promise(resolve=>{const tx=db.transaction('pending','readwrite');tx.objectStore('pending').put(foreign);tx.oncomplete=resolve});db.close();return foreign})()`);
 await submit(first,target,true);await saved(first);assert.deepEqual(await journal(first),[journalGuard]);checks.push('Confirmación elimina únicamente registro exacto del actor; journal de otro actor permanece');
 await first.button('Back to clients');await first.wait(`!!document.querySelector('.rc-settings select')`,'language settings');await first.field('.rc-settings select','es');await openUsers(first);
 await first.evaluate(`document.querySelector('.rc-admin-state').scrollIntoView({block:'start'})`);await writeFile(path.join(evidence,'state-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const materialErrors=errors.filter(e=>!e.includes('status of 401')&&!/^\/favicon/.test(e)&&!((e.startsWith('/api/v1/admin/')||e.startsWith('/api/v1/auth/'))&&(/status of (412|409|403|404) \(/.test(e)||e.includes('net::ERR_FAILED'))));assert.deepEqual(materialErrors,[]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,checks,browserErrors:materialErrors,limitations:['No reinicio Windows ni matriz exhaustiva IndexedDB; EN recorrido y textos DE/ES presentes sin aceptación visual completa.','Fixture state-reader usa permiso administrativo para entrada GUI; prueba de lector sin permiso queda API20/QA manual.']};await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch(error) {await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({run,status:'failed',checks,error:error.message,browserErrors:errors,responses,alerts:lastTab?await lastTab.evaluate(`[...document.querySelectorAll('[role=alert]')].map(x=>x.textContent)`).catch(()=>null):null},null,2));throw error;
} finally {if(browser){try{await browser.send('Browser.close')}catch{}}for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();}
