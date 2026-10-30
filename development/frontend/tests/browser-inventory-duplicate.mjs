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
 const info=await poll(async()=>(await fetch('http://127.0.0.1:'+port+'/json/version')).json(),'Edge endpoint');
 browser=await CDP.open(info.webSocketDebuggerUrl);
 async function session(user){
  const context=await browser.send('Target.createBrowserContext');
  const target=await browser.send('Target.createTarget',{url:origin,browserContextId:context.browserContextId});
  const targetInfo=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(t=>t.id===target.targetId),'target');
  const tab=await CDP.open(targetInfo.webSocketDebuggerUrl);lastTab=tab;
  for(const domain of ['Runtime','Log','Network','Page'])await tab.send(domain+'.enable');
  await tab.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await tab.wait(`!!document.querySelector('input[name=username]')&&!document.querySelector('button[type=submit]').disabled`,'login form');
  await tab.field('select','es');await tab.field('input[name=username]',user);await tab.field('input[name=password]',password);
  await tab.evaluate(`document.querySelector('form').requestSubmit()`);await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'authenticated clients');
  await tab.click(`[data-customer-id="${customerId}"]`);await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory');return tab;
 }
 const snapshot=tab=>tab.evaluate(`(async()=>{const r=await fetch('/api/v1/customers/${customerId}/project');if(!r.ok)throw Error('Snapshot status '+r.status);const value=await r.json();if(r.headers.get('etag')!=='"'+value.revision+'"')throw Error('ETag mismatch');return value})()`);
 async function openRack(tab,id){await tab.button('Gestionar infraestructura');await tab.wait(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`,'rack card');await tab.click(`[data-rack-id="${id}"] .rc-rack-open`);await tab.wait(`!!document.querySelector('#rack-detail-export')`,'physical rack');}
 async function shot(tab,name){await writeFile(path.join(evidence,name),Buffer.from((await tab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));}
 const first=await session(username),before=await snapshot(first);
 assert.equal(before.racks.length,2);assert.equal(before.devices.length,3);assert.equal(before.portGroups.length,4);assert.equal(before.ports.length,7);assert.equal(before.connections.length,2);
 assert.equal(before.ports.filter(p=>p.deviceId===ids.a&&p.gn===1).length,2);
 checks.push('SQL fixture:2 racks,3 devices,4 groups,7 ports,1 internal plus1 external cable; same gn1 in distinct groups retained');
 await first.evaluate(`(()=>{const b=[...document.querySelector('[data-rack-id="${ids.rackA}"]').querySelectorAll('button')].find(e=>e.textContent.trim()==='Duplicar');if(!b||b.disabled)throw Error('Duplicate button');b.click()})()`);
 await first.wait(`document.querySelector('dialog #operation-title')?.textContent==='Duplicar'`,'duplicate dialog');
 await first.field('dialog input[name=name]','Copia Ω <img>');await first.field('dialog select[name=includeConnections]','true');
 assert.equal(await first.evaluate(`document.querySelector('dialog select[name=includeConnections]').selectedOptions[0].textContent`),'Sí');
 assert.equal(await first.evaluate(`!!document.querySelector('dialog input[type=checkbox]')`),false,'Unconnected reserved port does not require cable confirmation');
 await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')&&document.querySelector('.rc-inventory-toolbar [role=status]').textContent==='Guardado por el servidor'`,'confirmed duplicate');
 const after=await snapshot(first);assert.equal(after.revision,before.revision+1);
 const added=key=>after[key].filter(row=>!before[key].some(old=>old.id===row.id));
 const copyRacks=added('racks'),newDevices=added('devices'),newGroups=added('portGroups'),newPorts=added('ports'),newCables=added('connections');
 assert.equal(copyRacks.length,1);assert.equal(newDevices.length,2);assert.equal(newGroups.length,3);assert.equal(newPorts.length,5);assert.equal(newCables.length,1);
 const rack=copyRacks[0],mapping={rackId:rack.id,devices:{},groups:{},ports:{},connectionId:newCables[0].id};
 const sourceRack=before.racks.find(row=>row.id===ids.rackA);
 assert.deepEqual(rack,{...sourceRack,id:rack.id,name:'Copia Ω <img>'});
 for(const original of before.devices.filter(row=>row.rackId===ids.rackA)){
  const candidates=newDevices.filter(row=>row.rackId===rack.id&&row.sortOrder===original.sortOrder);assert.equal(candidates.length,1);
  const copied=candidates[0];mapping.devices[original.id]=copied.id;assert.deepEqual(copied,{...original,id:copied.id,rackId:rack.id});
  for(const group of before.portGroups.filter(row=>row.deviceId===original.id)){
   const targets=newGroups.filter(row=>row.deviceId===copied.id&&row.sortOrder===group.sortOrder);assert.equal(targets.length,1);
   const newGroup=targets[0];mapping.groups[group.id]=newGroup.id;assert.deepEqual(newGroup,{...group,id:newGroup.id,deviceId:copied.id});
   for(const port of before.ports.filter(row=>row.groupId===group.id)){
    const ports=newPorts.filter(row=>row.groupId===newGroup.id&&row.sortOrder===port.sortOrder);assert.equal(ports.length,1);
    const newPort=ports[0];mapping.ports[port.id]=newPort.id;assert.deepEqual(newPort,{...port,id:newPort.id,deviceId:copied.id,groupId:newGroup.id});
   }
  }
 }
 const internal=before.connections.find(row=>row.id===ids.cable),copiedCable=newCables[0];
 assert.ok(Number.isFinite(Date.parse(copiedCable.createdAt)));assert.ok(Date.parse(copiedCable.createdAt)>=Date.parse(internal.createdAt));
 assert.deepEqual(copiedCable,{...internal,id:copiedCable.id,fromPortId:mapping.ports[internal.fromPortId],toPortId:mapping.ports[internal.toPortId],createdAt:copiedCable.createdAt});
 const newIds=[rack.id,...newDevices.map(x=>x.id),...newGroups.map(x=>x.id),...newPorts.map(x=>x.id),copiedCable.id];
 const oldIds=['racks','devices','portGroups','ports','connections'].flatMap(k=>before[k].map(x=>x.id));assert.equal(new Set(newIds).size,newIds.length);assert.ok(!newIds.some(id=>oldIds.includes(id)));
 const expected=structuredClone(before);expected.revision++;
 for(const key of ['racks','devices','portGroups','ports','connections'])expected[key].push(...added(key));
 assert.deepEqual(normalize(after),normalize(expected));
 for(const key of ['racks','devices','portGroups','ports','connections'])assert.deepEqual(after[key].filter(row=>before[key].some(old=>old.id===row.id)).sort((a,b)=>a.id.localeCompare(b.id)),[...before[key]].sort((a,b)=>a.id.localeCompare(b.id)));
 assert.ok(!after.connections.some(c=>c.id!==ids.externalCable&&[c.fromPortId,c.toPortId].includes(ids.pc)));
 assert.ok(!after.connections.some(c=>[c.fromPortId,c.toPortId].includes(mapping.ports[ids.pa2])),'Cloned externally wired source port is unconnected');
 checks.push('GUI Duplicar→name→Incluir cables internos Sí→Guardar confirmed once:all UUIDs remapped by device/group/order, exact attributes; originals and external cable unchanged, only internal cable copied, no source-port references');
 await openRack(first,rack.id);await first.wait(`document.querySelectorAll('[data-devid]').length===2&&!!document.querySelector('[data-wire="${copiedCable.id}"]')`,'cloned rack rendered');
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('[data-devid]')].map(e=>e.dataset.devid)`),[mapping.devices[ids.a],mapping.devices[ids.b]]);
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('.ir-wires [data-wire]')].map(e=>e.dataset.wire)`),[copiedCable.id]);
 assert.equal(await first.evaluate(`document.querySelector('[data-wire="${copiedCable.id}"]').getAttribute('stroke-dasharray')`),null);
 assert.equal(await first.evaluate(`document.querySelector('.ir-rack-title h1').childNodes[0].textContent`),'Copia Ω <img>');
 assert.equal(await first.evaluate(`!!document.querySelector('.ir-rack-title img')`),false);
 await shot(first,'duplicate-internal-cable-windows.png');
 await openRack(first,ids.rackA);
 await first.wait(`document.querySelectorAll('.ir-wires [data-wire]').length===2`,'source cables retained');
 assert.deepEqual((await first.evaluate(`[...document.querySelectorAll('.ir-wires [data-wire]')].map(e=>e.dataset.wire)`)).sort(),[ids.cable,ids.externalCable].sort());
 assert.equal(await first.evaluate(`document.querySelector('[data-wire="${ids.externalCable}"]').getAttribute('stroke-dasharray')`),'5 3');
 checks.push('Copied rack renders exactly one solid internal cable/new endpoints and literal name; source still renders original internal and external cable');
 const second=await session('move-second');
 for(const tab of [first,second]){
  await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${customerId}"]')`,'reloaded clients');await tab.click(`[data-customer-id="${customerId}"]`);
  await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'reloaded inventory');
  assert.deepEqual(normalize(await snapshot(tab)),normalize(after));await openRack(tab,rack.id);
  await tab.wait(`document.querySelectorAll('[data-devid]').length===2&&!!document.querySelector('[data-wire="${copiedCable.id}"]')`,'copied rack after reload');
 }
 checks.push('Two different authorized users with isolated cookie contexts and full reload read exact cloned project and cable');
 const materialErrors=errors.filter(e=>!/^\/api\/v1\/me: .*status of 401 |favicon\.ico/.test(e));assert.deepEqual(materialErrors,[]);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[]);
 await writeFile(path.join(evidence,'duplicate-map.json'),JSON.stringify(mapping,null,2));await writeFile(path.join(evidence,'expected-project.json'),JSON.stringify(after,null,2));
 const report={status:'passed',run,platform:process.platform,browser:info.Browser,revision:after.revision,checks,browserErrors:materialErrors,
  limitations:['SQL preparation, not GUI creation. One GUI duplication with internal cables included; no GUI variant without cables.','Unconnected reserved port copied without confirmation, connected-state negatives executed separately by Python API harness; no positive reserved checkbox path.','No full inventory parity, drag/touch, Dosen or real QA. ASP.NET restart/permissions/SQL exact comparison belong to Python harness.']};
 await writeFile(path.join(evidence,'browser-windows.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(error){
 let visibleText='';if(lastTab)try{visibleText=(await lastTab.evaluate(`document.body.innerText`)).replaceAll(password,'[redacted]').replaceAll(username,'[synthetic user]');await writeFile(path.join(evidence,'browser-failure.png'),Buffer.from((await lastTab.send('Page.captureScreenshot',{format:'png'})).data,'base64'));}catch{}
 await writeFile(path.join(evidence,'browser-windows-failure.json'),JSON.stringify({status:'failed',checks,error:error.message,browserErrors:errors,responses,visibleText},null,2));throw error;
}finally{if(browser)try{await browser.send('Browser.close');}catch{}for(const client of clients)client.ws.close();if(child.exitCode===null)child.kill();}
