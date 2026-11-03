import test from 'node:test';
import assert from 'node:assert/strict';
import {copyFile, mkdir, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import catalogues from '../src/hardware-selected506c.generated.json' with {type:'json'};
import chosen from '../../hardware/selected-models-506.json' with {type:'json'};
import {hardwareChoices, hardwareProfile, hardwareCreateCommand, hardwareFitsShelf} from '../src/hardware-mounting.ts';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {verifySelected506CHardwareCatalog} from '../verify-hardware-catalog.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const models=catalogues.flatMap(c=>c.profiles.map(p=>({...p,revision:c.version})));
const revision='selected506c-20261101-v1';
function device(profile){return {hardwareProfileKey:profile.key,hardwareProfileVersion:profile.revision,
 hardwareIdentity:{...profile.identity},u:profile.sizeU,mountParentId:profile.kind==='desktop'?'shelf':null,
 mountSlotKey:profile.kind==='desktop'?'main':null,
 ports:profile.groups.flatMap((group,index)=>Array.from({length:group.count},(_,i)=>({
  id:profile.key+'-'+group.key+'-'+(i+1),groupId:'g'+index,type:group.type,gn:i+1,
  rackclickFace:group.face,rackclickHardwareGroupKey:group.key,rackclickPowerRole:group.powerRole,label:'',status:'free'})))}}

test('C adds fifty exact selected identities beside all 478 previous definitions',()=>{
 assert.equal(models.length,50);assert.equal(hardwareChoices.length,884);
 assert.equal(hardwareChoices.filter(p=>p.revision!=='german-repeaters-20261103-v1'&&p.revision!=='german-cpe-20261103-v1'&&p.revision!==revision&&p.revision!=='selected506l-20261101-v1'&&p.revision!=='selected506l-support-20261101-v1'&&p.revision!=='selected506k-20261101-v1'&&p.revision!=='mount-support7u-20261101-v1'&&p.revision!=='selected506j-20261101-v1'&&p.revision!=='selected506i-20261101-v1'&&p.revision!=='selected506h-20261101-v1'&&p.revision!=='selected506g-20261101-v1'&&p.revision!=='selected506d-20261101-v1'&&p.revision!=='selected506e-20261101-v1'&&p.revision!=='selected506f-20261101-v1').length,478);
 assert.equal(hardwareChoices.filter(p=>p.revision==='selected506a-20261101-v1').length,17);
 assert.equal(hardwareChoices.filter(p=>p.revision==='selected506b-20261101-v1').length,50);
 for(const profile of models){
  const original=chosen.models.find(item=>'selected-'+item.id===profile.key);assert.ok(original,profile.key);
  assert.equal(profile.identity.manufacturer,original.manufacturer);assert.equal(profile.identity.model,original.model);
  assert.equal(profile.revision,revision);assert.equal(hardwareProfile(profile.key,revision).identity.sku,profile.identity.sku);
  for(const bad of ['latest','selected506b-20261101-v1',null])assert.equal(hardwareProfile(profile.key,bad),undefined);
 }
});

test('both B faces retain every exact group, ordinal, role and original UUID',()=>{
 for(const profile of models){const original=device(profile),before=structuredClone(original);let count=0;
  for(const face of ['front','rear']){const layout=hardwareShellLayout(original,face);assert.ok(layout,profile.key+' '+face);
   for(const socket of layout.sockets){
    assert.equal(socket.port,original.ports.find(port=>port.rackclickHardwareGroupKey===socket.groupKey&&port.gn===socket.ordinal));
    assert.equal(socket.port.rackclickFace,face);
    const template=profile.groups.find(group=>group.key===socket.groupKey);assert.equal(socket.port.rackclickPowerRole,template.powerRole);
   }
   assert.equal(new Set(layout.sockets.map(socket=>socket.port.id)).size,layout.sockets.length);count+=layout.sockets.length;
  }
  assert.equal(count,original.ports.length);assert.deepEqual(original,before);
 }
});

test('C rejects changed revision, identity, type, face, role, group or endpoint coverage',()=>{
 for(const profile of models)for(const mutate of [
  item=>item.hardwareProfileVersion='unknown',item=>item.hardwareIdentity.sku='neighbour',
  item=>item.ports[0].type='console',item=>item.ports[0].rackclickPowerRole='outlet',
  item=>item.ports[0].rackclickFace=item.ports[0].rackclickFace==='front'?'rear':'front',
  item=>item.ports[0].rackclickHardwareGroupKey='other',item=>item.ports[0].id=item.ports[1].id,
  item=>item.ports[0].gn=0,item=>item.ports.pop()]){
   const original=device(profile);mutate(original);
   assert.equal(hardwareShellLayout(original,'front'),null,profile.key);
   assert.equal(hardwareShellLayout(original,'rear'),null,profile.key);
 }
});

test('C creates the exact server revision on the already supported physical mount',()=>{
 for(const profile of models){
  const shelf=hardwareChoices.find(item=>hardwareFitsShelf(profile,item));
  if(profile.kind==='desktop')assert.ok(shelf,profile.key);
  const parent=shelf?{id:'shelf',rackId:'r',hardwareProfileKey:shelf.key,properties:{hardwareProfileVersion:shelf.revision}}:null;
  const form={profileKey:profile.key,profileVersion:revision,rackId:'r',name:profile.identity.model,
   ...(profile.kind==='desktop'?{mountParentId:'shelf'}:{})};
  assert.deepEqual(hardwareCreateCommand(form,{racks:[{id:'r'}],devices:parent?[parent]:[]}),
   {type:'device.createHardware',payload:{profileKey:profile.key,profileVersion:revision,rackId:'r',name:profile.identity.model,
    ...(profile.kind==='desktop'?{mountParentId:'shelf',mountSlotKey:'main'}:{})}});
 }
});

test('C geometry is immutable while original labels and RJ45 PoE remain usable',()=>{
 let poeCases=0;
 for(const profile of models){const original=device(profile),first=original.ports[0];
  const layout=hardwareShellLayout(original,first.rackclickFace),fill=layout.visual.plate.fill;
  assert.throws(()=>layout.visual.plate.fill='#ff0000',TypeError);
  first.label='<svg onload=invalid> Ω';
  assert.equal(hardwareShellLayout(original,first.rackclickFace).ports.find(port=>port.id===first.id).label,first.label);
  assert.equal(hardwareShellLayout(original,first.rackclickFace).visual.plate.fill,fill);
  const copper=original.ports.find(port=>port.type==='rj45');if(!copper)continue;
  copper.type='rj45_poe';copper.poe=true;poeCases++;
  for(const face of ['front','rear'])assert.ok(hardwareShellLayout(original,face),profile.key+' '+face);
  assert.equal(hardwareShellLayout(original,copper.rackclickFace).sockets.find(socket=>socket.port.id===copper.id).port,copper);
 }
 assert.ok(poeCases>0);
});

test('C build verifier accepts the complete manifest and rejects stale derived bytes',async()=>{
 await verifySelected506CHardwareCatalog(root);
 const manifestName='development/hardware/catalog-selected506c.manifest.json';
 const manifest=JSON.parse(await readFile(path.join(root,manifestName),'utf8'));
 const privateRoot=path.join(root,'.local');
 await mkdir(privateRoot,{recursive:true});
 const isolated=await mkdtemp(path.join(privateRoot,'selected506c-verifier-'));
 assert.ok(path.resolve(isolated).startsWith(path.resolve(privateRoot)+path.sep));
 try{
  for(const name of new Set([manifestName,...Object.keys(manifest.inputs),...Object.keys(manifest.files)])){
   const target=path.join(isolated,name);await mkdir(path.dirname(target),{recursive:true});await copyFile(path.join(root,name),target);
  }
  await verifySelected506CHardwareCatalog(isolated);
  const derived=path.join(isolated,'development/frontend/src/hardware-selected506c.generated.json');
  await writeFile(derived,(await readFile(derived)).toString()+'\n');
  await assert.rejects(()=>verifySelected506CHardwareCatalog(isolated),/selected506c_catalog_stale/);
 }finally{
  assert.ok(path.resolve(isolated).startsWith(path.resolve(privateRoot)+path.sep));
  await rm(isolated,{recursive:true,force:true});
 }
});
