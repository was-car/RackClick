import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {RackClickApi} from '../src/api.ts';
import {ChangeInbox,readClientChanges,changeActions} from '../src/client-changes.ts';
import {readClientChangeDetails} from '../src/client-change-details.ts';
import {changeDetailWords,changeEntityRows,changeEntitySummary} from '../src/client-change-detail-words.ts';

const id=n=>n.toString(16).padStart(8,'0')+'-abcd-4bcd-8bcd-123456789abc';
const actor=id(1),other=id(2),customer=id(3),site=id(10),building=id(11),room=id(12),rack=id(13),device=id(14),group=id(15);
function entity(kind,key,extra={}){
 const value={relation:'target',kind,id:key,name:'Original Ω 日本語 <img> & 😀',parentKind:null,parentId:null,deviceKind:null,rackId:null,roomId:null,sizeU:null,positionU:null,sortOrder:null,groupType:null,prefix:null,portCount:null};
 if(kind==='site')Object.assign(value,{parentKind:'customer',parentId:customer});
 if(kind==='building')Object.assign(value,{parentKind:'site',parentId:site});
 if(kind==='room')Object.assign(value,{parentKind:'building',parentId:building});
 if(kind==='rack')Object.assign(value,{parentKind:'room',parentId:room,roomId:room,sizeU:42});
 if(kind==='device')Object.assign(value,{parentKind:'rack',parentId:rack,rackId:rack,deviceKind:'rackEquipment',sizeU:1,sortOrder:0});
 if(kind==='portGroup')Object.assign(value,{parentKind:'device',parentId:device,sortOrder:0,groupType:'rj45',prefix:'A😀',portCount:24});
 return Object.assign(value,extra);
}
const captured=(beforeEntities=[],afterEntities=[])=>({status:'captured',beforeEntities,afterEntities});
const unavailable=()=>({status:'notAvailable',beforeEntities:[],afterEntities:[]});
const refs=()=>({status:'notAvailable',beforePorts:[],afterPorts:[],beforeConnections:[],afterConnections:[]});
function page(action='inventory.device.update',details=captured([entity('device',device),entity('portGroup',group)],[entity('device',device,{name:'Después'}) ,entity('portGroup',group)]),resource=device){
 return {customerId:customer,currentRevision:5,nextRevision:5,hasMore:false,refreshRequired:false,events:[{id:id(20),actor:{id:other,userNameCurrent:'Autor actual'},action,resourceId:resource,revisionBefore:4,revisionAfter:5,occurredAt:'2026-10-18T01:23:45.123456Z',context:refs(),details}]};
}
function api(value,expectedPath='/changes/details?afterRevision=4&limit=50',etag='"5"'){
 const a=new RackClickApi(async(url,init)=>{
  assert.equal(url,'/api/v1/customers/'+customer+expectedPath);assert.equal(init.body,undefined);assert.equal(init.method,undefined);assert.equal(init.cache,'no-store');assert.equal(init.credentials,'same-origin');
  return new Response(JSON.stringify(value),{headers:{ETag:etag}});
 });a.actorId=actor;return a;
}
const read=p=>readClientChangeDetails(api(p),customer,4,actor);
const reject=p=>assert.rejects(()=>read(p),{code:'response_invalid'});
const kinds={site,building,room,rack};

test('opt-in reader shares the unchanged closed v1 validator, no write or inventory refresh',async()=>{
 const p=page();assert.deepEqual(await read(p),p);
 const v1=structuredClone(p);delete v1.events[0].details;
 assert.deepEqual(await readClientChanges(api(v1,'/changes?afterRevision=4&limit=50'),customer,4,actor),v1);
 await assert.rejects(()=>readClientChanges(api(p,'/changes?afterRevision=4&limit=50'),customer,4,actor),{code:'response_invalid'});
 await reject(v1);
});
test('all 24 descriptive action shapes respect persisted before/after identity and parent/group ownership',async()=>{
 const actions=new Set();
 for(const kind of ['site','building','room'])for(const action of ['create','update','delete']){
  const e=entity(kind,kinds[kind]),details=captured(action==='create'?[]:[e],action==='delete'?[]:[{...e,name:'Actualizado'}]),name='inventory.'+kind+'.'+action;
  assert.deepEqual(await read(page(name,details,e.id)),page(name,details,e.id));actions.add(name);
 }
 for(const action of ['create','update','assignRoom','delete','duplicate']){
  const beforeRack=entity('rack',rack),afterRack=entity('rack',action==='duplicate'?id(30):rack,{name:'Rack siguiente'}),d=entity('device',device),g=entity('portGroup',group);
  let before=action==='create'?[]:[beforeRack],after=action==='delete'?[]:[afterRack];
  if(action==='delete')before.push(d,g);
  if(action==='duplicate'){
   before=[beforeRack,d,g].map(e=>({...e,relation:'source'}));
   after.push({...d,id:id(31),parentId:id(30),rackId:id(30)},{...g,id:id(32),parentId:id(31)});
  }
  const name='inventory.rack.'+action;await read(page(name,captured(before,after),afterRack.id));actions.add(name);
 }
 for(const action of ['create','createFromCatalog','createFromPrivateTemplate','createFromSharedTemplate','update','move','delete','reorder','editPortGroups']){
  let before=[entity('device',device),entity('portGroup',group)],after=structuredClone(before),resource=device;
  if(action.startsWith('create'))before=[];
  if(action==='delete')after=[];
  if(action==='move')Object.assign(after[0],{parentId:id(40),rackId:id(40),sortOrder:2});
  if(action==='reorder'){resource=rack;before=[entity('rack',rack,{relation:'scope'}),entity('device',device)];after=[structuredClone(before[0]),{...before[1],sortOrder:3}];}
  if(action==='editPortGroups'){before[0].relation=after[0].relation='scope';after[1]={...after[1],name:'Grupo renombrado',prefix:'B',groupType:'sfp',portCount:96};}
  const name='inventory.device.'+action;await read(page(name,captured(before,after),resource));actions.add(name);
 }
 const batch=page('inventory.devices.delete',captured([entity('device',device),entity('portGroup',group)],[]),id(20));await read(batch);actions.add(batch.events[0].action);
 assert.equal(actions.size,24);assert.equal([...changeActions].filter(a=>!actions.has(a)).length,7);
});
test('Dose and end device record a room, never invent rack placement, U positions or physical circuits',async()=>{
 for(const deviceKind of ['dose','endDevice']){
  const dose=entity('device',device,{parentKind:'room',parentId:room,rackId:null,roomId:room,deviceKind,sizeU:null});
  await read(page('inventory.device.create',captured([],[dose,entity('portGroup',group)])));
  await read(page('inventory.device.move',captured([dose],[{...dose,parentId:id(40),roomId:id(40)}])));
 }
 await read(page('inventory.rack.create',captured([],[entity('rack',rack,{parentKind:null,parentId:null,roomId:null})]),rack));
});
test('empty reorder scope and removing all groups remain complete captured descriptions',async()=>{
 const scope=entity('rack',rack,{relation:'scope'});await read(page('inventory.device.reorder',captured([scope],[scope]),rack));
 const d=entity('device',device,{relation:'scope'});await read(page('inventory.device.editPortGroups',captured([d,entity('portGroup',group)],[d])));
});
test('all 30 actions may honestly return no description; original seven contexts retain their validator',async()=>{
 for(const action of changeActions){const resource=action==='inventory.devices.delete'?id(20):device;await read(page(action,unavailable(),resource));}
 const p=page('inventory.ports.update',unavailable()),port={id:id(70),deviceId:device,groupId:group,type:'rj45',gn:1};
 p.events[0].context={...refs(),status:'captured',beforePorts:[port],afterPorts:[{...port,type:'rj45_poe'}]};await read(p);
 p.events[0].details=captured([entity('device',device)],[entity('device',device)]);await reject(p);
});
test('gap and initial cursors preserve the v1 envelope without inventing descriptions',async()=>{
 const p=page();p.events=[];p.refreshRequired=true;assert.deepEqual(await read(p),p);
 p.refreshRequired=false;const a=api(p,'/changes/details?limit=50');assert.deepEqual(await readClientChangeDetails(a,customer,null),p);
});
test('100 Unicode scalar values, 200 UTF16 units, literals and empty group text remain valid',async()=>{
 const p=page(),d=p.events[0].details;
 d.beforeEntities[0].name='😀'.repeat(100);d.afterEntities[0].name='Ω'.repeat(100);d.beforeEntities[1].name=d.afterEntities[1].name='';d.beforeEntities[1].prefix=d.afterEntities[1].prefix='';
 assert.deepEqual(await read(p),p);
 d.beforeEntities[1].prefix=d.afterEntities[1].prefix='😀'.repeat(100);assert.deepEqual(await read(p),p);
 for(const name of ['x'.repeat(101),'😀'.repeat(101),'a\0b','a\nb','\ud800','\udc00',' \u00a0\u2003 ',' leading','trailing\u2003']){const q=structuredClone(p);q.events[0].details.afterEntities[0].name=name;await reject(q);}
});
for(const [label,mutate]of Object.entries({
 extraEnvelope:p=>p.secret='private',extraEvent:p=>p.events[0].requestHash='private',extraDetails:p=>p.events[0].details.houseId=id(80),extraEntity:p=>p.events[0].details.beforeEntities[0].properties={secret:true},missingEntityField:p=>delete p.events[0].details.beforeEntities[0].positionU,
 wrongStatus:p=>p.events[0].details.status='partial',unavailableWithEntries:p=>p.events[0].details.status='notAvailable',unknownKind:p=>p.events[0].details.beforeEntities[0].kind='connection',unknownRelation:p=>p.events[0].details.beforeEntities[0].relation='current',nullEntry:p=>p.events[0].details.beforeEntities[0]=null,notArray:p=>p.events[0].details.beforeEntities={},
 duplicate:p=>p.events[0].details.beforeEntities.push({...p.events[0].details.beforeEntities[0],id:device.toUpperCase()}),zeroId:p=>p.events[0].details.beforeEntities[0].id='00000000-0000-0000-0000-000000000000',badId:p=>p.events[0].details.beforeEntities[0].parentId='missing',selfParent:p=>p.events[0].details.beforeEntities[0].parentId=device,
 wrongResource:p=>p.events[0].resourceId=id(90),wrongParentKind:p=>p.events[0].details.beforeEntities[0].parentKind='room',mixedPlacement:p=>p.events[0].details.beforeEntities[0].roomId=room,unmatchedRack:p=>p.events[0].details.beforeEntities[0].rackId=id(90),wrongGroupOwner:p=>p.events[0].details.beforeEntities[1].parentId=id(90),groupRack:p=>p.events[0].details.beforeEntities[1].rackId=rack,
 groupAlias:p=>p.events[0].details.beforeEntities[1].groupType='rj45_poe',groupCountZero:p=>p.events[0].details.beforeEntities[1].portCount=0,groupCountOver:p=>p.events[0].details.beforeEntities[1].portCount=97,groupCountFloat:p=>p.events[0].details.beforeEntities[1].portCount=1.5,groupPrefixNull:p=>p.events[0].details.beforeEntities[1].prefix=null,groupPrefixLong:p=>p.events[0].details.beforeEntities[1].prefix='x'.repeat(101),groupDeviceKind:p=>p.events[0].details.beforeEntities[1].deviceKind='rackEquipment',
 inventedPosition:p=>p.events[0].details.beforeEntities[0].positionU=1,badSize:p=>p.events[0].details.beforeEntities[0].sizeU=1001,zeroSize:p=>p.events[0].details.beforeEntities[0].sizeU=0,floatSize:p=>p.events[0].details.beforeEntities[0].sizeU=1.5,negativeOrder:p=>p.events[0].details.beforeEntities[0].sortOrder=-1,overOrder:p=>p.events[0].details.beforeEntities[0].sortOrder=2147483648,missingDeviceKind:p=>p.events[0].details.beforeEntities[0].deviceKind=null,emptyDeviceName:p=>p.events[0].details.beforeEntities[0].name='',
 forgedRevision:p=>p.events[0].revisionAfter=6,wrongCustomer:p=>p.customerId=id(80),wrongMore:p=>p.hasMore=true
}))test('closed descriptive DTO rejects '+label,async()=>{const p=page();mutate(p);await reject(p);});
test('512 entities per side are accepted intact; overflow, partial groups and policy mismatch are rejected',async()=>{
 const devices=Array.from({length:256},(_,i)=>entity('device',id(1000+i))),groups=devices.map((d,i)=>entity('portGroup',id(2000+i),{parentId:d.id}));
 const p=page('inventory.devices.delete',captured([...devices,...groups],[]),id(20));assert.equal((await read(p)).events[0].details.beforeEntities.length,512);
 p.events[0].details.beforeEntities.push(entity('device',id(9999)));await reject(p);
 const create=page('inventory.device.create',captured([entity('device',device)],[entity('device',device)]));await reject(create);
 const deleteWithAfter=page('inventory.device.delete',captured([entity('device',device)],[entity('device',device)]));await reject(deleteWithAfter);
 const reorder=page('inventory.device.reorder',captured([entity('rack',rack,{relation:'scope'}),entity('device',device)],[entity('rack',rack,{relation:'scope'})]),rack);await reject(reorder);
 const foreign=page('inventory.site.create',captured([],[entity('site',site,{parentId:id(99)})]),site);await reject(foreign);
});
test('updates and moves preserve captured group identities and device class; group editing may change its set',async()=>{
 for(const action of ['update','move']){
  const changedGroup=page('inventory.device.'+action);changedGroup.events[0].details.afterEntities[1].id=id(90);await reject(changedGroup);
  const missingGroup=page('inventory.device.'+action);missingGroup.events[0].details.afterEntities.pop();await reject(missingGroup);
  const changedKind=page('inventory.device.'+action);Object.assign(changedKind.events[0].details.afterEntities[0],{deviceKind:'dose',parentKind:'room',parentId:room,roomId:room,rackId:null,sizeU:null});await reject(changedKind);
 }
 const scope=entity('device',device,{relation:'scope'});await read(page('inventory.device.editPortGroups',captured([scope,entity('portGroup',group)],[scope,entity('portGroup',id(90))])));
});
test('action-specific invariants forbid forged placement, group changes, reorder metadata and duplicate ID reuse',async()=>{
 const location=page();Object.assign(location.events[0].details.afterEntities[0],{parentId:id(90),rackId:id(90)});await reject(location);
 const order=page();order.events[0].details.afterEntities[0].sortOrder=1;await reject(order);
 for(const action of ['update','move'])for(const field of ['name','prefix','groupType','sortOrder','portCount']){
  const p=page('inventory.device.'+action),g=p.events[0].details.afterEntities[1];g[field]={name:'New group',prefix:'B',groupType:'sfp',sortOrder:1,portCount:23}[field];await reject(p);
 }
 const before=[entity('rack',rack,{relation:'scope'}),entity('device',device)],after=structuredClone(before);after[1].name='Invented rename';await reject(page('inventory.device.reorder',captured(before,after),rack));
 after[1]=structuredClone(before[1]);after[0].sizeU=41;await reject(page('inventory.device.reorder',captured(before,after),rack));
 const scope=entity('device',device,{relation:'scope'});await reject(page('inventory.device.editPortGroups',captured([scope],[{...scope,name:'Invented rename'}])));
 const original=[entity('rack',rack),entity('device',device),entity('portGroup',group)].map(e=>({...e,relation:'source'})),copy=[entity('rack',id(30)),entity('device',device,{parentId:id(30),rackId:id(30)}),entity('portGroup',id(32))];
 await reject(page('inventory.rack.duplicate',captured(original,copy),id(30)));
});
test('authority is rechecked after GET, abort signal is forwarded, and cursors are bounded',async()=>{
 const p=page(),a=api(p),controller=new AbortController();a.fetcher=async(url,init)=>{assert.equal(init.signal,controller.signal);return new Response(JSON.stringify(p),{headers:{ETag:'"5"'}})};
 await readClientChangeDetails(a,customer,4,actor,controller.signal);
 a.fetcher=async()=>{a.actorId=other;return new Response(JSON.stringify(p),{headers:{ETag:'"5"'}})};
 await assert.rejects(()=>readClientChangeDetails(a,customer,4,actor),{code:'actor_changed'});
 for(const cursor of [0,-1,1.5,Number.MAX_SAFE_INTEGER+1])await assert.rejects(()=>readClientChangeDetails(api(p),customer,cursor,actor),{code:'changes_cursor_invalid'});
 await assert.rejects(()=>readClientChangeDetails(api(p,undefined,'"4"'),customer,4,actor),{code:'response_invalid'});
});
test('the existing ephemeral inbox keeps descriptions, does not apply a project or drop notices on an unapplied revision',async()=>{
 const p=await read(page()),box=new ChangeInbox(4);assert.equal(box.accept(p,4,actor),true);assert.deepEqual(box.events[0].details,p.events[0].details);box.apply(4);assert.equal(box.events.length,1);assert.equal(box.accept(p,4,actor),false);box.apply(5);assert.equal(box.events.length,0);
});
test('all UI field names translate while historical names, IDs and prefixes remain literal; scope is separate from source',()=>{
 const schema=x=>Object.fromEntries(Object.entries(x).map(([k,v])=>[k,typeof v==='object'?Object.keys(v).sort():typeof v]));
 for(const language of ['en','de','es']){
  assert.deepEqual(schema(changeDetailWords[language]),schema(changeDetailWords.es));
  const d=entity('device',device),g=entity('portGroup',group),rows=changeEntityRows(d,language),groupRows=changeEntityRows(g,language);
  assert.equal(rows.find(r=>r.field==='name').value,d.name);assert.equal(rows.find(r=>r.field==='parent').value.endsWith(rack),true);assert.equal(groupRows.find(r=>r.field==='prefix').value,g.prefix);assert.equal(rows.find(r=>r.field==='sortOrder').value,'0');assert.equal(rows.some(r=>r.field==='positionU'),false);
 }
 const source=entity('rack',rack,{relation:'source'}),target=entity('rack',id(30),{name:'Nuevo nombre'}),summary=changeEntitySummary(captured([source],[target]));assert.equal(summary.entities[0].name,'Nuevo nombre');assert.equal(changeEntitySummary(unavailable()),null);
 const many=Array.from({length:4},(_,i)=>entity('device',id(100+i)));assert.equal(changeEntitySummary(captured([] ,many)).more,true);assert.equal(changeEntitySummary(captured([],many)).entities.length,3);
});
test('component uses escaped React values and leaves the existing polling, explicit refresh and draft gate intact',async()=>{
 const component=await readFile(new URL('../src/RecordedEntityDetails.jsx',import.meta.url),'utf8'),notice=await readFile(new URL('../src/ClientChangeNotice.jsx',import.meta.url),'utf8');
 assert.doesNotMatch(component,/dangerouslySetInnerHTML|JSON\.stringify|localStorage|sessionStorage|fetch\(/);assert.match(component,/data-change-entity-side/);assert.match(component,/data-change-entity-id/);
 assert.match(notice,/readClientChangeDetails\(api,customerId,after,actorId,current\.signal\)/);assert.match(notice,/if\(!latest\.current\.canRefresh\|\|refreshing\|\|terminal\)return/);assert.match(notice,/controller\?\.abort\(\)/);assert.match(notice,/inbox\.current\.clear\(\)/);
});
