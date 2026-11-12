// Real app/HTTP/PostgreSQL scenario. Run only against a new empty isolated lab.
import assert from 'node:assert/strict';
import {mkdir,readFile,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
process.env.RACKCLICK_FIXTURE ||= '{}';
const {runScenario,poll,root}=await import('./browser-quince-support.mjs');
const expected={customers:50,sites:66,buildings:88,rooms:226,racks:180,devices:1563,portGroups:2869,ports:20665,connections:2207};
const panel=async tab=>{await tab.click('[data-admin-users]');await tab.wait(`!!document.querySelector('[data-admin-inventory-data]')&&!document.querySelector('[data-admin-inventory-data]').getAttribute('aria-busy').includes('true')`,'inventory data panel');await tab.click('[data-admin-section-link=inventory-data]');};
const waitIdle=tab=>tab.wait(`document.querySelector('[data-admin-inventory-data]').getAttribute('aria-busy')==='false'`,'inventory operation settled');
const state=tab=>tab.evaluate(`fetch('/api/v1/admin/inventory-data').then(r=>r.json())`);
const security=tab=>tab.evaluate(`fetch('/api/v1/me').then(r=>r.json()).then(x=>({user:x.user,systemhausCapabilities:x.permissions.systemhausCapabilities}))`);
await runScenario(async({first,session,browser,checks,origin,shot})=>{
 const before=await security(first);await panel(first);assert.equal((await state(first)).empty,true);
 for(const [lang,title] of [['en','Data and inventory copies'],['de','Daten und Inventarkopien'],['es','Datos y copias de inventario']]){
  await first.click('.ir-all-clients');await first.wait(`!!document.querySelector('.rc-settings select')`,'client settings');await first.field('.rc-settings select',lang);await panel(first);await first.wait(`document.querySelector('[data-admin-inventory-data] h2').textContent===${JSON.stringify(title)}`,'translated title');assert.equal(await first.evaluate(`document.querySelector('[data-admin-section-link=inventory-data]').textContent`),title);
 }
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-inventory-data-card]').length`),3);assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-demo]').disabled`),true);
 checks.push('Three RC9 administration cards and navigation translated EN/DE/ES; explicit Demo50 confirmation required.');

 // A request stopped before reaching the server still remains pending until
 // the real server acknowledges an explicit cancellation.
 await first.send('Fetch.enable',{patterns:[{urlPattern:'*/api/v1/admin/inventory-data/backup',requestStage:'Request'}]});
 await first.click('[data-inventory-data-backup]');
 const stopped=await poll(()=>first.paused?.find(x=>x.request.url.endsWith('/inventory-data/backup')),'paused backup');
 await first.send('Fetch.failRequest',{requestId:stopped.requestId,errorReason:'Aborted'});await first.send('Fetch.disable');await waitIdle(first);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-inventory-data-pending]')&&document.querySelector('[data-admin-account-controls]').disabled`),true);
 await first.click('[data-inventory-data-check]');await waitIdle(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-inventory-data-unknown]')`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-cancel]').disabled`),true);await first.click('[name=inventoryCancelConfirm]');await first.click('[data-inventory-data-cancel]');
 await first.wait(`!!document.querySelector('[data-inventory-data-cancelled]')&&!document.querySelector('[data-inventory-data-pending]')`,'server cancelled backup');assert.equal((await state(first)).empty,true);
 checks.push('Unsent intercepted backup remains pending after notRecorded, blocks other controls and clears only after explicit real server cancellation.');

 // Lose only the response after the actual server transaction has committed.
 first.paused=[];await first.send('Fetch.enable',{patterns:[{urlPattern:'*/api/v1/admin/inventory-data/demo50',requestStage:'Response'}]});
 await first.click('[name=inventoryDemoConfirm]');await first.click('[data-inventory-data-demo]');await first.wait(`!!document.querySelector('[data-inventory-data-pending]')`,'durable demo intention');
 const original=await first.evaluate(`document.querySelector('[data-inventory-data-pending] strong').textContent`);
 const committed=await poll(()=>first.paused?.find(x=>x.request.url.endsWith('/inventory-data/demo50')&&x.responseStatusCode===200),'committed demo response',60000);
 await first.send('Fetch.failRequest',{requestId:committed.requestId,errorReason:'Aborted'});await first.send('Fetch.disable');await waitIdle(first);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-inventory-data-pending]')&&document.querySelector('[data-inventory-data-backup]').disabled`),true);
 await first.send('Page.reload');await first.wait(`!!document.querySelector('.ir-nav')`,'reload session');await panel(first);
 await first.wait(`!!document.querySelector('[data-inventory-data-receipt]')&&!document.querySelector('[data-inventory-data-pending]')`,'original commit recovered');
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-receipt-request]').textContent`),original);
 const loaded=await state(first);assert.deepEqual(loaded.counts,expected);assert.equal(loaded.empty,false);assert.deepEqual(await security(first),before);
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-demo]').disabled&&document.querySelector('[data-inventory-data-restore]').disabled`),true);
 checks.push('Real Demo50 commit with lost response is recovered from durable journal after reload under the same request ID; exact nine counts and account/permissions preserved.');

 const second=await session();await panel(second);assert.deepEqual((await state(second)).counts,expected);assert.deepEqual(await security(second),before);
 const names=await second.evaluate(`fetch('/api/v1/customers').then(r=>r.json()).then(a=>a.map(x=>x.name).sort())`);assert.equal(names.length,50);
 await second.click('.ir-all-clients');await second.wait(`!!document.querySelector('.rc-settings select')`,'second-session client settings');await second.field('.rc-settings select','de');assert.deepEqual(await second.evaluate(`fetch('/api/v1/customers').then(r=>r.json()).then(a=>a.map(x=>x.name).sort())`),names);await second.field('.rc-settings select','es');await panel(second);
 checks.push('Second real login reads the 50 customers; language switching preserves all stored customer names.');

 await first.click('[data-inventory-data-backup]');await first.wait(`!!document.querySelector('[data-inventory-data-download]')&&!document.querySelector('[data-inventory-data-download]').disabled&&!document.querySelector('[data-inventory-data-pending]')`,'verified backup download');
 const backupRequest=await first.evaluate(`document.querySelector('[data-inventory-data-receipt-request]').textContent`);
 const metadata=await first.evaluate(`fetch('/api/v1/admin/inventory-data/operations/'+${JSON.stringify(backupRequest)}).then(r=>r.json()).then(x=>({sha256:x.operation.archive.sha256,byteLength:x.operation.archive.byteLength,filename:x.operation.archive.filename,counts:x.operation.counts}))`);
 assert.deepEqual(metadata.counts,expected);
 const downloadDir=path.join(root,'.local/browser-test/admin-data-download-'+crypto.randomUUID());await mkdir(downloadDir,{recursive:true});
 const {targetInfo}=await first.send('Target.getTargetInfo');assert.ok(targetInfo.browserContextId,'isolated download context');
 await browser.send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloadDir,browserContextId:targetInfo.browserContextId});await first.click('[data-inventory-data-download]');
 const downloaded=path.join(downloadDir,metadata.filename);await poll(async()=>{try{return(await stat(downloaded)).size===metadata.byteLength}catch{return false}},'saved archive');const bytes=await readFile(downloaded);assert.equal(createHash('sha256').update(bytes).digest('hex'),metadata.sha256);
 checks.push('Downloaded inventory file matches the server byte length and SHA-256; archive stays in a private isolated test directory.');

 const document=await first.send('DOM.getDocument');const input=await first.send('DOM.querySelector',{nodeId:document.root.nodeId,selector:'[name=inventoryDataFile]'});await first.send('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[downloaded]});await first.wait(`!document.querySelector('[data-inventory-data-preview]').disabled`,'selected copy hashed');await first.click('[data-inventory-data-preview]');await first.wait(`!!document.querySelector('[data-inventory-data-preview-result]')`,'real copy preview');
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-restore]').disabled&&document.querySelector('[name=inventoryRestoreConfirm]').disabled`),true);assert.deepEqual((await state(first)).counts,expected);assert.deepEqual(await security(first),before);
 checks.push('Real JSON file selection and server preview work; restoration and its confirmation stay disabled on populated inventory. Empty-target restoration is covered separately by backend/target-lab tests.');
 await shot(first,'inventory-data-es.png');
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await first.click('[data-admin-section-link=inventory-data]');assert.equal(await first.evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);assert.equal(await first.evaluate(`document.activeElement.id`),'rc-admin-inventory-data');await shot(first,'inventory-data-mobile.png');
 checks.push('Data navigation focuses its panel at 390px without horizontal page overflow.');
});
