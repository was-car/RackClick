// I-04.03: two real duplicate forms; SQL source preparation belongs to the runner.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,fixture as ids,delay} from './browser-quince-support.mjs';

const collections=['sites','buildings','rooms','racks','devices','portGroups','ports','connections'];
const allIds=project=>collections.flatMap(key=>project[key].map(row=>row.id));
const writeJson=(out,name,value)=>writeFile(path.join(out,name),JSON.stringify(value,null,2)+'\n');
const names=['Copia sin cables Ω <img>','Copia con reserva 東京 <img>'];

await runScenario(async({first,session,checks,shot,out,origin,responses})=>{
 await infrastructure(first);
 const original=await snapshot(first),writes=[],mappings=[];
 const commandPath='/api/v1/customers/'+ids.customer+'/commands';
 first.ws.addEventListener('message',event=>{
  const data=JSON.parse(event.data),request=data.params?.request;
  if(data.method==='Network.requestWillBeSent'&&request?.method==='POST'&&request.url===origin+commandPath){
   const headers=Object.fromEntries(Object.entries(request.headers).map(([key,value])=>[key.toLowerCase(),value]));
   writes.push({...JSON.parse(request.postData),revision:headers['if-match']});
  }
 });
 const equal=(actual,expected,label)=>assert.deepEqual(normalize(actual),normalize(expected),label);
 const audit=()=>first.evaluate(`(async()=>{const response=await fetch('/api/v1/admin/audit?limit=50');if(!response.ok)throw Error('Audit read status '+response.status);return response.json()})()`);
 async function openDuplicate(name,includeConnections){
  await first.evaluate(`(()=>{const row=document.querySelector('[data-rack-id="${ids.rackA}"]'),button=[...row.querySelectorAll('button')].find(b=>b.textContent.trim()==='Duplicar');if(!button||button.disabled)throw Error('Source duplicate button unavailable');button.click()})()`);
  await first.wait(`document.querySelector('dialog #operation-title')?.textContent==='Duplicar'`,'source duplicate form');
  await first.field('dialog [name=name]',name);await first.field('dialog [name=includeConnections]',String(includeConnections));
 }
 async function openRack(tab,id){
  await tab.button('Gestionar infraestructura');
  await tab.wait(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`,'rack card');
  await tab.click(`[data-rack-id="${id}"] .rc-rack-open`);await tab.wait(`!!document.querySelector('#rack-detail-export')`,'physical rack');
 }
 function assertCopy(before,after,name,includeConnections){
  const added=key=>after[key].filter(row=>!before[key].some(old=>old.id===row.id));
  const rackRows=added('racks'),devices=added('devices'),groups=added('portGroups'),ports=added('ports'),cables=added('connections');
  assert.equal(rackRows.length,1);assert.equal(devices.length,2);assert.equal(groups.length,3);assert.equal(ports.length,5);assert.equal(cables.length,includeConnections?1:0);
  const rack=rackRows[0],mapping={name,includeConnections,rackId:rack.id,devices:{},groups:{},ports:{},connectionId:includeConnections?cables[0].id:null};
  assert.deepEqual(rack,{...original.racks.find(row=>row.id===ids.rackA),id:rack.id,name});
  for(const device of original.devices.filter(row=>row.rackId===ids.rackA)){
   const targets=devices.filter(row=>row.rackId===rack.id&&row.sortOrder===device.sortOrder);assert.equal(targets.length,1);
   const copied=targets[0];mapping.devices[device.id]=copied.id;
   assert.deepEqual(copied,{...device,id:copied.id,rackId:rack.id});
   for(const group of original.portGroups.filter(row=>row.deviceId===device.id)){
    const groupTargets=groups.filter(row=>row.deviceId===copied.id&&row.sortOrder===group.sortOrder);assert.equal(groupTargets.length,1);
    const copiedGroup=groupTargets[0];mapping.groups[group.id]=copiedGroup.id;
    assert.deepEqual(copiedGroup,{...group,id:copiedGroup.id,deviceId:copied.id});
    for(const port of original.ports.filter(row=>row.groupId===group.id)){
     const portTargets=ports.filter(row=>row.groupId===copiedGroup.id&&row.sortOrder===port.sortOrder);assert.equal(portTargets.length,1);
     const copiedPort=portTargets[0];mapping.ports[port.id]=copiedPort.id;
     assert.deepEqual(copiedPort,{...port,id:copiedPort.id,deviceId:copied.id,groupId:copiedGroup.id});
    }
   }
  }
  const sourceDevices=original.devices.filter(row=>row.rackId===ids.rackA);
  const sourceGroups=original.portGroups.filter(row=>sourceDevices.some(d=>d.id===row.deviceId));
  const sourcePorts=original.ports.filter(row=>sourceDevices.some(d=>d.id===row.deviceId));
  for(const [key,source] of [['devices',sourceDevices],['groups',sourceGroups],['ports',sourcePorts]])assert.deepEqual(Object.keys(mapping[key]).sort(),source.map(row=>row.id).sort(),'Complete '+key+' mapping');
  assert.notEqual(mapping.ports[ids.pa],mapping.ports[ids.extraPort],'Repeated gn1 retains two port identities');
  assert.equal(ports.find(p=>p.id===mapping.ports[ids.pa]).status,'reserved');
  assert.equal(ports.find(p=>p.id===mapping.ports[ids.extraPort]).status,'reserved');
  if(includeConnections){
   const source=original.connections.find(row=>row.id===ids.cable),copied=cables[0];
   assert.ok(Number.isFinite(Date.parse(copied.createdAt))&&Date.parse(copied.createdAt)>Date.parse(source.createdAt),'Copied cable receives a new timestamp');
   assert.deepEqual(copied,{...source,id:copied.id,fromPortId:mapping.ports[source.fromPortId],toPortId:mapping.ports[source.toPortId],createdAt:copied.createdAt});
   assert.ok(![source.fromPortId,source.toPortId].includes(copied.fromPortId)&&![source.fromPortId,source.toPortId].includes(copied.toPortId),'Copied endpoints use only new ports');
  }
  const generated=[rack.id,...devices.map(row=>row.id),...groups.map(row=>row.id),...ports.map(row=>row.id),...cables.map(row=>row.id)];
  assert.equal(new Set(generated).size,generated.length);assert.ok(generated.every(id=>!allIds(before).includes(id)),'Entire new UUID sets are disjoint from source and earlier copy');
  assert.equal(new Set(allIds(after)).size,allIds(after).length,'No cross-collection UUID collisions');
  assert.ok(!after.connections.some(c=>[c.fromPortId,c.toPortId].includes(mapping.ports[ids.pa2])),'Copy of externally connected source port is unconnected');
  assert.ok(!after.connections.some(c=>[c.fromPortId,c.toPortId].includes(mapping.ports[ids.extraPort])),'Unconnected reserved port stays unconnected');
  if(!includeConnections)assert.ok(!after.connections.some(c=>Object.values(mapping.ports).some(id=>[c.fromPortId,c.toPortId].includes(id))),'No new copy port is connected when cables excluded');
  const expected=structuredClone(before);expected.revision++;
  for(const key of ['racks','devices','portGroups','ports','connections'])expected[key].push(...added(key));
  equal(after,expected,'Only exact copied rows and one revision were added');
  for(const key of collections)assert.deepEqual(normalize(after)[key].filter(row=>original[key].some(old=>old.id===row.id)),normalize(original)[key],'Original '+key+' remain exact');
  return mapping;
 }
 function oneAuditCommit(before,after){
  const added=after.events.filter(row=>!before.events.some(old=>old.id===row.id));
  assert.equal(added.length,1);assert.equal(added[0].action,'inventory.rack.duplicate');
  assert.deepEqual(after.events.filter(row=>before.events.some(old=>old.id===row.id)),before.events,'Earlier audit entries remain exact');
  assert.equal(after.nextBeforeId,null,'Small isolated audit page is complete');
 }

 assert.equal(original.racks.length,2);assert.equal(original.devices.length,3);assert.equal(original.portGroups.length,4);assert.equal(original.ports.length,7);assert.equal(original.connections.length,2);
 assert.equal(original.ports.find(p=>p.id===ids.pa).status,'reserved');assert.equal(original.ports.find(p=>p.id===ids.extraPort).status,'reserved');
 assert.equal(original.ports.filter(p=>p.deviceId===ids.a&&p.gn===1).length,2);
 assert.ok(!original.connections.some(c=>[c.fromPortId,c.toPortId].includes(ids.extraPort)));
 const initialAudit=await audit();assert.equal(initialAudit.nextBeforeId,null);
 await writeJson(out,'initial-project.json',original);

 await openDuplicate(names[0],false);
 assert.equal(await first.evaluate(`document.querySelector('dialog [name=includeConnections]').selectedOptions[0].textContent`),'No');
 assert.equal(await first.evaluate(`!!document.querySelector('dialog input[type=checkbox]')`),false,'Excluding cables never requires reserved-port confirmation');
 assert.equal(await first.evaluate(`document.querySelector('dialog form').checkValidity()`),true);
 await submit(first);await saved(first);
 const withoutCables=await snapshot(first),firstMap=assertCopy(original,withoutCables,names[0],false);mappings.push(firstMap);
 const afterFirstAudit=await audit();oneAuditCommit(initialAudit,afterFirstAudit);
 assert.equal(writes.length,1);assert.deepEqual(writes[0].payload,{id:ids.rackA,name:names[0],includeConnections:false,confirmedReservedPortIds:[]});
 await openRack(first,firstMap.rackId);
 await first.wait(`document.querySelectorAll('[data-devid]').length===2`,'without-cables copy rendered');
 assert.equal(await first.evaluate(`document.querySelectorAll('.ir-wires [data-wire]').length`),0);
 assert.equal(await first.evaluate(`!!document.querySelector('.ir-rack-title img')`),false);
 await shot(first,'duplicate-without-cables.png');await first.button('Gestionar infraestructura');
 checks.push('Source has connected reserved pa and unconnected reserved extraPort with repeated gn1; GUI copy with cables No needs no checkbox, commits once, maps every UUID and attribute, and adds no connection');

 await openDuplicate(names[1],true);
 await first.wait(`!!document.querySelector('dialog input[type=checkbox][required]')`,'connected reservation requires confirmation');
 assert.equal(await first.evaluate(`document.querySelector('dialog input[type=checkbox]').checked`),false);
 assert.equal(await first.evaluate(`document.querySelector('dialog input[type=checkbox]').validity.valueMissing`),true);
 assert.equal(await first.evaluate(`document.querySelector('dialog form').checkValidity()`),false);
 const beforeBlocked=await snapshot(first),beforeBlockedAudit=await audit(),writeCount=writes.length;
 await submit(first);await delay(250);
 assert.equal(writes.length,writeCount,'Native required checkbox blocks HTTP command');
 equal(await snapshot(first),beforeBlocked,'Blocked form preserves exact snapshot and revision');
 assert.deepEqual(await audit(),beforeBlockedAudit,'Blocked form preserves audit exactly');
 assert.equal(await first.evaluate(`!!document.querySelector('dialog[open]')`),true);
 await shot(first,'duplicate-required-confirmation.png');
 await first.click('dialog input[type=checkbox][required]');
 assert.equal(await first.evaluate(`document.querySelector('dialog input[type=checkbox]').checked&&document.querySelector('dialog form').checkValidity()`),true);
 await submit(first);await saved(first);
 const expected=await snapshot(first),secondMap=assertCopy(withoutCables,expected,names[1],true);mappings.push(secondMap);
 const finalAudit=await audit();oneAuditCommit(afterFirstAudit,finalAudit);
 assert.equal(expected.revision,original.revision+2);assert.equal(writes.length,2);
 assert.deepEqual(writes[1].payload,{id:ids.rackA,name:names[1],includeConnections:true,confirmedReservedPortIds:[ids.pa]});
 assert.ok(!writes[1].payload.confirmedReservedPortIds.includes(ids.extraPort));
 assert.ok(!writes[1].payload.confirmedReservedPortIds.some(id=>mappings.some(map=>Object.values(map.ports).includes(id))));
 assert.deepEqual(writes.map(w=>w.type),['rack.duplicate','rack.duplicate']);
 await openRack(first,secondMap.rackId);
 await first.wait(`!!document.querySelector('[data-wire="${secondMap.connectionId}"]')`,'confirmed internal copied cable');
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('.ir-wires [data-wire]')].map(e=>e.dataset.wire)`),[secondMap.connectionId]);
 assert.equal(await first.evaluate(`document.querySelector('[data-wire="${secondMap.connectionId}"]').getAttribute('stroke-dasharray')`),null);
 await shot(first,'duplicate-reserved-with-internal-cable.png');
 await openRack(first,ids.rackA);await first.wait(`document.querySelectorAll('.ir-wires [data-wire]').length===2`,'original source cables');
 assert.deepEqual((await first.evaluate(`[...document.querySelectorAll('.ir-wires [data-wire]')].map(e=>e.dataset.wire)`)).sort(),[ids.cable,ids.externalCable].sort());
 assert.equal(await first.evaluate(`document.querySelector('[data-wire="${ids.externalCable}"]').getAttribute('stroke-dasharray')`),'5 3');
 checks.push('Cables Sí shows required checkbox: unchecked submit sends zero POST and preserves snapshot/revision/audit; confirmation commits once carrying only old paUUID, copies exactly internal cable onto new endpoints, and preserves external cable/source/unconnected extraPort');

 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'first session reload');await infrastructure(first);
 equal(await snapshot(first),expected,'Reload retains both exact copies');
 const second=await session('move-second');await infrastructure(second);equal(await snapshot(second),expected,'Second authorized session reads both exact copies');
 for(const [tab,map] of [[first,firstMap],[second,secondMap]]){
  await openRack(tab,map.rackId);await tab.wait(`document.querySelectorAll('[data-devid]').length===2`,'copy in independent session');
  assert.deepEqual(await tab.evaluate(`[...document.querySelectorAll('[data-devid]')].map(e=>e.dataset.devid)`),[map.devices[ids.a],map.devices[ids.b]]);
 }
 checks.push('Full reload and second authorized cookie context preserve complete source, two distinct copies, device order and connection topology; Python checks exact nine-table SQL and server restart');
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[]);
 await writeJson(out,'duplicate-variant-maps.json',mappings);await writeJson(out,'expected-project.json',expected);
 await writeJson(out,'duplicate-variants-details.json',{writes,blockedSubmit:{httpCommands:0,snapshotAndRevisionUnchanged:true,auditUnchanged:true},auditBefore:initialAudit,auditAfter:finalAudit,limits:['Two synthetic rack duplicate variants; existing API refusal/permission battery runs separately. No Dosen, drag/touch, Windows reboot, actual QA or adoption.']});
});
