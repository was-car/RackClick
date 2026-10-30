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
export const root = path.resolve('../..'), evidence = process.env.RACKCLICK_TEST_OUTPUT || path.join(root, 'evidence/s1-20260928/frontend');
const run = new Date().toISOString().replaceAll(/[:.]/g, '-');
const profile = path.join(root, '.local/browser-test', run);
await mkdir(profile, { recursive: true }); await mkdir(evidence, { recursive: true });
const portServer = createServer(); portServer.listen(0, '127.0.0.1'); await once(portServer, 'listening'); const port = portServer.address().port; await new Promise(r => portServer.close(r));
const edge = process.env.RACKCLICK_EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const child = spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + port, '--user-data-dir=' + profile, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
export const clients = [], checks = [], errors = [], responses = [];
let lastTab;
export const delay = ms => new Promise(r => setTimeout(r, ms));
export async function poll(fn, label, duration = 15000) { const end = Date.now() + duration; let last; do { try { const v = await fn(); if (v) return v; } catch (e) { last = e; } await delay(100); } while (Date.now() < end); throw Error('Timed out: ' + label + (last ? ': ' + last.message : '')); }
export class CDP {
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if(data.method==='Fetch.requestPaused'){this.paused??=[];this.paused.push(data.params)}else if(data.method==='Page.javascriptDialogOpening'){this.send('Page.handleJavaScriptDialog',{accept:this.acceptDialog!==false}).catch(()=>{})}else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
 static async open(url) { const ws = new WebSocket(url); await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); }); const c = new CDP(ws); clients.push(c); return c; }
 send(method, params = {}) { const id = ++this.sequence; return new Promise((resolve, reject) => { const timer = setTimeout(() => { this.pending.delete(id); reject(Error('CDP timeout: ' + method)); }, 15000); this.pending.set(id, { resolve, reject, timer }); this.ws.send(JSON.stringify({ id, method, params })); }); }
 async evaluate(expression) { const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error('Browser evaluation failed: ' + result.exceptionDetails.text); return result.result.value; }
 async wait(expression, label) { return poll(() => this.evaluate(expression), label); }
 async field(selector, value) { return this.evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});if(!el)throw Error('Field missing');const proto=el.tagName==='SELECT'?HTMLSelectElement.prototype:el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return true})()`); }
 async click(selector) { await this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
 async button(text) { await this.evaluate(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!button)throw Error('Button missing');button.click()})()`); }
}

export const fixture=JSON.parse(process.env.RACKCLICK_FIXTURE),out=evidence;
export async function runScenario(scenario){
 let browser,tab;
 try{
 const info=await poll(async()=>(await fetch('http://127.0.0.1:'+port+'/json/version')).json(),'Edge');browser=await CDP.open(info.webSocketDebuggerUrl);
 async function session(name=username){const context=await browser.send('Target.createBrowserContext'),target=await browser.send('Target.createTarget',{url:origin,browserContextId:context.browserContextId});const t=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(x=>x.id===target.targetId),'target');tab=await CDP.open(t.webSocketDebuggerUrl);for(const d of ['Runtime','Network','Page'])await tab.send(d+'.enable');await tab.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await tab.wait(`!!document.querySelector('[name=username]')`,'login');await tab.field('select','es');await tab.field('[name=username]',name);await tab.field('[name=password]',password);await tab.evaluate(`document.querySelector('form').requestSubmit()`);await tab.wait(`!!document.querySelector('.ir-nav')`,'authenticated');return tab}
 const first=await session();
 await scenario({first,session,browser,info,checks,errors,responses,origin,fixture,out,username,password,shot:async(t,name)=>writeFile(path.join(out,name),Buffer.from((await t.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'))});
 assert.deepEqual(errors.filter(e=>!e.startsWith('/api/')&&!e.includes('favicon')),[]);
 const report={result:'PASS',browser:info.Browser,platform:process.platform,checks,responses,jsExceptions:errors.filter(e=>!e.startsWith('/api/')&&!e.includes('favicon')),limits:['Synthetic isolated SQL fixtures and real HTTP/Edge only. No Wascar QA, Windows reboot or full RC9 parity.']};await writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
 }catch(e){let visibleText='';if(tab)try{visibleText=(await tab.evaluate('document.body.innerText')).replaceAll(password,'[redacted]');await writeFile(path.join(out,'failure.png'),Buffer.from((await tab.send('Page.captureScreenshot',{format:'png'})).data,'base64'))}catch{}await writeFile(path.join(out,'browser-failure.json'),JSON.stringify({result:'FAIL',checks,error:String(e.stack),errors,responses,visibleText},null,2)+'\n');throw e}
 finally{if(browser)try{await browser.send('Browser.close')}catch{}for(const c of clients)c.ws.close();if(child.exitCode===null)child.kill()}
}
export async function infrastructure(tab){await tab.click(`[data-customer-id="${fixture.customer}"]`);await tab.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'inventory')}
export const snapshot=tab=>tab.evaluate(`fetch('/api/v1/customers/${fixture.customer}/project').then(r=>r.json())`);
export async function saved(tab){await tab.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')&&document.querySelector('.rc-inventory-toolbar [role=status]').textContent==='Guardado por el servidor'`,'confirmed save')}
export const submit=tab=>tab.evaluate(`document.querySelector('dialog[open] form').requestSubmit()`);
export const normalize=p=>{const v=structuredClone(p);for(const key of ['sites','buildings','rooms','racks','devices','portGroups','ports','connections'])v[key].sort((a,b)=>a.id.localeCompare(b.id));return v;};
