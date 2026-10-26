// One scoped Windows Edge/real-PostgreSQL scenario. No application mocks.
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {createServer} from 'node:net';
import {once} from 'node:events';
import path from 'node:path';
import assert from 'node:assert/strict';
const origin=process.env.RACKCLICK_TEST_ORIGIN,user=process.env.RACKCLICK_TEST_USERNAME,password=process.env.RACKCLICK_TEST_PASSWORD;
if(!origin||!user||!password||!['127.0.0.1','localhost','[::1]'].includes(new URL(origin).hostname))throw Error('Explicit isolated loopback fixture required.');
const root=path.resolve('../..'),out=process.env.RACKCLICK_TEST_OUTPUT,fixture=JSON.parse(process.env.RACKCLICK_FIXTURE),signals=process.env.RACKCLICK_SIGNALS;
if(!out)throw Error('Explicit evidence/signals required.');
const profile=path.join(root,'.local/browser-test','links1329-'+crypto.randomUUID());await mkdir(profile,{recursive:true});
const ps=createServer();ps.listen(0,'127.0.0.1');await once(ps,'listening');const port=ps.address().port;await new Promise(r=>ps.close(r));
const child=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port='+port,'--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
const clients=[],checks=[],errors=[],writes=[],selectionAccessibility=[];const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function poll(fn,label){const end=Date.now()+15000;let last;while(Date.now()<end){try{const r=await fn();if(r)return r;}catch(e){last=e;}await delay(80);}throw Error('Timeout: '+label+(last?': '+last.message:''));}
class CDP{constructor(ws){this.ws=ws;this.n=0;this.pending=new Map();ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const q=this.pending.get(m.id);if(q){this.pending.delete(m.id);clearTimeout(q.timer);m.error?q.reject(Error(m.error.message)):q.resolve(m.result);}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);else if(m.method==='Network.requestWillBeSent'&&m.params.request.method!=='GET')writes.push({method:m.params.request.method,path:new URL(m.params.request.url).pathname});});}static async open(url){const ws=new WebSocket(url);await once(ws,'open');const c=new CDP(ws);clients.push(c);return c;}send(method,params={}){const id=++this.n;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('CDP timeout '+method)),15000);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));});}async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;}async wait(expression,label){return poll(()=>this.evaluate(expression),label);}async click(selector){await this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}async field(selector,value){await this.evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const proto=e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));})()`);}}
let browser;
// A full administration page has other status regions. Inspect this exact DOM
// node in the accessibility tree, never count global role=status elements.
async function selectionStatus(tab,expected,label){
 assert.equal(await tab.evaluate(`window.relationStatusNode===document.querySelector('[data-relation-selection-status]')&&window.relationStatusNode.textContent===${JSON.stringify(expected)}`),true,label);
 const {root}=await tab.send('DOM.getDocument');
 const {nodeId}=await tab.send('DOM.querySelector',{nodeId:root.nodeId,selector:'[data-relation-selection-status]'});
 const {node}=await tab.send('DOM.describeNode',{nodeId});
 const {nodes}=await tab.send('Accessibility.getPartialAXTree',{backendNodeId:node.backendNodeId,fetchRelatives:false});
 const status=nodes.find(x=>x.backendDOMNodeId===node.backendNodeId);
 assert.ok(status);assert.equal(status.ignored,false);assert.equal(status.role.value,'status');
 const props=Object.fromEntries(status.properties.map(x=>[x.name,x.value.value]));
 assert.equal(props.live,'polite');assert.equal(props.atomic,true);
 assert.equal(await tab.evaluate(`!document.querySelector('[data-relation-group]')?.hasAttribute('aria-live')`),true);
 selectionAccessibility.push({label,text:expected,role:status.role.value,live:props.live,atomic:props.atomic,ignored:status.ignored});
}
try{
 const info=await poll(async()=>(await fetch('http://127.0.0.1:'+port+'/json/version')).json(),'Edge');browser=await CDP.open(info.webSocketDebuggerUrl);
 async function session(name=user){const c=await browser.send('Target.createBrowserContext'),t=await browser.send('Target.createTarget',{url:'about:blank',browserContextId:c.browserContextId});const ti=await poll(async()=>(await(await fetch('http://127.0.0.1:'+port+'/json/list')).json()).find(x=>x.id===t.targetId),'target'),tab=await CDP.open(ti.webSocketDebuggerUrl);for(const m of ['Runtime.enable','Network.enable','Page.enable'])await tab.send(m);await tab.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await tab.send('Page.navigate',{url:origin});await tab.wait(`!!document.querySelector('[name=username]')`,'login');await tab.field('select','es');await tab.field('[name=username]',name);await tab.field('[name=password]',password);await tab.evaluate(`document.querySelector('form').requestSubmit()`);await tab.wait(`!!document.querySelector('.ir-nav')`,'login confirmed');await tab.wait(`!!document.querySelector('.rc-settings select')&&!document.querySelector('.rc-settings select').disabled`,'preferences ready');await tab.field('.rc-settings select','es');await tab.wait(`document.querySelector('.rc-settings select').value==='es'&&!document.querySelector('.rc-settings select').disabled`,'Spanish confirmed');return tab;}

 const first=await session(),reader=await session('relations-reader');
 assert.equal(await reader.evaluate(`!!document.querySelector('[data-admin-users]')`),false);
 assert.equal(await reader.evaluate(`fetch('/api/v1/admin/user-groups').then(r=>r.status)`),403);
 await first.click('[data-admin-users]');await first.wait(`!!document.querySelector('[data-admin-groups]')`,'groups toggle');await first.click('[data-admin-groups]');
 await first.wait(`!!document.querySelector('[name=relationGroupId]')&&!document.querySelector('[name=relationGroupId]').disabled`,'shared snapshot');
 await first.evaluate(`window.relationStatusNode=document.querySelector('[data-relation-selection-status]');true`);
 await selectionStatus(first,'Elegir grupo','Before first group selection');
 const before=writes.length;
 await first.field('[name=groupName]','Borrador literal 東京');
 const selectedUser=await first.evaluate(`document.querySelector('[name=adminSelectedUser]').value`);
 await first.field('[name=relationGroupId]',fixture.ids.u1);
 await first.wait(`!!document.querySelector('[data-relation-group="${fixture.ids.u1}"]')`,'user group details');
 await selectionStatus(first,'Grupo seleccionado: Técnicos <img> 東京 · '+fixture.ids.u1,'Initial UUID');
 async function openLink(tab,type,id,label,key=false){
  const selector='[data-relation-open-'+type+'="'+id+'"]';
  await tab.wait(`!!document.querySelector(${JSON.stringify(selector)})`,label+' exists');
  assert.equal(await tab.evaluate(`document.querySelector(${JSON.stringify(selector)}).type`),'button');
  assert.ok((await tab.evaluate(`document.querySelector(${JSON.stringify(selector)}).getAttribute('aria-label')`)).includes(id));
  const count=writes.filter(w=>w.path.startsWith('/api/v1/admin/')).length;
  if(key){await tab.send('Page.bringToFront');await tab.evaluate(`document.querySelector(${JSON.stringify(selector)}).focus()`);await tab.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});await tab.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});}
  else await tab.click(selector);
  await tab.wait(`!!document.querySelector('[data-relation-group="${id}"]')`,label+' target');
  assert.equal(await tab.evaluate('document.activeElement.name'),'relationGroupId');
  assert.equal(await tab.evaluate('document.querySelector("[name=relationGroupId]").value'),id);
  assert.equal(writes.filter(w=>w.path.startsWith('/api/v1/admin/')).length,count);
 }
 await openLink(first,'customer',fixture.ids.cg1,'Grant targets customer group',true);
 await selectionStatus(first,'Grupo seleccionado: Clientes homónimos · '+fixture.ids.cg1,'Customer link');
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-relation-source]').length`),2);
 await openLink(first,'user',fixture.ids.u2,'Second homonymous source user group');
 await selectionStatus(first,'Grupo seleccionado: Técnicos <img> 東京 · '+fixture.ids.u2,'Inverse UUID');
 await openLink(first,'customer',fixture.ids.cg1,'Return to exact customer UUID');
 await openLink(first,'user',fixture.ids.u1,'Return to first homonymous source');
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-relation-open-customer]').length`),1);
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-admin-group-relations] img,[data-admin-group-relations] script').length`),0);
 await first.field('[name=relationGroupType]','customer');await first.field('[name=relationGroupId]',fixture.ids.cg2);
 assert.ok((await first.evaluate(`document.querySelector('[data-relation-group]').textContent`)).includes(fixture.ids.c1));
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-relation-open-user]').length`),0);
 assert.equal(await first.evaluate(`document.querySelector('[name=groupName]').value`),'Borrador literal 東京');
 assert.equal(await first.evaluate(`document.querySelector('[name=adminSelectedUser]').value`),selectedUser);
 checks.push('Exact grant/inverse navigation by UUID among homonyms; multiple parents, global/direct grants excluded; Enter, stable selector focus and literal names.');
 for(const lang of ['en','de','es']){
  const localized=await session();
  await localized.wait(`!document.querySelector('.rc-settings select').disabled`,'preferences loaded');
  await localized.field('.rc-settings select',lang);
  await localized.wait(`document.querySelector('.rc-settings select').value===${JSON.stringify(lang)}&&!document.querySelector('.rc-settings select').disabled`,'language saved');
  await localized.click('[data-admin-users]');await localized.wait(`!!document.querySelector('[data-admin-groups]')`,'localized groups');await localized.click('[data-admin-groups]');await localized.wait(`!!document.querySelector('[name=relationGroupId]')&&!document.querySelector('[name=relationGroupId]').disabled`,'localized snapshot');
  await localized.evaluate(`window.relationStatusNode=document.querySelector('[data-relation-selection-status]');true`);
  await localized.field('[name=relationGroupId]',fixture.ids.u1);
  await selectionStatus(localized,{en:'Selected group',de:'Ausgewählte Gruppe',es:'Grupo seleccionado'}[lang]+': Técnicos <img> 東京 · '+fixture.ids.u1,'Localized '+lang);
  await openLink(localized,'customer',fixture.ids.cg1,'Localized link '+lang,true);
  await openLink(localized,'user',fixture.ids.u1,'Localized inverse '+lang);
  await localized.wait(`document.querySelector('[data-admin-group-relations] h3').textContent.includes(${JSON.stringify({en:'Group relationships',de:'Gruppenbeziehungen',es:'Relaciones de grupos'}[lang])})`,'localized relationships');
  await localized.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  assert.ok(await localized.evaluate(`document.documentElement.scrollWidth<=innerWidth+1`));
  await localized.evaluate(`document.querySelector('[name=relationGroupType]').focus()`);
  await localized.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await localized.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
  assert.equal(await localized.evaluate(`document.activeElement.name`),'relationGroupId');
  await localized.evaluate(`document.querySelector('[data-admin-group-relations]').scrollIntoView({block:'start'})`);
  await writeFile(path.join(out,'relations-'+lang+'-390.png'),Buffer.from((await localized.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 }
 assert.equal(await first.evaluate(`document.querySelector('[name=groupName]').value`),'Borrador literal 東京');
 assert.equal(await first.evaluate(`document.querySelector('[name=adminSelectedUser]').value`),selectedUser);
 assert.equal(writes.filter(w=>w.path.startsWith('/api/v1/admin/')).length,0);checks.push('EN/DE/ES at390px, Tab between labeled selectors; zero writes, group draft and selected-user unchanged.');
 await writeFile(path.join(signals,'revoke.begin'),'ready');await poll(async()=>readFile(path.join(signals,'revoke.ready'),'utf8'),'real fixture revocation');
 assert.equal(await first.evaluate(`fetch('/api/v1/admin/user-groups').then(r=>r.status)`),403);
 await first.evaluate(`document.querySelector('.rc-admin-groups>button').click()`);
 await first.wait(`!document.querySelector('[data-relation-group]')&&document.querySelector('[name=relationGroupId]').disabled`,'old relationships removed');
 await selectionStatus(first,'Actualiza los grupos para cargar las relaciones vigentes.','Real403 removes stale selection and preserves status node');
 checks.push('Actual security.manage revocation returns403; Refresh hides previously selected relationships.');
 assert.deepEqual(errors,[]);
 checks.push('Existing compact polite/atomic status and stable selector focus verified with real links; no screen-reader speech claim.');
 const report={status:'PASS',browser:info.Browser,checks,selectionAccessibility,errors,screenReaderSpeechTested:false,limits:['One isolated1329 fixture; native full application, no AD/effective permission inference or Wascar QA.','Revocation simulated by fixture SQL, never by the read-only view.','DOM/AX verification does not test screen-reader speech. Read-only comparison covers eight group-related tables, not all39.']};await writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}catch(e){await writeFile(path.join(out,'browser-failure.json'),JSON.stringify({status:'FAIL',checks,error:String(e.stack),errors},null,2)+'\n');throw e;}
finally{if(browser)try{await browser.send('Browser.close');}catch{}for(const c of clients)c.ws.close();if(child.exitCode===null)child.kill();}
