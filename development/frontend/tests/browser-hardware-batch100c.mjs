import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,normalize} from './browser-quince-support.mjs';
await runScenario(async({first,session,fixture:f,checks,out,shot})=>{
 await infrastructure(first);assert.equal(f.batch100c.length,100);
 const initial=normalize(await snapshot(first)),results=[];
 for(const entry of f.batch100c){
  // Rack cards disappear after opening a detail. Continue through the real
  // sidebar, whose rack buttons remain available while a rack is selected.
  const rackName=initial.racks.find(r=>r.id===entry.rack).name;
  const navIndex=await first.evaluate(`([...document.querySelectorAll('.ir-racks button')]).findIndex(b=>b.querySelector('span')?.firstChild?.textContent===${JSON.stringify(rackName)})`);
  assert.ok(navIndex>=0,'sidebar rack '+rackName);
  await first.click(`.ir-racks button:nth-child(${navIndex+1})`);
  const row=`[data-devid="${entry.deviceId}"]`;
  await first.wait(`!!document.querySelector('${row} [data-batch-model]')`,'batch model '+entry.key);
  const item={key:entry.key,faces:[]};
  for(const face of ['front','rear']){
   await first.click(`[data-face="${face}"]`);
   await first.wait(`!!document.querySelector('${row} [data-shell-rendering="batch50-${face}"]')`,'batch face');
   const expected=initial.ports.filter(p=>p.deviceId===entry.deviceId&&p.face===face).map(p=>p.id).sort();
   const actual=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>b.dataset.vport).sort()`);assert.deepEqual(actual,expected);
   assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} image')`),false);
   const geometry=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>{const r=b.getBoundingClientRect();return {id:b.dataset.vport,w:r.width,h:r.height,owner:b.dataset.portOwner}})`);
   for(const b of geometry){assert.ok(b.w>=23.99&&b.h>=23.99,'target '+entry.key+' '+face+' '+JSON.stringify(b));assert.equal(b.owner,entry.deviceId)}
   const count=expected.length;item.faces.push({face,ports:count,minimumWidth:geometry.length?Math.min(...geometry.map(b=>b.w)):null,minimumHeight:geometry.length?Math.min(...geometry.map(b=>b.h)):null});
  }
  assert.equal(item.faces.reduce((n,f)=>n+f.ports,0),entry.portCount);
  if(results.length<2||results.length%10===0){await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,entry.key+'-rear.png')}
  results.push(item);
 }
 assert.deepEqual(normalize(await snapshot(first)),initial);
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),initial);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),initial);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),initial);const sample=f.batch100c[0];await reader.click(`[data-rack-id="${sample.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${sample.deviceId}"]').disabled`),true);
 await writeFile(path.join(out,'BROWSER-MODELS-100-05.json'),JSON.stringify({result:'PASS',models:results,observedThroughNativeGui:100,faces:200,noMutation:true,reloadAndSecondSession:true,readerReadOnly:true},null,2)+'\n');
 checks.push('Native Edge reads all100 API-created models/200faces with exact inventory UUIDs, no photos and socket targets>=24px; no inventory writes from inspection; reload/second session/reader preserved');
});
