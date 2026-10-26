import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {generateArtifacts,buildCatalog,sourceSha256,catalogVersion} from '../../../tools/catalog/generate_rc9_catalog.mjs';
import {rc9CatalogVersion,rc9CatalogSha256,validCatalog,readInventoryCatalog,filterCatalog,catalogCreateCommand} from '../src/inventory-catalog.ts';
import {RackClickApi} from '../src/api.ts';
import {prepareCommand,executeCommand,cancelPendingCommand} from '../src/inventory-api.ts';
import {pendingRecord,validPendingRecord} from '../src/pending-journal.ts';
import {catalogWords} from '../src/inventory-catalog-words.ts';
const canonical=JSON.parse(await readFile(new URL('../../catalog/rc9-catalog.json',import.meta.url),'utf8'));
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),customerId=id(1),actor=id(2),revision=7;
const fixture=(language='es')=>({customerId,revision,language,catalogVersion:rc9CatalogVersion,catalogSha256:rc9CatalogSha256,...structuredClone(canonical.languages[language])});
const project={customerId,revision,racks:[{id:id(3)}],rooms:[{id:id(4)}]};
const form=(preset='pdu')=>({catalogue:fixture(),catalogueActor:actor,catalogKey:preset,catalogKind:'rackEquipment',name:'Nombre <img> Ω',color:'#123abc',rackId:id(3),roomId:id(4),poeBudget:'',sn:'SERIAL',model:'modelo literal',ip:'',firmware:'',notes:'Nota Ω\n東京',groups:[{type:'rj45',count:2,name:'manual',prefix:'M'}]});
const response=(body,status=200,headers={})=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json',...headers}});
const api=fetcher=>{const value=new RackClickApi(fetcher);value.actorId=actor;value.csrf='synthetic';return value};

test('generator reproduces exact JSON and escaped C# bytes, source pin and current adapter hash',async()=>{
 const generated=await generateArtifacts(),json=await readFile(new URL('../../catalog/rc9-catalog.json',import.meta.url),'utf8'),cs=await readFile(new URL('../../server/src/RackClick.Server/InventoryRc9CatalogData.g.cs',import.meta.url),'utf8');
 assert.equal(generated.json,json);assert.equal(generated.cs,cs);assert.equal(createHash('sha256').update(json).digest('hex'),rc9CatalogSha256);assert.equal(JSON.parse(cs.match(/internal const string Json = (.*);/)[1]),json);assert.ok(json.endsWith('\n'));assert.equal(catalogVersion,rc9CatalogVersion);assert.equal(canonical.source.sha256,sourceSha256);assert.throws(()=>buildCatalog('changed source'),/integrity/);
});
test('effective RC9 catalogue is 33/7 in all languages, with literal added presets and no inferred power',()=>{
 for(const language of ['en','de','es']){const c=fixture(language);assert.equal(validCatalog(c,customerId,revision,language),true);assert.equal(c.presets.length,33);assert.equal(c.categories.length,7);assert.equal(c.presets.find(p=>p.key==='ap').sizeU,1);for(const key of ['sw8','sw16','sw8p','rtr8','fw4','nas1u','srv1u4','ap'])assert.equal(c.presets.find(p=>p.key===key).portGroups.some(g=>g.type==='power'),false);for(const p of c.presets)for(const g of p.portGroups)for(const port of g.ports){assert.equal(port.status,'free');assert.equal(port.watts,null);assert.deepEqual(port.properties,{});assert.equal('id' in port,false)}}
});
test('PDU/UPS roles and labels match RC9; groups and individual gn remain explicit',()=>{
 for(const [language,inlet,outlet] of [['en','Inlet','Outlet'],['de','Eingang','Ausgang'],['es','Entrada','Salida']])for(const [key,count] of [['pdu',9],['ups',5]]){const p=fixture(language).presets.find(p=>p.key===key),g=p.portGroups[0];assert.equal(g.ports.length,count);assert.deepEqual(g.ports.map(p=>p.gn),Array.from({length:count},(_,i)=>i+1));assert.equal(g.ports[0].label,inlet);assert.equal(g.ports[0].powerRole,'inlet');assert.equal(g.ports.at(-1).label,outlet+' '+(count-1));assert.equal(g.ports.at(-1).powerRole,'outlet');assert.ok(g.ports.every(p=>p.face==='rear'&&p.poe===false))}
 const sw=fixture().presets.find(p=>p.key==='sw24p');assert.equal(sw.portGroups[0].type,'rj45');assert.equal(sw.portGroups[0].ports[0].type,'rj45_poe');assert.equal(sw.portGroups[0].ports[0].poe,true);assert.equal(sw.portGroups[1].ports[0].gn,1);
});
test('closed catalogue rejects wrong owner/revision/language/hash, unknown fields, identities and live attributes',()=>{
 for(const mutate of [c=>c.customerId=id(9),c=>c.revision++,c=>c.language='de',c=>c.catalogSha256='0'.repeat(64),c=>c.catalogVersion='other',c=>c.extra=true,c=>c.categories[0].presetKeys.push('pdu'),c=>c.presets[0].id=id(9),c=>c.presets[0].portGroups[0].ports[0].watts=17,c=>c.presets[0].portGroups[0].ports[0].status='reserved',c=>c.presets[0].portGroups[0].ports[0].powerRole='inlet',c=>c.presets[0].portGroups[0].ports[0].properties.secret='bad']){const c=fixture();mutate(c);assert.equal(validCatalog(c,customerId,revision,'es'),false)}
});
test('catalogue GET sends If-Match and binds response to actor, customer, revision and language',async()=>{
 let call;const a=api(async(url,init)=>{call={url,init};return response(fixture(),200,{ETag:'"7"'})});const data=await readInventoryCatalog(a,customerId,revision,'es');assert.equal(data.presets.length,33);assert.equal(call.url,'/api/v1/customers/'+customerId+'/catalog?language=es');assert.equal(call.init.headers['If-Match'],'"7"');
 const wrong=api(async()=>response(fixture(),200,{ETag:'"8"'}));await assert.rejects(readInventoryCatalog(wrong,customerId,revision,'es'),e=>e.code==='response_invalid');
 const changed=api(async()=>{changed.actorId=id(9);return response(fixture(),200,{ETag:'"7"'})});await assert.rejects(readInventoryCatalog(changed,customerId,revision,'es'),e=>e.code==='actor_changed');
 await assert.rejects(readInventoryCatalog(a,customerId,revision,'fr'),e=>e.status===422);
});
test('category/search use server labels and connector metadata without modifying the selection',()=>{const c=fixture();assert.equal(filterCatalog(c,'Power','').length,2);assert.equal(filterCatalog(c,'','Alimentación').length,2);assert.equal(filterCatalog(c,'Switches','poe').length,3);assert.equal(filterCatalog(c,'','not a preset').length,0)});
test('initial GET412 is recoverable with a fresh project revision while the draft stays intact',async()=>{
 const requests=[],draft=form(),before=JSON.stringify(draft),a=api(async(_url,init)=>{const match=init.headers['If-Match'];requests.push(match);if(match==='"7"')return response({error:'revision_conflict'},412);return response({...fixture(),revision:8},200,{ETag:'"8"'})});
 await assert.rejects(readInventoryCatalog(a,customerId,7,'es'),e=>e.status===412);assert.equal(JSON.stringify(draft),before);
 const refreshed=await readInventoryCatalog(a,customerId,8,'es');assert.equal(JSON.stringify(draft),before);assert.deepEqual(requests,['"7"','"8"']);const ready={...draft,catalogue:refreshed};assert.equal(catalogCreateCommand(a,actor,{...project,revision:8},'es',ready).payload.name,draft.name);assert.deepEqual(ready.groups,draft.groups);
});
test('catalogue creation has exactly 11 keys, canonical reference and no copied layout/UUID; manual draft is untouched',()=>{
 const a=api(),f=form(),before=JSON.stringify(f),command=catalogCreateCommand(a,actor,project,'es',f);assert.equal(command.type,'device.createFromCatalog');assert.equal(Object.keys(command.payload).sort().join(),'catalogSha256,catalogVersion,color,kind,language,name,notes,poeBudget,presetKey,rackId,roomId');assert.equal(command.payload.roomId,null);assert.equal(command.payload.name,f.name);assert.equal(command.payload.color,'#123abc');assert.equal(command.payload.notes.text,f.notes);assert.equal(JSON.stringify(f),before);
 const ap=form('ap');ap.name='';const payload=catalogCreateCommand(a,actor,project,'es',ap).payload;assert.equal(payload.kind,'endDevice');assert.equal(payload.rackId,null);assert.equal(payload.roomId,id(4));assert.equal(payload.name,'Access Point (AP)');assert.equal('sizeU' in payload,false);
 f.catalogKind='dose';const dose=catalogCreateCommand(a,actor,project,'es',f).payload;assert.equal(dose.rackId,null);assert.equal(dose.roomId,id(4));
});
test('stale or foreign catalogue, bad placement and invalid colour are rejected before preparing a write',()=>{
 const a=api();for(const mutate of [f=>f.catalogue.revision++,f=>f.catalogueActor=id(9),f=>f.catalogKey='missing',f=>f.rackId=id(9),f=>f.color='red',f=>f.poeBudget='NaN']){const f=form();mutate(f);assert.throws(()=>catalogCreateCommand(a,actor,project,'es',f))}a.actorId=id(9);assert.throws(()=>catalogCreateCommand(a,actor,project,'es',form()),e=>e.status===412);
});
test('existing journal recovers exact catalogue command after lost response; malformed receipts remain uncertain',async()=>{
 let operation,calls=0;const a=api(async()=>{if(++calls===1)throw Error('response lost');return response({customerId,revision:8,requestId:operation.requestId,operationId:id(8),result:{resourceId:id(9),createdIds:[id(9),id(10)]}})});
 const command=catalogCreateCommand(a,actor,project,'es',form());operation=prepareCommand(a,customerId,command.type,command.payload,revision,actor);const journal=pendingRecord(operation,'addDevice','synthetic');assert.equal(validPendingRecord(journal,actor),true);await assert.rejects(executeCommand(a,operation),e=>e.uncertain===true);await executeCommand(a,operation);assert.equal(journal.operation.body,operation.body);
 for(const mutate of [r=>r.extra=true,r=>r.revision=9,r=>r.result.createdIds=[id(9),id(9)],r=>r.result.createdIds[0]=id(10),r=>r.result.extra=true]){const receipt={customerId,revision:8,requestId:operation.requestId,operationId:id(8),result:{resourceId:id(9),createdIds:[id(9)]}};mutate(receipt);const bad=api(async()=>response(receipt));await assert.rejects(executeCommand(bad,operation),e=>e.code==='response_invalid'&&e.uncertain===true);const cancel=api(async()=>response({state:'committed',customerId,requestId:operation.requestId,operation:receipt}));await assert.rejects(cancelPendingCommand(cancel,operation),e=>e.code==='response_invalid'&&e.uncertain===true)}
});
test('catalogue UI has the same translated controls in EN/DE/ES',()=>{for(const lang of ['de','es'])assert.deepEqual(Object.keys(catalogWords[lang]).sort(),Object.keys(catalogWords.en).sort())});
