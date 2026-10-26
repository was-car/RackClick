// I-04.05: destructive previews/cancellation for connected room objects and a
// mixed room/rack batch. Python owns SQL/operation/audit checkpoint assertions.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,poll,delay} from './browser-quince-support.mjs';

const kinds=['rackIds','deviceIds','groupIds','portIds','connectionIds'];
const sorted=values=>[...values].sort();
const writeJson=(out,name,value)=>writeFile(path.join(out,name),JSON.stringify(value,null,2)+'\n');

function deletionImpact(project,deviceIds){
 const removed=new Set(deviceIds);
 const portIds=project.ports.filter(row=>removed.has(row.deviceId)).map(row=>row.id);
 const ports=new Set(portIds);
 return {rackIds:[],deviceIds:sorted(deviceIds),
  groupIds:sorted(project.portGroups.filter(row=>removed.has(row.deviceId)).map(row=>row.id)),
  portIds:sorted(portIds),
  connectionIds:sorted(project.connections.filter(row=>ports.has(row.fromPortId)||ports.has(row.toPortId)).map(row=>row.id))};
}

function removedProject(project,impact){
 const value=structuredClone(project);value.revision++;
 for(const [collection,key] of [['racks','rackIds'],['devices','deviceIds'],['portGroups','groupIds'],['ports','portIds'],['connections','connectionIds']]){
  const ids=new Set(impact[key]);value[collection]=value[collection].filter(row=>!ids.has(row.id));
 }
 return value;
}

await runScenario(async({first,session,checks,fixture:f,out,shot,origin,responses})=>{
 const commandPath='/api/v1/customers/'+f.customer+'/commands',writes=[],previewRequests=[],previews=[],barriers=[];
 first.ws.addEventListener('message',event=>{
  const data=JSON.parse(event.data),request=data.params?.request;
  if(data.method!=='Network.requestWillBeSent'||request?.method!=='POST')return;
  const command=JSON.parse(request.postData||'{}');
  if(request.url===origin+commandPath+'/preview')previewRequests.push(command);
  if(request.url===origin+commandPath){
   const payload=structuredClone(command.payload),hasConfirmationToken=typeof payload.confirmationToken==='string'&&payload.confirmationToken.length>0;
   delete payload.confirmationToken;
   const headers=Object.fromEntries(Object.entries(request.headers).map(([key,value])=>[key.toLowerCase(),value]));
   // Deliberately never publish confirmation tokens, CSRF, cookies or headers.
   writes.push({type:command.type,payload,hasConfirmationToken,revision:headers['if-match']});
  }
 });

 assert.equal(await first.evaluate(`document.querySelector('.rc-settings select')?.value`),'es','Spanish laboratory session expected');
 await infrastructure(first);
 const initial=await snapshot(first);
 let expected=structuredClone(initial);
 const second=await session(f.secondName||'move-second');await infrastructure(second);
 assert.deepEqual(normalize(await snapshot(second)),normalize(expected),'Second actor starts with the same inventory');
 await writeJson(out,'initial-project.json',initial);
 const protectedCable=structuredClone(initial.connections.find(row=>row.id===f.protectedCable));
 assert.ok(protectedCable,'Independent nonincident protected cable exists');

 async function exact(label){assert.deepEqual(normalize(await snapshot(first)),normalize(expected),label)}
 async function barrier(stage){
  const project=await snapshot(first);
  await writeJson(out,stage+'-state.json',{stage,project,revision:project.revision,commandPosts:writes.length});
  const answer=await poll(async()=>{
   let text;try{text=await readFile(path.join(out,stage+'-continue.json'),'utf8')}catch(error){if(error.code==='ENOENT')return false;throw error}
   return JSON.parse(text);
  },'Python SQL/operation/audit check: '+stage,60000);
  assert.equal(answer.valid,true,'Python checkpoint must accept exact SQL/operation/audit state: '+stage);
  barriers.push({stage,valid:true,commandPosts:writes.length,revision:project.revision});
 }
 async function cancel(stage,label){
  const count=writes.length;
  await first.button('Cancelar');await first.wait(`!document.querySelector('dialog[open]')`,'cancelled preview');
  await delay(120);await exact(label);assert.equal(writes.length,count,label+': zero command POST');
  await barrier(stage);
 }
 async function openIndividual(){
  await first.evaluate(`(()=>{const row=document.querySelector('[data-room-device-id="${f.end}"]');if(!row)throw Error('End-device room card missing');const button=[...row.querySelectorAll('button')].find(b=>b.textContent.trim()==='Eliminar');if(!button||button.disabled)throw Error('Offered individual delete control unavailable');button.click()})()`);
  await first.wait(`!!document.querySelector('dialog[open] [name=name]')`,'individual delete dialog');
 }
 async function preview(wanted,label){
  await submit(first);
  await first.wait(`!!document.querySelector('dialog[open] [data-impact-kind="deviceIds"]')`,'server impact: '+label);
  const actual=Object.fromEntries(kinds.map(kind=>[kind,[]]));
  const sections=await first.evaluate(`[...document.querySelectorAll('dialog[open] [data-impact-kind]')].map(section=>({kind:section.dataset.impactKind,ids:[...section.querySelectorAll('[data-impact-id]')].map(row=>row.dataset.impactId)}))`);
  assert.equal(new Set(sections.map(section=>section.kind)).size,sections.length,'Impact has no duplicate sections');
  for(const section of sections){
   assert.ok(kinds.includes(section.kind),'Known impact collection');
   assert.equal(new Set(section.ids).size,section.ids.length,'Impact has no duplicate UUIDs');
   actual[section.kind]=sorted(section.ids);
  }
  assert.deepEqual(actual,wanted,'All five impact UUID collections exact: '+label);
  assert.equal(actual.connectionIds.includes(f.protectedCable),false,'Nonincident protected cable excluded');
  assert.equal(await first.evaluate(`!!document.querySelector('dialog[open] img')`),false,'Literal names do not create HTML elements');
  previews.push({label,impact:actual});
 }
 async function committed(next,label){
  await submit(first);
  await poll(async()=>(await snapshot(first)).revision===next.revision,'committed revision: '+label);
  await saved(first);expected=next;await exact(label);
  assert.equal(writes.length,expected.revision-initial.revision,'One POST per successful inventory commit');
  const current=await snapshot(first);
  assert.deepEqual(current.connections.find(row=>row.id===f.protectedCable),protectedCable,'Protected cable and both endpoints/attributes intact');
 }

 await barrier('ready');
 const singleImpact=deletionImpact(expected,[f.end]);
 assert.deepEqual(singleImpact,{rackIds:[],deviceIds:[f.end],groupIds:[f.gend],portIds:[f.pend],connectionIds:[f.roomCable]},'Independent single fixture shape');
 await openIndividual();await preview(singleImpact,'individual-cancel');
 assert.equal(await first.evaluate(`document.querySelector('dialog[open]').textContent.includes(${JSON.stringify(initial.devices.find(row=>row.id===f.dose).name)})`),true,'Incident cable preview names the retained Dose neighbour');
 await shot(first,'preview-single-room-object.png');
 await cancel('single-cancel','Cancelling individual deletion preserves the complete project');
 await openIndividual();await preview(singleImpact,'individual-confirm');
 await committed(removedProject(expected,singleImpact),'Individual end-device deletion removes only itself and its incident cable');
 assert.ok(expected.devices.some(row=>row.id===f.dose),'Neighbour Dose survives');
 assert.ok(expected.ports.some(row=>row.id===f.pdose2),'Retained incident endpoint survives as an unconnected port');
 await writeJson(out,'after-single-project.json',expected);
 await barrier('after-single');
 checks.push('Individual connected end-device: exact five impact sets; cancel changes no SQL/operations/audit at Python barrier; one commit removes only its device/group/port and roomCable, preserving its neighbour and protected cable');

 // Preserve the intentional selection order while crossing room/rack views.
 await first.click(`[data-select-device="${f.dose}"]`);
 await first.click(`[data-rack-id="${f.rackA}"] .rc-rack-open`);
 await first.wait(`!!document.querySelector('[data-devid="${f.b}"] input[type=checkbox]')`,'offered rack selection checkbox');
 await first.click(`[data-devid="${f.b}"] input[type=checkbox]`);
 await first.button('Gestionar infraestructura');
 assert.equal(await first.evaluate(`document.querySelector('[data-delete-selected]')?.textContent`),'Eliminar seleccionados (2/64)');
 const selected=[f.dose,f.b],batchImpact=deletionImpact(expected,selected);
 assert.deepEqual(batchImpact,{rackIds:[],deviceIds:sorted(selected),groupIds:sorted([f.gdose,f.gb]),
  portIds:sorted([f.pdose,f.pdose2,f.pdose3,f.pb,f.pb2]),connectionIds:sorted([f.cable,f.batchCable])},'Independent mixed batch fixture shape');
 await first.click('[data-delete-selected]');
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('dialog[open] [data-delete-device]')].map(row=>row.dataset.deleteDevice)`),selected,'Preview selection retains exact original UUID order');
 await preview(batchImpact,'batch-cancel');await shot(first,'preview-mixed-room-rack.png');
 await cancel('batch-cancel','Cancelling the mixed batch preserves the complete project');
 assert.equal(await first.evaluate(`document.querySelector('[data-delete-selected]')?.textContent`),'Eliminar seleccionados (2/64)','Cancelled batch selection retained');
 await first.click('[data-delete-selected]');await preview(batchImpact,'batch-confirm');
 await committed(removedProject(expected,batchImpact),'One mixed batch commit removes exactly Dose/B and incident cables');
 assert.equal(await first.evaluate(`!!document.querySelector('[data-delete-selected]')`),false,'Confirmed selection clears');
 assert.deepEqual(expected.connections,[protectedCable],'Only the nonincident protected cable remains');
 checks.push('Mixed room/rack selection [Dose,B]: exact five impact sets and two incident cables; cancel retains selection without commit; one batch commit preserves unselected hierarchy/devices/ports and nonincident cable');

 assert.deepEqual(writes.map(write=>write.type),['device.delete','devices.delete']);
 assert.deepEqual(writes.map(write=>write.payload),[{id:f.end},{deviceIds:selected}]);
 assert.deepEqual(writes.map(write=>write.revision),['"'+initial.revision+'"','"'+(initial.revision+1)+'"']);
 assert.ok(writes.every(write=>write.hasConfirmationToken),'Both confirmed commands carry a token without publishing it');
 assert.equal(expected.revision,initial.revision+2);
 assert.deepEqual(responses.filter(response=>response.path===commandPath).map(response=>response.status),[200,200]);
 assert.equal(previewRequests.length,4,'A fresh server preview is obtained after each cancellation');
 for(const tab of [first,second]){
  await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reloaded client list');
  await infrastructure(tab);assert.deepEqual(normalize(await snapshot(tab)),normalize(expected),'Full reload in either authorized session preserves exact state');
  assert.equal(await tab.evaluate(`!!document.querySelector('[data-room-device-id="${f.dose}"]')||!!document.querySelector('[data-room-device-id="${f.end}"]')`),false,'Deleted room cards stay absent');
 }
 await shot(first,'final-protected-cable.png');
 checks.push('Exactly two commands/ETags/revisions; both use fresh preview confirmation. Reload and another authorized actor read the exact surviving project; confirmation/CSRF/cookies never enter evidence');
 await writeJson(out,'expected-project.json',expected);
 await writeJson(out,'delete-impact-details.json',{writes,previews,previewRequests,barriers,expectedCommits:2,
  removedDevices:[f.end,f.dose,f.b],removedConnections:[f.roomCable,f.cable,f.batchCable],protectedCable,
  cancelChecks:{individual:true,mixedBatch:true,selectionRetained:true,pythonAtomicCheckpoints:true},
  limits:['SQL fixture, existing GUI actions, Spanish only; no Wascar QA, VM or Windows reboot.',
   'Python independently verifies exact SQL, operations/audit, permissions and process-restart persistence.',
   'This focus does not repeat the separate response-loss/idempotency/concurrency regression.']});
});
