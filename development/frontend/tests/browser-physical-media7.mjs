import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,normalize,saved} from './browser-quince-support.mjs';

async function portClick(tab,id){
 const point=await tab.evaluate(`(()=>{const p=document.querySelector('[data-ir-hit="${id}"]');p.scrollIntoView({block:'center'});const r=p.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
 await tab.send('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
 await tab.send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
 await tab.send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
}

await runScenario(async({first,session,fixture:f,checks,out,shot})=>{
 await infrastructure(first);
 await first.click(`[data-rack-id="${f.mixedRack}"] .rc-rack-open`);
 const initial=normalize(await snapshot(first));
 for(const kind of ['sfp56','qsfpdd']){
  const wanted=kind==='sfp56'?'SFP56':'QSFP-DD';
  const ends=[f.media7.a,f.media7.b].map(id=>initial.ports.find(p=>p.deviceId===id&&p.type===kind&&p.gn===3));
  assert.ok(ends.every(Boolean));
  await first.click('[data-face="front"]');
  for(const p of ends){
   const measure=await first.evaluate(`(()=>{const b=document.querySelector('[data-vport="${p.id}"]');if(!b)return null;const r=b.querySelector('[data-ir-hit]')?.getBoundingClientRect()||b.getBoundingClientRect();return {title:b.querySelector('title')?.textContent||b.getAttribute('title'),w:r.width,h:r.height,svg:b.querySelector('[data-physical-media]')?.outerHTML}})()`);
   assert.ok(measure&&measure.title.includes(wanted),JSON.stringify(measure));
   assert.ok(measure.w>=23.99&&measure.h>=23.99);
   assert.ok(measure.svg.includes(`data-physical-media="${kind}"`));
  }
  await portClick(first,ends[0].id);
  await portClick(first,ends[1].id);
  await saved(first);
  assert.ok((await snapshot(first)).connections.some(c=>c.fromPortId===ends[0].id&&c.toPortId===ends[1].id||c.fromPortId===ends[1].id&&c.toPortId===ends[0].id));
 }
 const after=normalize(await snapshot(first));
 assert.equal(after.connections.length,initial.connections.length+2);
 checks.push('Real Click-Click connects SFP56 and QSFP-DD UUIDs, named tooltips, distinct generic glyphs and targets>=24px; commit confirmed');
 // A cross-family click is rejected in the real UI and cannot create a cable.
 const before=normalize(await snapshot(first));
 const a=before.ports.find(p=>p.deviceId===f.media7.a&&p.type==='sfp56'&&p.gn===4);
 const b=before.ports.find(p=>p.deviceId===f.media7.b&&p.type==='qsfpdd'&&p.gn===4);
 await portClick(first,a.id);await portClick(first,b.id);
 await new Promise(r=>setTimeout(r,250));
 assert.deepEqual(normalize(await snapshot(first)),before);
 await first.click('[data-face="rear"]');
 for(const kind of ['sfp56','qsfpdd']){
  const p=before.ports.find(p=>p.deviceId===f.media7.a&&p.type===kind&&p.gn===2);
  const text=await first.evaluate(`document.querySelector('[data-vport="${p.id}"]').textContent`);
  assert.ok(text.includes('User <img> Ω '+kind));
  assert.equal(await first.evaluate(`!!document.querySelector('[data-vport="${p.id}"] img')`),false);
 }
 await shot(first,'media7-rear-labels.png');
 await first.click('[data-face="front"]');await shot(first,'media7-front-connections.png');
 await writeFile(path.join(out,'expected-browser-project.json'),JSON.stringify(before));
 await first.send('Page.reload',{ignoreCache:true});
 await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload');
 await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),before);
 const other=await session('hardware-second');await infrastructure(other);assert.deepEqual(normalize(await snapshot(other)),before);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),before);
 await writeFile(path.join(out,'BROWSER-MEDIA7.json'),JSON.stringify({result:'PASS',guiCables:2,newTypes:['sfp56','qsfpdd'],
  genericGlyphsAndTooltips:true,crossFamilyNoMutation:true,userLabelsEscaped:true,reload:true,secondSession:true,readerSameSnapshot:true},null,2)+'\n');
 checks.push('Cross-family UI refuses mutation; explicit rear labels escaped; reload and independent authorized/reader sessions retain snapshot');
});
