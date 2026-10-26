import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { allows } from '../src/api.ts';
import { inventoryWriteCapability } from '../src/inventory-operation-permission.ts';

const READ='inventory.read',EDIT='inventory.edit',DELETE='inventory.delete';
const customerId='99000000-0000-4000-8000-000000000021';
const otherCustomerId='99000000-0000-4000-8000-000000000022';
const deleteTypes=['site.delete','building.delete','room.delete','rack.delete','device.delete','devices.delete'];
const original=type=>Object.freeze({label:'untrusted presentation label',operation:Object.freeze({body:JSON.stringify({type,payload:{id:'synthetic'}})})});

test('ordinary or destructive drafts require edit unless deletion is explicitly declared',()=>{
 for(const draft of [{label:'edit'},{label:'remove'},{label:'removeSelected',destructive:true},{label:'undoGroups',destructive:true}])assert.equal(inventoryWriteCapability(draft,null),EDIT);
 assert.equal(inventoryWriteCapability({label:'remove',requiredCapability:DELETE},null),DELETE);
 assert.equal(inventoryWriteCapability({label:'edit',requiredCapability:EDIT},null),EDIT);
});

test('recovery classifies six closed delete types from immutable original JSON, overriding the draft hint',()=>{
 for(const type of deleteTypes){const recovery=original(type),before=JSON.stringify(recovery);assert.equal(inventoryWriteCapability({requiredCapability:EDIT},recovery),DELETE,type);assert.equal(JSON.stringify(recovery),before,type)}
 for(const type of ['site.update','rack.duplicate','device.createFromCatalog','device.editPortGroups','ports.update','operations.compensate']){
  const recovery=original(type),before=JSON.stringify(recovery);assert.equal(inventoryWriteCapability({requiredCapability:DELETE},recovery),EDIT,type);assert.equal(JSON.stringify(recovery),before,type);
 }
});

test('malformed recovery or an unknown delete type cannot inherit a permissive draft capability',()=>{
 const malformed=[{}, {operation:{}}, {operation:{body:'not JSON'}}, {operation:{body:'null'}}, {operation:{body:'[]'}}, {operation:{body:'{}'}}, {operation:{body:'{"type":42}'}},original('unknown.delete'),original('__proto__.delete')];
 for(const recovery of malformed)assert.equal(inventoryWriteCapability({requiredCapability:EDIT},recovery),null,JSON.stringify(recovery));
});

async function opening(capabilities,options={}){
 const source=await readFile(process.env.RACKCLICK_DELETE_PANEL_SOURCE||new URL('../src/InventoryPanel.jsx',import.meta.url),'utf8');
 const take=(from,to)=>{const a=source.indexOf(from),b=source.indexOf(to,a);assert.ok(a>=0&&b>a,from);return source.slice(a,b)};
 const events=[],session={user:{id:'synthetic'},permissions:{systemhausCapabilities:[],customers:[{customerId:options.scope||customerId,capabilities}]}};
 const env={inventoryWriteCapability,allows,session,customer:{id:customerId},blocked:!!options.blocked,
  canEdit:allows(session,EDIT,customerId),canDelete:allows(session,DELETE,customerId),named:{key:'name'},
  setError:error=>events.push({kind:'error',error}),setUndoCandidate(){},setUndoStale(){},setDraft:draft=>events.push({kind:'draft',draft})};
 const body=take('function open(value)','function hierarchy(')+take('function removeEntity(','function removeSelectedDevices(');
 const methods=new Function('env','const {'+Object.keys(env).join(',')+'}=env;\n'+body+'\nreturn {open,removeEntity};')(env);
 return {...methods,events,source};
}

test('actual open permits delete-only drafts and denies edit-only deletion while retaining scope and blocked guards',async()=>{
 const deletion={label:'remove',requiredCapability:DELETE};
 for(const [capabilities,draft,permitted,options] of [
  [[READ,DELETE],deletion,true,{}],[[READ,EDIT],deletion,false,{}],
  [[READ,EDIT],{label:'edit'},true,{}],[[READ,DELETE],{label:'edit'},false,{}],
  [[READ,DELETE],deletion,false,{scope:otherCustomerId}],[[READ,DELETE],deletion,false,{blocked:true}]
 ]){
  const h=await opening(capabilities,options);h.open(draft);
  assert.equal(h.events.some(event=>event.kind==='draft'),permitted,JSON.stringify({capabilities,draft,options}));
  if(!permitted)assert.equal(h.events.find(event=>event.kind==='error')?.error.status,403);
 }
});

test('real individual delete drafts explicitly declare delete and keep their exact entity command',async()=>{
 for(const entity of ['site','building','room','rack','device']){
  const h=await opening([READ,DELETE]);h.removeEntity(entity,{id:'synthetic-id',name:'Synthetic fixture'});
  const draft=h.events.find(event=>event.kind==='draft')?.draft;
  assert.ok(draft,entity);assert.equal(draft.requiredCapability,DELETE,entity);
  assert.deepEqual(draft.build(),{type:entity+'.delete',payload:{id:'synthetic-id'}},entity);
  assert.equal(draft.destructive,['rack','device'].includes(entity),entity);
 }
});
