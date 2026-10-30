// Windows Edge/CDP integration. No Playwright or additional npm dependency.
import { spawn } from 'node:child_process';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { createServer } from 'node:net';
import { once } from 'node:events';
import path from 'node:path';
import assert from 'node:assert/strict';
import {runAuditDetail} from './browser-admin-audit-detail.mjs';
import {runAuditAdministration} from './browser-admin-audit-administration.mjs';
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


 const fixture=JSON.parse(process.env.RACKCLICK_FIXTURE),caseId=process.env.RACKCLICK_CASE;
 const panel='[data-admin-audit]',result='[data-audit-result]';
 async function audit(tab){await tab.wait(`!!document.querySelector('[data-audit-navigation]')`,'Audit navigation');await tab.click('[data-audit-navigation]');await stable(tab);assert.equal(await tab.evaluate(`!!document.querySelector('.rc-admin-users')`),false)}
 async function stable(tab){await tab.wait(`!!document.querySelector('${result}')&&document.querySelector('${panel}').getAttribute('aria-busy')==='false'`,'audit page ready')}
 async function ids(tab){return tab.evaluate(`[...document.querySelectorAll('[data-audit-event]')].map(e=>e.dataset.auditEvent)`)}
 async function refresh(tab){await tab.click('[data-refresh-audit]');await stable(tab)}
 async function intercept(tab,stage='Response'){tab.paused=null;await tab.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/audit*',requestStage:stage}]})}
 async function pending(tab,except=null){return poll(()=>tab.paused&&tab.paused.requestId!==except&&tab.paused,'paused audit request')}
 async function fulfill(tab,req,status,data,etag){await tab.send('Fetch.fulfillRequest',{requestId:req.requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},...(etag?[{name:'ETag',value:etag}]:[])],body:Buffer.from(JSON.stringify(data)).toString('base64')})}
 async function noStale(tab){await tab.wait(`!!document.querySelector('${panel} [role=alert]')&&!document.querySelector('${result}')&&document.querySelector('[data-older-audit]').disabled`,'error clears audit page')}
 const first=await session();
 if(caseId==='1'){
  await first.click('[data-admin-users]');await first.wait(`!!document.querySelector('.rc-admin-users [data-user-id]')`,'Users page loaded');
  assert.equal(await first.evaluate(`!!document.querySelector('${panel}')`),false);
  assert.equal(responses.some(r=>r.path==='/api/v1/admin/audit'),false);
  checks.push('Usuarios conserva sus controles y no monta ni consulta Auditoría.');
 }
 await audit(first);
 if(caseId==='1'){
  const second=await session();await audit(second);
  await writeFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.begin'),'begin');await poll(()=>readFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.ready'),'utf8'),'read-only baseline');
  assert.deepEqual(await ids(first),fixture.ids.slice(0,50));assert.equal(await first.evaluate(`document.querySelector('${panel}').textContent.includes(${JSON.stringify(fixture.name)})`),true);
  assert.equal(await first.evaluate(`document.querySelector('${panel}').textContent.includes('synthetic-hidden-audit')`),false);assert.equal(await first.evaluate(`document.querySelectorAll('${panel} img').length`),0);
  await first.click('[data-older-audit]');await first.wait(`document.querySelector('[data-audit-event]')?.dataset.auditEvent===${JSON.stringify(fixture.ids[50])}`,'second page');assert.deepEqual(await ids(first),fixture.ids.slice(50,100));
  await first.click('[data-older-audit]');await first.wait(`document.querySelectorAll('[data-audit-event]').length===4`,'last page');assert.deepEqual(await ids(first),fixture.ids.slice(100));assert.equal(await first.evaluate(`document.querySelector('[data-older-audit]').disabled`),true);
  await refresh(first);assert.deepEqual(await ids(first),fixture.ids.slice(0,50));
  await reload(first);await first.wait(`!!document.querySelector('.ir-nav')`,'reloaded login session');await audit(first);assert.deepEqual(await ids(first),await ids(second));
  await writeFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.end'),'end');const equality=await poll(async()=>JSON.parse(await readFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.result'),'utf8')),'read-only result');assert.equal(equality.unchanged,true);
  checks.push('API/PostgreSQL reales: 104 eventos, páginas50/50/4, refresh/recarga/segunda sesión; Unicode y texto HTML literal; todas las tablas SQL idénticas durante el tramo de sólo lectura, después de logins.');
 }else if(caseId==='2'){
  const good=await first.evaluate(`fetch('/api/v1/admin/audit?limit=50').then(r=>r.json())`);
  for(const status of [401,403,404]){await intercept(first);await first.click('[data-refresh-audit]');const req=await pending(first);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);await fulfill(first,req,status,{error:'synthetic'});await first.send('Fetch.disable');await noStale(first);await refresh(first)}
  for(const kind of ['extra','order','etag','empty']){
   await intercept(first);await first.click('[data-refresh-audit]');const req=await pending(first),bad=structuredClone(good);let etag='"'+good.revision+'"';
   if(kind==='extra')bad.events[0].after_json={synthetic:true};if(kind==='order')bad.events.reverse();if(kind==='etag')etag='"999999"';if(kind==='empty'){bad.events=[];bad.nextBeforeId=null;}
   await fulfill(first,req,200,bad,etag);await first.send('Fetch.disable');if(kind==='empty'){await first.wait(`!!document.querySelector('[data-audit-empty]')&&!document.querySelector('[data-audit-event]')`,'explicit empty result');assert.equal(await first.evaluate(`document.querySelector('[data-older-audit]').disabled`),true)}else await noStale(first);await refresh(first);
  }
  await intercept(first,'Request');await first.click('[data-refresh-audit]');await first.send('Fetch.failRequest',{requestId:(await pending(first)).requestId,errorReason:'Failed'});await first.send('Fetch.disable');await noStale(first);await refresh(first);
  // Later refresh wins even when the earlier response is released afterwards.
  await intercept(first);await first.click('[data-refresh-audit]');const old=await pending(first);await first.click('[data-refresh-audit]');const recent=await pending(first,old.requestId),fresh=structuredClone(good);fresh.events.forEach(e=>e.actor.userName='fresh synthetic');await fulfill(first,recent,200,fresh,'"'+good.revision+'"');await first.wait(`document.querySelector('${result}')?.textContent.includes('fresh synthetic')`,'new refresh result');await first.send('Fetch.continueResponse',{requestId:old.requestId});await first.send('Fetch.disable');await delay(250);assert.equal(await first.evaluate(`document.querySelector('${result}').textContent.includes('fresh synthetic')`),true);
  await intercept(first);await first.click('[data-refresh-audit]');const held=await pending(first);await first.click('[data-admin-users]');await first.wait(`!!document.querySelector('.rc-admin-users')&&!document.querySelector('${panel}')`,'audit unmounted on Users navigation');const stale=structuredClone(good);stale.events.forEach(e=>e.actor.userName='stale unmount');await fulfill(first,held,200,stale,'"'+good.revision+'"');await first.send('Fetch.disable');await audit(first);assert.equal(await first.evaluate(`document.querySelector('${result}').textContent.includes('stale unmount')`),false);
  checks.push('CDP controlado:401/403/404/red, extra JSON/orden/ETag inválidos, vacío explícito, limpieza inmediata; dos respuestas fuera de orden y unmount sin restaurar datos antiguos.');
 }else if(caseId==='3'){
  for(const [lang,title,label] of [['en','Audit log','Refresh / most recent'],['de','Änderungsprotokoll','Aktualisieren / neueste'],['es','Auditoría','Actualizar / más recientes']]){
   await first.click('.rc-admin-audit-page header button');await first.wait(`!!document.querySelector('.rc-settings select')`,'language control');await first.field('.rc-settings select',lang);await audit(first);assert.equal(await first.evaluate(`document.querySelector('${panel} h3').textContent`),title);assert.equal(await first.evaluate(`document.querySelector('[data-refresh-audit]').textContent`),label);assert.equal(await first.evaluate(`document.querySelector('[data-apply-audit]').textContent`),{en:'Apply filters',de:'Filter anwenden',es:'Aplicar filtros'}[lang]);assert.equal(await first.evaluate(`document.querySelector('[data-clear-audit]').textContent`),{en:'Clear filters',de:'Filter löschen',es:'Limpiar filtros'}[lang]);assert.equal(await first.evaluate(`document.querySelector('${result}').textContent.includes(${JSON.stringify(fixture.name)})`),true);
  }
  assert.equal(await first.evaluate(`document.querySelector('.rc-admin-audit-page h1').textContent`),'Auditoría');
  assert.equal(await first.evaluate(`!!document.querySelector('.rc-admin-audit-page [data-effective-permissions],.rc-admin-audit-page [name=newUsername],.rc-admin-audit-page [data-user-id]')`),false);
  assert.equal(responses.some(r=>r.path==='/api/v1/admin/users'),false);
  assert.equal(await first.evaluate(`document.querySelector('[data-admin-users]').textContent`),'Usuarios');
  assert.equal(await first.evaluate(`document.querySelector('[data-audit-navigation]').textContent`),'Auditoría');
  await first.evaluate(`document.querySelector('${panel}').scrollIntoView({block:'start'})`);assert.equal(await first.evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);await writeFile(path.join(evidence,'audit-es-1440x1000.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  // Use real pointer input on the mobile menu and its separate Audit link.
  await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await first.click('.rc-admin-audit-page header button');await first.wait(`!!document.querySelector('.rc-settings select')`,'mobile clients');
  async function pointer(selector){const p=await first.evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,...p,button:'left',clickCount:1})}
  await pointer('.ir-mobile-nav');await first.wait(`!!document.querySelector('.ir-nav.open')`,'mobile menu open');
  await first.evaluate(`document.querySelector('[data-audit-navigation]').scrollIntoView({block:'center'})`);await pointer('[data-audit-navigation]');await stable(first);
  await first.wait(`!document.querySelector('.ir-nav.open')`,'mobile menu closes');
  assert.equal(await first.evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
  await writeFile(path.join(evidence,'audit-es-390x844.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  const reader=await session('audit-reader');assert.equal(await reader.evaluate(`!!document.querySelector('[data-admin-users],[data-audit-navigation]')`),false);assert.equal(await reader.evaluate(`fetch('/api/v1/admin/audit').then(r=>r.status)`),403);
  const admin=await session(fixture.name);
  const changed=await admin.evaluate(`(async()=>{const m=await fetch('/api/v1/me').then(r=>r.json()),s=await fetch('/api/v1/admin/users').then(r=>r.json());return (await fetch('/api/v1/admin/user-groups/${fixture.group}/members',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':m.csrf,'X-RackClick-Actor':m.user.id,'If-Match':'"'+s.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({userId:${JSON.stringify(fixture.admin)},assigned:false})})).status})()`);
  assert.equal(changed,200);await first.click('[data-refresh-audit]');await noStale(first);assert.equal(await first.evaluate(`document.querySelector('${panel} [role=alert]').textContent`),'Se requiere permiso global de administración.');
  checks.push('EN/DE/ES, página RC9 independiente de Usuarios/Grupos y sin consultar cuentas; capturas ES1440x1000/390x844 sin overflow, clic móvil real abre Auditoría y cierra menú; lector sin navegación/403 real; segunda cuenta retira membresía por API, sesión original recibe403 y borra la página.');
 }else if(caseId==='4'){
  const second=await session();await audit(second);
  await writeFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.begin'),'begin');await poll(()=>readFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.ready'),'utf8'),'read-only filter baseline');
  async function apply(tab,actorId,resourceId){await tab.field('[name=auditActorId]',actorId);await tab.field('[name=auditResourceId]',resourceId);await tab.click('[data-apply-audit]');await stable(tab)}
  await apply(first,fixture.secondary,'');assert.deepEqual(await ids(first),fixture.ids.slice(0,50));await first.click('[data-older-audit]');await first.wait(`document.querySelectorAll('[data-audit-event]').length===44`,'actor-only last page');assert.deepEqual(await ids(first),[...fixture.ids.slice(50,84),...fixture.ids.slice(94)]);
  await apply(first,'',fixture.extraResource);assert.deepEqual(await ids(first),fixture.ids.slice(94));
  await apply(first,fixture.secondary.toUpperCase(),fixture.resource.toUpperCase());assert.deepEqual(await ids(first),fixture.ids.slice(0,50));
  assert.equal(await first.evaluate(`document.querySelector('[data-audit-selection]').textContent.includes(${JSON.stringify(fixture.resource)})`),true);
  await first.click('[data-older-audit]');await first.wait(`document.querySelectorAll('[data-audit-event]').length===34`,'filtered last page');assert.deepEqual(await ids(first),fixture.ids.slice(50,84));
  await first.field('[name=auditResourceId]',fixture.extraResource);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);assert.equal(await first.evaluate(`document.querySelector('[data-refresh-audit]').disabled&&document.querySelector('[data-older-audit]').disabled`),true);
  await intercept(first);await first.click('[data-apply-audit]');const reset=await pending(first);const url=new URL(reset.request.url);assert.equal(url.searchParams.has('beforeId'),false);assert.equal(url.searchParams.get('resourceId'),fixture.extraResource);await first.send('Fetch.continueResponse',{requestId:reset.requestId});await first.send('Fetch.disable');await stable(first);assert.deepEqual(await ids(first),fixture.ids.slice(94));
  await refresh(first);assert.deepEqual(await ids(first),fixture.ids.slice(94));
  await apply(first,fixture.admin,fixture.resource);assert.deepEqual(await ids(first),fixture.ids.slice(84,94));
  await apply(first,fixture.admin,fixture.extraResource);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-empty]')`),true);assert.equal(await first.evaluate(`document.querySelector('[data-older-audit]').disabled`),true);
  await first.click('[data-clear-audit]');await stable(first);assert.deepEqual(await ids(first),fixture.ids.slice(0,50));assert.equal(await first.evaluate(`document.querySelector('[name=auditActorId]').value+document.querySelector('[name=auditResourceId]').value`),'');
  const sent=responses.filter(r=>r.path==='/api/v1/admin/audit').length;
  await first.field('[name=auditActorId]','bad');await first.click('[data-apply-audit]');await noStale(first);assert.equal(responses.filter(r=>r.path==='/api/v1/admin/audit').length,sent);
  await first.field('[name=auditActorId]','');assert.equal(await first.evaluate(`document.querySelector('[data-refresh-audit]').disabled`),true);await first.click('[data-clear-audit]');await stable(first);
  // Hold selection A while applying B. Releasing A cannot restore its page.
  await intercept(first);await first.field('[name=auditActorId]',fixture.secondary);await first.field('[name=auditResourceId]',fixture.resource);await first.click('[data-apply-audit]');const old=await pending(first);
  await first.field('[name=auditResourceId]',fixture.extraResource);assert.equal(await first.evaluate(`!!document.querySelector('${result}')`),false);await first.click('[data-apply-audit]');const recent=await pending(first,old.requestId);
  await first.send('Fetch.continueResponse',{requestId:recent.requestId});await stable(first);assert.deepEqual(await ids(first),fixture.ids.slice(94));await first.send('Fetch.continueResponse',{requestId:old.requestId});await first.send('Fetch.disable');await delay(200);assert.deepEqual(await ids(first),fixture.ids.slice(94));
  // Shape/order are valid, but these rows belong to another resource selection.
  const wrong=await first.evaluate(`fetch('/api/v1/admin/audit?limit=50').then(r=>r.json())`);await intercept(first);await first.click('[data-refresh-audit]');await fulfill(first,await pending(first),200,wrong,'"'+wrong.revision+'"');await first.send('Fetch.disable');await noStale(first);await refresh(first);assert.deepEqual(await ids(first),fixture.ids.slice(94));
  await apply(second,fixture.secondary,fixture.extraResource);assert.deepEqual(await ids(first),await ids(second));
  await first.evaluate('window.scrollTo(0,0)');await first.wait('scrollY===0','top of filter page');assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await writeFile(path.join(evidence,'audit-filters-es-1440x1000.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await writeFile(path.join(evidence,'audit-filters-es-390x844.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await reload(first);await first.wait(`!!document.querySelector('.ir-nav')`,'reloaded session');await audit(first);assert.equal(await first.evaluate(`document.querySelector('[name=auditActorId]').value+document.querySelector('[name=auditResourceId]').value`),'');assert.deepEqual(await ids(first),fixture.ids.slice(0,50));await apply(first,fixture.secondary,fixture.extraResource);assert.deepEqual(await ids(first),await ids(second));
  await writeFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.end'),'end');const equality=await poll(async()=>JSON.parse(await readFile(path.join(process.env.RACKCLICK_SIGNALS,'readonly.result'),'utf8')),'read-only filters result');assert.equal(equality.unchanged,true);
  checks.push('Filtros autor/recurso solos/combinados, UUID en mayúsculas, páginas50/34 y cambio reinicia cursor, vacío/limpiar/recarga/segunda sesión; editar retira datos hasta aplicar, inválido no envía, respuesta tardía de otra selección descartada, respuesta incompatible rechazada; capturas escritorio/móvil sin overflow; todas las tablas idénticas tras logins.');
 }else if(caseId==='5'){
  await runAuditDetail({fixture,first,session,audit,stable,refresh,reload,pending,fulfill,noStale,poll,delay,origin,evidence,checks});
 }else if(caseId==='6'){
  await runAuditAdministration({fixture,first,session,audit,stable,refresh,reload,pending,fulfill,noStale,poll,delay,origin,evidence,checks});
 }else throw Error('Unknown group');
 const materialErrors=errors.filter(e=>!e.includes('status of 401')&&!/^\/favicon/.test(e)&&!((e.startsWith('/api/v1/admin/')||e.startsWith('/api/v1/auth/'))&&(/status of (412|409|403|404) \(/.test(e)||e.includes('net::ERR_'))));assert.deepEqual(materialErrors,[]);
 const report={status:'passed',group:caseId,run,platform:process.platform,browser:info.Browser,checks,browserErrors:materialErrors,limitations:['Sólo fixture sintético y Edge headless nuevo, sin QA de Wascar ni aceptación completa.','Errores del grupo2 inyectados con CDP; grupo3 revoca por API real. No prueba todos los intercalados de concurrencia.']};await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(error){await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({run,status:'failed',checks,error:error.message,browserErrors:errors,responses},null,2));throw error;
}finally{if(browser){try{await browser.send('Browser.close')}catch{}}for(const c of clients)c.ws.close();if(child.exitCode===null)child.kill();}
