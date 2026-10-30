import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi } from '../src/api.ts';
import { assignCustomerMember, cancelCustomerMember, confirmedCustomerMember, customerMemberStatus, readCustomerMemberTargets } from '../src/admin-customer-group-members.ts';
const actor='12345678-1234-1234-1234-123456789abc', group='22345678-1234-1234-1234-123456789abc',user='32345678-1234-1234-1234-123456789abc';
const draft={actorId:actor,requestId:'42345678-1234-1234-1234-123456789abc',groupId:group,customerId:user,assigned:false,revision:3};
const committed={resource:{groupId:group,customerId:user,assigned:false},requestId:draft.requestId,systemhausRevision:4};
const json=data=>new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
function apiFor(fn){const api=new RackClickApi(fn);api.actorId=actor;api.csrf='test-csrf';return api}
test('original membership IDs, boolean, actor, key and revision retained for mutation and cancellation',async()=>{
 const calls=[];const api=apiFor(async(url,init)=>{calls.push({url,init});return json(url.endsWith('/cancel')?{requestId:draft.requestId,state:'committed',operation:committed}:committed)});
 assert.deepEqual(await assignCustomerMember(api,draft),committed);assert.deepEqual(await cancelCustomerMember(api,draft),committed);
 assert.equal(calls[0].url,'/api/v1/admin/customer-groups/'+group+'/members');assert.equal(calls[1].url,calls[0].url+'/operations/'+draft.requestId+'/cancel');
 for(const {init} of calls){assert.equal(init.method,'POST');assert.equal(init.headers['If-Match'],'"3"');assert.equal(init.headers['Idempotency-Key'],draft.requestId);assert.equal(init.headers['X-RackClick-Actor'],actor);assert.deepEqual(JSON.parse(init.body),{customerId:user,assigned:false})}
});
for(const [field,value] of [['groupId',actor],['customerId',actor],['assigned',true]])test('mismatched committed '+field+' cannot confirm',()=>assert.throws(()=>confirmedCustomerMember({...committed,resource:{...committed.resource,[field]:value}},draft),e=>e.code==='response_invalid'&&e.uncertain));
for(const wrong of [{...committed,requestId:actor},{...committed,systemhausRevision:5}])test('mismatched key/revision cannot confirm '+JSON.stringify(wrong),()=>assert.throws(()=>confirmedCustomerMember(wrong,draft),e=>e.code==='response_invalid'));
test('notRecorded retains intention and is not a cancellation confirmation',async()=>{
 let state='notRecorded';const api=apiFor(async()=>json({requestId:draft.requestId,state,operation:null}));assert.equal(await customerMemberStatus(api,draft),null);await assert.rejects(cancelCustomerMember(api,draft),e=>e.code==='response_invalid');state='cancelled';assert.equal((await cancelCustomerMember(api,draft)).state,'cancelled');
});
test('changed actor before or during a request rejects results',async()=>{
 let calls=0;const api=apiFor(async()=>{calls++;api.actorId=user;return json(committed)});await assert.rejects(assignCustomerMember(api,{...draft,actorId:user}),e=>e.code==='actor_changed');assert.equal(calls,0);await assert.rejects(assignCustomerMember(api,draft),e=>e.code==='actor_changed');assert.equal(calls,1);
});
for(const bad of [{...draft,groupId:'not-id'},{...draft,assigned:'false'},{...draft,customerId:undefined},{...draft,name:'extra'}])test('invalid draft sends nothing '+JSON.stringify(bad),async()=>{let sent=false;await assert.rejects(assignCustomerMember(apiFor(async()=>{sent=true;return json(committed)}),bad),e=>e.code==='request_invalid');assert.equal(sent,false)});
test('administrative customer targets share revision and retain ID identity without inventory access',async()=>{
 let revision=3,duplicate=false,bad=false;const urls=[];
 const api=apiFor(async url=>{urls.push(url);
  if(url.endsWith('/customers'))return json({revision,customers:[{id:user,name:'Same name'},...(duplicate?[{id:user,name:'Other'}]:[]),...(bad?[{id:'bad',name:'Bad'}]:[])]});
  if(url.endsWith('/users'))return new Response(JSON.stringify({revision:3,users:[]}),{headers:{'Content-Type':'application/json',ETag:'"3"'}});
  return json({revision:3,groups:url.endsWith('/customer-groups')?[{id:group,name:'Same name',customers:[]}]:[]});
 });
 assert.equal((await readCustomerMemberTargets(api)).customers[0].id,user);assert(urls.every(u=>u.startsWith('/api/v1/admin/')));
 revision=4;await assert.rejects(readCustomerMemberTargets(api),e=>e.code==='groups_changed');revision=3;duplicate=true;await assert.rejects(readCustomerMemberTargets(api),e=>e.code==='response_invalid');duplicate=false;bad=true;await assert.rejects(readCustomerMemberTargets(api),e=>e.code==='response_invalid');
});
