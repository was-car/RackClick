// Native Edge/CDP review of a local artifact. No API, database or user profiles.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createServer} from 'node:net';
const input=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);await mkdir(out,{recursive:true});
const port=await new Promise((resolve,reject)=>{const server=createServer();server.on('error',reject);server.listen(0,'127.0.0.1',()=>{const value=server.address().port;server.close(()=>resolve(value))})});
const edge=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port='+port,'--user-data-dir='+path.join(out,'edge'),'about:blank'],{windowsHide:true,stdio:'ignore'});
let ws,seq=0,debugEval,sendProtocol,browserClosed=false;const pending=new Map(),errors=[],faces=[];
const delay=()=>new Promise(r=>setTimeout(r,70));
try{
 let tab;for(let i=0;i<100;i++){try{const tabs=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();tab=tabs.find(t=>t.type==='page'&&t.url==='about:blank');if(tab)break}catch{}await delay()}
 assert.ok(tab,'Own blank page target required; background extensions are not pages');ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true})});
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
 sendProtocol=send;
 const evalJs=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value};
 debugEval=evalJs;
 await send('Page.enable');await send('Runtime.enable');await send('Emulation.setDeviceMetricsOverride',{width:1400,height:1050,deviceScaleFactor:1,mobile:false});const navigation=await send('Page.navigate',{url:pathToFileURL(path.join(input,'index.html')).href});assert.equal(navigation.errorText,undefined);
 for(let i=0;i<300;i++){if(await evalJs("document.querySelectorAll('[data-german-model]').length===6"))break;if(errors.length)break;await delay()}
 const keys=await evalJs("[...document.querySelectorAll('[data-german-model]')].map(b=>b.dataset.germanModel)");assert.equal(keys.length,6);
 for(const key of keys){
  await evalJs(`document.querySelector('[data-german-model="${key}"]').click()`);await delay();
  for(const face of ['Frontal','Trasera']){
   await evalJs(`([...document.querySelectorAll('.face-controls button')].find(b=>b.textContent===${JSON.stringify(face)})).click()`);await delay();
   const m=await evalJs(`(()=>{const s=document.querySelector('.rc-shell-scroll');return {model:${JSON.stringify(key)},face:${JSON.stringify(face)},available:s.clientWidth,scrollWidth:s.scrollWidth,bodyOverflow:document.documentElement.scrollWidth>innerWidth+1,ports:[...s.querySelectorAll('[data-vport]')].map(b=>({id:b.dataset.vport,type:b.dataset.portType,w:b.getBoundingClientRect().width,h:b.getBoundingClientRect().height}))}})()`);
   assert.equal(m.bodyOverflow,false);assert.equal(new Set(m.ports.map(p=>p.id)).size,m.ports.length);
   for(const p of m.ports){assert.ok(p.w>=23.99&&p.h>=23.99,p.id);await evalJs(`(()=>{const b=document.querySelector('[data-vport="${p.id}"]');b.scrollIntoView({block:'nearest',inline:'nearest'});b.focus();b.click()})()`);await delay();assert.ok((await evalJs("document.querySelector('[data-port-selection]').textContent")).includes(p.type))}
   if(face==='Frontal'){assert.equal(m.ports.length,0);assert.ok(m.scrollWidth<=m.available+1)}
   faces.push(m);
  }
 }
 for(const query of ['Drytek','Fritzbox','Fritz!Box','fritz box','AVM']){
  await evalJs(`(()=>{const i=document.querySelector('[data-hardware-profile]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,${JSON.stringify(query)});i.dispatchEvent(new Event('input',{bubbles:true}));i.focus()})()`);await delay();
  assert.equal(await evalJs("document.querySelector('[data-hardware-profile]').getAttribute('aria-expanded')"),'true');assert.ok(await evalJs("document.querySelectorAll('[data-hardware-choice]').length>0"));
 }
 for(const key of ['tplink-tl-sg108e-un6-0','zyxel-xgs1250-12','selected-nb-2ffc5d29f711ec36']){
  await evalJs(`document.querySelector('[data-review-example="${key}"]').click()`);await delay();
  await evalJs("document.querySelector('[data-native-rack-review]').open=true");await delay();
  assert.equal(await evalJs("document.querySelectorAll('[data-native-rack-review] [data-mounted-on]').length"),1);
  assert.equal(await evalJs("[...document.querySelectorAll('[data-native-rack-review] .rc-model-details')].every(d=>!d.open)"),true);
  const before=await evalJs("document.querySelector('[data-native-rack-review] [data-mounted-on]').getBoundingClientRect().width");
  await evalJs("document.querySelector('[data-native-rack-review] [data-hardware-enlarge]').click()");await delay();
  assert.equal(await evalJs("document.querySelector('[data-native-rack-review] [data-hardware-enlarge]').getAttribute('aria-expanded')"),'true');
  assert.ok(await evalJs("document.querySelector('[data-native-rack-review] [data-mounted-on]').getBoundingClientRect().width")>=before);
  await evalJs("document.querySelector('[data-native-rack-review] [data-hardware-enlarge]').click();document.querySelector('[data-native-rack-review]').open=false");await delay();
 }
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay();
 assert.equal(await evalJs('document.documentElement.scrollWidth>innerWidth+1'),false);
 await writeFile(path.join(out,'preview.png'),Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 assert.deepEqual(errors,[]);const report={result:'PASS',models:6,faces:faces.length,ports:faces.reduce((n,f)=>n+f.ports.length,0),aliases:5,nativeRackExamples:3,mobilePageOverflow:false,exceptions:errors,measurements:faces,limits:['Local renderer only; no API/SQL persistence or manual Wascar QA.']};
 await writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({result:report.result,models:6,faces:12,ports:report.ports,aliases:5,nativeRackExamples:3,mobilePageOverflow:false}));await send('Browser.close');browserClosed=true;
}catch(error){let page;try{page=await debugEval("({url:location.href,ready:document.readyState,title:document.title,body:document.body?.innerText?.slice(0,1200),scripts:[...document.scripts].map(s=>s.src)})")}catch{}await writeFile(path.join(out,'browser-failure.json'),JSON.stringify({result:'FAIL',error:String(error),exceptions:errors,measurements:faces,page},null,2)+'\n');console.error(JSON.stringify({result:'FAIL',exceptions:errors,page}));throw error}
finally{if(!browserClosed&&ws?.readyState===WebSocket.OPEN&&sendProtocol)try{await Promise.race([sendProtocol('Browser.close'),new Promise(r=>setTimeout(r,1500))])}catch{}ws?.close();if(edge.exitCode===null)edge.kill()}
