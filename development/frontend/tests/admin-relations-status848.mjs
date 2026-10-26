// Component-only Edge test. Synthetic props, no server API, database or real QA.
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {createServer} from 'node:http';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=fileURLToPath(new URL('../../../',import.meta.url));
const args=process.argv.slice(2),value=name=>args[args.indexOf(name)+1];
assert.ok(args.includes('--output'),'Explicit new evidence directory required');
const out=path.resolve(value('--output'));
await mkdir(out,{recursive:false});
const source=path.resolve(args.includes('--source')?value('--source'):path.join(root,'development/frontend/src/AdminGroupRelations.jsx'));
const bytes=await readFile(source),hash=b=>createHash('sha256').update(b).digest('hex');
const reference=path.join(root,'development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28');
const manifest=(await readFile(path.join(reference,'SHA256SUMS-PACKAGE.txt'),'utf8')).split(/\r?\n/);
const assets={};
for(const name of ['react.production.min.js','react-dom.production.min.js']){
 const data=await readFile(path.join(reference,'vendor',name));
 assert.equal(hash(data),manifest.find(x=>x.slice(66).replace(/^\.\//,'')==='vendor/'+name)?.slice(0,64));
 assets['/'+name]=data;
}
const entry=`import {AdminGroupRelations,relationWords} from ${JSON.stringify(source)};
window.words=relationWords;
window.synthetic={revision:1,userGroups:[{id:'a',name:'Equipo Ω <img src=x onerror=alert(1)>',members:[{id:'m',userName:'Técnico',active:true}],grants:[]},{id:'b',name:'同じ名前',members:[],grants:[]}],customerGroups:[{id:'c',name:'Cliente Ä',customers:[]}]};
window.show=(data=window.synthetic,lang='es')=>ReactDOM.render(<AdminGroupRelations data={data} lang={lang}/>,document.getElementById('root'));
window.show();`;
assets['/component.js']=(await build({stdin:{contents:entry,resolveDir:root,loader:'jsx'},bundle:true,write:false,target:'es2020'})).outputFiles[0].contents;
assets['/']=Buffer.from('<!doctype html><html><head><meta charset="utf-8"></head><body><div id="root"></div><script src="/react.production.min.js"></script><script src="/react-dom.production.min.js"></script><script src="/component.js"></script></body></html>');
const requests=[],errors=[],checks=[],connections=[],websockets=[];
const server=createServer((req,res)=>{requests.push({method:req.method,url:req.url});const body=assets[req.url];res.writeHead(body?200:404,{'Content-Type':req.url.endsWith('.js')?'text/javascript':'text/html'});res.end(body||'');});
server.on('connection',socket=>{connections.push(socket)});
server.listen(0,'127.0.0.1');await once(server,'listening');
const port=server.address().port,profile=path.join(root,'.local/browser-test','status848-'+randomUUID());await mkdir(profile,{recursive:true});
const edge=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function poll(fn,label){const end=Date.now()+15000;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch{}await delay(50)}throw Error('Timeout: '+label)}
class CDP{
 constructor(ws){this.ws=ws;this.id=0;this.pending=new Map();websockets.push(ws);ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=this.pending.get(m.id);if(p){this.pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text)});}
 static async open(url){const ws=new WebSocket(url);await once(ws,'open');return new CDP(ws)}
 send(method,params={}){return new Promise((resolve,reject)=>{const id=++this.id,timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP timeout '+method))},10000);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}))});}
 async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;}
}
let browser,tab,info,successful=false,failure,cleanupError;
try{
 const address=await poll(async()=>(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split(/\r?\n/)[0],'Edge endpoint');
 info=await(await fetch('http://127.0.0.1:'+address+'/json/version')).json();browser=await CDP.open(info.webSocketDebuggerUrl);
 const {targetId}=await browser.send('Target.createTarget',{url:'http://127.0.0.1:'+port+'/'});
 const target=await poll(async()=>(await(await fetch('http://127.0.0.1:'+address+'/json/list')).json()).find(x=>x.id===targetId),'page');
 tab=await CDP.open(target.webSocketDebuggerUrl);await tab.send('Runtime.enable');await tab.send('Accessibility.enable');
 await poll(()=>tab.evaluate(`!!window.show&&!!document.querySelector('[name=relationGroupId]')`),'component');
 assert.equal(await tab.evaluate(`(()=>{window.statusNode=document.querySelector('[data-relation-selection-status]');return !!statusNode&&statusNode.textContent===words.es.choose})()`),true,'Live status must exist BEFORE first selection');
 checks.push('Live status exists before first selection.');
 const choose=async(name,id)=>{await tab.evaluate(`(()=>{const s=document.querySelector('[name=${name}]');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(s,${JSON.stringify(id)});s.dispatchEvent(new Event('change',{bubbles:true}));})()`);};
 for(const [id,name] of [['a','Equipo Ω <img src=x onerror=alert(1)>'],['b','同じ名前']]){
  await choose('relationGroupId',id);
  assert.equal(await tab.evaluate(`statusNode===document.querySelector('[data-relation-selection-status]')&&statusNode.textContent===words.es.group+': '+${JSON.stringify(name)}+' · '+${JSON.stringify(id)}`),true);
  assert.equal(await tab.evaluate(`document.querySelector('[data-relation-group]').dataset.relationGroup`),id);
 }
 assert.equal(await tab.evaluate(`document.querySelector('[data-admin-group-relations] img')===null`),true);
 checks.push('A→B keeps the same live node, literal Unicode/HTML text and the correct detail.');
 await choose('relationGroupType','customer');
 assert.equal(await tab.evaluate(`statusNode.textContent===words.es.choose&&!document.querySelector('[data-relation-group]')`),true);
 await choose('relationGroupId','c');
 assert.equal(await tab.evaluate(`statusNode.textContent===words.es.group+': Cliente Ä · c'`),true);
 await tab.evaluate(`window.show(null)`);
 assert.equal(await tab.evaluate(`statusNode===document.querySelector('[data-relation-selection-status]')&&statusNode.textContent===words.es.unavailable&&document.querySelector('[name=relationGroupId]').disabled&&!document.querySelector('[data-relation-group]')`),true);
 await tab.evaluate(`window.show({...synthetic,customerGroups:[]})`);
 assert.equal(await tab.evaluate(`statusNode.textContent===words.es.choose&&!document.querySelector('[data-relation-group]')`),true);
 checks.push('Type switch, missing data and removed group clear old details without replacing status.');
 for(const lang of ['en','de','es']){
  await tab.evaluate(`window.show(synthetic,${JSON.stringify(lang)})`);await choose('relationGroupId','c');
  assert.equal(await tab.evaluate(`statusNode===document.querySelector('[data-relation-selection-status]')&&statusNode.textContent===words[${JSON.stringify(lang)}].group+': Cliente Ä · c'`),true);
 }
 const ax=(await tab.send('Accessibility.getFullAXTree')).nodes.filter(x=>x.role?.value==='status');
 assert.equal(ax.length,1);assert.equal(ax[0].ignored,false);
 const properties=Object.fromEntries(ax[0].properties.map(x=>[x.name,x.value.value]));assert.equal(properties.live,'polite');assert.equal(properties.atomic,true);
 assert.equal(await tab.evaluate(`document.querySelector('[data-relation-group]').hasAttribute('aria-live')`),false);
 await writeFile(path.join(out,'accessibility-status.json'),JSON.stringify(ax,null,2)+'\n');
 checks.push('EN/DE/ES preserve names; Edge accessibility tree exposes one polite atomic status, without live lists.');
 assert.ok(requests.every(x=>x.method==='GET'&&!x.url.startsWith('/api')));assert.deepEqual(errors,[]);successful=true;
}catch(e){failure={name:e.name,message:e.message};}
finally{
 try{if(browser)await browser.send('Browser.close');else edge.kill();if(edge.exitCode===null){await Promise.race([once(edge,'exit'),delay(5000)]);if(edge.exitCode===null){edge.kill();await once(edge,'exit')}}}catch(e){cleanupError=e.message;edge.kill()}
 for(const ws of websockets)ws.close();for(const s of connections)s.destroy();await new Promise(resolve=>server.close(resolve));
 const result={successful,checks,failure,cleanupError,browser:info?.Browser,platform:process.platform,node:process.version,sourceSha256:hash(bytes),sourceUnchanged:hash(await readFile(source))===hash(bytes),componentBundleOnly:true,fullApplicationBuild:false,syntheticProps:true,actualQaAccessed:false,postgresqlExecuted:false,screenReaderSpeechTested:false,ownedEdgeStopped:edge.exitCode!==null||edge.signalCode!==null,requests};
 await writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));if(!successful||cleanupError||!result.ownedEdgeStopped)process.exitCode=1;
}
