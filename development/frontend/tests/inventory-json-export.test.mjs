import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {prepareInventoryJsonExport,validateInventoryJsonExport,sendInventoryJsonExport,recoverInventoryJsonExport,downloadInventoryJsonExport,inventoryJsonExportAllowed} from '../src/inventory-json-export.ts';
import {inventoryJsonExportWords} from '../src/inventory-json-export-words.ts';
const id=n=>'10000000-0000-4000-8000-'+String(n).padStart(12,'0'),actor=id(1),customer=id(2);
function setup(){const api=new RackClickApi();api.actorId=actor;api.csrf='synthetic';return {api,operation:prepareInventoryJsonExport(api,actor,customer,7)}}
function inventory(){return {sites:[],buildings:[],rooms:[],racks:[{id:id(3),name:'Ω <img> original',roomId:null,location:'',sizeU:42,properties:{notes:'User supplied metadata'}}],devices:[{id:id(4),name:'Original',kind:'rackEquipment',rackId:id(3),roomId:null,sizeU:2,sortOrder:0,poeBudget:null,hardwareProfileKey:null,mountParentId:null,mountSlotKey:null,properties:{notes:'=plain JSON',hardwareIdentity:{manufacturer:'Synthetic'}}}],portGroups:[{id:id(5),deviceId:id(4),type:'rj45',name:'LAN',prefix:'',sortOrder:0}],ports:[{id:id(6),deviceId:id(4),groupId:id(5),type:'rj45',gn:1,sortOrder:0,label:'Ω <img>',status:'free',poe:false,watts:null,color:null,face:'front',powerRole:'unspecified',properties:{hardwareGroupKey:'front-lan',hardwarePortKey:'front-lan:1'}}],connections:[]}}
async function result(operation,change=()=>{}){
 const document={formatVersion:1,kind:'RackClickInventory',scope:'customer',customerId:customer,revision:7,inventory:inventory()};change(document);
 const bytes=new TextEncoder().encode(JSON.stringify(document)),rowCount=Object.values(document.inventory).filter(Array.isArray).reduce((n,v)=>n+v.length,0);
 return {kind:'inventoryExport',customerId:customer,revision:7,requestId:operation.requestId,operationId:id(8),archive:{format:'RackClickInventory-v1',scope:'customer',filename:`rackclick-inventory-${customer}-r7.json`,contentType:'application/json; charset=utf-8',encoding:'utf-8',rowCount,byteLength:bytes.length,sha256:Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex'),contentBase64:Buffer.from(bytes).toString('base64')}};
}

test('actual archive preserves inventory identities, user data, mounts and typed metadata without security collections',async()=>{
 const {operation}=setup();const data=await result(operation,d=>d.inventory.devices.push({id:id(9),name:'Shared child',kind:'rackEquipment',rackId:id(3),roomId:null,sizeU:0,sortOrder:1,poeBudget:null,hardwareProfileKey:'selected-nb-5bb0012c11525238',mountParentId:id(4),mountSlotKey:'shared',properties:{hardwareProfileVersion:'selected506l-20261101-v1'}}));
 const valid=await validateInventoryJsonExport(data,operation);assert.equal(valid.document.inventory.devices[1].mountParentId,id(4));assert.equal(valid.document.inventory.devices[1].mountSlotKey,'shared');assert.equal(valid.document.inventory.racks[0].name,'Ω <img> original');assert.equal(valid.document.inventory.ports[0].properties.hardwarePortKey,'front-lan:1');
 assert.deepEqual(Object.keys(valid.document).sort(),['formatVersion','kind','scope','customerId','revision','inventory'].sort());assert.equal(valid.bytes[0],123);
});
test('wrong receipt identities, digest, size, encoding, filename and metadata reject',async()=>{
 const {operation}=setup(),original=await result(operation);
 for(const mutate of [d=>d.customerId=id(99),d=>d.revision++,d=>d.requestId=id(99),d=>d.kind='report',d=>d.archive.scope='rack',d=>d.archive.byteLength++,d=>d.archive.rowCount++,d=>d.archive.sha256='0'.repeat(64),d=>d.archive.encoding='utf-8-bom',d=>d.archive.filename='../escape.json',d=>d.archive.contentBase64='bad!',d=>d.archive.extra=true]){
  const value=structuredClone(original);mutate(value);await assert.rejects(validateInventoryJsonExport(value,operation),e=>e.code==='response_invalid'&&e.uncertain);
 }
});
test('security/root extras, invalid references, duplicate identities and malformed collection rows reject even with valid hashes',async()=>{
 const {operation}=setup();for(const change of [d=>d.app_session=[],d=>d.inventory.app_user=[],d=>d.inventory.devices[0].rackId=id(99),d=>d.inventory.ports.push({...d.inventory.ports[0]}),d=>d.inventory.racks.push(null),d=>d.inventory.devices[0].password_hash='must not cross the boundary']){
  await assert.rejects(validateInventoryJsonExport(await result(operation,change),operation),e=>e.code==='response_invalid');
 }
});
test('lost response retries exact request and recovers only its committed receipt',async()=>{
 const {api,operation}=setup(),data=await result(operation),sent=[];api.request=async(path,init)=>{sent.push({path,init});if(sent.length===1)throw {uncertain:true};return {data:path.includes('/operations/')?{state:'committed',customerId:customer,requestId:operation.requestId,operation:data}:data}};
 await assert.rejects(sendInventoryJsonExport(api,operation));assert.deepEqual((await sendInventoryJsonExport(api,operation)).result,data);assert.equal(sent[0].init.body,sent[1].init.body);assert.equal(sent[0].init.headers['Idempotency-Key'],sent[1].init.headers['Idempotency-Key']);assert.equal(sent[1].init.headers['If-Match'],'"7"');assert.ok(Object.isFrozen(operation));
 assert.deepEqual((await recoverInventoryJsonExport(api,operation)).result,data);
 api.request=async()=>({data:{state:'notRecorded',customerId:customer,requestId:operation.requestId,operation:null}});assert.equal(await recoverInventoryJsonExport(api,operation),null);
 api.request=async()=>({data:{state:'committed',customerId:id(99),requestId:operation.requestId,operation:data}});await assert.rejects(recoverInventoryJsonExport(api,operation));
});
test('actor change or abort prevents returning data and downloads require both capabilities',async()=>{
 const {api,operation}=setup(),data=await result(operation);api.request=async()=>{api.actorId=id(99);return {data}};await assert.rejects(sendInventoryJsonExport(api,operation),e=>e.code==='actor_changed');api.actorId=actor;
 const session={user:{id:actor},permissions:{systemhausCapabilities:[],customers:[{customerId:customer,capabilities:['inventory.read']}]}};
 assert.equal(inventoryJsonExportAllowed(api,session,customer),false);let urls=0;const old=URL.createObjectURL;URL.createObjectURL=()=>{urls++;return 'blob:synthetic'};try{assert.throws(()=>downloadInventoryJsonExport({result:data,bytes:new Uint8Array(),document:{}},api,session,customer));assert.equal(urls,0)}finally{URL.createObjectURL=old}
 session.permissions.customers[0].capabilities.push('reports.export');assert.equal(inventoryJsonExportAllowed(api,session,customer),true);
 const controller=new AbortController();api.request=async()=>{controller.abort();return {data}};await assert.rejects(sendInventoryJsonExport(api,operation,controller.signal),e=>e.code==='actor_changed');
});
test('all three languages warn about inventory notes, and share the same action vocabulary',()=>{
 for(const lang of ['en','de','es']){assert.deepEqual(Object.keys(inventoryJsonExportWords[lang]).sort(),Object.keys(inventoryJsonExportWords.en).sort());assert.ok(inventoryJsonExportWords[lang].warning);assert.ok(inventoryJsonExportWords[lang].limits)}
});
