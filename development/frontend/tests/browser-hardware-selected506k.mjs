import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {chooseHardware} from './browser-hardware-picker-support.mjs';
import {runScenario,infrastructure,snapshot,normalize,saved,submit} from './browser-quince-support.mjs';
async function clickPort(tab,id){
 const point=await tab.evaluate(`(()=>{const p=document.querySelector('[data-vport="${id}"]');p.scrollIntoView({block:'center',inline:'center'});const r=p.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
 await tab.send('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
 await tab.send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await tab.send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
}
await runScenario(async({first,session,fixture:f,checks,out,shot})=>{
 await infrastructure(first);assert.equal(f.selected506k.length,52);
 const initial=normalize(await snapshot(first)),results=[];
 async function rack(id){const name=initial.racks.find(r=>r.id===id).name;const n=await first.evaluate(`([...document.querySelectorAll('.ir-racks button')]).findIndex(b=>b.querySelector('span')?.firstChild?.textContent===${JSON.stringify(name)})`);assert.ok(n>=0);await first.click(`.ir-racks button:nth-child(${n+1})`);}
 for(const e of f.selected506k){
  await rack(e.rack);const row=`[data-devid="${e.deviceId}"]`;await first.wait(`!!document.querySelector('${row} [data-batch-model]')`,'model '+e.key);
  const item={key:e.key,faces:[]};
  for(const face of ['front','rear']){
   await first.click(`[data-face="${face}"]`);await first.wait(`!!document.querySelector('${row} [data-shell-rendering="batch50-${face}"]')`,'face');
   const expected=initial.ports.filter(p=>p.deviceId===e.deviceId&&p.face===face).map(p=>p.id).sort();
   const actual=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>b.dataset.vport).sort()`);assert.deepEqual(actual,expected);
   assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} image')`),false);
   const geometry=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>{const r=b.getBoundingClientRect(),c=b.querySelector('[data-hardware-connector]');return {id:b.dataset.vport,w:r.width,h:r.height,owner:b.dataset.portOwner,descriptor:c?.dataset.hardwareConnector||null}})`);
   for(const b of geometry){assert.ok(b.w>=23.99&&b.h>=23.99,'target '+e.key+face+JSON.stringify(b));assert.equal(b.owner,e.deviceId);const p=initial.ports.find(p=>p.id===b.id);if(p.properties.hardwarePhysicalConnector)assert.equal(b.descriptor,p.properties.hardwarePhysicalConnector);}
   if(e.kind==='desktop'){
    const fit=await first.evaluate(`(()=>{const n=document.querySelector('${row} [data-shell-rendering="batch50-${face}"]');return {width:n.clientWidth,content:n.scrollWidth}})()`);
    assert.ok(fit.content<=fit.width+2,'Desktop enclosure must fit its shelf viewport: '+e.key+' '+face+' '+JSON.stringify(fit));
   }
   await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,e.key+'-'+face+'.png');
   item.faces.push({face,ports:expected.length,minimumWidth:geometry.length?Math.min(...geometry.map(g=>g.w)):null,minimumHeight:geometry.length?Math.min(...geometry.map(g=>g.h)):null,descriptorsMatch:true});
  }
  assert.equal(item.faces.reduce((n,f)=>n+f.ports,0),e.portCount);results.push(item);
 }
 assert.deepEqual(normalize(await snapshot(first)),initial);
 for(const pair of f.guiPairs){
  await rack(pair.rack);await first.click(`[data-face="${pair.face}"]`);await clickPort(first,pair.fromPortId);await clickPort(first,pair.toPortId);await saved(first);
  assert.ok((await snapshot(first)).connections.some(c=>(c.fromPortId===pair.fromPortId&&c.toPortId===pair.toPortId)||(c.toPortId===pair.fromPortId&&c.fromPortId===pair.toPortId)));
 }
 assert.equal((await snapshot(first)).connections.length,initial.connections.length+4);
 checks.push('Four actual UUID Click-Click saves: RJ45, IDC, serial console and role-correct power; no implicit RJ45/IDC cable');
 await first.click('[data-add-hardware]');assert.equal(await first.evaluate(`document.querySelector('[data-hardware-profile]').getAttribute('aria-expanded')`),'false');
 await first.click('[data-hardware-toggle]');const menu=await first.evaluate(`(()=>{const u=document.querySelector('[data-hardware-options]');return {height:u.clientHeight,content:u.scrollHeight,n:u.querySelectorAll('[role=option]').length}})()`);assert.equal(menu.n,805);assert.ok(menu.height<=241&&menu.content>menu.height);
 for(const vendor of ['APC','Panduit','TerraMaster','Opengear','CommScope']){
  await first.field('[data-hardware-profile]',vendor);assert.ok(await first.evaluate(`document.querySelectorAll('[data-hardware-choice]').length>0`));assert.ok(await first.evaluate(`([...document.querySelectorAll('[data-hardware-choice]')]).every(n=>n.textContent.toLowerCase().includes(${JSON.stringify(vendor.toLowerCase())}))`));
 }
 const gui=f.selected506k.find(e=>e.portCount===0);assert.ok(gui);await chooseHardware(first,gui.key,'selected506k-20261101-v1');
 assert.equal(await first.evaluate(`document.querySelector('[data-hardware-preview]').open`),false);await first.click('[data-hardware-preview] summary');
 assert.ok(await first.evaluate(`document.querySelector('[data-hardware-configuration]').textContent.length>20`));assert.ok(await first.evaluate(`document.querySelector('[data-hardware-review-limits] li')!==null`));
 await first.field('[data-hardware-name]','GUI catálogo K <img> Ω');await first.field('[data-hardware-rack]',gui.rack);
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await first.click('[data-hardware-toggle]');
 assert.ok(await first.evaluate(`(()=>{const d=document.querySelector('dialog[open]');return d.scrollWidth<=d.clientWidth+2&&document.querySelector('[data-hardware-options]').clientHeight<=241})()`));await shot(first,'picker-mobile.png');
 await first.click('[data-hardware-toggle]');await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await submit(first);await saved(first);
 const created=(await snapshot(first)).devices.find(d=>d.name==='GUI catálogo K <img> Ω');assert.ok(created);assert.equal(created.hardwareProfileKey,gui.key);assert.equal((await snapshot(first)).ports.filter(p=>p.deviceId===created.id).length,0);
 checks.push('805 choices in bounded collapsed search, five manufacturers, exact key/revision, configuration/BOM/limits visible only inside details, mobile390px and confirmed zero-port accessory creation');
 const expected=normalize(await snapshot(first));await writeFile(path.join(out,'expected-browser-project.json'),JSON.stringify(expected));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);const sample=f.selected506k[0];await reader.click(`[data-rack-id="${sample.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${sample.deviceId}"]').disabled`),true);
 await writeFile(path.join(out,'BROWSER-MODELS-506K.json'),JSON.stringify({result:'PASS',models:results,observedThroughNativeGui:52,faces:104,inspectionNoMutation:true,guiCreationVerified:true,typedGuiConnections:4,reloadAndSecondSession:true,readerReadOnly:true},null,2)+'\n');
 checks.push('52 models/104 faces, exact UUIDs and descriptor glyphs, targets>=24px, no photos, read-only inspection, reload and independent sessions');
});
