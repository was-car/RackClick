import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareCommand,executeCommand,cancelPendingCommand,rememberCompensation} from '../src/inventory-api.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
function fixture(){
 const api={actorId:id(1),sendMutation:async()=>null};
 const operation=prepareCommand(api,id(2),'operations.compensate',{operationId:id(3)},5);
 const data={customerId:id(2),revision:6,requestId:operation.requestId,operationId:id(4),result:{resourceId:id(5),compensationKind:'groupGrowth',removedPortIds:[id(6)],removedGroupIds:[id(7)],compensatedOperationId:id(3)}};
 api.sendMutation=async()=>data;return {api,operation,data};
}
test('structural result validates with explicit removed IDs',async()=>{const f=fixture();assert.deepEqual(await executeCommand(f.api,f.operation),f.data)});
test('malformed structural responses remain uncertain',async()=>{
 for(const mutate of [d=>d.revision++,d=>d.customerId=id(99),d=>d.requestId=id(99),d=>d.result.removedPortIds=[],d=>d.result.removedPortIds=[id(6),id(6)],d=>d.result.removedGroupIds=[id(6)],d=>d.result.removedGroupIds=[id(5)],d=>d.result.before={},d=>d.result.compensatedOperationId=id(99),d=>d.result.removedPortIds=Array.from({length:257},(_,i)=>id(i+100))]){
  const f=fixture();mutate(f.data);await assert.rejects(executeCommand(f.api,f.operation),e=>e.code==='response_invalid'&&e.uncertain);
 }
});
test('lost response replay and committed cancellation use the same structural validation',async()=>{
 const f=fixture();let count=0;f.api.sendMutation=async()=>{if(++count===1)throw {uncertain:true};return f.data};
 await assert.rejects(executeCommand(f.api,f.operation));assert.deepEqual(await executeCommand(f.api,f.operation),f.data);
 f.api.sendMutation=async()=>({state:'committed',customerId:id(2),requestId:f.operation.requestId,operation:f.data});
 assert.equal((await cancelPendingCommand(f.api,f.operation)).state,'committed');
 f.data.result.removedGroupIds=[id(6)];await assert.rejects(cancelPendingCommand(f.api,f.operation),e=>e.uncertain);
});
test('port-specific expectations cannot accept a structural result',async()=>{
 const f=fixture();rememberCompensation({actorId:id(1),customerId:id(2),operationId:id(3),revision:5,deviceId:id(5),groupId:id(7),portIds:[id(6)]});
 await assert.rejects(executeCommand(f.api,f.operation),e=>e.code==='response_invalid'&&e.uncertain);
});
