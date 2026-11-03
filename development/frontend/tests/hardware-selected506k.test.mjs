import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {copyFile, mkdir, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import catalogues from '../src/hardware-selected506k.generated.json' with {type:'json'};
import chosen from '../../hardware/selected-models-506.json' with {type:'json'};
import {hardwareChoices, hardwareProfile, hardwareCreateCommand, hardwareFitsShelf} from '../src/hardware-mounting.ts';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {verifySelected506KHardwareCatalog} from '../verify-hardware-catalog.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const models=catalogues.flatMap(c=>c.profiles.filter(p=>p.identity?.manufacturer).map(p=>({...p,revision:c.version})));
const revision='selected506k-20261101-v1';
function device(profile){return {hardwareProfileKey:profile.key,hardwareProfileVersion:profile.revision,
 hardwareIdentity:{...profile.identity},u:profile.sizeU,mountParentId:profile.kind==='desktop'?'shelf':null,
 mountSlotKey:profile.kind==='desktop'?'main':null,
 ports:profile.groups.flatMap((group,index)=>Array.from({length:group.count},(_,i)=>({
  id:profile.key+'-'+group.key+'-'+(i+1),groupId:'g'+index,type:group.type,gn:i+1,
  rackclickPhysicalConnector:group.physicalConnector??null,rackclickFace:group.face,rackclickHardwareGroupKey:group.key,rackclickPowerRole:group.powerRole,label:'',status:'free'})))}}

test('K adds the52 accepted identities and one separate7U support beside752 original definitions',async()=>{
 const plan=JSON.parse(await readFile(path.join(root,'evidence/s1-20261101/integracion506k/PLAN-FAMILIAS.json'),'utf8'));
 assert.equal(models.length,plan.models);assert.equal(hardwareChoices.length,884);
 assert.deepEqual(models.map(p=>p.key).sort(),Object.values(plan.authoring).flat().map(p=>'selected-'+p.id).sort());
 assert.equal(hardwareChoices.filter(p=>p.revision!=='german-repeaters-20261103-v1'&&p.revision!=='german-cpe-20261103-v1'&&p.revision!==revision&&p.revision!=='selected506l-20261101-v1'&&p.revision!=='selected506l-support-20261101-v1'&&p.revision!=='mount-support7u-20261101-v1').length,752);
 assert.equal(models.filter(p=>p.passthrough).length,6);assert.equal(models.filter(p=>!p.groups.length).length,10);
 for(const profile of models.filter(p=>p.passthrough)){
  const rule=profile.passthrough;assert.equal(rule.mapping,'one-to-one');assert.equal(rule.tracingAvailable,false);
  const front=profile.groups.find(g=>g.key===rule.frontGroup),rear=profile.groups.find(g=>g.key===rule.rearGroup);
  assert.deepEqual([front.type,rear.type,front.count,rear.count],['rj45','idc',rule.count,rule.count]);
  assert.equal(rear.physicalConnector,'idc-110');
 }
 const support=hardwareChoices.find(p=>p.key==='shelf-7u-deep');assert.equal(support.kind,'shelf');assert.equal(support.sizeU,7);
 assert.equal(support.slot.heightMm,280);assert.equal(support.groups.length,0);
 for(const profile of models){
  const original=chosen.models.find(item=>'selected-'+item.id===profile.key);assert.ok(original,profile.key);
  assert.equal(profile.identity.manufacturer,original.manufacturer);assert.equal(profile.identity.model,original.model);
  assert.equal(hardwareProfile(profile.key,revision).identity.sku,profile.identity.sku);
  for(const bad of ['latest','selected506j-20261101-v1',null])assert.equal(hardwareProfile(profile.key,bad),undefined);
 }
});

test('both K faces retain every exact group, ordinal, role and original UUID',()=>{
 for(const profile of models){const original=device(profile),before=structuredClone(original);let count=0;
  for(const face of ['front','rear']){const layout=hardwareShellLayout(original,face);assert.ok(layout,profile.key+' '+face);
   for(const socket of layout.sockets){
    assert.equal(socket.port,original.ports.find(port=>port.rackclickHardwareGroupKey===socket.groupKey&&port.gn===socket.ordinal));
    assert.equal(socket.port.rackclickFace,face);
    const template=profile.groups.find(group=>group.key===socket.groupKey);assert.equal(socket.port.rackclickPowerRole,template.powerRole);assert.equal(socket.port.type,template.type);
   }
   assert.equal(new Set(layout.sockets.map(socket=>socket.port.id)).size,layout.sockets.length);count+=layout.sockets.length;
  }
  if(profile.passthrough){
   const continuity=hardwareProfile(profile.key,revision).passthrough;
   for(let ordinal=1;ordinal<=continuity.count;ordinal++){
    const front=original.ports.find(p=>p.rackclickHardwareGroupKey===continuity.frontGroup&&p.gn===ordinal);
    const rear=original.ports.find(p=>p.rackclickHardwareGroupKey===continuity.rearGroup&&p.gn===ordinal);
    assert.ok(front&&rear);assert.notEqual(front.id,rear.id);assert.notEqual(front.groupId,rear.groupId);
   }
   assert.equal(continuity.tracingAvailable,false);
  }
  assert.equal(count,original.ports.length);assert.deepEqual(original,before);
 }

});

test('K rejects changed revision, identity, type, face, role, group or endpoint coverage',()=>{
 for(const profile of models.filter(p=>p.groups.length))for(const mutate of [
  item=>item.hardwareProfileVersion='unknown',item=>item.hardwareIdentity.sku='neighbour',
  item=>item.ports[0].type='usb_c',item=>item.ports[0].rackclickPowerRole=item.ports[0].rackclickPowerRole==='outlet'?'inlet':'outlet',
  item=>item.ports[0].rackclickFace=item.ports[0].rackclickFace==='front'?'rear':'front',
  item=>item.ports[0].rackclickHardwareGroupKey='other',item=>item.ports[0].id='',
  item=>item.ports[0].gn=0,item=>item.ports.pop()]){
   const original=device(profile);mutate(original);
   assert.equal(hardwareShellLayout(original,'front'),null,profile.key);
   assert.equal(hardwareShellLayout(original,'rear'),null,profile.key);
 }
});

test('K creates the exact server revision on the already supported physical mount',()=>{
 for(const profile of models){
  const shelf=hardwareChoices.find(item=>hardwareFitsShelf(profile,item));
  if(profile.kind==='desktop')assert.throws(()=>hardwareCreateCommand({profileKey:profile.key,profileVersion:revision,rackId:'r',name:profile.identity.model},{racks:[{id:'r'}],devices:[]}),error=>error.code==='mount_parent_invalid');
  if(profile.kind==='desktop')assert.ok(shelf,profile.key);
  const parent=shelf?{id:'shelf',rackId:'r',hardwareProfileKey:shelf.key,properties:{hardwareProfileVersion:shelf.revision}}:null;
  const form={profileKey:profile.key,profileVersion:revision,rackId:'r',name:profile.identity.model,
   ...(profile.kind==='desktop'?{mountParentId:'shelf'}:{})};
  assert.deepEqual(hardwareCreateCommand(form,{racks:[{id:'r'}],devices:parent?[parent]:[]}),
   {type:'device.createHardware',payload:{profileKey:profile.key,profileVersion:revision,rackId:'r',name:profile.identity.model,
    ...(profile.kind==='desktop'?{mountParentId:'shelf',mountSlotKey:'main'}:{})}});
 }
});

test('K geometry is immutable while original labels and RJ45 PoE remain usable',()=>{
 let poeCases=0;
 for(const profile of models.filter(p=>p.groups.length)){const original=device(profile),first=original.ports[0];
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

test('K build verifier accepts the complete manifest and rejects stale derived bytes',async()=>{
 await verifySelected506KHardwareCatalog(root);
 const manifestName='development/hardware/catalog-selected506k.manifest.json';
 const manifest=JSON.parse(await readFile(path.join(root,manifestName),'utf8'));
 const privateRoot=path.join(root,'.local');
 await mkdir(privateRoot,{recursive:true});
 const isolated=await mkdtemp(path.join(privateRoot,'selected506k-verifier-'));
 assert.ok(path.resolve(isolated).startsWith(path.resolve(privateRoot)+path.sep));
 try{
  for(const name of new Set([manifestName,...Object.keys(manifest.inputs),...Object.keys(manifest.files)])){
   const target=path.join(isolated,name);await mkdir(path.dirname(target),{recursive:true});await copyFile(path.join(root,name),target);
  }
  await verifySelected506KHardwareCatalog(isolated);
  // Rehash a private source fixture so this tests the name guard, not stale bytes.
  const authorName='development/hardware/selected506k/passive.json';
  const authorPath=path.join(isolated,authorName),manifestPath=path.join(isolated,manifestName);
  const authorBytes=await readFile(authorPath),manifestBytes=await readFile(manifestPath);
  for(const [name,valid]of [['A'.repeat(100),true],['\u{1f600}'.repeat(100),true],['e\u0301'.repeat(50),true],
    ['A'.repeat(101),false],['\u{1f600}'.repeat(101),false],['   ',false],['A\u0085B',false],['\ud800',false]]){
   const authored=JSON.parse(authorBytes);authored.models[0].definition.groups[0].name=name;
   const changed=Buffer.from(JSON.stringify(authored)),updated=structuredClone(manifest);
   updated.inputs[authorName]=createHash('sha256').update(changed).digest('hex');
   await writeFile(authorPath,changed);await writeFile(manifestPath,JSON.stringify(updated));
   if(valid)await verifySelected506KHardwareCatalog(isolated);
   else await assert.rejects(()=>verifySelected506KHardwareCatalog(isolated),/selected506k_group_name_invalid/);
  }
  for(const [prefix,valid]of [['\u{1f600}'.repeat(100),true],['\u{1f600}'.repeat(101),false]]){
   const authored=JSON.parse(authorBytes);authored.models[0].definition.groups[0].prefix=prefix;
   const changed=Buffer.from(JSON.stringify(authored)),updated=structuredClone(manifest);
   updated.inputs[authorName]=createHash('sha256').update(changed).digest('hex');
   await writeFile(authorPath,changed);await writeFile(manifestPath,JSON.stringify(updated));
   if(valid)await verifySelected506KHardwareCatalog(isolated);
   else await assert.rejects(()=>verifySelected506KHardwareCatalog(isolated),/selected506k_group_prefix_invalid/);
  }
  for(const mutate of [
   p=>p.passthrough.mapping='1:1',p=>p.passthrough.tracingAvailable=true,
   p=>p.passthrough.count--,p=>p.passthrough.rearGroup=p.passthrough.frontGroup,
   p=>p.groups[1].type='sfp',p=>p.passthrough.count=97]){
   const authored=JSON.parse(authorBytes);mutate(authored.models[0].definition);
   const changed=Buffer.from(JSON.stringify(authored)),updated=structuredClone(manifest);
   updated.inputs[authorName]=createHash('sha256').update(changed).digest('hex');
   await writeFile(authorPath,changed);await writeFile(manifestPath,JSON.stringify(updated));
   await assert.rejects(()=>verifySelected506KHardwareCatalog(isolated),/selected506k_(continuity|physical_connector)_invalid/);
  }
  await writeFile(authorPath,authorBytes);await writeFile(manifestPath,manifestBytes);
  await verifySelected506KHardwareCatalog(isolated);
  const derived=path.join(isolated,'development/frontend/src/hardware-selected506k.generated.json');
  await writeFile(derived,(await readFile(derived)).toString()+'\n');
  await assert.rejects(()=>verifySelected506KHardwareCatalog(isolated),/selected506k_catalog_stale/);
 }finally{
  assert.ok(path.resolve(isolated).startsWith(path.resolve(privateRoot)+path.sep));
  await rm(isolated,{recursive:true,force:true});
 }
});
