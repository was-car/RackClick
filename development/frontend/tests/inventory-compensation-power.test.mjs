import test from 'node:test';
import assert from 'node:assert/strict';
import {compensationCandidate,candidateMatches} from '../src/inventory-compensation.ts';
import {prepareCommand} from '../src/inventory-api.ts';
import {RackClickApi} from '../src/api.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),actor=id(1),customer=id(2),device=id(3),group=id(4),ids=[id(5),id(6),id(7)];
function fixture(changes,states){const api=new RackClickApi();api.actorId=actor;const operation=prepareCommand(api,customer,'ports.update',{deviceId:device,groupId:group,groupType:'rj45',portIds:ids,changes},7,actor),result={customerId:customer,requestId:operation.requestId,operationId:id(8),revision:8,result:{resourceId:device,changedIds:ids}},before={customerId:customer,revision:7,ports:ids.map((id,i)=>({id,deviceId:device,groupId:group,type:'rj45_poe',poe:true,watts:null,...states?.[i]}))};return{operation,result,before}}
const candidate=f=>compensationCandidate(f.operation,f.result,f.before,actor,customer);
test('PoE and watts produce a scoped candidate for heterogeneous null/zero/decimal rows without storing inverse values',()=>{
 for(const changes of [{poe:false},{watts:12.125},{watts:null},{watts:0},{status:'reserved',label:'Ω',color:'#123456',face:'rear',poe:false,watts:90}]){const f=fixture(changes,[{type:'rj45',poe:true,watts:null},{type:'rj45_poe',poe:false,watts:0},{watts:12.75}]),c=candidate(f);assert.ok(c,JSON.stringify(changes));assert.deepEqual(c.portIds,ids);assert.deepEqual(Object.keys(c).sort(),['actorId','customerId','deviceId','groupId','operationId','portIds','revision']);assert.deepEqual(f.before.ports.map(p=>p.watts),[null,0,12.75]);assert.ok(candidateMatches(c,{customerId:customer,revision:8},actor,customer));assert.equal(candidateMatches(c,{customerId:customer,revision:9},actor,customer),false)}
});
test('a supplied PoE boolean can change only the RJ45 alias; exact canonical no-op remains hidden',()=>{
 for(const [poe,type] of [[true,'rj45'],[false,'rj45_poe']]){const f=fixture({poe},Array.from({length:3},()=>({poe,type})));assert.ok(candidate(f),'boolean unchanged but alias normalises');for(const p of f.before.ports)p.type=poe?'rj45_poe':'rj45';assert.equal(candidate(f),null,'canonical boolean and alias unchanged')}
 for(const watts of [null,0,12.125,90]){const f=fixture({watts},Array.from({length:3},()=>({watts})));assert.equal(candidate(f),null);f.before.ports[2].watts=watts===null?0:null;assert.ok(candidate(f),'null and zero are distinct')}
 const f=fixture({watts:0},[{type:'rj45',poe:true,watts:0},{type:'rj45',poe:true,watts:0},{type:'rj45',poe:true,watts:0}]);assert.equal(candidate(f),null,'watts does not implicitly normalise legacy types');
});
test('six-field scope still rejects explicit type/roles/properties and never invents previous values after reload',()=>{
 for(const unsupported of [{type:'rj45'},{powerRole:'unspecified'},{properties:{}},{groupId:id(99)}]){const f=fixture({poe:false,watts:null,...unsupported});assert.equal(candidate(f),null)}
 const f=fixture({poe:true},[{type:'rj45_poe'},{type:'rj45_poe'},{type:'rj45_poe'}]);assert.equal(candidate(f),null);assert.ok(compensationCandidate(f.operation,f.result,null,actor,customer),'recovery delegates prior values to server');assert.equal(compensationCandidate(f.operation,f.result,null,id(99),customer),null);assert.equal(compensationCandidate(f.operation,{...f.result,customerId:id(99)},null,actor,customer),null);
});
