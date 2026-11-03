import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {chooseHardware} from './browser-hardware-picker-support.mjs';
import {runScenario,infrastructure,snapshot,normalize,saved,submit} from './browser-quince-support.mjs';
await runScenario(async({first,session,fixture:f,checks,out,shot})=>{
 await infrastructure(first);assert.equal(f.selected506c.length,50);
 const initial=normalize(await snapshot(first)),results=[];
 for(const entry of f.selected506c){
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
 // Compact search is exercised through the real operation form, not a hidden selector.
 await first.click('[data-add-hardware]');
 assert.equal(await first.evaluate(`document.querySelector('[data-hardware-profile]').getAttribute('aria-expanded')`),'false');
 assert.equal(await first.evaluate(`document.querySelector('[data-hardware-preview]').open`),false);
 await first.click('[data-hardware-toggle]');
 const menu=await first.evaluate(`(()=>{const u=document.querySelector('[data-hardware-options]');return {height:u.clientHeight,content:u.scrollHeight,options:u.querySelectorAll('[role=option]').length}})()`);
 assert.equal(menu.options,528);assert.ok(menu.height<=241&&menu.content>menu.height);
 await first.field('[data-hardware-profile]','sofos');
 assert.equal(await first.evaluate(`([...document.querySelectorAll('[data-hardware-choice]')]).every(n=>n.textContent.includes('Sophos'))`),true);
 await first.evaluate(`document.querySelector('[data-hardware-profile]').focus()`);
 for(const key of ['ArrowDown','Enter']){await first.send('Input.dispatchKeyEvent',{type:'keyDown',key});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key})}
 assert.equal(await first.evaluate(`document.querySelector('[data-hardware-selected]').textContent.includes('Sophos')`),true);
 await first.field('[data-hardware-profile]','no-such-model-<img>');
 assert.equal(await first.evaluate(`!!document.querySelector('[data-hardware-selected]')`),false);
 assert.equal(await first.evaluate(`document.querySelector('[data-hardware-profile]').checkValidity()`),false);
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-hardware-choice]').length`),0);
 assert.equal(await first.evaluate(`!!document.querySelector('.rc-hardware-picker img')`),false);
 await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter'});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter'});
 assert.deepEqual(normalize(await snapshot(first)),initial);
 for(const vendor of ['Fortinet','Aruba']){
  await first.field('[data-hardware-profile]',vendor);
  assert.equal(await first.evaluate(`document.querySelectorAll('[data-hardware-choice]').length>0`),true);
  assert.equal(await first.evaluate(`([...document.querySelectorAll('[data-hardware-choice]')]).every(n=>n.textContent.toLowerCase().includes(${JSON.stringify(vendor.toLowerCase())}))`),true);
 }
 await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27});
 assert.equal(await first.evaluate(`document.querySelector('[data-hardware-profile]').getAttribute('aria-expanded')`),'false');
 assert.equal(await first.evaluate(`!!document.querySelector('dialog[open]')`),true);
 await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27});
 await first.wait(`!document.querySelector('dialog[open]')`,'second Escape cancels the normal form');
 await first.click('[data-add-hardware]');
 // A rack-mounted B model is already known from the actual API snapshot.
 const guiModel=initial.devices.find(d=>d.id===f.selected506c.find(e=>initial.devices.find(d=>d.id===e.deviceId).sizeU>0).deviceId);
 await chooseHardware(first,guiModel.hardwareProfileKey,'selected506c-20261101-v1');
 await first.field('[data-hardware-name]','GUI catálogo C <img> Ω');
 await first.field('[data-hardware-rack]',guiModel.rackId);
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 await first.click('[data-hardware-toggle]');
 assert.equal(await first.evaluate(`(()=>{const d=document.querySelector('dialog[open]');return d.scrollWidth<=d.clientWidth+2&&document.querySelector('[data-hardware-options]').clientHeight<=241})()`),true);
 await shot(first,'picker-mobile.png');
 await first.click('[data-hardware-toggle]');
 await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await submit(first);await saved(first);
 const created=(await snapshot(first)).devices.find(d=>d.name==='GUI catálogo C <img> Ω');assert.ok(created);
 assert.equal(created.hardwareProfileKey,guiModel.hardwareProfileKey);assert.equal(created.properties.hardwareProfileVersion,'selected506c-20261101-v1');
 assert.equal((await snapshot(first)).ports.filter(p=>p.deviceId===created.id).length,initial.ports.filter(p=>p.deviceId===guiModel.id).length);
 checks.push('Visible compact search: sofos alias, Fortinet/Aruba, exact key/revision, keyboard selection/Escape, unknown input blocks old selection, dropdown<=240px/390px form, confirmed GUI creation and persistence');

 const expected=normalize(await snapshot(first));
 await writeFile(path.join(out,'expected-browser-project.json'),JSON.stringify(expected));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);const sample=f.selected506c[0];await reader.click(`[data-rack-id="${sample.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${sample.deviceId}"]').disabled`),true);
 await writeFile(path.join(out,'BROWSER-MODELS-506C.json'),JSON.stringify({result:'PASS',models:results,observedThroughNativeGui:50,faces:100,inspectionNoMutation:true,guiCreationVerified:true,reloadAndSecondSession:true,readerReadOnly:true},null,2)+'\n');
 checks.push('Native Edge reads all50 selected API-created models/100faces with exact inventory UUIDs, no photos and socket targets>=24px; no inventory writes from inspection; reload/second session/reader preserved');
});
