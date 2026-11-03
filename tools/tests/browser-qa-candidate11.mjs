// Tests the local worksheet in a fresh Edge profile; no RackClick service/VM.
import {spawn} from 'node:child_process';
import {mkdir, readFile, writeFile, readdir} from 'node:fs/promises';
import {createServer} from 'node:net';
import {once} from 'node:events';
import {randomUUID} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import {validateReport,summarize} from '../qa_candidate11.mjs';
const root=path.resolve(import.meta.dirname,'../..');
const out=process.env.RACKCLICK_QA11_OUTPUT;
if(!out||!path.resolve(out).startsWith(path.join(root,'.local')+path.sep))throw Error('New private output under .local required');
await mkdir(out,{recursive:false});const downloads=path.join(out,'downloads');await mkdir(downloads);
const portServer=createServer();portServer.listen(0,'127.0.0.1');await once(portServer,'listening');
const port=portServer.address().port;await new Promise(r=>portServer.close(r));
const edge=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
 ['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run',
 '--remote-debugging-address=127.0.0.1','--remote-debugging-port='+port,'--user-data-dir='+path.join(out,'profile'),
 '--window-size=1300,1000','about:blank'],{windowsHide:true,stdio:'ignore'});
const checks=[],errors=[];let ws;let sequence=0;const pending=new Map();
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function poll(fn,label){let last;for(let i=0;i<150;i++){try{const value=await fn();if(value)return value;}catch(e){last=e;}await delay(100);}throw Error(label+': '+(last?.message||'timeout'));}
async function send(method,params={}){
 const id=++sequence;return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method));},10000);
  pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}));
 });
}
async function evaluate(expression){
 const value=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
 if(value.exceptionDetails)throw Error('Evaluation failed');return value.result.value;
}
async function check(label,expression){assert.ok(await evaluate(expression),label);checks.push(label);}
async function selectFile(file){
 const d=await send('DOM.getDocument');const n=await send('DOM.querySelector',{nodeId:d.root.nodeId,selector:'#import'});
 await send('DOM.setFileInputFiles',{nodeId:n.nodeId,files:[file]});
}
const report={status:'FAIL',scope:'Synthetic worksheet UI in new Edge profile, not Wascar QA or application/VM acceptance',checks};
try{
 const tab=await poll(async()=>{
  const r=await fetch('http://127.0.0.1:'+port+'/json/list');
  if(!r.ok)return false;
  return (await r.json()).find(t=>t.type==='page' && t.url==='about:blank');
 },'Edge page (exclude extension/background targets)');
 ws=new WebSocket(tab.webSocketDebuggerUrl);await once(ws,'open');
 ws.addEventListener('message',event=>{
  const value=JSON.parse(event.data);
  if(value.id){const item=pending.get(value.id);if(item){pending.delete(value.id);clearTimeout(item.timer);value.error?item.reject(Error(value.error.message)):item.resolve(value.result);}}
  else if(value.method==='Page.javascriptDialogOpening')send('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});
  else if(value.method==='Runtime.exceptionThrown')errors.push(value.params.exceptionDetails.text);
 });
 await send('Page.enable');await send('Runtime.enable');
 await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});
 await send('Page.navigate',{url:pathToFileURL(path.join(root,'QA-CIERRE-CANDIDATA11.html')).href});
 await poll(()=>evaluate("document.querySelectorAll('[data-case]').length===14 && document.querySelector('#summary').textContent.includes('0/14')"),'Worksheet ready');
 checks.push('14 cases start untested');
 await evaluate("localStorage.setItem('rackclick-qa-prior-sentinel','previous notes preserved');document.querySelector('#origin').value='https://192.0.2.11:5443';document.querySelector('#origin').dispatchEvent(new Event('change'));document.querySelector('#confirmed').checked=true;document.querySelector('#confirmed').dispatchEvent(new Event('change'));");
 const notes='AUTOMATED TEST ONLY — <img src=x onerror=alert(1)> — not Wascar results';
 await evaluate("document.querySelector('[data-case=\"QA-166\"] [data-notes]').value="+JSON.stringify(notes)+";document.querySelector('[data-case=\"QA-166\"] [data-notes]').dispatchEvent(new Event('change'));document.querySelector('[data-case=\"QA-166\"] [data-result]').value='Pass';document.querySelector('[data-case=\"QA-166\"] [data-result]').dispatchEvent(new Event('change'));");
 await check('Pass and untrusted note stored without HTML execution',"document.querySelector('#summary').textContent.includes('1/14') && document.querySelectorAll('img').length===0");
 await send('Page.reload');
 await poll(()=>evaluate("document.querySelector('[data-case=\"QA-166\"] [data-notes]')?.value==="+JSON.stringify(notes)),'Reload notes');
 checks.push('reload preserves result and exact notes');
 await evaluate("document.querySelector('#export').click()");
 const downloaded=await poll(async()=>{const files=await readdir(downloads);return files.find(n=>n.endsWith('.json'));},'JSON export');
 const actual=JSON.parse(await readFile(path.join(downloads,downloaded),'utf8'));
 const spec=JSON.parse(await readFile(path.join(root,'docs/QA-CIERRE-CANDIDATA11.json'),'utf8'));
 validateReport(actual,spec);assert.equal(summarize(actual,spec).counts.Pass,1);assert.equal(summarize(actual,spec).adoption,false);
 checks.push('downloaded JSON exact candidate and no adoption');
 const key='rackclick.qa.candidate11.'+spec.candidate.archiveSha256;
 const beforeImport=await evaluate('localStorage.getItem('+JSON.stringify(key)+')');
 const invalid=structuredClone(actual);invalid.candidate.edition='10';
 const invalidPath=path.join(out,'invalid-fixture.json');await writeFile(invalidPath,JSON.stringify(invalid));
 await selectFile(invalidPath);
 await poll(()=>evaluate("document.querySelector('#notice').textContent.startsWith('Copia rechazada')"),'Wrong edition rejected');
 assert.equal(await evaluate('localStorage.getItem('+JSON.stringify(key)+')'),beforeImport);checks.push('wrong edition import preserves all current notes');
 const valid=structuredClone(actual);valid.records={'QA-167':{result:'Pass',notes:'AUTOMATED second synthetic record',caseSha256:spec.cases.find(c=>c.id==='QA-167').caseSha256,updatedUtc:new Date().toISOString()}};
 const validPath=path.join(out,'valid-fixture.json');await writeFile(validPath,JSON.stringify(valid));
 await selectFile(validPath);await poll(()=>evaluate("document.querySelector('#summary').textContent.includes('2/14')"),'Partial import');
 await check('partial import keeps pre-existing case',"document.querySelector('[data-case=\"QA-166\"] [data-notes]').value==="+JSON.stringify(notes));
 const stale=JSON.parse(await evaluate('localStorage.getItem('+JSON.stringify(key)+')'));stale.records['QA-166'].caseSha256='0'.repeat(64);
 await evaluate('localStorage.setItem('+JSON.stringify(key)+','+JSON.stringify(JSON.stringify(stale))+')');await send('Page.reload');
 await poll(()=>evaluate("document.querySelector('[data-case=\"QA-166\"] [data-badge]')?.textContent.startsWith('Desactualizado')"),'Stale row');
 await evaluate("document.querySelector('[data-case=\"QA-166\"] [data-notes]').value+=' additional note';document.querySelector('[data-case=\"QA-166\"] [data-notes]').dispatchEvent(new Event('change'));");
 await check('notes alone cannot promote stale Pass',"document.querySelector('[data-case=\"QA-166\"] [data-badge]').textContent.startsWith('Desactualizado') && document.querySelector('#summary').textContent.includes('1/14')");
 await evaluate("document.querySelector('[data-case=\"QA-166\"] [data-result]').value='Pass';document.querySelector('[data-case=\"QA-166\"] [data-result]').dispatchEvent(new Event('change'));");
 await check('explicit outcome reconfirmation updates current case',"document.querySelector('#summary').textContent.includes('2/14')");
 await check('unrelated prior result storage untouched',"localStorage.getItem('rackclick-qa-prior-sentinel')==='previous notes preserved'");
 assert.deepEqual(errors,[]);checks.push('no browser script errors');
 const shot=await send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(out,'worksheet.png'),Buffer.from(shot.data,'base64'));
 report.status='PASS';
}catch(error){
 report.error=error.message;report.browserErrors=errors;process.exitCode=1;
 try{
  report.observed=await evaluate("({rows:document.querySelectorAll('[data-case]').length,summary:document.getElementById('summary')?.textContent,url:location.href})");
  const shot=await send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(out,'failure.png'),Buffer.from(shot.data,'base64'));
 }catch{}
}
finally{
 await writeFile(path.join(out,'RESULTADOS.json'),JSON.stringify(report,null,2)+'\n');
 if(ws){try{await send('Browser.close');}catch{}ws.close();}
 await Promise.race([once(edge,'exit'),delay(3000)]);if(edge.exitCode===null)edge.kill();
 console.log(JSON.stringify(report));
}
