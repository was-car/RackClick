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
 const first=await session();await first.field('select','en');await first.click('[data-admin-users]');
 await first.wait(`!!document.querySelector('input[name=newUsername]')&&!document.querySelector('.rc-admin-users button[type=submit]').disabled`,'administration ready');
 const name='Admin Test München 東京';
 await first.field('input[name=newUsername]',name);await first.field('input[name=newPassword]',password);
 await first.evaluate(`document.querySelector('.rc-admin-users form').requestSubmit()`);
 await first.wait(`[...document.querySelectorAll('[data-user-id] h2')].some(x=>x.textContent===${JSON.stringify(name.toLowerCase())})&&!document.querySelector('.rc-admin-users .ir-warning')`,'user confirmed');
 assert.equal(await first.evaluate(`document.querySelector('input[name=newPassword]').value`),'');
 const listing=await first.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json())`);assert.equal(listing.users.length,2);
 assert.ok(listing.users.every(u=>Object.keys(u).sort().join() === 'active,id,userName'));
 checks.push('Alta Unicode desde GUI confirmada, contraseña retirada del formulario y listado sin secretos');
 await reload(first);await first.wait(`!!document.querySelector('[data-admin-users]')`,'reload');await first.click('[data-admin-users]');
 await first.wait(`document.querySelectorAll('[data-user-id]').length===2`,'persisted users');
 const second=await session();await second.field('select','en');await second.click('[data-admin-users]');await second.wait(`document.querySelectorAll('[data-user-id]').length===2`,'second admin session');
 assert.deepEqual(await second.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json())`),listing);
 checks.push('Recarga y otra sesión administrativa leen la misma cuenta persistida');
 const unprivileged=await session(name);assert.equal(await unprivileged.evaluate(`!!document.querySelector('[data-admin-users]')`),false);
 assert.equal(await unprivileged.evaluate(`fetch('/api/v1/admin/users').then(r=>r.status)`),403);
 assert.deepEqual(await unprivileged.evaluate(`fetch('/api/v1/customers').then(r=>r.json())`),[]);
 checks.push('Cuenta nueva inicia sesión y carece de permisos de clientes y administración; GET directo devuelve403');

 lastTab=first;
 const recoveredName='Lost response account';await first.field('input[name=newUsername]',recoveredName);await first.field('input[name=newPassword]',password);
 await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users',requestStage:'Response'}]});
 await first.evaluate(`document.querySelector('.rc-admin-users form').requestSubmit()`);
 const paused=await poll(()=>first.paused,'creation response intercepted');assert.equal(paused.responseStatusCode,201);
 const journal=()=>first.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminUsers.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
 const records=await journal();assert.equal(records.length,1);assert.equal(Object.keys(records[0]).sort().join(),'actorId,requestId,revision,username');assert.ok(!JSON.stringify(records).includes(password));
 await first.send('Fetch.failRequest',{requestId:paused.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('.rc-admin-users [role=alert]')`,'uncertain create');
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:300,y:120,button:'left',clickCount:1});
 await reload(first);await first.wait(`!!document.querySelector('[data-admin-users]')`,'reload pending');await first.click('[data-admin-users]');
 await first.wait(`!!document.querySelector('.rc-admin-users .ir-warning')`,'restored metadata');assert.deepEqual(await journal(),records);
 assert.equal(await first.evaluate(`document.querySelector('input[name=newPassword]').value`),'');
 await first.button('Check original result');await first.wait(`!document.querySelector('.rc-admin-users .ir-warning')&&document.querySelectorAll('[data-user-id]').length===3`,'original commit recovered');
 assert.deepEqual(await journal(),[]);
 const final=await first.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json())`);assert.equal(final.revision,listing.revision+1);assert.equal(final.users.filter(u=>u.userName===recoveredName.toLowerCase()).length,1);
 checks.push('Respuesta perdida tras201: recarga recupera UUID sin contraseña local y consulta confirma el alta única');
 // Lose a creation before it reaches the server, then advance the house revision elsewhere.
 const staleName='Cancelled old intent'; first.paused=null;
 await first.field('input[name=newUsername]',staleName);await first.field('input[name=newPassword]',password);
 await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users',requestStage:'Request'}]});
 await first.evaluate(`document.querySelector('.rc-admin-users form').requestSubmit()`);
 const unsent=await poll(()=>first.paused,'unsent creation intercepted');
 await first.send('Fetch.failRequest',{requestId:unsent.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('.rc-admin-users [role=alert]')`,'unsent uncertain creation');
 const staleRecords=await journal();assert.equal(staleRecords.length,1);
 await second.button('Refresh');await second.wait(`document.querySelectorAll('[data-user-id]').length===3`,'second revision refreshed');
 await second.field('input[name=newUsername]','Revision advance');await second.field('input[name=newPassword]',password);
 await second.evaluate(`document.querySelector('.rc-admin-users form').requestSubmit()`);
 await second.wait(`document.querySelectorAll('[data-user-id]').length===4`,'another session advances revision');
 await first.button('Check original result');
 await first.wait(`document.querySelector('.rc-admin-users [role=status]').textContent.includes('No result is recorded yet')`,'notRecorded message visible');
 await first.evaluate(`document.querySelector('.rc-admin-users form').requestSubmit()`);
 await first.wait(`document.querySelector('.rc-admin-users [role=alert]')?.textContent.includes('revision changed')`,'stale original returns conflict');
 assert.deepEqual(await journal(),staleRecords);
 // Lose the cancellation response as well; only a later authoritative status may clear the journal.
 first.paused=null;
 await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/users/operations/*/cancel',requestStage:'Response'}]});
 await first.click('[data-cancel-user]');const canceled=await poll(()=>first.paused,'cancellation response intercepted');assert.equal(canceled.responseStatusCode,200);
 await first.send('Fetch.failRequest',{requestId:canceled.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('.rc-admin-users [role=alert]')`,'uncertain cancellation retains intent');
 assert.deepEqual(await journal(),staleRecords);
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:300,y:120,button:'left',clickCount:1});
 await reload(first);await first.wait(`!!document.querySelector('[data-admin-users]')`,'reload cancellation');await first.click('[data-admin-users]');
 await first.wait(`!!document.querySelector('[data-cancel-user]')`,'cancelled journal restored');await first.button('Check original result');
 await first.wait(`!document.querySelector('.rc-admin-users .ir-warning')&&document.querySelector('.rc-admin-users [role=status]').textContent.includes('Cancellation confirmed')`,'server cancellation recovered');
 assert.deepEqual(await journal(),[]);
 const afterCancel=await first.evaluate(`fetch('/api/v1/admin/users').then(r=>r.json())`);assert.equal(afterCancel.users.length,4);assert.equal(afterCancel.users.some(u=>u.userName===staleName.toLowerCase()),false);
 await first.field('input[name=newUsername]',staleName);await first.field('input[name=newPassword]',password);
 await first.evaluate(`document.querySelector('.rc-admin-users form').requestSubmit()`);
 await first.wait(`document.querySelectorAll('[data-user-id]').length===5&&!document.querySelector('.rc-admin-users .ir-warning')`,'new intent after cancellation succeeds');
 checks.push('Petición no enviada y revisión avanzada: notRecorded visible,412 conserva journal, cancelación perdida se recupera tras recarga y permite nueva alta');
 await first.click('.ir-crumb-home');await first.wait(`!document.querySelector('.rc-admin-users')`,'breadcrumb exits users');
 await first.click('[data-admin-users]');await first.wait(`document.querySelectorAll('[data-user-id]').length===5`,'users can be reopened');
 checks.push('Breadcrumb Infrastructure sale de Usuarios y permite regresar');
 await first.click('[data-admin-groups]');
 await first.wait(`!!document.querySelector('[data-user-group-id]')&&!document.querySelector('.rc-admin-groups [role=status]')`,'administrative groups loaded');
 const groupsText=await first.evaluate(`document.querySelector('.rc-admin-groups').innerText`);
 assert.ok(groupsText.includes('Systemhaus Administrators')&&groupsText.includes(username)&&groupsText.includes('Manage security')&&groupsText.includes('Entire Systemhaus'));
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-grant-id]').length`),8);
 assert.ok(!groupsText.includes(listing.users[0].id));
 assert.ok(groupsText.includes('Customer groups')&&groupsText.includes('No groups.'));
 await first.button('Refresh groups');await first.wait(`document.querySelectorAll('[data-grant-id]').length===8&&!document.querySelector('.rc-admin-groups [role=status]')`,'groups refresh');
 checks.push('Consulta GUI de grupo administrador, miembros,8 permisos globales, grupos de clientes vacíos y recarga sin UUID visibles');
 await writeFile(path.join(evidence,'users-windows.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const materialErrors=errors.filter(e=>!/^\/api\/v1\/me: .*status of 401 \(|^\/favicon\.ico: .*status of 404 \(/.test(e)&&!(e.startsWith('/api/v1/admin/users')&&(/status of (403|412) \(/.test(e)||e.includes('net::ERR_FAILED'))));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[{path:'/api/v1/admin/users',status:403},{path:'/api/v1/admin/users',status:412}]);
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,origin,checks,browserErrors:materialErrors,limitations:['Alta/listado/cancelación; grupos/reset/desactivación todavía pendientes.','Recarga de página, no reinicio Windows. No ensaya todos los fallos de IndexedDB ni todos los cambios de sesión.']};
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
