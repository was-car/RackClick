import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';
await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 const switches=[];
 async function add(key,version,name){await first.click('[data-add-hardware]');await chooseHardware(first,key,version);await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',f.rack);await submit(first);await saved(first);return (await snapshot(first)).devices.find(d=>d.name===name).id;}
 for(const name of ['Aruba A Ω','Aruba B'])switches.push(await add('aruba-jl682a','aruba-20261030-v1',name));
 const p=await snapshot(first),ports=p.ports.filter(x=>switches.includes(x.deviceId));assert.equal(ports.length,58);
 const port=(did,type,n)=>ports.find(p=>p.deviceId===did&&p.type===type&&p.gn===n).id;
 const row=`[data-devid="${switches[0]}"]`,other=`[data-devid="${switches[1]}"]`,scroll=row+' .rc-shell-scroll';
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'aruba1930-front');
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),28);
 assert.notEqual(port(switches[0],'rj45',1),port(switches[0],'sfp',1));
 assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} image')`),false);
 async function clickPort(id,button='left'){
  const at=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${id}"]');b.scrollIntoView({block:'center',inline:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);
  assert.ok(at.w>=24&&at.h>=24);for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:at.x,y:at.y,button,clickCount:1});
 }
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 const before=normalize(await snapshot(first));
 for(const p of ports.filter(p=>p.deviceId===switches[0]&&p.face==='front')){await clickPort(p.id);await first.wait(`document.querySelector('[data-vport="${p.id}"]').getAttribute('aria-pressed')==='true'`,'Aruba28socket');await first.click('.ir-connect-hint button');}
 assert.deepEqual(normalize(await snapshot(first)),before);
 await clickPort(port(switches[0],'rj45',1));await clickPort(port(switches[1],'rj45',1));await saved(first);
 await clickPort(port(switches[0],'sfp',1));await clickPort(port(switches[1],'sfp',4));await saved(first);
 const network=(await snapshot(first)).connections;assert.equal(network.length,2);
 await first.send('Emulation.setDeviceMetricsOverride',{width:1920,height:1200,deviceScaleFactor:1,mobile:false});
 await first.evaluate(`(()=>{document.querySelector('${scroll}').scrollLeft=0;document.querySelector('${other} .rc-shell-scroll').scrollLeft=0;document.querySelector('${row}').scrollIntoView({block:'center'})})()`);await shot(first,'aruba-front-copper-sfp.png');
 checks.push('Two exact JL682A revisions create58UUIDs/3groups each,28native front selections; copper and SFP cables use distinct group IDs despite shared gn1');
 const wire=network.find(c=>c.fromPortId===port(switches[0],'rj45',1));
 const aligned=`(()=>{const w=document.querySelector('[data-wire="${wire.id}"]'),b=document.querySelector('[data-vport="${wire.fromPortId}"]');if(!w||!b)return false;const p=w.getPointAtLength(0),q=new DOMPoint(p.x,p.y).matrixTransform(w.getScreenCTM()),r=b.getBoundingClientRect();return Math.hypot(q.x-r.x-r.width/2,q.y-r.y-r.height/2)<1.1})()`;
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await first.wait(aligned,'wire before switch scroll');await first.evaluate(`document.querySelector('${scroll}').scrollLeft=600`);await first.wait(aligned,'wire follows switch scroll');
 await clickPort(port(switches[0],'sfp',4));await first.wait(`document.querySelector('[data-vport="${port(switches[0],'sfp',4)}"]').getAttribute('aria-pressed')==='true'`,'mobile SFP4');await shot(first,'aruba-mobile-sfp.png');await first.click('.ir-connect-hint button');
 // A face change must not strand the rear inlet beyond the old SFP scroll offset.
 await first.click('[data-face="rear"]');
 const rearMobile=await first.evaluate(`(()=>{const s=document.querySelector('${scroll}'),r=s.getBoundingClientRect(),b=s.querySelector('[data-vport]').getBoundingClientRect();return {scroll:s.scrollLeft,inside:b.left>=r.left&&b.right<=r.right+1}})()`);
 assert.equal(rearMobile.scroll,0);assert.equal(rearMobile.inside,true);
 await clickPort(port(switches[0],'power',1));await first.click('.ir-connect-hint button');
 await first.send('Emulation.setDeviceMetricsOverride',{width:1920,height:1200,deviceScaleFactor:1,mobile:false});
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),1);
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-vport]').dataset.vport`),port(switches[0],'power',1));
 assert.equal(ports.find(p=>p.id===port(switches[0],'power',1)).powerRole,'inlet');
 await clickPort(port(switches[0],'power',1));await clickPort(f.pduPort);await saved(first);
 await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,'aruba-rear-power.png');
 checks.push('Rear has only the real AC inlet, no fake network ports/fans; inlet→outlet power cable confirmed;390px/SFP4/cable scrolling preserve UUIDs');
 await first.click('[data-face="front"]');await clickPort(port(switches[0],'rj45',3),'right');await first.wait(`!!document.querySelector('dialog section.rc-form')`,'port label');
 await first.field('dialog section.rc-form>label:nth-last-child(2) select','label');await first.field('dialog section.rc-form>label:last-child input','LAN <svg> Ω');await submit(first);await saved(first);
 assert.equal(await first.evaluate(`([...document.querySelectorAll('${row} .rc-aruba-label')]).some(n=>n.textContent==='LAN <svg> Ω')`),true);assert.equal(await first.evaluate(`!!document.querySelector('${row} .rc-aruba-label svg')`),false);
 await first.click(`[data-hardware-edit="${switches[0]}"]`);await first.field('dialog [name=name]','Aruba editado Ω');await first.field('dialog [name=notes]','Referencia física, no telemetría');await submit(first);await saved(first);
 const expected=normalize(await snapshot(first));assert.equal(expected.connections.length,3);assert.deepEqual(expected.ports.filter(p=>switches.includes(p.deviceId)).map(p=>p.id),before.ports.filter(p=>switches.includes(p.deviceId)).map(p=>p.id));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);await second.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await second.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'aruba1930-front');
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);await reader.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${switches[0]}"]').disabled`),true);
 checks.push('Label text escaped, name/notes and29ports per model survive reload and second authorized session; reader cannot edit');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
