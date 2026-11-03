import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {hardwareReference} from '../src/hardware-mounting.ts';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';

await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);
 await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 const ids={};
 async function create(key,name,parent,destination=f.rack){
  await first.click('[data-add-hardware]');await first.wait(`!!document.querySelector('dialog[open] [data-hardware-profile]')`,'hardware dialog');
  await chooseHardware(first,key,'hw-reference-v1');await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',destination);
  if(parent)await first.field('[data-hardware-parent]',parent);
  await submit(first);await saved(first);const p=await snapshot(first),d=p.devices.find(d=>d.name===name);assert.ok(d,key+' saved');ids[key]=d.id;
  const profile=hardwareReference.profiles.find(p=>p.key===key);
  assert.equal(d.hardwareProfileKey,key);assert.deepEqual(d.properties.physicalDimensionsMm,{width:profile.widthMm,height:profile.heightMm,depth:profile.depthMm});assert.equal(d.properties.hardwareProfileVersion,hardwareReference.version);
  for(const g of profile.groups){const ports=p.ports.filter(port=>port.deviceId===d.id&&port.properties.hardwareGroupKey===g.key);assert.equal(ports.length,g.count);assert.ok(ports.every(port=>port.face===g.face&&port.type===g.type));}
  return d.id;
 }
 const shelf=await create('shelf-2u','Bandeja QA');
 const fw=await create('desktop-firewall-6','Firewall QA <img> Ω',shelf);
 await create('switch-24','Switch QA');await create('patchpanel-24','Patch panel QA');
 await first.wait(`!!document.querySelector('[data-mounted-rack]')`,'mounted rack');
 let p=await snapshot(first);assert.equal(p.devices.filter(d=>d.rackId===f.rack).length,4);assert.equal(p.ports.filter(port=>port.deviceId!==f.legacy).length,81);
 assert.equal(p.devices.find(d=>d.id===fw).mountParentId,shelf);assert.equal(p.devices.find(d=>d.id===fw).sizeU,0);
 assert.equal(await first.evaluate(`document.querySelector('[data-mount-occupancy]').textContent.includes('4/4 U')`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-mounted-on="${shelf}"]').closest('[data-hardware-key="shelf-2u"]')!==null`),true);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-devid="${fw}"] img')`),false);
 checks.push('GUI created all four profiles with dimensions and actual front/rear groups matching the reference; 4U reserved, 81 unique ports; nested firewall escapes literal text');
 const port=(key,face,gn)=>p.ports.find(port=>port.deviceId===ids[key]&&port.face===face&&port.gn===gn).id;
 async function connect(a,b,count){await first.click(`[data-vport="${a}"]`);await first.click(`[data-vport="${b}"]`);await saved(first);await first.wait(`document.querySelectorAll('[data-wire]').length>=${count}`,'cable visible');}
 await connect(port('desktop-firewall-6','front',1),port('switch-24','front',1),1);
 await connect(port('switch-24','front',2),port('patchpanel-24','front',1),2);
 await first.evaluate(`document.querySelector('[data-mounted-rack]').scrollIntoView({block:'start'})`);await shot(first,'mounting-front.png');
 await first.click('[data-face="rear"]');
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-hardware-key="patchpanel-24"] [data-vport]').length`),24);
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-hardware-key="switch-24"] [data-vport]').length`),2);
 await connect(port('patchpanel-24','rear',1),port('desktop-firewall-6','rear',1),1);
 p=await snapshot(first);assert.equal(p.connections.length,3);
 const panel=p.ports.filter(port=>port.deviceId===ids['patchpanel-24']);assert.equal(panel.filter(port=>port.gn===1).length,2);assert.equal(new Set(panel.filter(port=>port.gn===1).map(port=>port.groupId)).size,2);
 checks.push('Click-Click persisted three cables using independent front/rear UUIDs; the repeated panel number 1 is unambiguous');
 await shot(first,'mounting-rear.png');
 // Editing metadata must retain mounting, template facts, ports and cables.
 await first.click(`[data-hardware-edit="${fw}"]`);await first.field('dialog [name=name]','Firewall persistido Ω');await first.field('dialog [name=notes]','Datos sintéticos <script>literal</script>');await submit(first);await saved(first);
 // An editable field must never claim to persist an omitted value.
 await first.click(`[data-hardware-edit="${fw}"]`);assert.equal(await first.evaluate(`!!document.querySelector('dialog [name=poeBudget]')`),false);await first.button('Cancelar');
 const beforeRejected=normalize(await snapshot(first));
 await first.click('[data-add-hardware]');await chooseHardware(first,'switch-24','hw-reference-v1');await first.field('[data-hardware-name]','No cabe');await submit(first);
 await first.wait(`document.querySelector('dialog[open] [role=alert]')?.textContent.includes('no tiene espacio')`,'full rack rejected');assert.deepEqual(normalize(await snapshot(first)),beforeRejected);await first.button('Cancelar');
 checks.push('Full-rack GUI rejection keeps the dialog and exact project; omitted PoE budget is not editable');
 // Preserve the adopted renderer and its interactions when profiles share a rack with legacy devices.
 await create('shelf-2u','Bandeja rack mixto',undefined,f.mixedRack);
 await first.button('Gestionar infraestructura');await first.click(`[data-rack-id="${f.mixedRack}"] .rc-rack-open`);await first.wait(`!!document.querySelector('.ir-device-row[data-devid="${f.legacy}"]')`,'legacy RC9 row');
 assert.equal(await first.evaluate(`!!document.querySelector('.ir-device-row[data-devid="${f.legacy}"] .ir-face')`),true);
 await first.evaluate(`(()=>{const row=document.querySelector('[data-devid="${f.legacy}"]');[...row.querySelectorAll('.ir-device-actions button')].find(b=>b.textContent.trim()==='−').click()})()`);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-devid="${f.legacy}"] .ir-face')`),false);
 await first.evaluate(`(()=>{const row=document.querySelector('[data-devid="${f.legacy}"]');[...row.querySelectorAll('.ir-device-actions button')].find(b=>b.textContent.trim()==='+').click()})()`);
 await first.click(`[data-devid="${f.legacy}"] .ir-device-actions button:nth-child(2)`);await saved(first);
 await first.click('[data-face="rear"]');assert.equal(await first.evaluate(`document.querySelectorAll('[data-devid="${f.legacy}"] [data-ir-hit]').length`),2);
 await shot(first,'mounting-mixed-rc9.png');checks.push('Mixed rack keeps the original RC9 NAS row, collapse/expand, ordering and automatic rear ports');
 const expected=normalize(await snapshot(first));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload clients');await infrastructure(first);
 assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.equal(await reader.evaluate(`document.querySelector('[data-add-hardware]')===null`),true);assert.deepEqual(normalize(await snapshot(reader)),expected);
 checks.push('Metadata edit preserves all mounting/port/cable identities; reload, a second authorized account and a reader see the committed state; reader has no create control');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
