// I-04.02: real Edge forms against a new synthetic PostgreSQL laboratory.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,fixture as ids} from './browser-quince-support.mjs';

const location='Ubicación Ω 東京 <img data-rack-variant="literal"> & final';
const initialName='Switch catálogo Ω <img data-rack-variant="initial">';
const editedName='Switch editado 東京 <img data-rack-variant="device">';
const initialNotes={sn:'SERIAL inicial Ω',model:'Modelo inicial',ip:'192.0.2.18',firmware:'FW inicial',text:'Nota inicial <img> 東京'};
const editedNotes={sn:'SERIAL literal <img> Ω',model:'Modelo <b>東京</b>',ip:'192.0.2.28 Ω',firmware:'FW 2 <script>literal</script>',text:'Notas editadas Ω\n東京 <img data-rack-variant="notes"> & final'};
const collections=['sites','buildings','rooms','racks','devices','portGroups','ports','connections'];
const writeJson=(out,name,value)=>writeFile(path.join(out,name),JSON.stringify(value,null,2)+'\n');

await runScenario(async({first,session,checks,shot,out,origin,responses})=>{
 await infrastructure(first);
 const original=await snapshot(first),writes=[];
 const commandPath='/api/v1/customers/'+ids.customer+'/commands';
 first.ws.addEventListener('message',event=>{
  const data=JSON.parse(event.data),request=data.params?.request;
  if(data.method==='Network.requestWillBeSent'&&request?.method==='POST'&&request.url===origin+commandPath){
   const headers=Object.fromEntries(Object.entries(request.headers).map(([key,value])=>[key.toLowerCase(),value]));
   writes.push({...JSON.parse(request.postData),revision:headers['if-match']});
  }
 });
 async function close(){
  await first.evaluate(`(()=>{const button=[...document.querySelectorAll('dialog[open] button')].find(b=>b.textContent.trim()==='Cancelar');if(!button)throw Error('Cancel button missing');button.click()})()`);
  await first.wait(`!document.querySelector('dialog[open]')`,'dialog cancelled');
 }
 async function inlineEdit(attribute,id){
  await first.evaluate(`(()=>{const row=document.querySelector(${JSON.stringify('['+attribute+'="'+id+'"]')}),bar=[...row.children].find(e=>e.classList.contains('rc-inline-buttons')),button=[...bar.querySelectorAll('button')].find(b=>b.textContent.trim()==='Editar');if(!button)throw Error('Inline edit missing');button.click()})()`);
  await first.wait(`!!document.querySelector('dialog[open] [name=name]')`,'inline editor');
 }
 async function options(field,keys,prefix){
  const actual=await first.evaluate(`[...document.querySelectorAll(${JSON.stringify('dialog[open] select[name='+field+'] option')})].map(o=>({value:o.value,text:o.textContent,title:o.title}))`);
  const selected=keys.map(key=>actual.find(o=>o.value===ids[key]));
  for(let index=0;index<keys.length;index++){
   const value=selected[index],id=ids[keys[index]];
   assert.ok(value,'Option exists for '+keys[index]);
   assert.ok(value.text.startsWith(prefix),'Literal name/path retained: '+keys[index]);
   assert.ok(value.text.includes(id),'Complete UUID in option: '+keys[index]);
   assert.ok(value.title.includes(id)&&value.title.includes(prefix),'Complete UUID and path/name in title: '+keys[index]);
  }
  assert.equal(new Set(selected.map(o=>o.text)).size,keys.length,'Repeated names remain distinguishable');
  return actual;
 }
 async function openRack(id){
  if(!await first.evaluate(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`))await first.button('Gestionar infraestructura');
  await first.wait(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`,'rack card');
  await first.click(`[data-rack-id="${id}"] .rc-rack-open`);
  await first.wait(`!!document.querySelector('#rack-detail-export')`,'rack physical view');
 }
 function equal(actual,expected,label){assert.deepEqual(normalize(actual),normalize(expected),label)}
 function assertTooltip(tab,id){return tab.evaluate(`document.querySelector('[data-devid="${id}"] .ir-device-name')?.title`)}

 assert.equal(original.sites.length,2);assert.equal(original.buildings.length,2);assert.equal(original.rooms.length,2);
 assert.equal(original.racks.length,2);assert.equal(original.devices.length,3);
 for(const key of ['sites','buildings','rooms','racks'])assert.ok(original[key].every(row=>row.name==='room'));
 const originalIds=collections.flatMap(key=>original[key].map(row=>row.id));
 assert.equal(new Set(originalIds).size,originalIds.length,'Every synthetic inventory UUID is unique');
 assert.equal(original.devices.filter(d=>d.rackId===ids.rackA).reduce((sum,d)=>sum+d.sizeU,0),2);
 assert.equal(original.devices.filter(d=>d.rackId===ids.rackB).reduce((sum,d)=>sum+d.sizeU,0),1);

 await inlineEdit('data-building-id',ids.buildingA);
 const siteOptions=await options('siteId',['siteA','siteB'],'room');await close();
 await inlineEdit('data-room-id',ids.roomA);
 const buildingOptions=await options('buildingId',['buildingA','buildingB'],'room');await close();
 await inlineEdit('data-rack-id',ids.rackA);
 const roomOptions=await options('roomId',['roomA','roomB'],'room / room / room');
 assert.equal(await first.evaluate(`document.querySelector('dialog [name=name]').value`),'room');
 await first.field('dialog [name=roomId]',ids.roomB);await first.field('dialog [name=sizeU]','2');await first.field('dialog [name=location]',location);
 await shot(first,'rack-edit-repeated-paths.png');await submit(first);await saved(first);
 let expected=structuredClone(original);expected.revision++;
 Object.assign(expected.racks.find(r=>r.id===ids.rackA),{roomId:ids.roomB,sizeU:2,location});
 equal(await snapshot(first),expected,'Rack edit changes only room, exact occupied capacity, location and revision');
 await openRack(ids.rackA);
 assert.equal(await first.evaluate(`document.querySelector('.ir-rack-title p').textContent`),location);
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-rack-variant]').length`),0,'Location remains text, no injected element');
 await first.button('Gestionar infraestructura');
 await inlineEdit('data-rack-id',ids.rackA);await first.field('dialog [name=sizeU]','1');
 const failedStart=responses.length;await submit(first);
 await first.wait(`!!document.querySelector('dialog[open] [role=alert]')`,'below occupied capacity rejection');
 assert.ok((await first.evaluate(`document.querySelector('dialog [role=alert]').textContent`)).length>0);
 assert.deepEqual(responses.slice(failedStart).filter(r=>r.path===commandPath&&r.status>=400),[{path:commandPath,status:409}]);
 equal(await snapshot(first),expected,'Rejected 1U reduction preserves the complete project and revision');
 assert.equal(await first.evaluate(`document.querySelector('dialog [name=sizeU]').value`),'1','Rejected draft remains visible');
 await shot(first,'rack-capacity-409.png');await close();
 equal(await snapshot(first),expected,'Cancel after rejection preserves committed state');
 checks.push('Repeated site/building/room paths expose literal room and full UUID/title; rackA moves to selected roomB and shrinks to occupied2U;1U returns409 with draft retained and entire snapshot/revision unchanged');

 await openRack(ids.rackA);await first.click(`[data-devid="${ids.a}"] button[title="Opciones del equipo"]`);
 await first.wait(`document.querySelector('dialog #operation-title')?.textContent==='Mover'`,'move rack equipment');
 const rackOptions=await options('rackId',['rackA','rackB'],'room');
 assert.ok(rackOptions.filter(o=>[ids.rackA,ids.rackB].includes(o.value)).every(o=>!o.text.startsWith('Sala')),'Literal rack name is not a dictionary key');
 await shot(first,'rack-move-literal-options.png');await close();
 equal(await snapshot(first),expected,'Inspecting and cancelling move writes nothing');
 checks.push('Opciones del equipo→Mover distinguishes two racks literally named room by complete UUID/title without translating the name; cancel preserves all data');

 await first.button('Gestionar infraestructura');await first.button('Añadir equipo');
 await first.wait(`!!document.querySelector('dialog [name=catalogKey] option[value=sw8p]')`,'real server catalogue sw8p');
 await first.field('dialog [name=catalogKey]','sw8p');
 await first.wait(`!!document.querySelector('[data-catalog-preview="sw8p"]')`,'sw8p server preview');
 const catalogue=await first.evaluate(`(async()=>{const response=await fetch('/api/v1/customers/${ids.customer}/catalog?language=es',{headers:{'If-Match':'"'+${expected.revision}+'"'}});if(!response.ok)throw Error('Catalogue reference status '+response.status);const data=await response.json();return {catalogVersion:data.catalogVersion,catalogSha256:data.catalogSha256,language:data.language,preset:data.presets.find(p=>p.key==='sw8p')}})()`);
 assert.ok(catalogue.preset);assert.equal(catalogue.language,'es');
 await first.field('dialog [name=rackId]',ids.rackB);await first.field('dialog [name=name]',initialName);
 for(const [key,value] of Object.entries(initialNotes))await first.field('dialog [name='+({text:'notes'}[key]||key)+']',value);
 await submit(first);await saved(first);
 const createdProject=await snapshot(first),created=createdProject.devices.find(d=>!original.devices.some(o=>o.id===d.id));
 assert.ok(created,'One real catalogue equipment created');assert.equal(createdProject.devices.length,original.devices.length+1);
 assert.equal(created.name,initialName);assert.equal(created.kind,'rackEquipment');assert.equal(created.rackId,ids.rackB);assert.equal(created.roomId,null);
 assert.equal(created.sizeU,catalogue.preset.sizeU);
 assert.deepEqual(created.properties,{preset:catalogue.preset.label,icon:catalogue.preset.icon,color:catalogue.preset.color,notes:initialNotes,catalog:{presetKey:'sw8p',version:catalogue.catalogVersion,sha256:catalogue.catalogSha256,language:'es'}});
 const createdGroups=createdProject.portGroups.filter(g=>g.deviceId===created.id),createdPorts=createdProject.ports.filter(p=>p.deviceId===created.id);
 assert.equal(createdGroups.length,2);assert.equal(createdPorts.length,10);assert.equal(createdPorts.filter(p=>p.poe&&p.type==='rj45_poe').length,8);
 assert.equal(createdPorts.filter(p=>p.type==='sfp').length,2);assert.equal(createdPorts.filter(p=>p.type==='power').length,0);
 assert.ok([created.id,...createdGroups.map(g=>g.id),...createdPorts.map(p=>p.id)].every(id=>!originalIds.includes(id)));
 const createdExpected=structuredClone(expected);createdExpected.revision++;
 createdExpected.devices.push(created);createdExpected.portGroups.push(...createdGroups);createdExpected.ports.push(...createdPorts);
 equal(createdProject,createdExpected,'Creation adds only real preset device/groups/ports and revision');
 await writeJson(out,'created-project.json',createdProject);await writeJson(out,'catalogue-reference.json',catalogue);

 await openRack(ids.rackB);await first.click(`[data-devid="${created.id}"] .ir-device-name`);
 await first.wait(`!!document.querySelector('dialog [name=sn]')`,'RC9 equipment name opens edit form');
 assert.equal(await first.evaluate(`document.querySelector('dialog [name=name]').value`),initialName);
 for(const [key,value] of Object.entries(initialNotes))assert.equal(await first.evaluate(`document.querySelector(${JSON.stringify('dialog [name='+({text:'notes'}[key]||key)+']')}).value`),value);
 await first.field('dialog [name=name]',editedName);await first.field('dialog [name=sizeU]','2');await first.field('dialog [name=poeBudget]','0');
 for(const [key,value] of Object.entries(editedNotes))await first.field('dialog [name='+({text:'notes'}[key]||key)+']',value);
 await submit(first);await saved(first);
 expected=structuredClone(createdProject);expected.revision++;
 Object.assign(expected.devices.find(d=>d.id===created.id),{name:editedName,sizeU:2,poeBudget:0,properties:{...created.properties,notes:editedNotes}});
 equal(await snapshot(first),expected,'Edit changes only name, sizeU, budget, five notes and revision');
 const tooltip=await assertTooltip(first,created.id);
 for(const value of [editedName,...Object.values(editedNotes)])assert.ok(tooltip.includes(value),'Literal edited tooltip field preserved');
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-rack-variant]').length`),0,'Device/notes remain literal text');
 await shot(first,'catalogue-equipment-edited.png');
 checks.push('Añadir equipo creates genuine server sw8p with fresh device/group/portUUIDs; RC9 name editor persists name,2U,zero budget,five literal notes while all catalogue/preset/icon/colour,nonnote properties,kind/rack,groups/ports/cables remain exact');

 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'first session reload');await infrastructure(first);
 equal(await snapshot(first),expected,'Full reload keeps exact final snapshot');await openRack(ids.rackB);
 assert.equal(await assertTooltip(first,created.id),tooltip,'Reload preserves exact tooltip');
 const second=await session('move-second');await infrastructure(second);
 equal(await snapshot(second),expected,'Independent authorized cookie session reads exact final snapshot');
 await second.click(`[data-rack-id="${ids.rackB}"] .rc-rack-open`);await second.wait(`!!document.querySelector('[data-devid="${created.id}"] .ir-device-name')`,'second session preset device');
 assert.equal(await assertTooltip(second,created.id),tooltip,'Second actor sees the same literal tooltip');
 checks.push('Full reload and second authorized session retain exact project, catalogue equipment and literal tooltip; native runner separately checks SQL and server restart');
 assert.deepEqual(writes.map(w=>w.type),['rack.update','rack.update','device.createFromCatalog','device.update']);
 assert.equal(writes[2].payload.presetKey,'sw8p');assert.equal(writes[2].payload.rackId,ids.rackB);
 assert.deepEqual(responses.filter(r=>r.path.startsWith('/api/')&&r.status>=400&&!(r.path==='/api/v1/me'&&r.status===401)),[{path:commandPath,status:409}]);
 await writeJson(out,'expected-project.json',expected);
 await writeJson(out,'rack-variants-details.json',{siteOptions,buildingOptions,roomOptions,rackOptions,location,initialName,editedName,initialNotes,editedNotes,createdDeviceId:created.id,tooltip,writes,limits:['One real sw8p preset and normal rack equipment; not all33 presets, Dosen, drag/touch, Windows reboot, actual QA or adoption.']});
});
