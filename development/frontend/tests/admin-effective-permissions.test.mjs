import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {readEffectivePermissions,readEffectivePermissionAccounts,readEffectivePermissionView} from '../src/admin-effective-permissions.ts';
const actor='12345678-1234-1234-1234-123456789abc',user='22345678-1234-1234-1234-123456789abc',customer='32345678-1234-1234-1234-123456789abc',group='42345678-1234-1234-1234-123456789abc',cg='52345678-1234-1234-1234-123456789abc',zero='00000000-0000-0000-0000-000000000000';
const source={userGroupId:group,userGroupName:'Gruppe <img> 😀',capability:'legacy.synthetic',scopeType:'customerGroup',scopeId:cg};
const snapshot={revision:3,user:{id:user,userName:'Literal <script> 😀',active:true},permissions:{systemhausCapabilities:['systemhaus.read'],customers:[{customerId:customer,capabilities:['inventory.read','legacy.synthetic']}],sources:[source,{...source,capability:'inventory.read'}]}};
const copy=()=>structuredClone(snapshot);
const response=(data,etag='"3"')=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json',ETag:etag}});
function apiFor(fn){const api=new RackClickApi(fn);api.actorId=actor;return api}
const readApi=(data,etag)=>apiFor(async()=>response(data,etag));
test('GET exacto, no-store, sin mutación ni cabeceras de escritura; unknown literal sin promoción global',async()=>{const api=apiFor(async(path,init)=>{assert.equal(path,'/api/v1/admin/users/'+user+'/effective-permissions');assert.equal(init.method,undefined);assert.equal(init.cache,'no-store');assert.equal(init.body,undefined);assert.equal(init.headers,undefined);return response(snapshot)});assert.deepEqual(await readEffectivePermissions(api,user),snapshot);assert.deepEqual(snapshot.permissions.systemhausCapabilities,['systemhaus.read'])});
const invalidCases={
 'top-level extra':d=>d.password='forbidden',
 'revision zero':d=>d.revision=0,'revision unsafe':d=>d.revision=Number.MAX_SAFE_INTEGER+1,'revision string':d=>d.revision='3',
 'wrong user':d=>d.user.id=actor,'zero user':d=>d.user.id=zero,'empty name':d=>d.user.userName=' ',
 'active type':d=>d.user.active='true','user extra':d=>d.user.hash='forbidden',
 'permissions extra':d=>d.permissions.other=[],
 'caps type':d=>d.permissions.systemhausCapabilities='inventory.read',
 'empty capability':d=>d.permissions.systemhausCapabilities=[' '],
 'duplicate globals':d=>d.permissions.systemhausCapabilities=['x','x'],
 'null customer':d=>d.permissions.customers=[null],
 'duplicate customers':d=>d.permissions.customers.push(d.permissions.customers[0]),
 'zero customer':d=>d.permissions.customers[0].customerId=zero,
 'customer extra':d=>d.permissions.customers[0].name='invented',
 'missing inventory.read':d=>d.permissions.customers[0].capabilities=['legacy.synthetic'],
 'duplicate customer caps':d=>d.permissions.customers[0].capabilities.push('inventory.read'),
 'null source':d=>d.permissions.sources=[null],
 'source extra':d=>d.permissions.sources[0].grantId=group,
 'scope enum':d=>d.permissions.sources[0].scopeType='all',
 'global nonnull':d=>d.permissions.sources[0].scopeType='systemhaus',
 'customer null':d=>{d.permissions.sources[0].scopeType='customer';d.permissions.sources[0].scopeId=null},
 'zero group':d=>d.permissions.sources[0].userGroupId=zero,
 'zero scope':d=>d.permissions.sources[0].scopeId=zero,
 'empty group name':d=>d.permissions.sources[0].userGroupName='',
 'empty source cap':d=>d.permissions.sources[0].capability='',
 'inactive permissions':d=>d.user.active=false,
};
for(const [name,mutate] of Object.entries(invalidCases))test('DTO rechaza '+name,async()=>{const data=copy();mutate(data);await assert.rejects(readEffectivePermissions(readApi(data),user),e=>e.code==='response_invalid')});
for(const etag of ['"4"','W/"3"','3',''])test('ETag rechaza '+etag,async()=>assert.rejects(readEffectivePermissions(readApi(snapshot,etag),user),e=>e.code==='response_invalid'));
for(const id of [zero,'bad',''])test('objetivo inválido no envía '+id,async()=>{let called=false;await assert.rejects(readEffectivePermissions(apiFor(async()=>{called=true}),id),e=>e.code==='request_invalid');assert.equal(called,false)});
test('actor antes y después del await; rechazo antes no envía',async()=>{let sent=0;const api=apiFor(async()=>{sent++;api.actorId=user;return response(snapshot)});await assert.rejects(readEffectivePermissions(api,user,user),e=>e.code==='actor_changed');assert.equal(sent,0);await assert.rejects(readEffectivePermissions(api,user,actor),e=>e.code==='actor_changed');assert.equal(sent,1)});
test('inactivo exige y acepta tres arrays vacíos',async()=>{const d=copy();d.user.active=false;d.permissions={systemhausCapabilities:[],customers:[],sources:[]};assert.deepEqual(await readEffectivePermissions(readApi(d),user),d)});
function targetsApi(change=()=>{}){const values={
 '/admin/users':{revision:3,users:[snapshot.user]},
 '/admin/customers':{revision:3,customers:[{id:customer,name:'Cliente literal 😀'}]},
 '/admin/user-groups':{revision:3,groups:[{id:group,name:source.userGroupName,members:[snapshot.user],grants:[{id:actor,capability:'legacy.synthetic',scope:'customerGroup',target:{id:cg,name:'Clientes <b>literal</b>'}}]}]},
 '/admin/customer-groups':{revision:3,groups:[{id:cg,name:'Clientes <b>literal</b>',customers:[{id:customer,name:'Cliente literal 😀'}]}]},
 ['/admin/users/'+user+'/effective-permissions']:copy()};change(values);return apiFor(async path=>{const d=values[path.replace('/api/v1','')];return response(d,'"'+d?.revision+'"')})}
test('targets frescos reutilizados aceptan unknown; nombres persistidos por ID, misma revisión',async()=>{const v=await readEffectivePermissionView(targetsApi(),user);assert.deepEqual(v.snapshot,snapshot);assert.equal(v.targets.customers[0].name,'Cliente literal 😀');assert.equal(v.targets.userGroups[0].grants[0].capability,'legacy.synthetic')});
for(const [label,change] of [
 ['revision mismatch',v=>v['/admin/customers'].revision=4],
 ['target missing',v=>v['/admin/customers'].customers=[]],
 ['customer group missing',v=>v['/admin/customer-groups'].groups=[]],
 ['user group name mismatch',v=>v['/admin/user-groups'].groups[0].name='wrong'],
 ['user missing',v=>v['/admin/users'].users=[]],
 ['active mismatch',v=>v['/admin/users'].users=[{...snapshot.user,active:false}]],
 ['duplicate customers',v=>v['/admin/customers'].customers.push(v['/admin/customers'].customers[0])],
 ['zero target',v=>v['/admin/customers'].customers[0].id=zero],
])test('composición rechaza '+label,async()=>assert.rejects(readEffectivePermissionView(targetsApi(change),user),e=>['response_invalid','groups_changed'].includes(e.code)));
test('ETag de usuarios reutilizados también es obligatorio',async()=>{const valid=targetsApi(),api=apiFor(async(path,init)=>{const r=await valid.fetcher(path,init);if(path.endsWith('/admin/users'))r.headers.set('ETag','"4"');return r});await assert.rejects(readEffectivePermissionView(api,user),e=>e.code==='response_invalid')});
test('accounts rechaza duplicados y exige actor',async()=>{await assert.rejects(readEffectivePermissionAccounts(targetsApi(v=>v['/admin/users'].users.push(snapshot.user))),e=>e.code==='response_invalid');const api=targetsApi();await assert.rejects(readEffectivePermissionAccounts(api,user),e=>e.code==='actor_changed')});

test('sources legacy idénticas se preservan',async()=>{const d=copy();d.permissions.sources.push(d.permissions.sources[0]);assert.deepEqual(await readEffectivePermissions(readApi(d),user),d)});

test('grupos y clientes sin ETag válidos según contrato',async()=>{const valid=targetsApi(),api=apiFor(async(path,init)=>{const r=await valid.fetcher(path,init);if(!path.endsWith('/admin/users')&&!path.endsWith('/effective-permissions'))r.headers.delete('ETag');return r});assert.deepEqual((await readEffectivePermissionView(api,user)).snapshot,snapshot)});
