import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';
await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 async function add(key,version,name,parent,rack=f.rack){
  await first.click('[data-add-hardware]');await chooseHardware(first,key,version);await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',rack);if(parent)await first.field('[data-hardware-parent]',parent);await submit(first);await saved(first);return (await snapshot(first)).devices.find(d=>d.name===name).id;
 }
 const shelfA=await add('shelf-2u','hw-reference-v1','Bandeja Fortinet A');
 const fgA=await add('fortinet-fg60f','fortinet-20261030-v1','FortiGate A Ω',shelfA);
 const shelfB=await add('shelf-2u','hw-reference-v1','Bandeja Fortinet B');
 const fgB=await add('fortinet-fg60f','fortinet-20261030-v1','FortiGate B',shelfB);
 const aruba=await add('aruba-jl682a','aruba-20261030-v1','Aruba conservado',null,f.mixedRack);
 const p=await snapshot(first),ports=p.ports.filter(x=>[fgA,fgB].includes(x.deviceId));assert.equal(ports.length,20);assert.equal(p.ports.length,51);
 for(const id of [fgA,fgB]){const d=p.devices.find(d=>d.id===id);assert.equal(d.sizeU,0);assert.deepEqual(d.properties.physicalDimensionsMm,{width:216,height:38.5,depth:160});}
 assert.equal(await first.evaluate(`document.querySelector('[data-mount-occupancy]').textContent.includes('4/4 U')`),true);
 const row=`[data-devid="${fgA}"]`,scroll=row+' .rc-shell-scroll';
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'fortigate60f-front');
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),0);
 assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} image')`),false);
 await first.send('Emulation.setDeviceMetricsOverride',{width:1920,height:1200,deviceScaleFactor:1,mobile:false});
 const frontFits=await first.evaluate(`(()=>{const s=document.querySelector('${scroll}'),r=s.getBoundingClientRect(),v=s.querySelector('svg').getBoundingClientRect();return v.left>=r.left&&v.right<=r.right+1})()`);assert.equal(frontFits,true,'Desktop shelf shows the complete front without horizontal scrolling');
 await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,'fortigate-front-indicators.png');
 await first.click('[data-face="rear"]');
 const port=(did,group,n)=>ports.find(p=>p.deviceId===did&&p.properties.hardwareGroupKey===group&&p.gn===n).id;
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),10);
 assert.equal(await first.evaluate(`([...document.querySelectorAll('${row} .rc-fortinet-print')]).map(n=>n.textContent).join('|')`),'RESET|DC +12V|USB|CONSOLE|1|2|3|4|5|A|B|DMZ|WAN1|WAN2');
 async function clickPort(id,button='left'){
  const at=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${id}"]');b.scrollIntoView({block:'center',inline:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);
  assert.ok(at.w>=24&&at.h>=24);for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:at.x,y:at.y,button,clickCount:1});
 }
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 const before=normalize(await snapshot(first));
 for(const p of ports.filter(p=>p.deviceId===fgA)){await clickPort(p.id);await first.wait(`document.querySelector('[data-vport="${p.id}"]').getAttribute('aria-pressed')==='true'`,'Fortinet10socket');await first.click('.ir-connect-hint button');}
 assert.deepEqual(normalize(await snapshot(first)),before);
 for(const [group,a,b] of [['rear-lan',1,1],['rear-fortilink',1,2],['rear-wan',1,2]]){await clickPort(port(fgA,group,a));await clickPort(port(fgB,group,b));await saved(first);}
 const network=(await snapshot(first)).connections;assert.equal(network.length,3);
 await first.evaluate(`(()=>{document.querySelector('${scroll}').scrollLeft=0;document.querySelector('[data-devid="${fgB}"] .rc-shell-scroll').scrollLeft=0;document.querySelector('${row}').scrollIntoView({block:'center'})})()`);await shot(first,'fortigate-rear-three-cables.png');
 checks.push('Two FG-60F instances retain20Ethernet UUIDs in four groups, mounted on two shelves reserving4U total; front0ports/rear10ports,3Ethernet cables committed by IDs');
 const wire=network.find(c=>c.fromPortId===port(fgA,'rear-lan',1));assert.ok(wire);
 const aligned=`(()=>{const w=document.querySelector('[data-wire="${wire.id}"]'),b=document.querySelector('[data-vport="${wire.fromPortId}"]');if(!w||!b)return false;const p=w.getPointAtLength(0),q=new DOMPoint(p.x,p.y).matrixTransform(w.getScreenCTM()),r=b.getBoundingClientRect();return Math.hypot(q.x-r.x-r.width/2,q.y-r.y-r.height/2)<1.1})()`;
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 await clickPort(port(fgA,'rear-lan',2));await first.click('.ir-connect-hint button');await first.wait(aligned,'mobile rear wire follows scroll');
 await shot(first,'fortigate-mobile-rear.png');
 await first.click('[data-face="front"]');assert.equal(await first.evaluate(`document.querySelector('${scroll}').scrollLeft`),0);assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),0);
 await first.click('[data-face="rear"]');assert.equal(await first.evaluate(`document.querySelector('${scroll}').scrollLeft`),0);
 await first.send('Emulation.setDeviceMetricsOverride',{width:1920,height:1200,deviceScaleFactor:1,mobile:false});
 await first.evaluate(`document.querySelector('[data-vport="${port(fgA,'rear-dmz',1)}"]').focus()`);await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await first.wait(`document.querySelector('[data-vport="${port(fgA,'rear-dmz',1)}"]').getAttribute('aria-pressed')==='true'`,'keyboard DMZ');await first.click('.ir-connect-hint button');
 await clickPort(port(fgA,'rear-dmz',1),'right');await first.wait(`!!document.querySelector('dialog section.rc-form')`,'port label');await first.field('dialog section.rc-form>label:nth-last-child(2) select','label');await first.field('dialog section.rc-form>label:last-child input','DMZ <svg> Ω');await submit(first);await saved(first);
 assert.equal(await first.evaluate(`([...document.querySelectorAll('${row} .rc-fortinet-label')]).some(n=>n.textContent==='DMZ <svg> Ω')`),true);assert.equal(await first.evaluate(`!!document.querySelector('${row} .rc-fortinet-label svg')`),false);
 await first.click(`[data-hardware-edit="${fgA}"]`);await first.field('dialog [name=name]','FortiGate editado Ω');await first.field('dialog [name=notes]','Referencia sin telemetría ni adaptación DC');await submit(first);await saved(first);
 const expected=normalize(await snapshot(first));assert.equal(expected.connections.length,3);assert.deepEqual(expected.ports.filter(p=>[fgA,fgB].includes(p.deviceId)).map(p=>p.id),before.ports.filter(p=>[fgA,fgB].includes(p.deviceId)).map(p=>p.id));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);await second.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await second.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'fortigate60f-front');
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);await reader.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${fgA}"]').disabled`),true);
 await first.click(`[data-rack-id="${f.mixedRack}"] .rc-rack-open`);assert.equal(await first.evaluate(`document.querySelector('[data-devid="${aruba}"] [data-shell-rendering]').dataset.shellRendering`),'aruba1930-front');
 checks.push('DC/USB/serial console are labelled drawings, no connectable UUID; keyboard/labels/mobile/cable anchors/reload/other session/reader work; Aruba29port profile coexists');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
