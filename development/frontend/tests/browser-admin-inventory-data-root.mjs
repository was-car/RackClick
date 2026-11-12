// Actual ServerApp/AdminUsers/AdminInventoryData/API/React/IndexedDB; synthetic HTTP boundary only.
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve('../..'),out=process.env.RACKCLICK_TEST_OUTPUT||path.join(root,'.local/admin-data-root');await mkdir(out,{recursive:true});
const {build}=await import(process.env.RACKCLICK_ESBUILD_MODULE||pathToFileURL(path.join(root,'development/frontend/node_modules/esbuild/lib/main.js')).href);
const bundle=await build({entryPoints:['src/ServerApp.jsx'],bundle:true,write:false,logLevel:'warning'});
const vendor=path.join(root,'development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/vendor');
const assets={'/app.js':bundle.outputFiles[0].contents,'/react.js':await readFile(path.join(vendor,'react.production.min.js')),'/react-dom.js':await readFile(path.join(vendor,'react-dom.production.min.js'))};
const actor='12345678-1234-1234-1234-123456789abc',house='22345678-1234-1234-1234-123456789abc';
const empty={customers:0,sites:0,buildings:0,rooms:0,racks:0,devices:0,portGroups:0,ports:0,connections:0};
const customers=Array.from({length:50},(_,n)=>({id:crypto.randomUUID(),name:'Literal <名> customer '+(n+1),revision:1}));
const caps=['systemhaus.read','systemhaus.manage','security.manage','inventory.read','reports.export','customer.create','inventory.edit'];
let populated=false,authenticated=true,houseRead=true,deferShared=false;const held=[],calls=[];
const server=createServer(async(req,res)=>{
 res.setHeader('Cache-Control','no-store');
 const json=(value,status=200,etag)=>{res.statusCode=status;res.setHeader('Content-Type','application/json');if(etag)res.setHeader('ETag',etag);res.end(JSON.stringify(value));};
 if(req.url.startsWith('/api/')){
  const p=req.url.slice(4);calls.push({path:p,method:req.method});
  if(p==='/v1/auth/logout'){authenticated=false;res.statusCode=204;res.end();return;}
  if(p==='/v1/me'){json(authenticated?{user:{id:actor,houseId:house,userName:'Synthetic root admin'},csrf:'synthetic',permissions:{systemhausCapabilities:houseRead?caps:caps.filter(c=>c!=='systemhaus.read'),customers:populated?customers.map(c=>({customerId:c.id,capabilities:['inventory.read','inventory.edit','customer.manage','reports.export']})):[]}}:{error:'authentication_required'},authenticated?200:401);return;}
  if(!authenticated){json({error:'authentication_required'},401);return;}
  if(p==='/v1/systemhaus'||p==='/v1/customers'){
   const send=()=>p==='/v1/systemhaus'?json({id:house,name:'Synthetic house',revision:populated?8:7},200,'"'+(populated?8:7)+'"'):json(populated?customers:[]);
   if(deferShared&&populated)held.push(send);else send();return;
  }
  if(/^\/v1\/customers\/[^/]+\/project$/.test(p)){json({customerId:p.split('/')[3],revision:1,sites:[],buildings:[],rooms:[],racks:[],devices:[],portGroups:[],ports:[],connections:[]},200,'"1"');return;}
  if(p==='/v1/me/preferences'){json({kind:'userPreferences',ownerId:actor,revision:0,language:null,theme:null},200,'"0"');return;}
  if(p==='/v1/admin/users'){json({revision:populated?8:7,users:[{id:actor,userName:'Synthetic root admin',active:true}]},200,'"'+(populated?8:7)+'"');return;}
  if(p==='/v1/admin/inventory-data'){json({systemhausRevision:populated?8:7,empty:!populated,counts:populated?{...empty,customers:50}:empty,demo:{available:true,counts:{...empty,customers:50}},maxArchiveBytes:33554432});return;}
  if(p==='/v1/admin/inventory-data/demo50'&&req.method==='POST'){
   let body='';for await(const chunk of req)body+=chunk;assert.equal(JSON.parse(body).confirmation,'LOAD DEMO50');assert.equal(req.headers['x-rackclick-actor'],actor);assert.equal(req.headers['if-match'],'"7"');populated=true;
   json({kind:'inventoryData',action:'demo50',requestId:req.headers['idempotency-key'],operationId:'42345678-1234-1234-1234-123456789abc',systemhausRevision:8,counts:{...empty,customers:50},archive:null});return;
  }
  json({error:'forbidden'},403);return;
 }
 res.setHeader('Content-Type',assets[req.url]?'text/javascript':'text/html');res.end(assets[req.url]||'<!doctype html><meta charset="utf-8"><div id="root"></div><script defer src="/react.js"></script><script defer src="/react-dom.js"></script><script defer src="/app.js"></script>');
});
server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
const profile=path.join(out,'edge-'+crypto.randomUUID());await mkdir(profile,{recursive:true});
const child=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
const sockets=[],checks=[];let browser;const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function poll(fn,label){const end=Date.now()+15000;let error;while(Date.now()<end){try{const value=await fn();if(value)return value;}catch(e){error=e;}await delay(50);}throw Error('Timeout '+label+(error?': '+error.message:''));}
class CDP{constructor(ws){this.ws=ws;this.next=0;this.pending=new Map();ws.onmessage=e=>{const d=JSON.parse(e.data),p=this.pending.get(d.id);if(!p)return;this.pending.delete(d.id);clearTimeout(p.timer);d.error?p.reject(Error(d.error.message)):p.resolve(d.result);};}static async open(url){const ws=new WebSocket(url);await once(ws,'open');sockets.push(ws);return new CDP(ws)}send(method,params={}){return new Promise((resolve,reject)=>{const id=++this.next,timer=setTimeout(()=>reject(Error('CDP timeout '+method)),15000);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));})}async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}}
try{
 const active=await poll(async()=>(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n'),'Edge'),port=Number(active[0]);browser=await CDP.open('ws://127.0.0.1:'+port+active[1]);
 const target=await browser.send('Target.createTarget',{url:origin});const info=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(x=>x.id===target.targetId),'target');const tab=await CDP.open(info.webSocketDebuggerUrl);
 const click=selector=>tab.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 async function mount(){await tab.send('Page.navigate',{url:origin});await poll(()=>tab.evaluate('!!document.querySelector(".ir-nav")'),'authenticated root');await click('[data-admin-users]');await poll(()=>tab.evaluate('document.querySelector("[data-admin-inventory-data]")?.getAttribute("aria-busy")==="false"&&!document.querySelector("[data-admin-account-controls]").disabled'),'admin ready');await click('[name=inventoryDemoConfirm]');await poll(()=>tab.evaluate('!document.querySelector("[data-inventory-data-demo]").disabled'),'demo confirmation');}
 await mount();assert.equal(await tab.evaluate('document.querySelectorAll(".ir-client-link").length'),0);await click('[data-inventory-data-demo]');await poll(()=>tab.evaluate('!!document.querySelector("[data-inventory-data-receipt]")&&!document.querySelector("[data-inventory-data-pending]")&&document.querySelector("[data-admin-inventory-data]").getAttribute("aria-busy")==="false"'),'normal demo committed');
 assert.equal(await tab.evaluate('document.querySelectorAll(".ir-client-link").length'),50,'Committed import must refresh the actual root navigation without reload');assert.equal(calls.filter(x=>x.path==='/v1/systemhaus').length,2);assert.equal(calls.filter(x=>x.path==='/v1/customers').length,2);await click('.ir-all-clients');assert.equal(await tab.evaluate('document.querySelectorAll("[data-customer-id]").length'),50);await click('[data-customer-id]');await poll(()=>tab.evaluate('!!document.querySelector(".rc-inventory-toolbar")'),'new client project');assert.equal(await tab.evaluate('!!document.querySelector("[data-add-hardware]")'),true,'Imported customer must have its effective edit controls without reload');await click('.ir-all-clients');checks.push('Normal Demo50 commit updates root navigation, cards and effective edit controls of a newly opened customer without reload; receipt survives the refreshed permission projection.');
 const initialMe=calls.filter(x=>x.path==='/v1/me').length;await click('[data-admin-users]');await poll(()=>tab.evaluate('document.querySelector("[data-admin-inventory-data]")?.getAttribute("aria-busy")==="false"'),'reopened admin');assert.equal(calls.filter(x=>x.path==='/v1/me').length,initialMe);assert.equal(calls.filter(x=>x.path==='/v1/admin/inventory-data/demo50').length,1);checks.push('Reopening Administration does not repeat the import or session refresh.');
 populated=false;houseRead=false;calls.length=0;await mount();await click('[data-inventory-data-demo]');await poll(()=>tab.evaluate('document.querySelectorAll(".ir-client-link").length===50&&document.querySelector("[data-admin-inventory-data]")?.getAttribute("aria-busy")==="false"'),'no house.read callback');assert.equal(calls.filter(x=>x.path==='/v1/systemhaus').length,0);checks.push('The real root honors systemhaus.read while refreshing permitted customers.');
 populated=false;houseRead=true;calls.length=0;deferShared=true;await mount();await click('[data-inventory-data-demo]');await poll(()=>held.length===2,'deferred post-commit root reads');await tab.evaluate(`[...document.querySelectorAll('.ir-settings')].find(x=>x.textContent==='Sign out').click()`);await poll(()=>tab.evaluate('!!document.querySelector("[name=username]")'),'logout');for(const release of held.splice(0))release();await delay(100);assert.equal(await tab.evaluate('!!document.querySelector(".ir-nav")'),false);assert.equal(await tab.evaluate('document.body.textContent.includes("Literal <名> customer")'),false);checks.push('Post-commit house/customer replies arriving after logout cannot republish a previous session.');
 const report={result:'PASS',checks,limits:['Actual root and panel code with synthetic HTTP responses; no PostgreSQL, installed QA or VM.']};await writeFile(path.join(out,'root-browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{for(const release of held.splice(0))release();if(browser)try{await browser.send('Browser.close')}catch{}for(const s of sockets)s.close();if(child.exitCode===null)child.kill();await new Promise(r=>server.close(r));}
