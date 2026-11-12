import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi } from '../src/api.ts';
// The first run deliberately asserts the absent adapter, before implementation.
let module;
try { module = await import('../src/admin-inventory-data.ts'); } catch (e) { if (e.code !== 'ERR_MODULE_NOT_FOUND') throw e; }
const subject = () => { assert.ok(module, 'Inventory administration adapter has not been implemented'); return module; };
const actor='12345678-1234-1234-1234-123456789abc',house='22345678-1234-1234-1234-123456789abc',requestId='32345678-1234-1234-1234-123456789abc',operationId='42345678-1234-1234-1234-123456789abc';
const context={actorId:actor,houseId:house,origin:'http://127.0.0.1:49500'};
const counts={customers:0,sites:0,buildings:0,rooms:0,racks:0,devices:0,portGroups:0,ports:0,connections:0};
const populated={...counts,customers:1,sites:1};
const caps=['systemhaus.manage','security.manage','inventory.read','reports.export','customer.create','inventory.edit'];
const session=(capabilities=caps)=>({user:{id:actor,houseId:house,userName:'Literal <名>'},permissions:{systemhausCapabilities:capabilities,customers:[]}});
const intent=(action='demo50',extra={})=>({...context,requestId,action,revision:7,...extra});
const receipt=(action='demo50',extra={})=>({kind:'inventoryData',action,requestId,operationId,systemhausRevision:action==='backup'?7:8,counts:populated,archive:null,...extra});
const json=data=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}});
const apiFor=fn=>{const api=new RackClickApi(fn);api.actorId=actor;api.csrf='synthetic';return api;};
const file=()=>new Blob(['{"name":"Literal <名> Ä"}'],{type:'application/json'});

test('only both global management grants show data; scoped grants never substitute',()=>{
 const {inventoryDataAllowed}=subject();assert.equal(inventoryDataAllowed(session()),true);
 for(const grants of [[],['security.manage'],['systemhaus.manage']])assert.equal(inventoryDataAllowed(session(grants)),false);
 const scoped=session([]);scoped.permissions.customers=[{customerId:house,capabilities:caps}];assert.equal(inventoryDataAllowed(scoped),false);
 assert.equal(inventoryDataAllowed(null),false);
});
test('export and import need their own global capabilities before intent creation',()=>{
 const {prepareInventoryDataIntent}=subject();
 for(const cap of caps){const s=session(caps.filter(x=>x!==cap));const action=['inventory.read','reports.export'].includes(cap)?'backup':'demo50';assert.throws(()=>prepareInventoryDataIntent(s,action,7,null,context.origin),e=>e.code==='inventory_data_forbidden');}
 const d=prepareInventoryDataIntent(session(),'demo50',7,null,context.origin);assert.equal(d.actorId,actor);assert.equal(d.houseId,house);assert.equal(d.origin,context.origin);assert.equal(d.revision,7);assert.equal(d.action,'demo50');assert.match(d.requestId,/^[0-9a-f-]{36}$/);
});
test('status validates counts, empty and bounded archive size before use',async()=>{
 const {readInventoryData}=subject();const value={systemhausRevision:7,empty:true,counts,demo:{available:true,counts:populated},maxArchiveBytes:33554432};
 assert.deepEqual(await readInventoryData(apiFor(async()=>json(value)),context),value);
 for(const bad of [{...value,empty:'true'},{...value,empty:true,counts:populated},{...value,maxArchiveBytes:33554433},{...value,counts:{...counts,ports:-1}},{...value,counts:{...counts,password:0}}])await assert.rejects(readInventoryData(apiFor(async()=>json(bad)),context),e=>e.code==='response_invalid');
});
test('oversized input is rejected before arrayBuffer allocation; UTF8 bytes are hashed unchanged',async()=>{
 const {readInventoryDataFile}=subject();let read=false;
 await assert.rejects(readInventoryDataFile({size:33554433,arrayBuffer:async()=>{read=true;return new ArrayBuffer(0);}},33554432),e=>e.code==='inventory_archive_size');assert.equal(read,false);
 const loaded=await readInventoryDataFile(file(),33554432);const bytes=new Uint8Array(await file().arrayBuffer());
 assert.equal(loaded.byteLength,bytes.length);assert.equal(loaded.contentBase64,Buffer.from(bytes).toString('base64'));
 assert.equal(loaded.archiveSha256,Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex'));
});
test('preview must echo exact file hash/length and supported format before restore',async()=>{
 const {readInventoryDataFile,previewInventoryData}=subject();const input=await readInventoryDataFile(file(),33554432);
 const preview={archiveSha256:input.archiveSha256,byteLength:input.byteLength,counts:populated,format:'RackClickInventoryBackup-v1',schemaVersion:48};const calls=[];
 assert.deepEqual(await previewInventoryData(apiFor(async(url,init)=>{calls.push({url,init});return json(preview);}),context,input),preview);
 assert.equal(calls[0].url,'/api/v1/admin/inventory-data/preview');assert.deepEqual(JSON.parse(calls[0].init.body),{contentBase64:input.contentBase64});assert.equal(calls[0].init.headers['X-RackClick-CSRF'],'synthetic');
 for(const bad of [{...preview,archiveSha256:'0'.repeat(64)},{...preview,byteLength:1},{...preview,schemaVersion:49},{...preview,format:'pg_dump'}])await assert.rejects(previewInventoryData(apiFor(async()=>json(bad)),context,input),e=>e.code==='response_invalid');
});
test('demo sends exact confirmation, actor, revision and original request key',async()=>{
 const {sendInventoryData}=subject();let call;
 assert.deepEqual(await sendInventoryData(apiFor(async(url,init)=>{call={url,init};return json(receipt());}),intent(),context),receipt());
 assert.equal(call.url,'/api/v1/admin/inventory-data/demo50');assert.deepEqual(JSON.parse(call.init.body),{confirmation:'LOAD DEMO50'});
 assert.equal(call.init.headers['X-RackClick-Actor'],actor);assert.equal(call.init.headers['If-Match'],'"7"');assert.equal(call.init.headers['Idempotency-Key'],requestId);
});
test('restore binds content digest and byte length and never accepts complete material in journal intent',async()=>{
 const {readInventoryDataFile,sendInventoryData,validInventoryDataIntent}=subject();const input=await readInventoryDataFile(file(),33554432);const d=intent('restore',{archiveSha256:input.archiveSha256,byteLength:input.byteLength});let sent=0;
 assert.equal(validInventoryDataIntent(d),true);assert.equal(validInventoryDataIntent({...d,contentBase64:input.contentBase64}),false);
 await sendInventoryData(apiFor(async(url,init)=>{sent++;assert.deepEqual(JSON.parse(init.body),{contentBase64:input.contentBase64,archiveSha256:input.archiveSha256,confirmation:'RESTORE INVENTORY'});return json(receipt('restore'));}),d,context,input);
 await assert.rejects(sendInventoryData(apiFor(async()=>{sent++;return json(receipt('restore'));}),d,context,{...input,contentBase64:'e30='}),e=>e.code==='inventory_archive_changed');assert.equal(sent,1);
});
test('malformed receipts never confirm commit and remain uncertain',async()=>{
 const {sendInventoryData}=subject();
 for(const bad of [{...receipt(),requestId:house},{...receipt(),action:'restore'},{...receipt(),kind:'user'},{...receipt(),systemhausRevision:9},{...receipt(),operationId:'bad'},{...receipt(),counts:{...counts,ports:0.5}},{...receipt(),archive:{contentBase64:'e30='}}])await assert.rejects(sendInventoryData(apiFor(async()=>json(bad)),intent(),context),e=>e.code==='response_invalid'&&e.uncertain);
});
test('backup requires exact operation filename, byte length and SHA256 before download',async()=>{
 const {readInventoryDataFile,sendInventoryData,verifyInventoryDataArchive}=subject();const input=await readInventoryDataFile(file(),33554432);
 const archive={format:'RackClickInventoryBackup-v1',filename:`rackclick-inventory-backup-${operationId}.json`,contentType:'application/json; charset=utf-8',encoding:'utf-8',byteLength:input.byteLength,sha256:input.archiveSha256,contentBase64:input.contentBase64};
 const saved=receipt('backup',{archive});assert.deepEqual(await sendInventoryData(apiFor(async()=>json(saved)),intent('backup'),context),saved);
 const download=await verifyInventoryDataArchive(archive,operationId);assert.equal(await download.blob.text(),await file().text());assert.equal(download.filename,archive.filename);
 for(const bad of [{...archive,filename:'../copy.json'},{...archive,sha256:'0'.repeat(64)},{...archive,byteLength:1},{...archive,contentBase64:'%%%%'},{...archive,byteLength:33554433}])await assert.rejects(verifyInventoryDataArchive(bad,operationId),e=>['response_invalid','inventory_archive_integrity'].includes(e.code));
});
test('notRecorded and HTTP403 never establish rollback or cancellation',async()=>{
 const {inventoryDataStatus}=subject();assert.equal(await inventoryDataStatus(apiFor(async()=>json({state:'notRecorded',requestId,operation:null})),intent(),context),null);
 for(const value of [{state:'cancelled',requestId,operation:receipt()},{state:'notRecorded',requestId,operation:receipt()},{state:'committed',requestId:house,operation:receipt()}])await assert.rejects(inventoryDataStatus(apiFor(async()=>json(value)),intent(),context),e=>e.code==='response_invalid');
 await assert.rejects(inventoryDataStatus(apiFor(async()=>new Response('{"error":"forbidden"}',{status:403})),intent(),context),e=>e.status===403);
 assert.deepEqual(await inventoryDataStatus(apiFor(async()=>json({state:'committed',requestId,operation:receipt()})),intent(),context),receipt());
});
test('lost mutation response is sent once; explicit status query recovers same receipt',async()=>{
 const {sendInventoryData,inventoryDataStatus}=subject();let post=0,get=0;
 const api=apiFor(async(url,init)=>{if(init.method==='POST'){post++;throw Error('reply lost after commit');}get++;return json({state:'committed',requestId,operation:receipt()});});
 await assert.rejects(sendInventoryData(api,intent(),context),e=>e.uncertain);assert.equal(post,1);assert.deepEqual(await inventoryDataStatus(api,intent(),context),receipt());assert.equal(post,1);assert.equal(get,1);
});
test('actor, house and origin mismatch fail before sending; actor change after reply cannot confirm',async()=>{
 const {sendInventoryData}=subject();let sent=0;const api=apiFor(async()=>{sent++;api.actorId=house;return json(receipt());});
 for(const change of [{actorId:house},{houseId:actor},{origin:'http://127.0.0.1:49501'}])await assert.rejects(sendInventoryData(api,intent(),{...context,...change}),e=>e.code==='actor_changed');
 assert.equal(sent,0);await assert.rejects(sendInventoryData(api,intent(),context),e=>e.code==='actor_changed'&&e.uncertain);assert.equal(sent,1);
});
test('durable intention must succeed before any POST and retains pending after uncertain result',async()=>{
 const {executeInventoryDataIntent}=subject();const events=[];
 await assert.rejects(executeInventoryDataIntent(apiFor(async()=>{events.push('POST');return json(receipt());}),intent(),context,null,{write:async()=>{events.push('journal');throw Error('storage failed');},pending:()=>events.push('pending')}),/storage failed/);assert.deepEqual(events,['journal']);
 events.length=0;
 await assert.rejects(executeInventoryDataIntent(apiFor(async()=>{events.push('POST');throw Error('lost');}),intent(),context,null,{write:async()=>events.push('journal'),pending:()=>events.push('pending')}),e=>e.uncertain);assert.deepEqual(events,['journal','pending','POST']);
});
test('committed receipt survives cleanup failure and notRecorded never removes intention',async()=>{
 const {completeInventoryDataIntent}=subject();const events=[],steps={current:()=>true,remember:()=>events.push('receipt'),remove:async()=>{events.push('remove');throw Error('storage failed')},clear:()=>events.push('clear'),reload:()=>events.push('reload')};
 await completeInventoryDataIntent(null,intent(),steps);assert.deepEqual(events,[]);
 await assert.rejects(completeInventoryDataIntent(receipt(),intent(),steps),/storage failed/);assert.deepEqual(events,['receipt','remove']);
});
test('explicit cancel binds original action/digest and headers; a committed result recovers the original instead',async()=>{
 const {cancelInventoryData}=subject();assert.equal(typeof cancelInventoryData,'function','Explicit server cancellation is missing');
 const calls=[],api=apiFor(async(url,init)=>{calls.push({url,init});return json({state:'cancelled',requestId,operation:null});});
 assert.deepEqual(await cancelInventoryData(api,intent(),context),{state:'cancelled',requestId,operation:null});
 assert.equal(calls[0].url,'/api/v1/admin/inventory-data/operations/'+requestId+'/cancel');assert.deepEqual(JSON.parse(calls[0].init.body),{action:'demo50',archiveSha256:null});assert.equal(calls[0].init.headers['If-Match'],'"7"');assert.equal(calls[0].init.headers['Idempotency-Key'],requestId);
 const restore=intent('restore',{archiveSha256:'a'.repeat(64),byteLength:100});
 await cancelInventoryData(apiFor(async(url,init)=>{assert.deepEqual(JSON.parse(init.body),{action:'restore',archiveSha256:'a'.repeat(64)});return json({state:'cancelled',requestId,operation:null});}),restore,context);
 assert.deepEqual(await cancelInventoryData(apiFor(async()=>json({state:'committed',requestId,operation:receipt()})),intent(),context),receipt());
 for(const bad of [{state:'notRecorded',requestId,operation:null},{state:'cancelled',requestId:house,operation:null},{state:'cancelled',requestId,operation:receipt()},{state:'committed',requestId,operation:receipt('restore')}])await assert.rejects(cancelInventoryData(apiFor(async()=>json(bad)),intent(),context),e=>e.code==='response_invalid'&&e.uncertain);
});
test('only confirmed cancellation permits cleanup; lost cancel and notRecorded preserve the intention',async()=>{
 const {cancelInventoryData,completeInventoryDataIntent,inventoryDataStatus}=subject();assert.equal(typeof cancelInventoryData,'function','Explicit server cancellation is missing');
 await assert.rejects(cancelInventoryData(apiFor(async()=>{throw Error('lost cancellation');}),intent(),context),e=>e.uncertain);
 const cancelled={state:'cancelled',requestId,operation:null};assert.deepEqual(await inventoryDataStatus(apiFor(async()=>json(cancelled)),intent(),context),cancelled);
 const events=[],steps={current:()=>true,remember:value=>events.push(value===null?'cancelled':'commit'),remove:async()=>events.push('remove'),clear:()=>events.push('clear'),reload:()=>events.push('reload')};
 await completeInventoryDataIntent(null,intent(),steps);assert.deepEqual(events,[]);await completeInventoryDataIntent(cancelled,intent(),steps);assert.deepEqual(events,['cancelled','remove','clear','reload']);
 await assert.rejects(completeInventoryDataIntent({...cancelled,requestId:house},intent(),steps),e=>e.code==='response_invalid');
 await assert.rejects(completeInventoryDataIntent(cancelled,intent(),{...steps,knownResult:receipt()}),e=>e.code==='response_invalid');
});
