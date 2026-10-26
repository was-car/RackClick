import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,poll} from './browser-quince-support.mjs';

// Every mutation uses the real editor. Fixture values are synthetic; only command
// type, payload and revision are retained, never cookies or authentication headers.
await runScenario(async({first,session,checks,fixture:f,out,shot,responses})=>{
 const commandPath=`/api/v1/customers/${f.customer}/commands`;
 const writes=[],planned=[];
 first.ws.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.method!=='Network.requestWillBeSent')return;
  const request=message.params.request;
  if(request.method!=='POST'||new URL(request.url).pathname!==commandPath)return;
  const command=JSON.parse(request.postData);
  const etag=Object.entries(request.headers).find(([key])=>key.toLowerCase()==='if-match')?.[1];
  const revision=/^"?([0-9]+)"?$/.exec(String(etag));
  writes.push({type:command.type,payload:command.payload,revision:revision?Number(revision[1]):null});
 });

 await infrastructure(first);
 const initial=await snapshot(first),expected=structuredClone(initial);
 const objects=[
  {key:'dose',id:f.dose,networkGroup:f.gdose,networkPort:f.pdose,powerGroup:f.gpowerDose,powerPort:f.ppowerDose,powerNeighbor:f.ppow2Dose},
  {key:'end',id:f.end,networkGroup:f.gend,networkPort:f.pend,powerGroup:f.gpowerEnd,powerPort:f.ppowerEnd,powerNeighbor:f.ppow2End}
 ];
 const fields=['status','poe','watts','color','label','face'];
 for(const object of objects){
  assert.ok(f.fieldSpec?.[object.key],`field specification for ${object.key}`);
  const device=initial.devices.find(value=>value.id===object.id);
  assert.equal(device.sizeU,null,'room devices have no rack units');
  const network=initial.ports.find(value=>value.id===object.networkPort);
  const power=initial.ports.find(value=>value.id===object.powerPort);
  assert.equal(network.deviceId,object.id);assert.equal(network.groupId,object.networkGroup);
  assert.equal(power.deviceId,object.id);assert.equal(power.groupId,object.powerGroup);
  assert.equal(network.gn,1);assert.equal(power.gn,1,'gn repeats in a different group');
  assert.equal(initial.portGroups.find(value=>value.id===object.networkGroup).type,'rj45');
  assert.equal(initial.portGroups.find(value=>value.id===object.powerGroup).type,'power');
  assert.equal(initial.ports.find(value=>value.id===object.powerNeighbor).groupId,object.powerGroup);
  assert.ok(!initial.connections.some(value=>Object.values(value).includes(object.powerPort)),
   'power role is edited on an unconnected port, without inventing an electrical circuit');
 }
 await writeFile(path.join(out,'initial-project.json'),JSON.stringify(initial,null,2)+'\n');

 async function openDevice(tab,id){
  await tab.evaluate(`(()=>{const row=document.querySelector('[data-room-device-id="${id}"]');if(!row)throw Error('room device missing');const button=[...row.querySelectorAll('button')].find(b=>b.textContent.trim()==='Editar');if(!button||button.disabled)throw Error('device editor unavailable');button.click()})()`);
  await tab.wait(`!!document.querySelector('dialog[open] [name=name]')`,'room device editor');
 }
 async function commit(command,changeExpected){
  const before=expected.revision;
  planned.push({...command,revision:before});
  changeExpected();expected.revision++;
  await submit(first);
  // A previous operation may still show "saved". First confirm this revision
  // in PostgreSQL through the project API, then require the GUI confirmation.
  const actual=await poll(async()=>{
   const value=await snapshot(first);return value.revision>=expected.revision?value:null;
  },`server revision ${expected.revision}`);
  await saved(first);
  assert.deepEqual(normalize(actual),normalize(expected),`only intended fields change after ${command.type} #${planned.length}`);
  assert.deepEqual(writes,planned,'GUI sends exactly the intended commands, IDs, group family and revision');
 }
 async function chooseSelect(tab,probe,value){
  await tab.evaluate(`(()=>{const select=[...document.querySelectorAll('dialog[open] select')].find(s=>[...s.options].some(o=>o.value===${JSON.stringify(probe)}));if(!select)throw Error('port select unavailable');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(select,${JSON.stringify(String(value))});select.dispatchEvent(new Event('change',{bubbles:true}))})()`);
 }
 async function editPort(object,portId,groupId,groupType,field,value){
  await first.evaluate(`(()=>{const port=document.querySelector('[data-room-port="${portId}"]');if(!port)throw Error('room port missing');port.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))})()`);
  await first.wait(`!!document.querySelector('dialog[open] .rc-port-selection')`,'port editor');
  const selection=await first.evaluate(`(()=>{const selects=[...document.querySelectorAll('dialog[open] select')];const group=selects.find(s=>[...s.options].some(o=>o.value===${JSON.stringify(groupId)}));return{groupId:group?.value,checked:document.querySelectorAll('dialog[open] .rc-port-selection input:checked').length,total:document.querySelectorAll('dialog[open] .rc-port-selection input').length}})()`);
  assert.equal(selection.groupId,groupId,'context menu keeps the actual group ID');
  assert.equal(selection.checked,1,'context menu selects exactly the clicked port');
  assert.equal(selection.total,initial.ports.filter(port=>port.groupId===groupId).length);
  await chooseSelect(first,'powerRole',field);
  const options={status:'free',poe:'true',face:'auto',powerRole:'unspecified'};
  if(field in options){
   await first.wait(`[...document.querySelectorAll('dialog[open] select')].some(s=>[...s.options].some(o=>o.value===${JSON.stringify(options[field])}))`,'port value choices');
   await chooseSelect(first,options[field],value);
  }else{
   assert.equal(await first.evaluate(`document.querySelectorAll('dialog[open] input:not([type=checkbox])').length`),1);
   await first.field('dialog[open] input:not([type=checkbox])',value===null?'':String(value));
  }
  const command={type:'ports.update',payload:{deviceId:object.id,groupId,groupType,portIds:[portId],changes:{[field]:value}}};
  await commit(command,()=>{
   const port=expected.ports.find(port=>port.id===portId);
   port[field]=value;
   if(field==='poe')port.type=value?'rj45_poe':'rj45';
  });
 }

 for(const object of objects){
  const spec=f.fieldSpec[object.key];
  await openDevice(first,object.id);
  assert.equal(await first.evaluate(`!!document.querySelector('dialog[open] [name=sizeU]')`),false,'room editor has no rack unit field');
  for(const [name,value] of Object.entries({name:spec.name,poeBudget:spec.poeBudget,sn:spec.notes.sn,model:spec.notes.model,ip:spec.notes.ip,firmware:spec.notes.firmware,notes:spec.notes.text}))
   await first.field(`dialog[open] [name=${name}]`,value===null?'':String(value));
  await commit({type:'device.update',payload:{id:object.id,name:spec.name,poeBudget:spec.poeBudget,properties:{notes:spec.notes}}},()=>{
   const device=expected.devices.find(value=>value.id===object.id);
   device.name=spec.name;device.poeBudget=spec.poeBudget;
   device.properties??={};device.properties.notes={...device.properties.notes,...spec.notes};
  });
 }
 for(const object of objects){
  const spec=f.fieldSpec[object.key];
  assert.deepEqual(Object.keys(spec.networkChanges).sort(),[...fields].sort(),'fixture specifies each network field once');
  for(const field of fields)await editPort(object,object.networkPort,object.networkGroup,'rj45',field,spec.networkChanges[field]);
  await editPort(object,object.powerPort,object.powerGroup,'power','powerRole',spec.powerRole);
 }

 assert.equal(planned.length,16);assert.equal(expected.revision,initial.revision+16);
 assert.deepEqual(writes.map(write=>write.type),['device.update','device.update',...Array(14).fill('ports.update')]);
 assert.deepEqual(responses.filter(response=>response.path===commandPath).map(response=>response.status),Array(16).fill(200));
 assert.deepEqual(expected.portGroups,initial.portGroups,'base group family and complete group metadata stay unchanged');
 assert.deepEqual(expected.connections,initial.connections,'existing cables are not replaced or deleted');
 for(const object of objects)assert.deepEqual(expected.ports.find(port=>port.id===object.powerNeighbor),initial.ports.find(port=>port.id===object.powerNeighbor),'unselected neighboring power port unchanged');
 checks.push('GUI: dos device.update con nombre, presupuesto y cinco notas, sin sizeU; catorce ports.update por ID y grupo/tipo explícitos. Los dieciséis reciben 200 y revisión nueva confirmada antes del estado de guardado.');
 checks.push('RJ45 y power repiten gn=1: sólo cambia el UUID seleccionado. PoE cambia tipo/poe del puerto; los grupos conservan rj45. Identidades, sala, propiedades completas, sizeU=null, vecinos y cables se conservan.');

 async function displayed(tab){
  assert.deepEqual(normalize(await snapshot(tab)),normalize(expected));
  for(const object of objects){
   const spec=f.fieldSpec[object.key];
   const display=await tab.evaluate(`(()=>{const row=document.querySelector('[data-room-device-id="${object.id}"]');return{title:row?.querySelector('h3')?.textContent,images:row?.querySelectorAll('img').length,injections:document.querySelectorAll('[data-room-field-injection]').length}})()`);
   assert.equal(display.title,spec.name,'Unicode and markup-looking names render as literal text');
   assert.equal(display.images,0);assert.equal(display.injections,0,'fixture markup never becomes an element');
   await openDevice(tab,object.id);
   const metadata=await tab.evaluate(`(()=>{const form=document.querySelector('dialog[open]');return Object.fromEntries(['name','poeBudget','sn','model','ip','firmware','notes'].map(name=>[name,form.querySelector('[name="'+name+'"]').value]))})()`);
   assert.deepEqual(metadata,{name:spec.name,poeBudget:String(spec.poeBudget),sn:spec.notes.sn,model:spec.notes.model,ip:spec.notes.ip,firmware:spec.notes.firmware,notes:spec.notes.text});
   assert.equal(await tab.evaluate(`document.querySelectorAll('dialog[open] [data-room-field-injection],dialog[open] img').length`),0,'notes stay literal in the editor');
   await tab.evaluate(`(()=>{const button=[...document.querySelectorAll('dialog[open] footer button')].find(b=>b.type==='button'&&b.textContent.trim()==='Cancelar');if(!button)throw Error('cancel unavailable');button.click()})()`);
   await tab.wait(`!document.querySelector('dialog[open]')`,'read-only editor closed');
  }
 }
 const second=await session(f.secondName);await infrastructure(second);await displayed(second);
 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'first session reload');await infrastructure(first);await displayed(first);
 await second.send('Page.reload');await second.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'second session reload');await infrastructure(second);await displayed(second);
 assert.deepEqual(writes,planned,'reloading and inspecting editors send no further commands');
 await shot(first,'room-fields-final.png');
 checks.push('Recarga y segunda cuenta autorizada leen el mismo proyecto y los cinco metadatos desde los controles reales; Unicode y <img> permanecen como texto literal. Roles power se editan sin cable ni afirmación sobre circuito físico.');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
 await writeFile(path.join(out,'room-fields-details.json'),JSON.stringify({writes,expectedCommits:16,initialRevision:initial.revision,finalRevision:expected.revision,secondSession:true,reloadedSessions:2,noRoomSizeUInput:true,physicalPowerCircuitTested:false},null,2)+'\n');
});
