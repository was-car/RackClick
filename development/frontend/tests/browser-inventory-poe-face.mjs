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
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
 static async open(url) { const ws = new WebSocket(url); await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); }); const c = new CDP(ws); clients.push(c); return c; }
 send(method, params = {}) { const id = ++this.sequence; return new Promise((resolve, reject) => { const timer = setTimeout(() => { this.pending.delete(id); reject(Error('CDP timeout: ' + method)); }, 15000); this.pending.set(id, { resolve, reject, timer }); this.ws.send(JSON.stringify({ id, method, params })); }); }
 async evaluate(expression) { const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error('Browser evaluation failed: ' + result.exceptionDetails.text); return result.result.value; }
 async wait(expression, label) { return poll(() => this.evaluate(expression), label); }
 async field(selector, value) { return this.evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});if(!el)throw Error('Field missing');const proto=el.tagName==='SELECT'?HTMLSelectElement.prototype:el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return true})()`); }
 async click(selector) { await this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
 async button(text) { await this.evaluate(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!button)throw Error('Button missing');button.click()})()`); }
}
let browser;
const ids=JSON.parse(process.env.RACKCLICK_FIXTURE),customerId=ids.customer;
const normalize=project=>{const value=structuredClone(project);for(const key of ['sites','buildings','rooms','racks','devices','portGroups','ports','connections'])value[key].sort((a,b)=>a.id.localeCompare(b.id));return value;};
try{
 const info=await poll(async()=>(await fetch('http://127.0.0.1:'+port+'/json/version')).json(),'Edge endpoint');browser=await CDP.open(info.webSocketDebuggerUrl);
 async function session(user){
  const context=await browser.send('Target.createBrowserContext');const target=await browser.send('Target.createTarget',{url:origin,browserContextId:context.browserContextId});
  const targetInfo=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(t=>t.id===target.targetId),'target');
  const tab=await CDP.open(targetInfo.webSocketDebuggerUrl);lastTab=tab;for(const domain of ['Runtime','Log','Network','Page'])await tab.send(domain+'.enable');
  await tab.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await tab.wait(`!!document.querySelector('input[name=username]')&&!document.querySelector('button[type=submit]').disabled`,'login form');
  await tab.field('select','es');await tab.field('input[name=username]',user);await tab.field('input[name=password]',password);await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'clients');await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory loaded');return tab;
 }
 const snapshot=tab=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Snapshot status '+r.status);const value=await r.json();if(r.headers.get('etag')!=='"'+value.revision+'"')throw Error('ETag mismatch');return value})()`);
 async function openRack(tab){await tab.button('Gestionar infraestructura');await tab.wait(`!!document.querySelector('[data-rack-id="${ids.rackA}"] .rc-rack-open')`,'rack card');await tab.click(`[data-rack-id="${ids.rackA}"] .rc-rack-open`);await tab.wait(`!!document.querySelector('#rack-detail-export')`,'rack view');}
 const present=tab=>tab.evaluate(`document.querySelectorAll('[data-vport="${ids.pa}"]').length`);
 async function view(tab,face,visible){await tab.click(`[data-face="${face}"]`);await tab.wait(`document.querySelector('[data-face="${face}"]').getAttribute('aria-pressed')==='true'&&document.querySelectorAll('[data-vport="${ids.pa}"]').length===${visible?1:0}`,'face '+face+' target visibility');}
 async function tooltip(tab){return tab.evaluate(`document.querySelector('[data-vport="${ids.pa}"] > title').textContent`);}
 async function shot(tab,name){await writeFile(path.join(evidence,name),Buffer.from((await tab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));}
 const first=await session(username);let expected=await snapshot(first);const original=structuredClone(expected);
 const initial=expected.ports.find(p=>p.id===ids.pa);assert.equal(initial.type,'rj45_poe');assert.equal(initial.poe,true);assert.equal(initial.watts,17.5);assert.equal(initial.face,'front');assert.equal(expected.connections.length,1);
 const originalCable=expected.connections[0];assert.equal(originalCable.fromPortId,ids.pa);assert.equal(originalCable.toPortId,ids.pb);
 await openRack(first);await view(first,'front',true);assert.ok((await tooltip(first)).includes('Watts documentados: 17.5 W'));assert.ok((await tooltip(first)).includes('PoE: ON'));
 assert.equal(await first.evaluate(`document.querySelector('[data-vport="${ids.pa}"] [data-poe]').getAttribute('data-poe')`),'on');
 checks.push('SQL-prepared connected RJ45PoE ON17.5W, explicit front, exact UUID/group/cable; tooltip and PoE indicator show ON');
 async function edit(field,value,patch){
  await first.evaluate(`document.querySelector('[data-vport="${ids.pa}"]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))`);
  await first.wait(`!!document.querySelector('dialog .rc-port-selection')`,'port edit');
  const selected=await first.evaluate(`[...document.querySelectorAll('dialog .rc-port-selection input')].map((e,i)=>({checked:e.checked,label:e.closest('label').textContent}))`);
  assert.equal(selected.filter(x=>x.checked).length,1);assert.ok(selected.find(x=>x.checked).label.includes('Objetivo PoE Ω'));
  await first.field('dialog section > label:nth-of-type(2) select',field);await first.field('dialog section > label:last-child select',value);
  await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
  expected=structuredClone(expected);expected.revision++;Object.assign(expected.ports.find(p=>p.id===ids.pa),patch);
  await first.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')&&document.querySelector('.rc-inventory-toolbar [role=status]').textContent==='Guardado por el servidor'`,'server confirmed port edit');
  assert.deepEqual(normalize(await snapshot(first)),normalize(expected));
  assert.deepEqual(expected.connections,original.connections);assert.equal(expected.ports.find(p=>p.id===ids.pa).watts,17.5);assert.equal(expected.ports.find(p=>p.id===ids.pa).groupId,initial.groupId);
 }
 await edit('poe','false',{poe:false,type:'rj45'});await view(first,'front',true);
 assert.ok((await tooltip(first)).includes('Watts documentados: 17.5 W'));assert.ok((await tooltip(first)).includes('PoE: OFF'));
 assert.equal(await first.evaluate(`document.querySelector('[data-vport="${ids.pa}"] [data-poe]').getAttribute('data-poe')`),'off');
 assert.equal(await first.evaluate(`!!document.querySelector('[data-wire="${ids.cable}"]')`),true);
 await shot(first,'poe-off-watts-preserved-windows.png');
 checks.push('Right-click port→CambiarPoE→OFF→Guardar: only poe false/type rj45 change;17.5W, UUID/group/cable/endpoints/rest identical, tooltip OFF and watts preserved');
 await edit('face','rear',{face:'rear'});await view(first,'front',false);await view(first,'rear',true);
 assert.ok((await tooltip(first)).includes('17.5 W'));assert.ok((await tooltip(first)).includes('PoE: OFF'));
 assert.equal(await first.evaluate(`!!document.querySelector('[data-wire="${ids.cable}"]')`),true);
 checks.push('CaraTrasera persists on same UUID; target absent in front and once in rear; cable remains same even when opposite endpoint is on other displayed face');
 await edit('face','front',{face:'front'});await view(first,'rear',false);await view(first,'front',true);
 await edit('face','auto',{face:'auto'});await view(first,'rear',false);await view(first,'front',true);
 checks.push('ExplicitFrontal thenAutomática persist on same UUID; generic fixture automatic front rule tested without inventing terminals or circuits');
 await edit('face','rear',{face:'rear'});await view(first,'front',false);await view(first,'rear',true);
 await shot(first,'poe-off-rear-same-port-windows.png');
 const second=await session('move-second');
 for(const tab of [first,second]){
  await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'reload clients');await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'reload inventory');assert.deepEqual(normalize(await snapshot(tab)),normalize(expected));
  await openRack(tab);await view(tab,'front',false);await view(tab,'rear',true);
  const text=await tooltip(tab);assert.ok(text.includes('Watts documentados: 17.5 W')&&text.includes('PoE: OFF'));assert.equal(await present(tab),1);
 }
 checks.push('Full reload in two distinct authorized users/cookie contexts reads exact final OFF17.5W/rear and single UUID, same cable and complete project');
 const materialErrors=errors.filter(e=>!/^\/api\/v1\/me: .*status of 401 |favicon\.ico/.test(e));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[]);
 await writeFile(path.join(evidence,'expected-project.json'),JSON.stringify(expected,null,2));
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,revision:expected.revision,checks,browserErrors:materialErrors,
  limitations:['SQL preparation, not GUI creation. Five GUI edits:OFF/rear/front/auto/rear.','Documented power only; no electrical supply/telemetry/circuit certification or physical terminal inferred from a face.','Automatic front only for this generic fixture preset; no all-preset/connector parity or touchscreen/drag tests.','Python separately verifies SQL9tables, rejection atomicity/permissions and isolated ASP.NET restart. No real QA/PG or Windows restart.']};
 await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(error){let visibleText='';if(lastTab)try{visibleText=(await lastTab.evaluate(`document.body.innerText`)).replaceAll(password,'[redacted]').replaceAll(username,'[synthetic user]');await writeFile(path.join(evidence,'browser-failure.png'),Buffer.from((await lastTab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));}catch{}
 await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({status:'failed',checks,error:error.message,browserErrors:errors,responses,visibleText},null,2));throw error;
}finally{if(browser)try{await browser.send('Browser.close');}catch{}for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();}
