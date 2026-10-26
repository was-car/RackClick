import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,normalize,fixture as ids} from './browser-quince-support.mjs';
await runScenario(async({first,session,checks,shot,out})=>{
 async function singleton(tab,label){const count=await tab.evaluate(`({inventory:document.querySelectorAll('.rc-inventory').length,channels:document.querySelectorAll('[data-client-change-channel]').length,reads:document.querySelectorAll('[data-inventory-read]').length})`);assert.deepEqual(count,{inventory:1,channels:1,reads:1},label);}
 await infrastructure(first);const original=await snapshot(first);await singleton(first,'initial single inventory/channel/read panel');
 const read=tab=>tab.click('[data-read-toggle]');
 const ready=tab=>tab.wait(`!!document.querySelector('[data-read-summary]')&&!document.querySelector('[data-inventory-read] [aria-busy=true]')`,'read response');
 const rows=tab=>tab.evaluate(`[...document.querySelectorAll('[data-read-row]')].map(n=>n.dataset.readRow)`);
 async function tab(tab,view){await tab.click('[data-read-tab="'+view+'"]');await ready(tab)}
 async function filter(tab,key,value){await tab.field('[data-read-filter="'+key+'"]',value);await ready(tab)}
 await read(first);await ready(first);assert.equal((await rows(first)).length,25);
 // Site, building and room links focus their exact identity, despite homonyms.
 for(const [kind,id,selector] of [['site',ids.site,'data-site-id'],['building',ids.building,'data-building-id'],['room',ids.roomA,'data-room-id'],['device',ids.a,'data-devid'],['port',ids.pa,'data-vport']]){
  await filter(first,'kind',kind);await filter(first,'query',kind==='port'?'Before one':kind==='device'?'Equipo móvil':'');
  await first.click('[data-read-navigate="'+id+'"]');await first.wait(`document.activeElement?.getAttribute('${selector}')==='${id}'`,'exact '+kind+' navigation focus');
 }
 checks.push('Search native site/building/room/device/port links focus actual DOM identity; literal homonyms and Unicode remain escaped');
 await tab(first,'ports');await filter(first,'query','');await ready(first);const one=await rows(first);await first.click('[data-read-next]');await ready(first);const two=await rows(first);assert.equal(one.length,25);assert.equal(two.length,25);assert.equal(one.filter(id=>two.includes(id)).length,0);
 await filter(first,'status','disabled');assert.deepEqual(await rows(first),[ids.pa2]);
 await filter(first,'status','all');await filter(first,'family','power');assert.deepEqual(await rows(first),[]);
 await filter(first,'family','rj45');await filter(first,'query','Before one');assert.deepEqual(await rows(first),[ids.pa]);
 const info=await first.evaluate(`document.querySelector('[data-read-row]').textContent`);assert.ok(info.includes(ids.ga)&&info.includes(ids.a)&&info.includes(ids.pa)&&info.includes('17.5'));
 await tab(first,'connections');await filter(first,'query','');assert.equal((await rows(first)).length,2);await filter(first,'query','Cable literal');assert.deepEqual(await rows(first),[ids.cable]);let text=await first.evaluate(`document.querySelector('[data-read-row]').textContent`);assert.ok(text.includes(ids.pa)&&text.includes(ids.pc)&&text.includes('Entre racks: Sí'));
 await filter(first,'query','Room literal');assert.deepEqual(await rows(first),[ids.roomCable]);text=await first.evaluate(`document.querySelector('[data-read-row]').textContent`);assert.ok(text.includes(ids.dosePort)&&text.includes(ids.endPort)&&text.includes('Desconocido'));
 assert.equal(await first.evaluate(`!!document.querySelector('[data-inventory-read] img')`),false);
 assert.deepEqual(normalize(await snapshot(first)),normalize(original));
 checks.push('Paged ports disjoint UUIDs, stored status/family/query, repeated gn separated, connected distinct; cables one row per UUID with current endpoints, cross-rack derived and room cable unknown; queries do not write inventory');
 const second=await session('move-second');await infrastructure(second);await read(second);await ready(second);await singleton(second,'second actor read singleton');
 const reader=await session('move-reader');await infrastructure(reader);await read(reader);await ready(reader);await tab(reader,'ports');await ready(reader);await singleton(reader,'reader ports singleton');assert.equal(await reader.evaluate(`!!document.querySelector('[data-inventory-read] button[data-edit]')`),false);
 // Preserve a page cursor across a remote rename and room move; late metadata cannot advance the project.
 await tab(first,'ports');await filter(first,'query','');await first.click('[data-read-next]');await ready(first);
 await second.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json());for(const command of [{type:'device.update',payload:{id:'${ids.dose}',name:'Renombrado 東京 <img>'}},{type:'device.move',payload:{id:'${ids.dose}',roomId:'${ids.roomB}'}}]){const p=await fetch('/api/v1/customers/${ids.customer}/project').then(r=>r.json());const r=await fetch('/api/v1/customers/${ids.customer}/commands',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':me.user.id,'If-Match':'"'+p.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(command)});if(!r.ok)throw Error('write '+r.status)}})()`);
 await first.click('[data-read-next]');await first.wait(`!!document.querySelector('[data-read-error]')`,'stale 412');assert.deepEqual(await rows(first),[]);assert.ok((await first.evaluate(`document.querySelector('[data-read-error]').textContent`)).includes('revisión cambió'));
 await first.click('[data-read-refresh]');await ready(first);assert.equal(await first.evaluate(`document.querySelector('[data-read-previous]').disabled`),true);
 await filter(first,'query','Renombrado');assert.deepEqual(await rows(first),[ids.dosePort]);text=await first.evaluate(`document.querySelector('[data-read-row]').textContent`);assert.ok(text.includes(ids.roomB)&&text.includes('Renombrado 東京 <img>'));
 const expected=await snapshot(first);assert.equal(expected.revision,original.revision+2);await singleton(first,'after filters/pages/remote refresh singleton');
 checks.push('Other actor rename/move: next page receives 412, clears old rows, explicit refresh resets cursor and uses current UUID paths; no revision advancement from query metadata');
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await first.evaluate(`document.querySelector('[data-inventory-read]').scrollIntoView({block:'start'})`);await shot(first,'inventory-read-mobile.png');assert.ok(await first.evaluate(`document.querySelector('[data-inventory-read]').getBoundingClientRect().right<=window.innerWidth+1`));
 await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await first.evaluate(`document.querySelector('[data-inventory-read]').scrollIntoView({block:'start'})`);await shot(first,'inventory-read-desktop.png');
 for(const t of [first,second,reader]){await t.send('Page.reload');await t.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'reload');await infrastructure(t);assert.deepEqual(normalize(await snapshot(t)),normalize(expected));await read(t);await ready(t);await singleton(t,'reload each actor/read-only singleton')}
 checks.push('Two actors and scoped reader reload shared state; 390px panel, desktop screenshots, no export/edit offered');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
