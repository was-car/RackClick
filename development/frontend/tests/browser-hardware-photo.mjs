import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';
import {hardwarePhoto} from '../src/hardware-photo.ts';

await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 const ids=[];
 for(const name of ['Foto original A Ω','Foto original B']){
  await first.click('[data-add-hardware]');await chooseHardware(first,'startech-c6panelutp241uft','startech-20261030-v1');
  await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',f.rack);await submit(first);await saved(first);
  ids.push((await snapshot(first)).devices.find(d=>d.name===name).id);
 }
 const row=`[data-devid="${ids[0]}"]`,other=`[data-devid="${ids[1]}"]`,scroller=row+' .rc-shell-scroll';
 await first.wait(`document.querySelectorAll('[data-shell-rendering="photograph"]').length===2`,'two original photographs');
 const p=await snapshot(first),ports=p.ports.filter(x=>ids.includes(x.deviceId));
 const port=(did,face,gn)=>ports.find(p=>p.deviceId===did&&p.face===face&&p.gn===gn).id;
 const bindings=await first.evaluate(`([...document.querySelectorAll('${row} [data-photo-hit]')]).map(f=>({ordinal:Number(f.dataset.photoHit),id:f.querySelector('[data-vport]').dataset.vport}))`);
 assert.deepEqual(bindings,Array.from({length:24},(_,i)=>({ordinal:i+1,id:port(ids[0],'front',i+1)})));
 const source=await first.evaluate(`document.querySelector('${row} image').getAttribute('href')`);assert.ok(source.startsWith('blob:'));
 // The host permits Blob images but deliberately not fetch(blob:) via connect-src.
 const digest=await first.evaluate(`fetch(${JSON.stringify(hardwarePhoto.path)},{credentials:'omit'}).then(r=>r.arrayBuffer()).then(b=>crypto.subtle.digest('SHA-256',b)).then(h=>Array.from(new Uint8Array(h),n=>n.toString(16).padStart(2,'0')).join(''))`);assert.equal(digest,hardwarePhoto.sha256);
 // Calibrated centers are original-image coordinates, not a re-spaced port strip.
 const geometry=await first.evaluate(`([...document.querySelectorAll('${row} foreignObject')]).map(f=>[f.x.baseVal.value+f.width.baseVal.value/2,f.y.baseVal.value+f.height.baseVal.value/2])`);assert.deepEqual(geometry,hardwarePhoto.centers);
 await first.evaluate(`document.querySelector('${row}').scrollIntoView({block:'center'})`);await shot(first,'photo-original-desktop.png');
 // Every front UUID can be selected from its transparent region without saving.
 const beforeClicks=normalize(await snapshot(first));
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 for(let i=1;i<=24;i++){
  const target=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${port(ids[0],'front',i)}"]');b.scrollIntoView({block:'center',inline:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:target.x,y:target.y,button:'left',clickCount:1});
  await first.wait(`document.querySelector('[data-vport="${port(ids[0],'front',i)}"]').getAttribute('aria-pressed')==='true'`,'select original port '+i);
  await first.click('.ir-connect-hint button');
 }
 assert.deepEqual(normalize(await snapshot(first)),beforeClicks);
 await first.click(`[data-vport="${port(ids[0],'front',1)}"]`);await first.click(`[data-vport="${port(ids[1],'front',1)}"]`);await saved(first);
 checks.push('Original JPEG SHA matches exactly;24transparent UUID hit regions preserve original geometry/colors;24selection/cancel cycles do not write');
 await first.click('[data-face="rear"]');assert.equal(await first.evaluate(`!!document.querySelector('${row} image')`),false);
 assert.equal(await first.evaluate(`document.querySelector('${row} [data-shell-mode]').dataset.shellMode`),'generic');
 await first.click(`[data-vport="${port(ids[0],'rear',1)}"]`);await first.click(`[data-vport="${port(ids[1],'rear',1)}"]`);await saved(first);
 await first.click('[data-face="front"]');await first.wait(`!!document.querySelector('${row} image')`,'photo returns');
 await first.send('Page.bringToFront');await first.send('Emulation.setFocusEmulationEnabled',{enabled:true});
 await first.evaluate(`document.querySelector('[data-vport="${port(ids[0],'front',2)}"]').focus()`);
 await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await first.wait(`document.querySelector('[data-vport="${port(ids[0],'front',2)}"]').getAttribute('aria-pressed')==='true'`,'native Enter');await first.click('.ir-connect-hint button');
 const beforeMobile=normalize(await snapshot(first)),cable=beforeMobile.connections.find(c=>[c.fromPortId,c.toPortId].includes(port(ids[0],'front',1)));
 const aligned=`(()=>{const w=document.querySelector('[data-wire="${cable.id}"]'),b=document.querySelector('[data-vport="${cable.fromPortId}"]');if(!w||!b)return false;const p=w.getPointAtLength(0),v=new DOMPoint(p.x,p.y).matrixTransform(w.getScreenCTM()),r=b.getBoundingClientRect();return Math.hypot(v.x-r.x-r.width/2,v.y-r.y-r.height/2)<1.1})()`;
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 await first.wait(aligned,'cable before scroll');await first.evaluate(`(()=>{const s=document.querySelector('${scroller}');s.scrollLeft=s.scrollWidth;document.querySelector('[data-vport="${port(ids[0],'front',24)}"]').scrollIntoView({block:'center'})})()`);
 await first.wait(aligned,'cable follows photo scroll');
 const target=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${port(ids[0],'front',24)}"]'),r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);assert.ok(target.w>=24&&target.h>=24);
 for(const type of ['mousePressed','mouseReleased'])await first.send('Input.dispatchMouseEvent',{type,x:target.x,y:target.y,button:'left',clickCount:1});
 await first.wait(`document.querySelector('[data-vport="${port(ids[0],'front',24)}"]').getAttribute('aria-pressed')==='true'`,'pointer photo24');await shot(first,'photo-original-mobile.png');await first.click('.ir-connect-hint button');
 assert.deepEqual(normalize(await snapshot(first)),beforeMobile);await first.send('Emulation.clearDeviceMetricsOverride',{});
 // Altered or missing bytes never display as the model photo. No file is changed.
 await first.send('Page.addScriptToEvaluateOnNewDocument',{source:`{const old=window.fetch;window.fetch=(u,o)=>String(u)==='${hardwarePhoto.path}'?Promise.resolve(new Response(new Uint8Array(${hardwarePhoto.bytes}))):old(u,o);}`});
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 await first.wait(`document.querySelector('${row} [data-photo-status]')?.dataset.photoStatus==='failed'`,'corrupt image fallback');
 assert.equal(await first.evaluate(`document.querySelectorAll('${row} [data-vport]').length`),24);assert.equal(await first.evaluate(`!!document.querySelector('${row} image')`),false);
 const expected=normalize(await snapshot(first));assert.deepEqual(expected,beforeMobile);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);await second.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);await second.wait(`!!document.querySelector('${row} image')`,'second original');
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);await reader.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);assert.equal(await reader.evaluate(`document.querySelector('[data-hardware-edit="${ids[0]}"]').disabled`),true);
 checks.push('Two independent face cables, native keyboard,390pxpointer/scroll/wire, corrupt-photo fallback, reload, second session and reader preserve all data');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
