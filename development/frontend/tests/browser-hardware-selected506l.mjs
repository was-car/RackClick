import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {chooseHardware} from './browser-hardware-picker-support.mjs';
import {runScenario,infrastructure,snapshot,normalize,saved,submit} from './browser-quince-support.mjs';
const revision='selected506l-20261101-v1';
async function clickPort(tab,id){const point=await tab.evaluate(`(()=>{const p=document.querySelector('[data-vport="${id}"]');if(!p)throw Error('port_missing');p.scrollIntoView({block:'center',inline:'center'});const r=p.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2}})()`);await tab.send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await tab.send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});}
await runScenario(async({first,session,fixture:f,checks,out,shot})=>{
 await infrastructure(first);assert.equal(f.selected506l.length,62);
 const initial=normalize(await snapshot(first)),results=[];
 async function rack(id){const name=initial.racks.find(r=>r.id===id)?.name;assert.ok(name);const index=await first.evaluate(`([...document.querySelectorAll('.ir-racks button')]).findIndex(b=>b.querySelector('span')?.firstChild?.textContent===${JSON.stringify(name)})`);assert.ok(index>=0);await first.click(`.ir-racks button:nth-child(${index+1})`);}
 async function faceButton(face){await first.click(`[data-face="${face}"]`);}
 for(const e of f.selected506l){
  const container=e.kind==='rackContainer',room=['wall','pole','din','floor'].includes(e.kind);
  const resource=e.deviceId||e.resourceId||e.id;
  if(container){await rack(e.rack||resource);await first.wait(`!!document.querySelector('[data-rack-container-appearance]')`,'container appearance');await first.click('[data-rack-container-appearance] summary');}
  else if(room){await first.click('.rc-inventory-toolbar button:first-child');await first.wait(`!!document.querySelector('[data-room-hardware="${resource}"]')`,'room hardware');}
  else{await rack(e.rack);await first.wait(`!!document.querySelector('[data-devid="${resource}"] [data-batch-model]')`,'rack model');}
  const row=container?'[data-rack-container-appearance]':room?`[data-room-hardware="${resource}"]`:`[data-devid="${resource}"]`;
  const item={key:e.key,kind:e.kind,faces:[]};
  for(const face of ['front','rear']){
   if(room)await first.click(row+' .rc-inline-buttons button:nth-child('+(face==='front'?1:2)+')');else await faceButton(face);
   await first.wait(`!!document.querySelector('${row} [data-shell-rendering="batch50-${face}"]')`,'face '+e.key+face);
   const expected=container?[]:initial.ports.filter(p=>p.deviceId===resource&&p.face===face).map(p=>p.id).sort();
   const observed=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>{const r=b.getBoundingClientRect(),c=b.querySelector('[data-hardware-connector]');return{id:b.dataset.vport,w:r.width,h:r.height,owner:b.dataset.portOwner,descriptor:c?.dataset.hardwareConnector||null}})`);
   assert.deepEqual(observed.map(p=>p.id).sort(),expected);
   assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} image')`),false);
   for(const port of observed){assert.ok(port.w>=23.99&&port.h>=23.99,'small target '+e.key+' '+face);assert.equal(port.owner,resource);const p=initial.ports.find(p=>p.id===port.id);if(p.properties.hardwarePhysicalConnector)assert.equal(port.descriptor,p.properties.hardwarePhysicalConnector);}
   await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,e.key+'-'+face+'.png');
   item.faces.push({face,ports:observed.length,targetsAtLeast24:true,descriptorAndUuidMatch:true});
  }
  assert.equal(item.faces.reduce((n,p)=>n+p.ports,0),e.portCount||0);results.push(item);
 }
 assert.deepEqual(normalize(await snapshot(first)),initial);
 for(const pair of f.guiPairs||[]){
  if(pair.rack)await rack(pair.rack);else await first.click('.rc-inventory-toolbar button:first-child');
  if(pair.rack)await faceButton(pair.face||'rear');
  await clickPort(first,pair.fromPortId);await clickPort(first,pair.toPortId);await saved(first);
  assert.ok((await snapshot(first)).connections.some(c=>c.fromPortId===pair.fromPortId&&c.toPortId===pair.toPortId||c.toPortId===pair.fromPortId&&c.fromPortId===pair.toPortId));
 }
 await first.click('[data-add-hardware]');assert.equal(await first.evaluate(`document.querySelector('[data-hardware-profile]').getAttribute('aria-expanded')`),'false');
 await first.click('[data-hardware-toggle]');const menu=await first.evaluate(`(()=>{const n=document.querySelector('[data-hardware-options]');return{height:n.clientHeight,count:n.querySelectorAll('[role=option]').length}})()`);assert.equal(menu.count,868);assert.ok(menu.height<=241);
 const sample=f.selected506l.find(e=>e.kind==='rackContainer');assert.ok(sample);await chooseHardware(first,sample.key,revision);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-hardware-room]')&&!document.querySelector('[data-hardware-rack]')`),true);
 await first.field('[data-hardware-name]','GUI armario L <img> Ω');await first.field('[data-hardware-room]',initial.rooms[0].id);await submit(first);await saved(first);
 const after=normalize(await snapshot(first)),created=after.racks.find(r=>r.name==='GUI armario L <img> Ω');assert.ok(created);assert.equal(created.hardwareProfileKey,sample.key);assert.equal(after.devices.some(d=>d.rackId===created.id),false);
 await writeFile(path.join(out,'expected-browser-project.json'),JSON.stringify(after));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),after);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),after);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),after);assert.equal(await reader.evaluate(`!!document.querySelector('[data-add-hardware]')`),false);
 await writeFile(path.join(out,'BROWSER-MODELS-506L.json'),JSON.stringify({result:'PASS',models:results,faces:124,selectedPorts:results.flatMap(r=>r.faces).reduce((n,f)=>n+f.ports,0),inspectionDidNotMutate:true,guiConnections:(f.guiPairs||[]).length,guiRackCreation:true,reloadAndSecondSession:true,readerReadOnly:true},null,2)+'\n');
 checks.push('62 models,124 native front/rear views including four empty enclosures; exact endpoint UUIDs and targets; compact868 picker, GUI rack factory, reload and independent scoped sessions');
});
