import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';

await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 const ids=[],key='startech-c6panelutp241uft',version='startech-20261030-v1';
 for(const name of ['Panel frontal A Ω','Panel frontal B']){
  await first.click('[data-add-hardware]');await chooseHardware(first,key,version);
  await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',f.rack);await submit(first);await saved(first);
  ids.push((await snapshot(first)).devices.find(d=>d.name===name).id);
 }
 let p=await snapshot(first);const ports=p.ports.filter(x=>ids.includes(x.deviceId));assert.equal(ports.length,96);
 const port=(did,face,gn)=>ports.find(p=>p.deviceId===did&&p.face===face&&p.gn===gn).id;
 const row=`[data-devid="${ids[0]}"]`,screen=row+' .rc-shell-scroll';
 assert.deepEqual(await first.evaluate(`(()=>{const r=document.querySelector('${row}');return [...r.querySelectorAll('[data-shell-block]')].map(b=>[...b.querySelectorAll('[data-vport]')].map(p=>p.getAttribute('data-vport')))})()`),Array.from({length:4},(_,i)=>Array.from({length:6},(_,j)=>port(ids[0],'front',i*6+j+1))));
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-mode]').dataset.shellMode`),'specific');
 const portIds=await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>b.dataset.vport)`);
 assert.deepEqual(portIds,Array.from({length:24},(_,i)=>port(ids[0],'front',i+1)));
 assert.equal(await first.evaluate(`!!document.querySelector('${row} img,${row} iframe')`),false);
 checks.push('Exact revision renders four blocks of six original UUID controls; no images, frames or new connectors');
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'interactive-front');
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} image,${row} img,${row} [data-photo-hit]').length`),0);
 const jackGeometry=await first.evaluate(`(()=>{const r=document.querySelector('${row}');return [...r.querySelectorAll('[data-vport]')].map(b=>{const a=b.getBoundingClientRect(),j=b.querySelector('[data-front-jack]').getBoundingClientRect();return {w:a.width,h:a.height,delta:Math.hypot(a.x+a.width/2-j.x-j.width/2,a.y+a.height/2-j.y-j.height/2),fill:getComputedStyle(b.querySelector('[data-front-jack] path')).fill}})})()`);
 assert.equal(jackGeometry.length,24);assert.ok(jackGeometry.every(x=>x.w>=24&&x.h>=24&&x.delta<.1&&x.fill==='rgb(4, 5, 7)'));
 async function pointClick(id,button='left'){
  const at=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${id}"]');b.scrollIntoView({block:'center',inline:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,...at,button,clickCount:1});
 }
 const beforePointers=normalize(await snapshot(first));
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 for(let i=1;i<=24;i++){
  await pointClick(port(ids[0],'front',i));
  await first.wait(`document.querySelector('[data-vport="${port(ids[0],'front',i)}"]').getAttribute('aria-pressed')==='true'`,'visible socket '+i);
  await first.click('.ir-connect-hint button');
 }
 assert.deepEqual(normalize(await snapshot(first)),beforePointers);
 await pointClick(port(ids[0],'front',1));await pointClick(port(ids[1],'front',1));await saved(first);
 assert.equal(await first.evaluate(`document.querySelector('[data-vport="${port(ids[0],'front',1)}"]').dataset.portConnected`),'true');
 checks.push('Flat front has24visible sockets, centered cable targets and no photograph;24native pointer/cancel cycles preserve data; native Click-Click saves front cable');
 await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,'flat-front-desktop.png');
 // Native keyboard activation on an unchanged HTML button, not a synthetic .click().
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 await first.evaluate(`(()=>{window.__shellKeys=[];const b=document.querySelector('[data-vport="${port(ids[0],'front',2)}"]');for(const type of ['keydown','keyup','click'])b.addEventListener(type,e=>window.__shellKeys.push({type:e.type,key:e.key,trusted:e.isTrusted,prevented:e.defaultPrevented}));b.focus()})()`);
 const keyboardBefore=await first.evaluate(`({focus:document.hasFocus(),active:document.activeElement?.dataset?.vport,disabled:document.activeElement?.disabled})`);
 await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
 await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
 await writeFile(path.join(out,'keyboard-diagnostic.json'),JSON.stringify({before:keyboardBefore,after:await first.evaluate(`({active:document.activeElement?.dataset?.vport,events:window.__shellKeys,pressed:document.querySelector('[data-vport="${port(ids[0],'front',2)}"]').getAttribute('aria-pressed'),alert:document.querySelector('[role=alert]')?.textContent})`)}));
 await first.wait(`document.querySelector('[data-vport="${port(ids[0],'front',2)}"]').getAttribute('aria-pressed')==='true'`,'keyboard selection');
 await first.click('.ir-connect-hint button');
 const beforeFace=normalize(await snapshot(first));await first.click('[data-face="rear"]');
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-mode]').dataset.shellMode`),'specific');
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-caption]').textContent.includes('parejas lógicas')`),true);
 assert.deepEqual(await first.evaluate(`([...document.querySelectorAll('${row} [data-vport]')]).map(b=>b.dataset.vport)`),Array.from({length:24},(_,i)=>port(ids[0],'rear',24-i)));
 assert.deepEqual(normalize(await snapshot(first)),beforeFace);
 const rearBefore=normalize(await snapshot(first));
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-rendering]').dataset.shellRendering`),'interactive-rear');
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-rear-logical-number]').length`),24);
 for(let i=1;i<=24;i++){
  await pointClick(port(ids[0],'rear',i));await first.wait(`document.querySelector('[data-vport="${port(ids[0],'rear',i)}"]').getAttribute('aria-pressed')==='true'`,'rear socket '+i);await first.click('.ir-connect-hint button');
 }
 assert.deepEqual(normalize(await snapshot(first)),rearBefore);
 await pointClick(port(ids[0],'rear',1));await pointClick(port(ids[1],'rear',1));await saved(first);
 const rearCable=(await snapshot(first)).connections.find(c=>c.fromPortId===port(ids[0],'rear',1)||c.toPortId===port(ids[0],'rear',1));
 const rearAligned=`(()=>{const w=document.querySelector('[data-wire="${rearCable.id}"]'),b=document.querySelector('[data-vport="${rearCable.fromPortId}"]');if(!w||!b)return false;const p=w.getPointAtLength(0),q=new DOMPoint(p.x,p.y).matrixTransform(w.getScreenCTM()),r=b.getBoundingClientRect();return Math.hypot(q.x-r.x-r.width/2,q.y-r.y-r.height/2)<1.1})()`;
 await first.wait(rearAligned,'rear cable mouth alignment');
 await first.evaluate(`document.querySelector('${screen}').scrollLeft=100`);await first.wait(rearAligned,'rear wire follows scroll');
 await first.evaluate(`document.querySelector('${screen}').scrollLeft=0`);
 checks.push('Rear-specific bodies/retainers, logical numbers outside plate,24native rear UUID selections and separate rear cable at visible mouth; no front mutation');
 await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,'flat-rear-specific.png');
 checks.push('Front and model-specific rear connect separate cables by UUID; keyboard Enter selects; changing face alone does not write');
 await first.click('[data-face="front"]');
 const beforeMobile=normalize(await snapshot(first));
 const cable=beforeMobile.connections.find(c=>[c.fromPortId,c.toPortId].includes(port(ids[0],'front',1)));
 const wireAligned=`(()=>{const wire=document.querySelector('[data-wire="${cable.id}"]'),button=document.querySelector('[data-vport="${cable.fromPortId}"]');if(!wire||!button)return false;const p=wire.getPointAtLength(0),q=new DOMPoint(p.x,p.y).matrixTransform(wire.getScreenCTM()),r=button.getBoundingClientRect();return Math.hypot(q.x-r.x-r.width/2,q.y-r.y-r.height/2)<1.1})()`;
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 await first.wait(wireAligned,'wire geometry before scroll');
 await first.evaluate(`(()=>{const s=document.querySelector('${screen}');s.scrollLeft=s.scrollWidth;s.scrollIntoView({block:'center'})})()`);
 await first.wait(wireAligned,'wire follows horizontal scroll');
 const box=await first.evaluate(`(()=>{const s=document.querySelector('${screen}'),b=document.querySelector('[data-vport="${port(ids[0],'front',24)}"]'),r=b.getBoundingClientRect(),v=s.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height,inside:r.left>=v.left&&r.right<=v.right+1,scroll:s.scrollWidth>s.clientWidth,right:v.right}})()`);
 assert.ok(box.scroll&&box.inside&&box.width>=24&&box.height>=24&&box.right<=392);
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:box.x,y:box.y,button:'left',clickCount:1});
 assert.equal(await first.evaluate(`document.querySelector('[data-vport="${port(ids[0],'front',24)}"]').getAttribute('aria-pressed')`),'true');
 await shot(first,'flat-front-mobile-scroll.png');await first.click('.ir-connect-hint button');
 assert.deepEqual(normalize(await snapshot(first)),beforeMobile);
 await first.send('Emulation.clearDeviceMetricsOverride',{});
 await first.click(`[data-hardware-edit="${ids[0]}"]`);await first.field('dialog [name=name]','Panel <img src=x> Ω');await first.field('dialog [name=notes]','Nombre conservado, puertos reales');await submit(first);await saved(first);
 p=await snapshot(first);assert.equal(p.connections.length,2);assert.deepEqual(p.ports.filter(x=>ids.includes(x.deviceId)),ports);
 assert.equal(await first.evaluate(`!!document.querySelector('${row} img')`),false);
 // The original context/label editor still operates on the UUID of a visible socket.
 await pointClick(port(ids[0],'front',3),'right');
 await first.wait(`!!document.querySelector('dialog section.rc-form')`,'native context editor');
 await first.field('dialog section.rc-form>label:nth-last-child(2) select','label');
 await first.field('dialog section.rc-form>label:last-child input','Uplink <svg> Ω');await submit(first);await saved(first);
 assert.equal(await first.evaluate(`([...document.querySelectorAll('${row} .rc-front-user-label')]).some(n=>n.textContent==='Uplink <svg> Ω')`),true);
 assert.equal(await first.evaluate(`!!document.querySelector('${row} .rc-front-user-label svg')`),false);
 await pointClick(port(ids[0],'front',3),'right');await first.wait(`!!document.querySelector('dialog section.rc-form')`,'port status editor');
 await first.field('dialog section.rc-form>label:last-child select','reserved');await submit(first);await saved(first);
 await first.send('Input.dispatchMouseEvent',{type:'mouseMoved',x:1,y:1});
 assert.equal(await first.evaluate(`getComputedStyle(document.querySelector('[data-vport="${port(ids[0],'front',3)}"]')).outlineStyle`),'dashed');
 await pointClick(port(ids[0],'front',3),'right');await first.wait(`!!document.querySelector('dialog section.rc-form')`,'port color editor');
 await first.field('dialog section.rc-form>label:nth-last-child(2) select','color');await first.field('dialog section.rc-form>label:last-child input','#d946ef');await submit(first);await saved(first);
 assert.equal(await first.evaluate(`getComputedStyle(document.querySelector('[data-vport="${port(ids[0],'front',3)}"]'),'::before').backgroundColor`),'rgb(217, 70, 239)');
 await first.evaluate(`(()=>{const s=document.querySelector('${screen}');s.scrollLeft=0;document.querySelector('${row}').scrollIntoView({block:'center'})})()`);await shot(first,'flat-label-status-color.png');
 await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await first.click('[data-face="rear"]');await pointClick(port(ids[0],'rear',3),'right');await first.wait(`!!document.querySelector('dialog section.rc-form')`,'rear label editor');
 await first.field('dialog section.rc-form>label:nth-last-child(2) select','label');await first.field('dialog section.rc-form>label:last-child input','Trasera <svg> Ω');await submit(first);await saved(first);
 assert.equal(await first.evaluate(`([...document.querySelectorAll('${row} [data-rear-logical-label]')]).some(n=>n.textContent==='Trasera <svg> Ω')`),true);
 assert.equal(await first.evaluate(`!!document.querySelector('${row} [data-rear-logical-label] svg')`),false);
 await first.evaluate(`(()=>{document.querySelector('${screen}').scrollLeft=0;document.querySelector('${row}').scrollIntoView({block:'center'})})()`);await shot(first,'rear-specific-label.png');
 await first.click('[data-face="front"]');
 const expected=normalize(await snapshot(first));
 assert.deepEqual(expected.ports.map(x=>x.id),beforeMobile.ports.map(x=>x.id));assert.equal(expected.connections.length,2);
 checks.push('Native socket context retains batch UUID/group editor: label escaped and visible, reserved outline and custom color indicator; no port identity or cable loss');
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);await second.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 assert.equal(await second.evaluate(`document.querySelector('${row} [data-shell-mode]').dataset.shellMode`),'specific');
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);await reader.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${ids[0]}"]').disabled`),true);
 checks.push('390px horizontal scroll and actual pointer reach port24; text escaped; rename/reload/second session/read-only preserve all96ports and2cables');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
