import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,fixture as ids} from './browser-quince-support.mjs';
const row=id=>`[data-poe-device="${id}"]`;
await runScenario(async({first,session,checks,shot,out})=>{
 await infrastructure(first);let expected=await snapshot(first),original=structuredClone(expected);
 assert.equal(await first.evaluate(`document.querySelector('[data-poe-budget-summary]').tagName`),'DETAILS');
 assert.equal(await first.evaluate(`document.querySelector('[data-poe-budget-summary]').open`),false);
 assert.ok(await first.evaluate(`(()=>{const n=document.querySelector('[data-poe-budget-summary]>summary [data-poe-overview-exceeded]');return n&&n.textContent.startsWith('2 ·')&&n.getBoundingClientRect().height>0})()`),'Both over-budget warnings remain visible with PoE collapsed');
 assert.ok(await first.evaluate(`document.querySelector('[data-poe-budget-summary]>summary [data-poe-overview-incomplete]').getBoundingClientRect().height>0`));
 await first.click('[data-poe-budget-summary]>summary');
 await first.wait(`document.querySelector('[data-poe-budget-summary]').open`,'explicit PoE expansion');
 checks.push('Read-only PoE starts collapsed; two exceeded-budget warnings and incomplete-data summary stay visible; native click expands details');
 async function summary(tab,id,known,budget,unknown,eligible,exceeded,incomplete){
  const selector=row(id);await tab.wait(`(()=>{const r=document.querySelector('${selector}');return r&&r.querySelector('[data-poe-known]')?.textContent===${JSON.stringify(known+' W')}&&r.querySelector('[data-poe-limit]')?.textContent===${JSON.stringify(budget)}&&r.querySelector('[data-poe-unknown]')?.textContent===${JSON.stringify(String(unknown))}&&r.querySelector('[data-poe-eligible]')?.textContent===${JSON.stringify(String(eligible))}&&!!r.querySelector('[data-poe-exceeded]')===${exceeded}&&!!r.querySelector('[data-poe-incomplete]')===${incomplete}})()`,'complete summary projection');
  assert.deepEqual(await tab.evaluate(`(()=>{const r=document.querySelector('${selector}');return {known:r.querySelector('[data-poe-known]').textContent,budget:r.querySelector('[data-poe-limit]').textContent,unknown:r.querySelector('[data-poe-unknown]').textContent,eligible:r.querySelector('[data-poe-eligible]').textContent,exceeded:!!r.querySelector('[data-poe-exceeded]'),incomplete:!!r.querySelector('[data-poe-incomplete]')}})()`),{known:known+' W',budget,unknown:String(unknown),eligible:String(eligible),exceeded,incomplete});
 }
 await summary(first,ids.a,0,'No documentado',1,2,false,true);await summary(first,ids.b,5,'0 W',0,1,true,false);await summary(first,ids.c,2.5,'2 W',0,1,true,false);
 for(const id of [ids.a,ids.b])assert.ok((await first.evaluate(`document.querySelector('${row(id)} h3').textContent`)).includes(id));
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-poe-budget-summary] button,[data-poe-budget-summary] input').length`),0);
 checks.push('null budget≠0, null watts≠known0; disabled5/faulty2.5 still count; OFF9.5/AC90 excluded; duplicate literal names include full UUID; read-only summary');
 await shot(first,'poe-summary-initial.png');
 for(const [lang,title,missing] of [['en','PoE budget','Not documented'],['de','PoE-Budget','Nicht dokumentiert'],['es','Presupuesto PoE','No documentado']]){
  await first.click('.ir-all-clients');await first.wait(`!!document.querySelector('.ir-clients-home .rc-settings select')`,'client home language control');
  await first.field('.ir-clients-home .rc-settings select',lang);await infrastructure(first);await first.wait(`document.querySelector('[data-poe-budget-summary] h2')?.textContent===${JSON.stringify(title)}`,'language '+lang);
  await summary(first,ids.a,0,missing,1,2,false,true);assert.ok((await first.evaluate(`document.querySelector('${row(ids.a)} h3').textContent`)).includes('PoE literal Ω <img>'));
 }
 checks.push('EN/DE/ES local labels and warnings, user names never translated or interpreted as HTML');
 const second=await session('move-second');await infrastructure(second);await summary(second,ids.b,5,'0 W',0,1,true,false);
 await first.click(`[data-rack-id="${ids.rackA}"] .rc-rack-open`);await first.wait(`!!document.querySelector('[data-vport="${ids.pb2}"]')`,'rack port');
 assert.equal(await first.evaluate(`!!document.querySelector('${row(ids.c)}')`),false);
 await first.evaluate(`document.querySelector('[data-vport="${ids.pb2}"]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))`);
 await first.wait(`!!document.querySelector('dialog .rc-port-selection')`,'decimal watts editor');
 await first.field('dialog section > label:nth-of-type(2) select','watts');await first.field('dialog section > label:last-child input','0.1');
 assert.deepEqual(await first.evaluate(`(()=>{const e=document.querySelector('dialog section > label:last-child input');return {value:e.value,stepMismatch:e.validity.stepMismatch,valid:e.checkValidity()}})()`),{value:'0.1',stepMismatch:false,valid:true});
 await first.button('Cancelar');await first.wait(`!document.querySelector('dialog[open]')`,'cancel watts without write');
 await first.click(`[data-devid="${ids.b}"] .ir-device-name`);await first.wait(`!!document.querySelector('dialog input[name=poeBudget]')`,'decimal device budget editor');
 await first.field('dialog input[name=poeBudget]','0.3');
 assert.deepEqual(await first.evaluate(`(()=>{const e=document.querySelector('dialog input[name=poeBudget]');return {value:e.value,stepMismatch:e.validity.stepMismatch,valid:e.checkValidity()}})()`),{value:'0.3',stepMismatch:false,valid:true});
 await first.button('Cancelar');await first.wait(`!document.querySelector('dialog[open]')`,'cancel budget without write');
 assert.deepEqual(normalize(await snapshot(first)),normalize(original));
 checks.push('Real RC9 port editor accepts watts0.1 and device-name editor accepts budget0.3 without HTML stepMismatch; Cancel closes both with exact unchanged persisted snapshot');
 await first.evaluate(`document.querySelector('[data-vport="${ids.pb2}"]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))`);
 await first.wait(`!!document.querySelector('dialog .rc-port-selection')`,'port editor');
 await first.field('dialog section > label:nth-of-type(2) select','poe');await first.field('dialog section > label:last-child select','true');await submit(first);await saved(first);
 expected.revision++;Object.assign(expected.ports.find(p=>p.id===ids.pb2),{poe:true,type:'rj45_poe'});
 assert.deepEqual(normalize(await snapshot(first)),normalize(expected));await summary(first,ids.b,14.5,'0 W',0,2,true,false);
 checks.push('GUI commit OFF9.5→ON preserves documented watts/cable/UUID and refreshes known total to14.5 in rack-scoped summary');
 await first.evaluate(`document.querySelector('[data-vport="${ids.pa2}"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);
 await first.wait(`!!document.querySelector('.ir-connect-hint')`,'Click-Click selection');const hint=await first.evaluate(`document.querySelector('.ir-connect-hint').textContent`);
 await second.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json()),p=await fetch('/api/v1/customers/${ids.customer}/project').then(r=>r.json());const r=await fetch('/api/v1/customers/${ids.customer}/commands',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':me.user.id,'If-Match':'"'+p.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({type:'device.update',payload:{id:'${ids.b}',poeBudget:14.5}})});if(!r.ok)throw Error('Budget command '+r.status);return r.json()})()`);
 expected.revision++;expected.devices.find(d=>d.id===ids.b).poeBudget=14.5;
 assert.deepEqual(normalize(await snapshot(first)),normalize(expected));assert.equal(await first.evaluate(`document.querySelector('.ir-connect-hint').textContent`),hint);
 await first.button('Quitar selección');await first.button('Actualizar');await summary(first,ids.b,14.5,'14.5 W',0,2,false,false);
 await second.button('Actualizar');await summary(second,ids.b,14.5,'14.5 W',0,2,false,false);
 for(const tab of [first,second]){await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'reload');await infrastructure(tab);assert.deepEqual(normalize(await snapshot(tab)),normalize(expected));await summary(tab,ids.b,14.5,'14.5 W',0,2,false,false)}
 assert.deepEqual(expected.connections,original.connections);assert.equal(expected.ports.find(p=>p.id===ids.pb2).watts,9.5);
 checks.push('Real HTTP budget0→14.5 in second session; Click-Click selection preserved; explicit refresh removes exact-limit warning; reload in two authorized sessions shows identical persisted projection');
 const reader=await session('move-reader');await infrastructure(reader);await summary(reader,ids.a,0,'No documentado',1,2,false,true);await summary(reader,ids.b,14.5,'14.5 W',0,2,false,false);
 checks.push('Read-only scoped user sees same authorized shared summary without extra endpoint or write permission');
 await shot(first,'poe-summary-desktop.png');await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 assert.equal(await first.evaluate(`(()=>{const r=document.querySelector('[data-poe-budget-summary]');return r.scrollWidth<=r.clientWidth+1})()`),true);await shot(first,'poe-summary-mobile.png');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
