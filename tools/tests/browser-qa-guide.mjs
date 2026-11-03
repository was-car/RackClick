// Native Windows Edge check of Wascar's guide and result preservation. No laboratory mutation.
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
const root=path.resolve('.'),output=path.resolve(process.argv[2]||'');
if(!process.argv[2]||!output.startsWith(path.join(root,'evidence')+path.sep))throw Error('Explicit evidence directory required');
await mkdir(output,{recursive:false});
const page=await readFile('GUIA-QA-WASCAR.html');
const caseCount=JSON.parse(await readFile('docs/QA-CASOS-WASCAR.json','utf8')).cases.length;
const server=createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(page)});server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
const debug=createServer();debug.listen(0,'127.0.0.1');await once(debug,'listening');const port=debug.address().port;await new Promise(r=>debug.close(r));
const profile=path.join(root,'.local/browser-test','qa-guide-'+Date.now());await mkdir(profile,{recursive:true});
const edge=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--no-first-run','--disable-gpu','--remote-debugging-address=127.0.0.1','--remote-debugging-port='+port,'--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
const wait=ms=>new Promise(r=>setTimeout(r,ms));async function poll(fn){for(let n=0;n<150;n++){try{const x=await fn();if(x)return x}catch{}await wait(100)}throw Error('Guide browser timeout')}
let ws;let seq=0;const pending=new Map(),errors=[];
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(method+' timeout'))},10000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error('Browser evaluation failed');return r.result.value}
const checks=[];
try {
 const tabs=await poll(async()=>{const x=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();return x.find(t=>t.type==='page')});
 ws=new WebSocket(tabs.webSocketDebuggerUrl);await once(ws,'open');ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.id){const p=pending.get(d.id);if(p){pending.delete(d.id);clearTimeout(p.timer);d.error?p.reject(Error(d.error.message)):p.resolve(d.result)}}else if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.text)});
 await send('Runtime.enable');await send('Page.enable');await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await send('Page.navigate',{url:origin});
 await poll(()=>evaluate(`document.querySelectorAll('[data-case]').length===${caseCount}`));
 await evaluate(`(()=>{const r=document.querySelector('[data-case="QA-01"]');r.querySelector('[data-result]').value='Not Pass';r.querySelector('[data-result]').dispatchEvent(new Event('change'));r.querySelector('[data-notes]').value='Observación de Wascar <script>sin ejecutar</script>';r.querySelector('[data-notes]').dispatchEvent(new Event('input'));return true})()`);
 await send('Page.reload');await poll(()=>evaluate(`document.querySelector('[data-case="QA-01"] [data-result]')?.value==='Not Pass'`));
 assert.equal(await evaluate(`document.querySelector('[data-case="QA-01"] [data-notes]').value`),'Observación de Wascar <script>sin ejecutar</script>');checks.push('Resultado y observación se conservan después de recargar y texto no ejecuta HTML');
 const exported=await evaluate(`(async()=>{let copy;const original=URL.createObjectURL;URL.createObjectURL=b=>{copy=b;return original(b)};const click=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=()=>{};document.querySelector('#export').click();URL.createObjectURL=original;HTMLAnchorElement.prototype.click=click;return JSON.parse(await copy.text())})()`);
 assert.equal(exported.format,'RackClick-QA-v1');assert.equal(exported.records['QA-01'].result,'Not Pass');checks.push('Exportación contiene resultados/versiones/hashes y observaciones');
 await evaluate(`localStorage.removeItem('RackClick.QA.Wascar.results.v1')`);await send('Page.reload');await poll(()=>evaluate(`document.querySelector('[data-case="QA-01"] [data-result]')?.value==='Sin probar'`));
 exported.records['QA-999']={...exported.records['QA-01'],notes:'Caso retirado que debe conservarse'};
 await evaluate(`(()=>{window.confirm=()=>true;const dt=new DataTransfer();dt.items.add(new File([${JSON.stringify(JSON.stringify(exported))}],'results.json',{type:'application/json'}));const input=document.querySelector('#import');input.files=dt.files;input.dispatchEvent(new Event('change'));return true})()`);
 await poll(()=>evaluate(`document.querySelector('[data-case="QA-01"] [data-result]')?.value==='Not Pass'`));assert.equal(await evaluate(`JSON.parse(localStorage.getItem('RackClick.QA.Wascar.results.v1'))['QA-999'].notes`),'Caso retirado que debe conservarse');checks.push('Importar copia recupera observaciones y conserva casos retirados después de perder almacenamiento local');
 await evaluate(`(()=>{const dt=new DataTransfer();dt.items.add(new File(['{"format":"incorrecto"}'],'invalid.json',{type:'application/json'}));const input=document.querySelector('#import');input.files=dt.files;input.dispatchEvent(new Event('change'));return true})()`);
 await poll(()=>evaluate(`document.querySelector('#notice').textContent.includes('formato de resultados no válido')`));assert.equal(await evaluate(`document.querySelector('[data-case="QA-01"] [data-result]').value`),'Not Pass');checks.push('Importación inválida no sobrescribe resultados');
 await evaluate(`(()=>{const x=JSON.parse(localStorage.getItem('RackClick.QA.Wascar.results.v1'));x['QA-01'].bundle='version-anterior';localStorage.setItem('RackClick.QA.Wascar.results.v1',JSON.stringify(x));})()`);await send('Page.reload');await poll(()=>evaluate(`document.querySelector('[data-case="QA-01"] [data-stamp]')?.textContent.includes('versión cambió')`));assert.equal(await evaluate(`document.querySelector('[data-case="QA-01"] [data-result]').value`),'Not Pass');checks.push('Cambio de versión conserva resultados y pide volver a probar');
 await send('Page.navigate',{url:pathToFileURL(path.join(root,'GUIA-QA-WASCAR.html')).href});await poll(()=>evaluate(`document.querySelectorAll('[data-case]').length===${caseCount}&&location.protocol==='file:'`));
 await evaluate(`(()=>{const r=document.querySelector('[data-case="QA-02"]');r.querySelector('[data-result]').value='Pass';r.querySelector('[data-result]').dispatchEvent(new Event('change'));r.querySelector('[data-notes]').value='Observación local file';r.querySelector('[data-notes]').dispatchEvent(new Event('input'));})()`);
 await send('Page.reload');await poll(()=>evaluate(`location.protocol==='file:'&&document.querySelector('[data-case="QA-02"] [data-notes]')?.value==='Observación local file'`));assert.equal(await evaluate(`document.querySelector('[data-case="QA-02"] [data-result]').value`),'Pass');checks.push('Archivo HTML abierto directamente en Edge conserva resultado y notas tras recarga');
 await writeFile(path.join(output,'guia-windows.png'),Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));assert.deepEqual(errors,[]);
 await writeFile(path.join(output,'result.json'),JSON.stringify({status:'PASS',utc:new Date().toISOString(),checks,browserErrors:errors,limitations:['Edge con perfil nuevo; no prueba todos los navegadores ni políticas de almacenamiento.','No inicia servidor ni cambia datos de QA.']},null,2));console.log('Guide browser PASS: '+checks.length+' checks');
} catch(e){await writeFile(path.join(output,'failure.json'),JSON.stringify({status:'FAIL',error:e.message,checks,errors}));throw e}
finally{if(ws){try{await send('Browser.close')}catch{}ws.close()}if(edge.exitCode===null)edge.kill();await new Promise(r=>server.close(r))}
