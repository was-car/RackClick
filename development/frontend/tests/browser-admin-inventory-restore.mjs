// Real browser restoration into a second, empty, isolated application database.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
process.env.RACKCLICK_FIXTURE ||= '{}';
const {runScenario,root}=await import('./browser-quince-support.mjs');
const archive=path.resolve(process.env.RACKCLICK_INVENTORY_ARCHIVE||'');
assert.ok(archive.startsWith(path.join(root,'.local')+path.sep),'Explicit private synthetic archive required');
const bytes=await readFile(archive),sha256=createHash('sha256').update(bytes).digest('hex');
const expected={customers:50,sites:66,buildings:88,rooms:226,racks:180,devices:1563,portGroups:2869,ports:20665,connections:2207};
const state=tab=>tab.evaluate(`fetch('/api/v1/admin/inventory-data').then(r=>r.json())`);
// Effective per-customer permission projections legitimately grow with restored
// customers; compare identity and the pre-existing global authority instead.
const identity=tab=>tab.evaluate(`fetch('/api/v1/me').then(r=>r.json()).then(x=>({user:x.user,systemhausCapabilities:x.permissions.systemhausCapabilities}))`);
const panel=async tab=>{await tab.click('[data-admin-users]');await tab.wait(`document.querySelector('[data-admin-inventory-data]')?.getAttribute('aria-busy')==='false'`,'empty-target panel');await tab.click('[data-admin-section-link=inventory-data]');};
await runScenario(async({first,session,checks,shot})=>{
 const before=await identity(first);await panel(first);assert.equal((await state(first)).empty,true);
 const document=await first.send('DOM.getDocument');
 const input=await first.send('DOM.querySelector',{nodeId:document.root.nodeId,selector:'[name=inventoryDataFile]'});
 await first.send('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[archive]});
 await first.wait(`!document.querySelector('[data-inventory-data-preview]').disabled`,'archive read and hashed');
 await first.click('[data-inventory-data-preview]');await first.wait(`!!document.querySelector('[data-inventory-data-preview-result]')`,'preview');
 assert.equal((await state(first)).empty,true,'preview must not write');
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-preview-result]').textContent.includes('${sha256}')`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-restore]').disabled`),true);
 await first.click('[name=inventoryRestoreConfirm]');await first.click('[data-inventory-data-restore]');
 await first.wait(`!!document.querySelector('[data-inventory-data-receipt]')&&!document.querySelector('[data-inventory-data-pending]')&&document.querySelector('[data-admin-inventory-data]').getAttribute('aria-busy')==='false'`,'restore committed and navigation refreshed');
 assert.deepEqual((await state(first)).counts,expected);assert.deepEqual(await identity(first),before);
 assert.equal(await first.evaluate(`document.querySelectorAll('.ir-client-link').length`),50,'restored customers must appear in navigation without reloading');
 checks.push('A real downloaded inventory copy is selected and previewed without writes; explicit confirmation commits all50customers in a second empty database, preserving destination identity and permissions.');
 await first.send('Page.reload');await first.wait(`!!document.querySelector('.ir-nav')`,'reload');await panel(first);
 assert.deepEqual((await state(first)).counts,expected);
 const second=await session();await panel(second);assert.deepEqual((await state(second)).counts,expected);
 assert.equal(await first.evaluate(`document.querySelector('[data-inventory-data-demo]').disabled&&document.querySelector('[data-inventory-data-restore]').disabled`),true);
 checks.push('Reload and a separate authenticated browser session read the restored counts; additional demo loads/restores are unavailable on the populated target.');
 await shot(first,'inventory-restored-second-database.png');
});
