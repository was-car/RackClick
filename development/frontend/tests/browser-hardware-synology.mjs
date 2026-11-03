import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';
await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 async function add(key,version,name){await first.click('[data-add-hardware]');await chooseHardware(first,key,version);await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',f.rack);await submit(first);await saved(first);return (await snapshot(first)).devices.find(d=>d.name===name).id;}
 const nasA=await add('synology-rs1221plus','synology-20261030-v1','Synology A Ω');
 const nasB=await add('synology-rs1221plus','synology-20261030-v1','Synology B');
 const aruba=await add('aruba-jl682a','aruba-20261030-v1','Aruba junto al NAS');
 const p=await snapshot(first),ports=p.ports.filter(x=>[nasA,nasB].includes(x.deviceId));assert.equal(ports.length,10);assert.equal(p.ports.length,42);
 for(const id of [nasA,nasB]){const d=p.devices.find(d=>d.id===id);assert.equal(d.sizeU,2);assert.equal(d.mountParentId,null);assert.deepEqual(d.properties.physicalDimensionsMm,{width:482,height:88,depth:306.6});}
 assert.equal(await first.evaluate(`document.querySelector('[data-mount-occupancy]').textContent.includes('6/6 U')`),true);
 const row=`[data-devid="${nasA}"]`,scroll=row+' .rc-shell-scroll';
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'synology-rs1221plus-front');
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),0);assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-synology-tray]').length`),8);
 assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} image')`),false);
 await first.send('Emulation.setDeviceMetricsOverride',{width:1920,height:1500,deviceScaleFactor:1,mobile:false});
 const full=await first.evaluate(`(()=>{const s=document.querySelector('${scroll}'),r=s.getBoundingClientRect(),v=s.querySelector('svg').getBoundingClientRect();return v.left>=r.left&&v.right<=r.right+1})()`);assert.equal(full,true);
 await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,'synology-front-eight-trays.png');
 await first.click('[data-face="rear"]');
 const port=(did,type,n)=>ports.find(p=>p.deviceId===did&&p.type===type&&p.gn===n).id;
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),5);assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-synology-fan]').length`),2);
 const acPrintInside=await first.evaluate(`(()=>{const s=document.querySelector('${row} .rc-synology-face'),p=s.querySelectorAll(':scope > rect')[1].getBBox(),t=[...s.querySelectorAll('text')].find(n=>n.textContent==='AC IN').getBBox();return t.x>=p.x&&t.y>=p.y&&t.x+t.width<=p.x+p.width&&t.y+t.height<=p.y+p.height})()`);assert.equal(acPrintInside,true,'AC IN print must stay on the rear metal plate');
 const physical=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>({id:b.dataset.vport,x:b.getBoundingClientRect().x})).sort((a,b)=>a.x-b.x).map(p=>p.id)`);assert.deepEqual(physical,[port(nasA,'power',1),...[4,3,2,1].map(n=>port(nasA,'rj45',n))]);
 async function clickPort(id,button='left'){
  const at=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${id}"]');b.scrollIntoView({block:'center',inline:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);assert.ok(at.w>=24&&at.h>=24);
  for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:at.x,y:at.y,button,clickCount:1});
 }
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 const before=normalize(await snapshot(first));for(const p of ports.filter(p=>p.deviceId===nasA)){await clickPort(p.id);await first.wait(`document.querySelector('[data-vport="${p.id}"]').getAttribute('aria-pressed')==='true'`,'Synology5UUID');await first.click('.ir-connect-hint button');}assert.deepEqual(normalize(await snapshot(first)),before);
 await clickPort(port(nasA,'rj45',1));await clickPort(port(nasB,'rj45',1));await saved(first);
 const arubaPort=p.ports.find(x=>x.deviceId===aruba&&x.type==='rj45'&&x.gn===1).id;
 await clickPort(port(nasA,'rj45',2));await first.click('[data-face="front"]');await clickPort(arubaPort);await saved(first);await first.click('[data-face="rear"]');
 await clickPort(port(nasA,'power',1));await clickPort(f.pduPort);await saved(first);
 const network=(await snapshot(first)).connections;assert.equal(network.length,3);
 await first.evaluate(`(()=>{document.querySelector('${scroll}').scrollLeft=0;document.querySelector('${row}').scrollIntoView({block:'center'})})()`);await shot(first,'synology-rear-copper-and-power.png');
 checks.push('Two exact RS1221+ roots reserve2U each; front8trays/0ports, rear4LAN+1AC, two copper cables and AC inlet->outlet committed; Aruba29ports coexist; generic PDU is synthetic');
 const wire=network.find(c=>c.fromPortId===port(nasA,'rj45',1));assert.ok(wire);
 const aligned=`(()=>{const w=document.querySelector('[data-wire="${wire.id}"]'),b=document.querySelector('[data-vport="${wire.fromPortId}"]');if(!w||!b)return false;const p=w.getPointAtLength(0),q=new DOMPoint(p.x,p.y).matrixTransform(w.getScreenCTM()),r=b.getBoundingClientRect();return Math.hypot(q.x-r.x-r.width/2,q.y-r.y-r.height/2)<1.1})()`;
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await clickPort(port(nasA,'rj45',4));await first.click('.ir-connect-hint button');await first.wait(aligned,'NAS wire follows actual scroll');await shot(first,'synology-mobile-lan.png');
 await first.click('[data-face="front"]');assert.equal(await first.evaluate(`document.querySelector('${scroll}').scrollLeft`),0);assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),0);await first.click('[data-face="rear"]');assert.equal(await first.evaluate(`document.querySelector('${scroll}').scrollLeft`),0);
 await first.send('Emulation.setDeviceMetricsOverride',{width:1920,height:1500,deviceScaleFactor:1,mobile:false});
 await first.evaluate(`document.querySelector('[data-vport="${port(nasA,'rj45',3)}"]').focus()`);await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await first.wait(`document.querySelector('[data-vport="${port(nasA,'rj45',3)}"]').getAttribute('aria-pressed')==='true'`,'keyboard LAN3');await first.click('.ir-connect-hint button');
 await clickPort(port(nasA,'rj45',3),'right');await first.wait(`!!document.querySelector('dialog section.rc-form')`,'port label');await first.field('dialog section.rc-form>label:nth-last-child(2) select','label');await first.field('dialog section.rc-form>label:last-child input','NAS <svg> Ω');await submit(first);await saved(first);
 assert.equal(await first.evaluate(`([...document.querySelectorAll('${row} .rc-synology-label')]).some(n=>n.textContent==='NAS <svg> Ω')`),true);assert.equal(await first.evaluate(`!!document.querySelector('${row} .rc-synology-label svg')`),false);
 await first.click(`[data-hardware-edit="${nasA}"]`);await first.field('dialog [name=name]','Synology editado Ω');await first.field('dialog [name=notes]','Bandejas representadas, sin estado de discos');await submit(first);await saved(first);
 const expected=normalize(await snapshot(first));assert.deepEqual(expected.ports.filter(p=>[nasA,nasB].includes(p.deviceId)).map(p=>p.id),before.ports.filter(p=>[nasA,nasB].includes(p.deviceId)).map(p=>p.id));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);await second.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await second.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'synology-rs1221plus-front');
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);await reader.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${nasA}"]').disabled`),true);
 checks.push('Five original UUIDs/cancel preserve snapshot; native keyboard, escaped label, metadata, mobile targets/scroll/wire and face reset; reload/other session/reader preserve inventory');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
