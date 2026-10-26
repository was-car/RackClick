import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi } from '../src/api.ts';
import { cancelGroup, confirmedGroup, createGroup, groupStatus, readAdminGroups } from '../src/admin-groups.ts';
const id='12345678-1234-1234-1234-123456789abc';
const userGroups={revision:3,groups:[{id,name:'Administrators',members:[{id,userName:'test-user',active:true}],grants:[{id,capability:'security.manage',scope:'systemhaus',target:null}]}]};
const customerGroups={revision:3,groups:[]};
const json=data=>new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});

test('groups load through GET without writes and retain declared scope',async()=>{
 const methods=[];const api=new RackClickApi(async(url,init)=>{methods.push(init?.method||'GET');return json(url.endsWith('/user-groups')?userGroups:customerGroups)});api.actorId=id;
 const result=await readAdminGroups(api);
 assert.equal(result.userGroups[0].grants[0].scope,'systemhaus');assert.deepEqual(result.customerGroups,[]);assert.deepEqual(methods,['GET','GET']);
});
test('different group snapshot revisions are rejected',async()=>{
 const api=new RackClickApi(async url=>json(url.endsWith('/user-groups')?userGroups:{...customerGroups,revision:4}));api.actorId=id;
 await assert.rejects(readAdminGroups(api),e=>e.code==='groups_changed');
});
test('targeted permission with no target is rejected',async()=>{
 const malformed=structuredClone(userGroups);malformed.groups[0].grants[0].scope='customer';
 const api=new RackClickApi(async url=>json(url.endsWith('/user-groups')?malformed:customerGroups));api.actorId=id;
 await assert.rejects(readAdminGroups(api),e=>e.code==='response_invalid');
});
test('actor change during group loading is rejected',async()=>{
 let api;api=new RackClickApi(async url=>{api.actorId='changed';return json(url.endsWith('/user-groups')?userGroups:customerGroups)});api.actorId=id;
 await assert.rejects(readAdminGroups(api),e=>e.code==='actor_changed');
});

const draft={actorId:id,requestId:'22345678-1234-1234-1234-123456789abc',kind:'customerGroup',name:'  München 東京  ',revision:3};
const created={resource:{id,name:'München 東京',kind:'customerGroup'},requestId:draft.requestId,systemhausRevision:4};
test('group creation and cancellation preserve original route, body, actor, key and revision',async()=>{
 const calls=[];const api=new RackClickApi(async(url,init)=>{calls.push({url,init});return json(url.endsWith('/cancel')?{requestId:draft.requestId,state:'committed',operation:created}:created)});api.actorId=id;api.csrf='csrf-test';
 assert.deepEqual(await createGroup(api,draft),created);assert.deepEqual(await cancelGroup(api,draft),created);
 assert.equal(calls[0].url,'/api/v1/admin/customer-groups');assert.equal(calls[1].url,'/api/v1/admin/customer-groups/operations/'+draft.requestId+'/cancel');
 for(const {init} of calls){assert.equal(init.method,'POST');assert.equal(init.headers['If-Match'],'"3"');assert.equal(init.headers['Idempotency-Key'],draft.requestId);assert.equal(init.headers['X-RackClick-Actor'],id);assert.deepEqual(JSON.parse(init.body),{name:draft.name})}
});
test('a mismatched successful group result remains unconfirmed',()=>{
 for(const wrong of [{...created,requestId:id},{...created,systemhausRevision:5},{...created,resource:{...created.resource,kind:'userGroup'}},{...created,resource:{...created.resource,name:'Other'}}])assert.throws(()=>confirmedGroup(wrong,draft),e=>e.code==='response_invalid'&&e.uncertain);
});
test('confirmation uses server whitespace policy: trims NEL but preserves BOM',()=>{
 for(const [name,saved] of [['\u0085München\u0085','München'],['\ufeffMünchen\ufeff','\ufeffMünchen\ufeff']]) {
  assert.deepEqual(confirmedGroup({...created,resource:{...created.resource,name:saved}},{...draft,name}).resource.name,saved);
 }
});
test('notRecorded is not cancellation; cancellation must be terminal with null operation',async()=>{
 let reply={requestId:draft.requestId,state:'notRecorded',operation:null};const api=new RackClickApi(async()=>json(reply));api.actorId=id;api.csrf='csrf-test';
 assert.equal(await groupStatus(api,draft),null);await assert.rejects(cancelGroup(api,draft),e=>e.code==='response_invalid'&&e.uncertain);
 reply={...reply,state:'cancelled'};assert.deepEqual(await cancelGroup(api,draft),reply);
 reply={...reply,operation:created};await assert.rejects(groupStatus(api,draft),e=>e.code==='response_invalid');
});
test('invalid drafts and changed actors cannot send group requests or accept in-flight results',async()=>{
 let calls=0;let change=false;const api=new RackClickApi(async()=>{calls++;if(change)api.actorId='changed';return json(created)});api.actorId=id;api.csrf='csrf-test';
 await assert.rejects(createGroup(api,{...draft,kind:'unknown'}),e=>e.code==='request_invalid');
 await assert.rejects(groupStatus(api,{...draft,actorId:draft.requestId}),e=>e.code==='actor_changed');assert.equal(calls,0);
 change=true;await assert.rejects(createGroup(api,draft),e=>e.code==='actor_changed');assert.equal(calls,1);
});
