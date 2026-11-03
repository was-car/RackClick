// Native Edge/CDP review of a local artifact. No API, database or user profiles.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
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
 const catalog=JSON.parse(await readFile(path.resolve('development/frontend/src/hardware-german-repeaters.generated.json'),'utf8')).flatMap(c=>c.profiles);assert.equal(catalog.length,10);
 for(let i=0;i<300;i++){if(await evalJs("document.querySelectorAll('[data-repeater-model]').length===10"))break;if(errors.length)break;await delay()}
 assert.equal(await evalJs("document.querySelectorAll('[data-repeater-model]').length"),10);
 for(const width of [1280,700,390]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:1050,deviceScaleFactor:1,mobile:width<500});await delay();
  for(const model of catalog){
   await evalJs(`document.querySelector('[data-repeater-model="${model.key}"]').click()`);await delay();
   for(const [face,text] of [['front','Frontal'],['rear','Trasera']]){
    await evalJs(`([...document.querySelectorAll('[data-room-hardware] .rc-inline-buttons button')].find(b=>b.textContent===${JSON.stringify(text)})).click()`);await delay();
    const m=await evalJs(`(()=>{const s=document.querySelector('[data-room-hardware]');return {model:${JSON.stringify(model.key)},face:${JSON.stringify(face)},viewport:${width},pageOverflow:document.documentElement.scrollWidth>innerWidth+1,owner:s.dataset.roomHardware,ports:[...s.querySelectorAll('[data-room-port]')].map(b=>({id:b.dataset.vport,owner:b.dataset.portOwner,w:b.getBoundingClientRect().width,h:b.getBoundingClientRect().height})),plug:s.querySelectorAll('[data-hardware-connector="eu-2pin-plug"]').length}})()`);
    assert.equal(m.pageOverflow,false,model.key);assert.equal(m.owner,model.key);const expected=model.groups.filter(g=>g.face===face).reduce((n,g)=>n+g.count,0);assert.equal(m.ports.length,expected,model.key+face);assert.equal(new Set(m.ports.map(p=>p.id)).size,expected);
    for(const p of m.ports){assert.ok(p.w>=23.99&&p.h>=23.99,p.id);assert.equal(p.owner,model.key);await evalJs(`(()=>{const b=document.querySelector('[data-room-port="${p.id}"]');b.scrollIntoView({inline:'nearest',block:'nearest'});b.focus();b.click()})()`);await delay();assert.equal(await evalJs(`document.querySelector('[data-room-port="${p.id}"]').getAttribute('aria-pressed')`),'true')}
    if(model.groups.some(g=>g.physicalConnector==='eu-2pin-plug'&&g.face===face))assert.equal(m.plug,1);
    faces.push(m);
   }
   await evalJs("document.querySelector('[data-room-enlarge]').click()");await delay();assert.equal(await evalJs("document.querySelector('[data-room-enlarge]').getAttribute('aria-expanded')"),'true');await evalJs("document.querySelector('[data-room-enlarge]').click()");await delay();
  }
 }
 for(const query of ['repetidor','repetidores','repeter','Verstärker','FRITZ Repeater','AVM repeater','devolo','Telekom','TP-Link']){
  await evalJs(`(()=>{const i=document.querySelector('[data-hardware-profile]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,${JSON.stringify(query)});i.dispatchEvent(new Event('input',{bubbles:true}));i.focus()})()`);await delay();assert.ok(await evalJs("document.querySelectorAll('[data-hardware-choice]').length>0"),query);
 }
 for(const [lang,front] of [['de','Vorderseite'],['en','Front'],['es','Frontal']]){
  await evalJs(`(()=>{const s=document.querySelector('.controls select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(s,${JSON.stringify(lang)});s.dispatchEvent(new Event('change',{bubbles:true}))})()`);await delay();assert.ok(await evalJs(`([...document.querySelectorAll('[data-room-hardware] button')].some(b=>b.textContent===${JSON.stringify(front)}))`));
 }
 assert.deepEqual(errors,[]);assert.equal(await evalJs("document.querySelectorAll('[data-mounted-rack]').length"),0);
 await writeFile(path.join(out,'preview.png'),Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const report={result:'PASS',models:10,faces:20,viewportCases:faces.length,portRepresentations:faces.reduce((n,f)=>n+f.ports.length,0),searchQueries:9,languages:3,noRackMounts:true,exceptions:errors,measurements:faces,limits:['Real room renderer with local fixtures, no API/SQL persistence or manual Wascar QA.']};await writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({result:'PASS',models:10,faces:20,viewportCases:report.viewportCases,portRepresentations:report.portRepresentations,searchQueries:9,languages:3}));await send('Browser.close');browserClosed=true;
}catch(error){let page;try{page=await debugEval("({url:location.href,ready:document.readyState,title:document.title,body:document.body?.innerText?.slice(0,1200)})")}catch{}await writeFile(path.join(out,'browser-failure.json'),JSON.stringify({result:'FAIL',error:String(error),exceptions:errors,measurements:faces,page},null,2)+'\n');console.error(JSON.stringify({result:'FAIL',error:String(error),exceptions:errors,page}));throw error}
finally{if(!browserClosed&&ws?.readyState===WebSocket.OPEN&&sendProtocol)try{await Promise.race([sendProtocol('Browser.close'),new Promise(r=>setTimeout(r,1500))])}catch{}ws?.close();if(edge.exitCode===null)edge.kill()}
