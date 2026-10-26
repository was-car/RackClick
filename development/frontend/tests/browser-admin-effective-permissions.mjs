// Windows Edge/CDP integration. No Playwright or additional npm dependency.
import { spawn } from 'node:child_process';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
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

 const fixture=JSON.parse(process.env.RACKCLICK_FIXTURE),ids=fixture.ids,names=fixture.names,caseId=process.env.RACKCLICK_CASE;
 const panel='[data-effective-permissions]',result='[data-effective-result]';
 async function users(tab){await tab.wait(`!!document.querySelector('[data-admin-users]')`,'admin navigation');await tab.click('[data-admin-users]');await tab.wait(`!!document.querySelector('${panel}')&&!document.querySelector('select[name=effectiveUser]').disabled`,'effective accounts ready')}
 async function refresh(tab){await tab.click('[data-refresh-effective]');await tab.wait(`!document.querySelector('select[name=effectiveUser]').disabled&&!document.querySelector('${panel} [role=status]')`,'fresh accounts')}
 async function query(tab,id=ids.target){await tab.field('select[name=effectiveUser]',id);await tab.click('[data-query-effective]');await tab.wait(`!!document.querySelector('${result}')`,'effective snapshot');return tab.evaluate(`document.querySelector('${result}').textContent`)}
 async function snapshot(tab,id=ids.target){return tab.evaluate(`fetch('/api/v1/admin/users/${id}/effective-permissions').then(async r=>({status:r.status,data:await r.json()}))`)}
 async function me(tab){return tab.evaluate(`fetch('/api/v1/me').then(async r=>({status:r.status,data:r.ok?await r.json():null}))`)}
 async function mutate(tab,url,body){return tab.evaluate(`(async()=>{const x=await fetch('/api/v1/me').then(r=>r.json()),s=await fetch('/api/v1/admin/users').then(r=>r.json());const r=await fetch(${JSON.stringify(url)},{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':x.csrf,'X-RackClick-Actor':x.user.id,'If-Match':'"'+s.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(${JSON.stringify(body)})});return {status:r.status}})()`)}
 async function intercept(tab,stage='Request',pattern=origin+'/api/v1/admin/users/*/effective-permissions'){tab.paused=null;await tab.send('Fetch.enable',{patterns:[{urlPattern:pattern,requestStage:stage}]})}
 async function pending(tab){return poll(()=>tab.paused,'intercepted permission response')}
 async function fulfill(tab,req,status,data,etag){await tab.send('Fetch.fulfillRequest',{requestId:req.requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},...(etag?[{name:'ETag',value:etag}]:[])],body:Buffer.from(JSON.stringify(data)).toString('base64')})}
 async function noStale(tab){await tab.wait(`!!document.querySelector('${panel} [role=alert]')&&!document.querySelector('${result}')&&document.querySelector('select[name=effectiveUser]').disabled`,'error clears result and account list')}
 const first=await session();await first.field('select','en');await users(first);
 if(caseId==='1'){
  const second=await session();await second.field('select','en');await users(second);const targetSession=await session(names.target);
  const signalDir=process.env.RACKCLICK_SIGNALS;await writeFile(path.join(signalDir,'readonly.begin'),'begin');await poll(async()=>readFile(path.join(signalDir,'readonly.ready'),'utf8').catch(()=>false),'SQL baseline');
  const text=await query(first),api=await snapshot(first);assert.equal(api.status,200);assert.deepEqual(api.data.permissions,(await me(targetSession)).data.permissions);
  assert.deepEqual(api.data.permissions.systemhausCapabilities,['systemhaus.read']);const customers=api.data.permissions.customers;assert.deepEqual(customers.map(c=>c.customerId).sort(),[ids.a,ids.b,ids.c].sort());
  assert.deepEqual(customers.find(c=>c.customerId===ids.a).capabilities,['inventory.edit','inventory.read','security.manage','systemhaus.read']);
  assert.deepEqual(customers.find(c=>c.customerId===ids.b).capabilities,['customer.manage','inventory.edit','inventory.read','legacy.synthetic','systemhaus.read']);
  assert.deepEqual(customers.find(c=>c.customerId===ids.c).capabilities,['customer.manage','inventory.read','legacy.synthetic','systemhaus.read']);
  assert.equal(api.data.permissions.sources.length,11);assert.equal(api.data.permissions.sources.filter(s=>s.capability==='legacy.synthetic').length,2);
  for(const name of [names.target,names.a,names.b,names.c,names.d,names.direct,names.grouped,names.cg1,names.cg2])assert.ok(text.includes(name),'Saved literal names visible');
  assert.ok(text.includes(ids.d));assert.ok(text.includes('legacy.synthetic'));assert.equal(await first.evaluate(`!!document.querySelector('${result} script,${result} img,${result} b')`),false);
  assert.equal(await first.evaluate(`document.querySelectorAll('[data-effective-sources] li').length`),11);
  assert.equal(await first.evaluate(`document.querySelector('[data-effective-global]').textContent.includes('legacy.synthetic')`),false);
  assert.equal(await first.evaluate(`document.querySelectorAll('[data-effective-customer]').length`),3);
  assert.ok((await query(second)).includes(names.target));await reload(first);await users(first);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);assert.ok((await query(first)).includes(names.target));
  await writeFile(path.join(signalDir,'readonly.end'),'end');const readonly=await poll(async()=>JSON.parse(await readFile(path.join(signalDir,'readonly.result'),'utf8').catch(()=>'null')),'SQL immutable result');assert.equal(readonly.unchanged,true);
  checks.push('Unión global/directa/dos grupos superpuestos; comparación /me;11 sources con legacy duplicada; nombres literales/XSS; capacidades e IDs; recarga/otra cookie; todas las tablas SQL inmutables durante lecturas GUI');
 }else if(caseId==='2'){
  const existing=await session(names.target);await query(first);const before=await snapshot(first);
  assert.equal((await mutate(first,'/api/v1/admin/user-groups/'+ids.grouped+'/members',{userId:ids.target,assigned:false})).status,200);
  const fresh=await query(first),after=await snapshot(first);assert.ok(after.data.revision>before.data.revision);assert.equal(await first.evaluate(`document.querySelectorAll('[data-effective-customer]').length`),1);assert.ok(!fresh.includes(names.b));assert.deepEqual(after.data.permissions,(await me(existing)).data.permissions);
  const grant=crypto.randomUUID();assert.equal((await mutate(first,'/api/v1/admin/user-groups/'+ids.direct+'/grants',{grantId:grant,capability:'inventory.edit',scope:'customer',targetId:ids.a,assigned:true})).status,200);
  await query(first);assert.ok((await snapshot(first)).data.permissions.customers[0].capabilities.includes('inventory.edit'));assert.deepEqual((await snapshot(first)).data.permissions,(await me(existing)).data.permissions);
  assert.equal((await mutate(first,'/api/v1/admin/user-groups/'+ids.direct+'/grants',{grantId:grant,capability:'inventory.edit',scope:'customer',targetId:ids.a,assigned:false})).status,200);await query(first);assert.ok(!(await snapshot(first)).data.permissions.customers[0].capabilities.includes('inventory.edit'));
  assert.equal((await mutate(first,'/api/v1/admin/users/'+ids.target+'/state',{active:false})).status,200);await query(first);const inactive=(await snapshot(first)).data;assert.equal(inactive.user.active,false);assert.deepEqual(inactive.permissions,{systemhausCapabilities:[],customers:[],sources:[]});assert.equal((await me(existing)).status,401);assert.ok((await first.evaluate(`document.querySelector('${result}').textContent`)).includes('Potential permissions are not shown'));assert.equal(await first.evaluate(`document.querySelectorAll('${result} li').length`),0);
  checks.push('API existentes cambian membresía/grant/estado; nueva consulta y revisión; /me misma sesión refleja cambios; inactivo tres listas vacías, no potenciales y sesión previa401');
 }else if(caseId==='3'){
  for(const status of [401,403,404]){await query(first);await intercept(first);await first.click('[data-query-effective]');const req=await pending(first);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);await fulfill(first,req,status,{error:status===401?'authentication_required':status===403?'forbidden':'not_found'});await first.send('Fetch.disable');await noStale(first);await refresh(first)}
  await query(first);await intercept(first);await first.click('[data-query-effective]');await first.send('Fetch.failRequest',{requestId:(await pending(first)).requestId,errorReason:'InternetDisconnected'});await first.send('Fetch.disable');await noStale(first);await refresh(first);
  for(const kind of ['malformed','etag','revision','association']){await query(first);const api=(await snapshot(first)).data;await intercept(first);await first.click('[data-query-effective]');const req=await pending(first);if(kind==='malformed')api.permissions.sources=[null];if(kind==='revision')api.revision++;if(kind==='association')api.user.id=ids.admin;await fulfill(first,req,200,api,kind==='etag'?'"999999"':'"'+api.revision+'"');await first.send('Fetch.disable');await noStale(first);await refresh(first)}
  // Two real backend responses held in reverse completion order; changing selector invalidates old request.
  await query(first);await intercept(first,'Response');await first.click('[data-query-effective]');const older=await pending(first);await first.field('select[name=effectiveUser]',ids.admin);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);first.paused=null;await first.click('[data-query-effective]');const newer=await pending(first);await first.send('Fetch.continueResponse',{requestId:newer.requestId});await first.wait(`document.querySelector('${result}')?.textContent.includes(${JSON.stringify(ids.admin)})`,'new target rendered');await first.send('Fetch.continueResponse',{requestId:older.requestId});await first.send('Fetch.disable');await delay(300);assert.equal(await first.evaluate(`document.querySelector('${result}').firstElementChild.textContent.includes(${JSON.stringify(ids.admin)})`),true);assert.equal(await first.evaluate(`document.querySelector('${result}').firstElementChild.textContent.includes(${JSON.stringify(ids.target)})`),false);
  // Refresh cancels a pending read; completing it cannot restore previous data.
  await first.field('select[name=effectiveUser]',ids.target);await intercept(first,'Response');await first.click('[data-query-effective]');const refreshOld=await pending(first);await refresh(first);await first.send('Fetch.continueResponse',{requestId:refreshOld.requestId});await first.send('Fetch.disable');await delay(250);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);
  // Unmount while response is held; reopening the panel starts without a result.
  await first.field('select[name=effectiveUser]',ids.target);await intercept(first,'Response');await first.click('[data-query-effective]');const unmounted=await pending(first);await first.click('.rc-admin-users header button');await first.wait(`!document.querySelector('${panel}')`,'panel unmounted');await first.send('Fetch.continueResponse',{requestId:unmounted.requestId});await first.send('Fetch.disable');await users(first);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);
  // Account-refresh403 clears the previous result and selectable accounts.
  await query(first);await intercept(first,'Request',origin+'/api/v1/admin/users');await first.click('[data-refresh-effective]');await fulfill(first,await pending(first),403,{error:'forbidden'});await first.send('Fetch.disable');await noStale(first);
  checks.push('401/403/404/red simulados por CDP; DTO/ETag/revisión/asociación inválidos; vaciado inmediato; dos respuestas reales fuera de orden, cambio de selector, refresh y unmount; refresh403 borra cuentas/resultados; ningún éxito falso');
 }else if(caseId==='4'){
  for(const [lang,title,queryText] of [['en','Effective permissions','Read permissions'],['de','Effektive Berechtigungen','Berechtigungen abrufen'],['es','Permisos efectivos','Consultar permisos']]){
   if(lang!=='en'){await first.click('.rc-admin-users header button');await first.wait(`!!document.querySelector('.rc-settings select')`,'language settings');await first.field('.rc-settings select',lang);await users(first)}
   assert.equal(await first.evaluate(`document.querySelector('${panel} h3').textContent`),title);assert.equal(await first.evaluate(`document.querySelector('[data-query-effective]').textContent`),queryText);const text=await query(first);assert.ok(text.includes(names.target));assert.ok(text.includes(names.grouped));assert.ok(text.includes('legacy.synthetic'));
  }
  const reader=await session(names.reader);assert.equal(await reader.evaluate(`!!document.querySelector('[data-admin-users]')`),false);assert.equal((await snapshot(reader)).status,403);
  assert.equal(await first.evaluate(`(()=>{const p=document.querySelector('${panel}'),s=document.querySelector('.rc-admin-sessions'),c=document.querySelector('.ir-client-cards');return !!(s.compareDocumentPosition(p)&Node.DOCUMENT_POSITION_FOLLOWING)&&!!(p.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)})()`),true);
  await first.evaluate(`document.querySelector('${panel}').scrollIntoView({block:'start'})`);await writeFile(path.join(evidence,'effective-permissions-es-1440x1000.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  checks.push('Etiquetas EN/DE/ES; datos conservados; lector sin navegación y403 API real; ubicación debajo sesiones/antes tarjetas; captura sintética ES1440x1000');
 }else throw Error('Unknown test group');
 const materialErrors=errors.filter(e=>!e.includes('status of 401')&&!/^\/favicon/.test(e)&&!((e.startsWith('/api/v1/admin/')||e.startsWith('/api/v1/auth/'))&&(/status of (412|409|403|404) \(/.test(e)||e.includes('net::ERR_'))));assert.deepEqual(materialErrors,[]);
 const report={status:'passed',group:caseId,run,platform:process.platform,browser:info.Browser,origin,checks,browserErrors:materialErrors,limitations:['Fixture sintético y perfil Edge headless nuevos; no aceptación visual de Wascar ni QA restaurado.','Errores CDP indicados son inyección controlada; lector403, cambios y composición usan API/PostgreSQL reales.']};await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} catch(error) {await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({run,status:'failed',checks,error:error.message,browserErrors:errors,responses,alerts:lastTab?await lastTab.evaluate(`[...document.querySelectorAll('[data-effective-permissions] [role=alert]')].map(x=>x.textContent)`).catch(()=>null):null},null,2));throw error;
} finally {if(browser){try{await browser.send('Browser.close')}catch{}}for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();}