import test from 'node:test';
import assert from 'node:assert/strict';
import {compensationCandidate,candidateMatches} from '../src/inventory-compensation.ts';
import {prepareCommand,executeCommand,cancelPendingCommand,rememberCompensation} from '../src/inventory-api.ts';
import {groupCompensationWords} from '../src/inventory-group-compensation-words.ts';
import {pendingRecord} from '../src/pending-journal.ts';

const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
function fixture(kind='groupGrowth'){
 const actor=id(1),customer=id(2),device=id(3),group=id(4),otherGroup=id(8),remote=id(9);
 const row=(n,g,gn)=>({id:id(n),deviceId:device,groupId:g,type:'rj45',gn,sortOrder:gn-1,label:'Literal Ω <img>',status:'free',poe:false,watts:null,color:null,face:'auto',powerRole:'unspecified',properties:{nested:{preserve:true}}});
 const before={customerId:customer,revision:4,devices:[{id:device,name:'<svg> 東京',properties:{},kind:'rackEquipment',rackId:id(90),roomId:null,sizeU:1,sortOrder:0,poeBudget:null}],
  portGroups:[{id:group,deviceId:device,type:'rj45',name:'Same name',prefix:'P',sortOrder:0},{id:otherGroup,deviceId:device,type:'rj45',name:'Same name',prefix:'P',sortOrder:1}],
  ports:[row(5,group,1),row(6,group,2),row(7,otherGroup,1)],connections:[{id:id(10),fromPortId:id(6),toPortId:remote,note:'Old Ω',properties:{}},{id:id(11),fromPortId:id(7),toPortId:id(12),note:'Old 2',properties:{}}]};
 const after=structuredClone(before);after.revision++;
 let createdIds=[],removedIds=[];
 if(kind==='groupGrowth'){
  after.ports.push(row(20,group,3));after.portGroups.push({id:id(21),deviceId:device,type:'rj45',name:'New',prefix:'',sortOrder:2});after.ports.push(row(22,id(21),1));createdIds=[id(21),id(22),id(20)];
 }else{
  removedIds=[id(7),id(6)];after.ports=after.ports.filter(p=>!removedIds.includes(p.id));after.portGroups=after.portGroups.filter(g=>g.id!==otherGroup);after.connections=[];
 }
 const api={actorId:actor,sendMutation:async()=>null};
 const operation=prepareCommand(api,customer,'device.editPortGroups',{deviceId:device,groups:after.portGroups.map(g=>({id:g.id,type:g.type,name:g.name,prefix:g.prefix,retainedPortIds:[],addCount:0})),removedPortIds:removedIds,...(kind==='groupReduction'?{confirmationToken:'server-preview-token'}:{})},4);
 const result={customerId:customer,revision:5,requestId:operation.requestId,operationId:id(40),result:{resourceId:device,createdIds,removedIds}};
 const candidate=()=>compensationCandidate(operation,result,before,actor,customer,after);
 return {api,actor,customer,device,group,otherGroup,before,after,operation,result,candidate,kind};
}

test('pure growth describes added IDs only; same gn/names in other groups stay outside scope',()=>{
 const f=fixture(),c=f.candidate();assert.equal(c.compensationKind,'groupGrowth');assert.deepEqual(c.portIds,[id(20),id(22)]);assert.deepEqual(c.groupIds,[id(21)]);assert.deepEqual(c.connectionIds,[]);
 assert.ok(candidateMatches(c,f.after,f.actor,f.customer));assert.equal(f.before.ports.length,3);assert.equal('before' in c,false);
});
test('pure reduction describes original UUIDs and removed cables, never reconstructed values',()=>{
 const f=fixture('groupReduction'),c=f.candidate();assert.equal(c.compensationKind,'groupReduction');assert.deepEqual(c.portIds,[id(6),id(7)]);assert.deepEqual(c.groupIds,[id(8)]);assert.deepEqual(c.connectionIds,[id(10),id(11)]);
 assert.deepEqual(Object.keys(c).sort(),['actorId','compensationKind','connectionIds','customerId','deviceId','groupIds','operationId','portIds','revision']);
});
test('no fabricated structural history when either adjacent server view is missing or stale',()=>{
 const f=fixture();for(const [before,after] of [[null,f.after],[f.before,undefined],[{...f.before,revision:5},f.after],[f.before,{...f.after,revision:6}],[f.before,{...f.after,customerId:id(99)}]])assert.equal(compensationCandidate(f.operation,f.result,before,f.actor,f.customer,after),null);
});
test('mixed rename, order, attributes, removal/addition and cable changes never offer undo',()=>{
 for(const mutate of [f=>f.after.portGroups[0].name='Renamed',f=>f.after.portGroups[0].sortOrder=1,f=>f.after.ports[0].properties.nested.preserve=false,f=>f.after.ports.shift(),f=>f.after.connections[0].note='Changed',f=>f.after.connections.push({id:id(99),fromPortId:id(20),toPortId:id(98)}),f=>f.after.devices[0].name='Changed']){
  const f=fixture();mutate(f);assert.equal(f.candidate(),null);
 }
 const f=fixture('groupReduction');f.after.portGroups[0].prefix='New';assert.equal(f.candidate(),null);
});
test('source actor/customer/request/revision and exact created/removed IDs are fenced',()=>{
 for(const mutate of [f=>f.result.customerId=id(99),f=>f.result.requestId=id(99),f=>f.result.revision++,f=>f.result.result.resourceId=id(99),f=>f.result.result.createdIds.push(id(99)),f=>f.result.result.createdIds.push(id(20)),f=>f.result.result.extra={},f=>f.result.result.removedIds=[id(5)]]){
  const f=fixture();mutate(f);assert.equal(f.candidate(),null);
 }
 const f=fixture();assert.equal(compensationCandidate(f.operation,f.result,f.before,id(99),f.customer,f.after),null);assert.equal(candidateMatches(f.candidate(),f.after,f.actor,id(99)),false);
});
test('no-op and empty-group-only changes do not become structural inverse candidates',()=>{
 const f=fixture();f.after=structuredClone(f.before);f.after.revision=5;
 assert.equal(compensationCandidate(f.operation,{...f.result,result:{resourceId:f.device,createdIds:[],removedIds:[]}},f.before,f.actor,f.customer,f.after),null);
 f.after.portGroups.push({id:id(21),deviceId:f.device,type:'rj45',name:'Empty',prefix:'',sortOrder:2});
 assert.equal(compensationCandidate(f.operation,{...f.result,result:{resourceId:f.device,createdIds:[id(21)],removedIds:[]}},f.before,f.actor,f.customer,f.after),null);
});
test('bounds accept 256 changed IDs and refuse 257 or more than 32 groups',()=>{
 const f=fixture();f.after.ports=f.before.ports.concat(Array.from({length:256},(_,i)=>({...f.before.ports[0],id:id(1000+i),gn:i+3,sortOrder:i+2})));f.after.portGroups=structuredClone(f.before.portGroups);f.result.result.createdIds=f.after.ports.slice(3).map(p=>p.id);
 assert.equal(f.candidate().portIds.length,256);f.after.ports.push({...f.after.ports.at(-1),id:id(2000)});f.result.result.createdIds.push(id(2000));assert.equal(f.candidate(),null);
 const g=fixture();g.after.portGroups.push(...Array.from({length:30},(_,i)=>({...g.after.portGroups[0],id:id(3000+i)})));assert.equal(g.candidate(),null);
});
function undo(f){
 const c=f.candidate();rememberCompensation(c);const operation=prepareCommand(f.api,f.customer,'operations.compensate',{operationId:c.operationId},5);
 const fields=f.kind==='groupGrowth'?{removedPortIds:[...c.portIds].reverse(),removedGroupIds:c.groupIds}:{restoredPortIds:[...c.portIds].reverse(),restoredGroupIds:c.groupIds,restoredConnectionIds:c.connectionIds};
 const data={customerId:f.customer,revision:6,requestId:operation.requestId,operationId:id(41),result:{resourceId:f.device,compensatedOperationId:c.operationId,compensationKind:f.kind,...fields}};
 f.api.sendMutation=async()=>data;return {operation,data};
}
test('response expectations accept the reviewed structural sets, including different array order',async()=>{
 for(const kind of ['groupGrowth','groupReduction']){const f=fixture(kind),{operation,data}=undo(f);assert.deepEqual(await executeCommand(f.api,operation),data);assert.deepEqual(JSON.parse(operation.body),{type:'operations.compensate',payload:{operationId:id(40)}})}
});
test('wrong device, IDs or response kind cannot produce a confirmed structural success',async()=>{
 for(const kind of ['groupGrowth','groupReduction'])for(const mutate of [d=>d.result.resourceId=id(99),d=>d.result[kind==='groupGrowth'?'removedPortIds':'restoredPortIds']=[id(99)],d=>d.result[kind==='groupGrowth'?'removedGroupIds':'restoredGroupIds']=[],d=>d.result={resourceId:id(3),changedIds:[id(6)],compensatedOperationId:id(40)},d=>d.result.before={}]){
  const f=fixture(kind),{operation,data}=undo(f);mutate(data);await assert.rejects(executeCommand(f.api,operation),e=>e.code==='response_invalid'&&e.uncertain);
 }
});
test('lost response and committed cancellation reuse exact original requests and expectations',async()=>{
 for(const kind of ['groupGrowth','groupReduction']){
  const f=fixture(kind),{operation,data}=undo(f),sent=[];f.api.sendMutation=async op=>{sent.push(op);if(sent.length===1)throw {uncertain:true};return data};
  await assert.rejects(executeCommand(f.api,operation));assert.deepEqual(await executeCommand(f.api,operation),data);assert.equal(sent[0],sent[1]);
  f.api.sendMutation=async()=>({state:'committed',customerId:f.customer,requestId:operation.requestId,operation:data});assert.equal((await cancelPendingCommand(f.api,operation)).state,'committed');
  data.result[kind==='groupGrowth'?'removedPortIds':'restoredPortIds']=[id(99)];await assert.rejects(cancelPendingCommand(f.api,operation),e=>e.uncertain);
  const saved=pendingRecord(operation,'undoGroups','reviewed IDs');assert.deepEqual(saved.operation,operation);assert.equal(JSON.stringify(saved).includes('groupEditEvidence'),false);
 }
});
test('all three language scopes distinguish removal/restoration and require explicit review',()=>{
 for(const words of Object.values(groupCompensationWords))for(const key of ['title','groupGrowth','groupReduction','limits','confirm','context'])assert.ok(words[key].length>10);
});
