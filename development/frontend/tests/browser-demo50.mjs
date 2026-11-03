import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,normalize} from './browser-quince-support.mjs';

async function clickPort(tab,id){
 const point=await tab.evaluate(`(()=>{const e=document.querySelector('[data-vport="${id}"]');if(!e)throw Error('port_missing');e.scrollIntoView({block:'center',inline:'center'});const r=e.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2}})()`);
 for(const type of ['mousePressed','mouseReleased'])await tab.send('Input.dispatchMouseEvent',{type,...point,button:'left',clickCount:1});
}
await runScenario(async({first,session,fixture:f,checks,out,shot})=>{
 await first.wait(`document.querySelectorAll('[data-customer-id]').length===50`,'fifty synthetic clients');
 const visible=await first.evaluate(`([...document.querySelectorAll('[data-customer-id]')]).map(e=>e.dataset.customerId)`);
 assert.deepEqual([...visible].sort(),f.customers.map(c=>c.id).sort());checks.push('all fifty customers visible and UUIDs match');
 const representatives=['c01','c11','c21','c29','c35','c41','c47'];
 const faces=[];
 for(let i=0;i<representatives.length;i++){
  const key=representatives[i],customer=f.customers.find(c=>c.key===key),lang=['es','de','en'][i%3];
  await first.field('.rc-settings select',lang);await first.wait(`document.querySelector('.rc-settings select')?.value===${JSON.stringify(lang)}&&!document.querySelector('.rc-settings select').disabled`,'language saved');
  await first.click(`[data-customer-id="${customer.id}"]`);await first.wait(`!!document.querySelector('.rc-inventory-toolbar')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'representative inventory');
  const project=await first.evaluate(`fetch('/api/v1/customers/${customer.id}/project').then(r=>r.json())`);
  assert.ok(project.racks.length>0&&project.devices.length>0&&project.connections.length>0);
  assert.ok(await first.evaluate(`document.body.textContent.includes(${JSON.stringify(customer.name)})`),'name preserved without translation');
  await first.click('.ir-racks button:first-child');await first.wait(`!!document.querySelector('[data-face="front"]')`,'selected rack faces');
  for(const face of ['front','rear']){
   await first.click(`[data-face="${face}"]`);assert.equal(await first.evaluate(`!!document.querySelector('[data-face="${face}"][aria-pressed="true"]')||document.querySelector('[data-face="${face}"]').className.includes('active')`),true);
   faces.push({customer:key,face,language:lang});
  }
  if(i===0)await shot(first,'demo50-rack.png');
  const pair=f.guiPairs.find(p=>p.customerKey===key);
  if(pair){
   const rack=project.racks.find(r=>r.id===pair.rackId),index=await first.evaluate(`([...document.querySelectorAll('.ir-racks button')]).findIndex(b=>b.querySelector('span')?.firstChild?.textContent===${JSON.stringify(rack.name)})`);
   assert.ok(index>=0);await first.click(`.ir-racks button:nth-child(${index+1})`);await first.click(`[data-face="${pair.face}"]`);
   await clickPort(first,pair.fromPortId);await clickPort(first,pair.toPortId);
   await first.wait(`!document.querySelector('dialog[open]')&&!document.querySelector('.rc-inventory-toolbar button:disabled')`,'connection committed');
   await first.wait(`fetch('/api/v1/customers/${customer.id}/project').then(r=>r.json()).then(p=>p.connections.some(c=>[c.fromPortId,c.toPortId].includes(${JSON.stringify(pair.fromPortId)})&&[c.fromPortId,c.toPortId].includes(${JSON.stringify(pair.toPortId)})))`,'Click-Click persisted');
  }
  await first.click('.ir-all-clients');await first.wait(`document.querySelectorAll('[data-customer-id]').length===50`,'return to fifty clients');
 }
 await first.send('Page.reload');await first.wait(`document.querySelectorAll('[data-customer-id]').length===50`,'reload fifty clients');
 const second=await session();await second.wait(`document.querySelectorAll('[data-customer-id]').length===50`,'second session');
 for(const pair of f.guiPairs){
  const project=await second.evaluate(`fetch('/api/v1/customers/${pair.customerId}/project').then(r=>r.json())`);
  assert.ok(project.connections.some(c=>[c.fromPortId,c.toPortId].includes(pair.fromPortId)&&[c.fromPortId,c.toPortId].includes(pair.toPortId)));
 }
 checks.push('seven scenarios, fourteen front/rear views, ES/DE/EN, native Click-Click, reload and second session');
 await writeFile(path.join(out,'DEMO50-BROWSER.json'),JSON.stringify({result:'PASS',customerCount:50,representatives,faces,clickClickConnections:f.guiPairs.length,reloadAndSecondSession:true},null,2)+'\n');
});
