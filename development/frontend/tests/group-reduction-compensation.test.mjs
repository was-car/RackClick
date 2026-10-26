import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareCommand,executeCommand,cancelPendingCommand,rememberCompensation} from '../src/inventory-api.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
function fixture(){
 const api={actorId:id(101),sendMutation:async()=>null};
 const operation=prepareCommand(api,id(102),'operations.compensate',{operationId:id(103)},5);
 const data={customerId:id(102),revision:6,requestId:operation.requestId,operationId:id(104),result:{resourceId:id(105),compensationKind:'groupReduction',restoredPortIds:[id(106)],restoredGroupIds:[id(107)],restoredConnectionIds:[id(108)],compensatedOperationId:id(103)}};
 api.sendMutation=async()=>data;return {api,operation,data};
}
test('restored IDs variant permits cables or no cable/group to restore',async()=>{
 const f=fixture();assert.deepEqual(await executeCommand(f.api,f.operation),f.data);
 f.data.result.restoredGroupIds=[];f.data.result.restoredConnectionIds=[];assert.deepEqual(await executeCommand(f.api,f.operation),f.data);
});
test('invalid identities, collisions, missing fields and bounded counts remain uncertain',async()=>{
 for(const mutate of [d=>d.revision++,d=>d.requestId=id(199),d=>d.customerId=id(199),d=>d.result.compensatedOperationId=id(199),d=>d.result.restoredPortIds=[],d=>d.result.restoredPortIds=[id(106),id(106)],d=>d.result.restoredGroupIds=[id(106)],d=>d.result.restoredConnectionIds=[id(105)],d=>d.result.restoredConnectionIds=[id(108),id(109)],d=>delete d.result.restoredConnectionIds,d=>d.result.before={},d=>d.result.restoredPortIds=Array.from({length:256},(_,i)=>id(i+200))]){
  const f=fixture();mutate(f.data);await assert.rejects(executeCommand(f.api,f.operation),e=>e.code==='response_invalid'&&e.uncertain);
 }
});
test('lost response replay and committed cancellation validate the restored variant',async()=>{
 const f=fixture();let attempts=0;f.api.sendMutation=async()=>{if(++attempts===1)throw {uncertain:true};return f.data};
 await assert.rejects(executeCommand(f.api,f.operation));assert.deepEqual(await executeCommand(f.api,f.operation),f.data);
 f.api.sendMutation=async()=>({state:'committed',customerId:id(102),requestId:f.operation.requestId,operation:f.data});
 assert.equal((await cancelPendingCommand(f.api,f.operation)).state,'committed');
 f.data.result.restoredConnectionIds=[id(106)];await assert.rejects(cancelPendingCommand(f.api,f.operation),e=>e.uncertain);
});
test('attribute-only response expectations reject the reduction variant',async()=>{
 const f=fixture();rememberCompensation({actorId:id(101),customerId:id(102),operationId:id(103),revision:5,deviceId:id(105),groupId:id(107),portIds:[id(106)]});
 await assert.rejects(executeCommand(f.api,f.operation),e=>e.code==='response_invalid'&&e.uncertain);
});
