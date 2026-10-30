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
 async function session(user = username, secret = password) {
  const context = await browser.send('Target.createBrowserContext');
  const target = await browser.send('Target.createTarget', { url: 'about:blank', browserContextId: context.browserContextId });
  const info = await poll(async () => (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.id === target.targetId), 'session target');
  const tab = await CDP.open(info.webSocketDebuggerUrl); lastTab = tab; await tab.send('Runtime.enable'); await tab.send('Log.enable'); await tab.send('Network.enable'); await tab.send('Page.enable'); await tab.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await tab.send('Page.navigate',{url:origin});
  await tab.wait(`!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled`, 'login screen');
  await tab.field('select', 'es'); await tab.field('input[name=username]', user); await tab.field('input[name=password]', secret); await tab.evaluate(`document.querySelector('form').requestSubmit()`);
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
 async function openUsers(tab){await tab.wait(`!!document.querySelector('[data-admin-users]')`,'admin link');await tab.click('[data-admin-users]');await tab.wait(`!!document.querySelector('[data-reset-password]')&&(!document.querySelector('select[name=passwordUser]').disabled||!!document.querySelector('[data-pending-password]'))`,'password form ready')}
 const first=await session();await first.field('select','en');await openUsers(first);
 const second=await session('second-admin');await second.field('select','en');await openUsers(second);
 const target=process.env.RACKCLICK_FIXTURE_TARGET,admin=process.env.RACKCLICK_FIXTURE_ADMIN,newPassword=process.env.RACKCLICK_NEW_PASSWORD;
 if(!newPassword)throw Error('Locally supplied new password required');
 const reader=await session('password-reader'),reader2=await session('password-reader');
 const journal=tab=>tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminUserPassword.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
 async function refresh(tab){await tab.click('[data-refresh-password]');await tab.wait(`!document.querySelector('select[name=passwordUser]').disabled`,'accounts ready')}
 async function submit(tab,id,secret){await tab.field('select[name=passwordUser]',id);await tab.field('input[name=resetPassword]',secret);await tab.evaluate(`document.querySelector('[data-reset-password]').requestSubmit()`)}
 async function saved(tab){await tab.wait(`!document.querySelector('[data-pending-password]')&&document.querySelector('[data-password-result]')?.textContent.includes('confirmed by the server')`,'reset confirmed')}
 const me=tab=>tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`);
 async function pause(tab,id,stage){tab.paused=null;await tab.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users/'+id+'/password',requestStage:stage}]})}
 async function lose(tab){const req=await poll(()=>tab.paused,'password request');await tab.send('Fetch.failRequest',{requestId:req.requestId,errorReason:'Failed'});await tab.send('Fetch.disable');await tab.wait(`!!document.querySelector('.rc-admin-password [role=alert]')`,'unconfirmed reset');return req}
 // 1: committed reset, two old sessions revoked, new login and another administrator read.
 await submit(first,target,newPassword);await saved(first);assert.equal(await me(reader),401);assert.equal(await me(reader2),401);
 assert.equal(await reader.evaluate(`fetch('/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'password-reader',password:${JSON.stringify(password)}})}).then(r=>r.status)`),401);
 const fresh=await session('password-reader',newPassword);assert.equal(await me(fresh),200);
 assert.equal(await second.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json()).then(x=>x.users.find(u=>u.id==='${target}').active)`),true);
 assert.equal(await first.evaluate(`document.querySelector('input[name=resetPassword]').value`),'');
 checks.push('GUI reset confirmado, dos sesiones antiguas revocadas, login antiguo rechazado/nuevo correcto; otra sesión lee cuenta activa; campo secreto limpio');
 // 2: drop a committed response, reload public journal, query original once without revoking a new session.
 await refresh(first);await pause(first,target,'Response');await submit(first,target,password);const lost=await poll(()=>first.paused,'committed reset');assert.equal(lost.responseStatusCode,200);const original=await journal(first);assert.equal(Object.keys(original[0]).sort().join(),'actorId,requestId,revision,userId');await lose(first);
 const after=await session('password-reader',password);await reload(first);await openUsers(first);assert.deepEqual(await journal(first),original);assert.equal(await first.evaluate(`document.querySelector('input[name=resetPassword]').value`),'');await first.click('[data-check-password]');await saved(first);assert.deepEqual(await journal(first),[]);assert.equal(await me(after),200);
 checks.push('Respuesta perdida/recarga: journal exacto sin secreto, GET committed elimina intención sin repetir reset ni revocar sesión nueva');
 // 3: own reset requires acknowledgement; lost response needs NEW login same actor before GET recovery.
 await refresh(first);await first.field('select[name=passwordUser]',admin);await first.field('input[name=resetPassword]',newPassword);assert.equal(await first.evaluate(`!!document.querySelector('[data-own-password-warning]')&&document.querySelector('[data-reset-password] button[type=submit]').disabled`),true);await first.click('input[name=passwordSelfConfirm]');await pause(first,admin,'Response');await first.evaluate(`document.querySelector('[data-reset-password]').requestSubmit()`);const selflost=await poll(()=>first.paused,'self commit');assert.equal(selflost.responseStatusCode,200);const ownOriginal=await journal(first);await lose(first);await first.click('[data-check-password]');await first.wait(`!!document.querySelector('[data-password-login]')`,'new login required');assert.equal(await me(first),401);assert.deepEqual(await journal(first),ownOriginal);
 await first.field('input[name=resetLoginPassword]',newPassword);await first.evaluate(`document.querySelector('[data-password-login]').requestSubmit()`);await first.wait(`!document.querySelector('[data-password-login]')&&!document.querySelector('[data-check-password]').disabled`,'new login same actor');assert.equal(await me(first),200);assert.deepEqual(await journal(first),ownOriginal);assert.equal(await first.evaluate(`document.querySelector('input[name=resetPassword]').value`),'');await first.click('[data-check-password]');await saved(first);assert.equal(await me(first),200);
 checks.push('Reset propio: aviso/checkbox; respuesta perdida y401 no confirman; login NUEVO mismo actor + GET confirma sin revocar sesión nueva');
 // 4: unsent intent => notRecorded stays pending; stale revision never rewrites metadata; cancel fences tardy POST.
 await refresh(first);await pause(first,target,'Request');await submit(first,target,newPassword);await lose(first);const stale=(await journal(first))[0];await refresh(second);await submit(second,target,password);await saved(second);await first.click('[data-check-password]');await first.wait(`document.querySelector('[data-password-result]')?.textContent.includes('No result is recorded')`,'notRecorded');assert.deepEqual(await journal(first),[stale]);await first.field('input[name=resetPassword]',newPassword);await first.evaluate(`document.querySelector('[data-reset-password]').requestSubmit()`);await first.wait(`document.querySelector('.rc-admin-password [role=alert]')?.textContent.includes('conflicts')`,'stale revision');assert.deepEqual(await journal(first),[stale]);await first.click('[data-cancel-password]');await first.wait(`!document.querySelector('[data-pending-password]')&&document.querySelector('[data-password-result]')?.textContent.includes('Cancellation confirmed')`,'cancel confirmed');
 const tardy=await first.evaluate(`(async()=>{const identity=await fetch('/api/v1/me').then(r=>r.json());const r=await fetch('/api/v1/admin/users/${target}/password',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':identity.csrf,'X-RackClick-Actor':${JSON.stringify(stale.actorId)},'Idempotency-Key':${JSON.stringify(stale.requestId)},'If-Match':${JSON.stringify('"'+stale.revision+'"')}},body:JSON.stringify({password:${JSON.stringify(newPassword)}})});return {status:r.status,error:(await r.json()).error}})()`);assert.deepEqual(tardy,{status:409,error:'operation_cancelled'});
 checks.push('notRecorded/412 conservan IDs/revisión; cancel{} confirmado y POST tardío409 cercado');
 // 5: real reader has no admin link and server rejects read/reset/cancel. Journal cross actor preserved.
 const deniedReader=await session('password-reader',password);
 assert.equal(await deniedReader.evaluate(`!!document.querySelector('[data-admin-users]')`),false);
 const denied=await deniedReader.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json());const headers={'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':me.user.id,'If-Match':'"1"','Idempotency-Key':crypto.randomUUID()};const read=await fetch('/api/v1/admin/users');const reset=await fetch('/api/v1/admin/users/${target}/password',{method:'POST',headers,body:JSON.stringify({password:${JSON.stringify(newPassword)}})});const cancel=await fetch('/api/v1/admin/users/${target}/password/operations/'+headers['Idempotency-Key']+'/cancel',{method:'POST',headers,body:'{}'});return [read.status,reset.status,cancel.status]})()`);assert.deepEqual(denied,[403,403,403]);
 const foreign=await first.evaluate(`(async()=>{const db=await new Promise(resolve=>{const r=indexedDB.open('RackClick.AdminUserPassword.v1',1);r.onsuccess=()=>resolve(r.result)});const foreign={actorId:crypto.randomUUID(),requestId:crypto.randomUUID(),userId:crypto.randomUUID(),revision:1};await new Promise(resolve=>{const tx=db.transaction('pending','readwrite');tx.objectStore('pending').put(foreign);tx.oncomplete=resolve});db.close();return foreign})()`);await refresh(first);await submit(first,target,password);await saved(first);assert.deepEqual(await journal(first),[foreign]);
 checks.push('Lector real: sin botón administrativo y403 servidor en lectura/reset/cancel; confirmación preserva journal de otro actor');
 await first.button('Back to clients');await first.wait(`!!document.querySelector('.rc-settings select')`,'language settings');await first.field('.rc-settings select','es');await openUsers(first);await first.evaluate(`document.querySelector('.rc-admin-password').scrollIntoView({block:'start'})`);await writeFile(path.join(evidence,'password-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const materialErrors=errors.filter(e=>!e.includes('status of 401')&&!/^\/favicon/.test(e)&&!((e.startsWith('/api/v1/admin/')||e.startsWith('/api/v1/auth/'))&&(/status of (412|409|403|404) \(/.test(e)||e.includes('net::ERR_FAILED'))));assert.deepEqual(materialErrors,[]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,checks,browserErrors:materialErrors,limitations:['No reinicio Windows ni matriz exhaustiva de fallos IndexedDB; EN recorrido y textos DE/ES sin aceptación visual completa.','Sólo fixture sintético nuevo; ningún laboratorio ni credencial de Wascar actualizado.']};await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch(error) {await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({run,status:'failed',checks,error:error.message,browserErrors:errors,responses,alerts:lastTab?await lastTab.evaluate(`[...document.querySelectorAll('[role=alert]')].map(x=>x.textContent)`).catch(()=>null):null},null,2));throw error;
} finally {if(browser){try{await browser.send('Browser.close')}catch{}}for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();}
