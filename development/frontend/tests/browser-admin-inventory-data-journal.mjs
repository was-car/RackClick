// Real Windows Edge/IndexedDB boundary test; no database or application install.
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve('../..'),output=process.env.RACKCLICK_TEST_OUTPUT||path.join(root,'.local/admin-data-journal');
const {build}=await import(process.env.RACKCLICK_ESBUILD_MODULE||'esbuild');
const compiled=await build({entryPoints:['src/admin-inventory-data.ts'],bundle:true,write:false,format:'iife',globalName:'InventoryData',logLevel:'warning'});
const server=createServer((req,res)=>{res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type',req.url==='/adapter.js'?'text/javascript':'text/html');res.end(req.url==='/adapter.js'?compiled.outputFiles[0].contents:'<!doctype html><script src="/adapter.js"></script><p>Isolated IndexedDB test</p>');});
server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
const profile=path.join(root,'.local/browser-test/admin-data-journal-'+crypto.randomUUID());await mkdir(profile,{recursive:true});await mkdir(output,{recursive:true});
const child=spawn(process.env.RACKCLICK_EDGE_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
const {readFile}=await import('node:fs/promises');const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function poll(fn,label){const end=Date.now()+15000;let error;while(Date.now()<end){try{const value=await fn();if(value)return value;}catch(e){error=e;}await pause(50);}throw Error('Timeout: '+label+(error?': '+error.message:''));}
const sockets=[];let browser;const checks=[];
class CDP{
 constructor(ws){this.ws=ws;this.next=0;this.pending=new Map();ws.onmessage=event=>{const data=JSON.parse(event.data);const promise=this.pending.get(data.id);if(!promise)return;this.pending.delete(data.id);clearTimeout(promise.timer);data.error?promise.reject(Error(data.error.message)):promise.resolve(data.result);};}
 static async open(url){const ws=new WebSocket(url);await once(ws,'open');sockets.push(ws);return new CDP(ws)}
 send(method,params={}){return new Promise((resolve,reject)=>{const id=++this.next,timer=setTimeout(()=>reject(Error('CDP timeout '+method)),15000);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));})}
 async evaluate(expression){const value=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(value.exceptionDetails)throw Error(value.exceptionDetails.exception?.description||value.exceptionDetails.text);return value.result.value;}
}
try{
 const active=await poll(async()=>(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n'),'Edge');const port=Number(active[0]);
 browser=await CDP.open('ws://127.0.0.1:'+port+active[1]);
 const target=await browser.send('Target.createTarget',{url:origin});const info=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(x=>x.id===target.targetId),'target');const tab=await CDP.open(info.webSocketDebuggerUrl);
 await poll(()=>tab.evaluate('typeof InventoryData!=="undefined"'),'adapter');
 const context={actorId:'12345678-1234-1234-1234-123456789abc',houseId:'22345678-1234-1234-1234-123456789abc',origin};
 const intent={...context,requestId:'32345678-1234-1234-1234-123456789abc',action:'demo50',revision:7};
 await tab.evaluate(`window.context=${JSON.stringify(context)};window.intent=${JSON.stringify(intent)};`);
 assert.equal(await tab.evaluate(`InventoryData.inventoryDataJournal('read',context)`),null);
 assert.deepEqual(await tab.evaluate(`InventoryData.inventoryDataJournal('write',context,intent)`),intent);checks.push('Real IndexedDB durable write/read, bound to origin/Systemhaus/actor.');
 for(const change of [{actorId:'42345678-1234-1234-1234-123456789abc'},{houseId:'42345678-1234-1234-1234-123456789abc'},{origin:'http://127.0.0.1:1'}])assert.equal(await tab.evaluate(`InventoryData.inventoryDataJournal('read',{...context,...${JSON.stringify(change)}})`),null);
 for(const expression of ["InventoryData.inventoryDataJournal('write',context,{...intent,requestId:'42345678-1234-1234-1234-123456789abc'})","InventoryData.inventoryDataJournal('remove',context,{...intent,revision:8})","InventoryData.inventoryDataJournal('write',context,{...intent,contentBase64:'private archive'})"]){assert.equal(await tab.evaluate(`(${expression}).then(()=>false,e=>e.code==='inventory_data_storage')`),true);}
 assert.deepEqual(await tab.evaluate(`InventoryData.inventoryDataJournal('read',context)`),intent);checks.push('Different request, wrong removal and archive material are rejected without replacing the original intention.');
 const records=await tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.AdminInventoryData.v1',1);r.onsuccess=()=>{const db=r.result,tx=db.transaction('pending'),q=tx.objectStore('pending').getAll();q.onsuccess=()=>resolve(q.result);tx.oncomplete=()=>db.close()};r.onerror=reject})`);
 assert.deepEqual(records,[{key:JSON.stringify([origin,context.houseId,context.actorId]),intent}]);checks.push('Stored record contains only the exact small intention and scope key; no archive or credentials.');
 await tab.send('Page.reload');await poll(()=>tab.evaluate('typeof InventoryData!=="undefined"'),'reload');assert.deepEqual(await tab.evaluate(`InventoryData.inventoryDataJournal('read',${JSON.stringify(context)})`),intent);checks.push('Intention survives a real page reload.');
 await tab.evaluate(`window.context=${JSON.stringify(context)};window.intent=${JSON.stringify(intent)};`);
 await tab.evaluate(`InventoryData.inventoryDataJournal('remove',context,intent)`);assert.equal(await tab.evaluate(`InventoryData.inventoryDataJournal('read',context)`),null);
 const result=await tab.evaluate(`Promise.allSettled([InventoryData.inventoryDataJournal('write',context,intent),InventoryData.inventoryDataJournal('write',context,{...intent,requestId:'52345678-1234-1234-1234-123456789abc'})]).then(values=>values.map(x=>x.status))`);
 assert.equal(result.filter(x=>x==='fulfilled').length,1);assert.equal(result.filter(x=>x==='rejected').length,1);checks.push('Concurrent readwrite transactions admit one intention and reject the other.');
 const report={result:'PASS',checks,limits:['Standalone adapter/real Edge IndexedDB, no PostgreSQL, app GUI or Wascar QA.']};await writeFile(path.join(output,'journal-browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{if(browser)try{await browser.send('Browser.close')}catch{}for(const ws of sockets)ws.close();if(child.exitCode===null)child.kill();await new Promise(resolve=>server.close(resolve));}
