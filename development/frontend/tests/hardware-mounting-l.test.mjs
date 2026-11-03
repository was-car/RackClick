import {hardwareShellLayout} from '../src/hardware-shells.ts';
import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareChoices,hardwareCreateCommand,hardwareProfile,mountOccupancy} from '../src/hardware-mounting.ts';
import {validProject,projectToRc9} from '../src/inventory-model.ts';
import {recordedGroupClassification} from '../src/hardware-connector-classification.mjs';
const revision='selected506l-20261101-v1';
const choice=kind=>hardwareChoices.find(p=>p.revision===revision&&p.kind===kind);
function fixture(){return {customerId:'customer',revision:1,sites:[{id:'site',name:'site',properties:{}}],buildings:[{id:'building',siteId:'site',name:'building',properties:{}}],rooms:[{id:'room',buildingId:'building',name:'room',properties:{}}],racks:[{id:'rack',roomId:'room',name:'rack',location:'',sizeU:60,properties:{}}],devices:[],portGroups:[],ports:[],connections:[]}}
const form=p=>({profileKey:p.key,profileVersion:p.revision,name:'Nombre intacto Ω',rackId:'rack',roomId:'room',mountParentId:'',mountSlotKey:'vertical-left'});
test('catalogue holds every chosen L model plus one exact successor, without latest fallback',()=>{
 assert.equal(hardwareChoices.length,884);
 assert.equal(hardwareChoices.filter(p=>p.revision===revision).length,62);
 const key='selected-nb-e5030fe747d79fe6';
 assert.ok(hardwareProfile(key,'selected506a-20261101-v1'));
 assert.equal(hardwareProfile(key,'selected506a-20261101-v1').groups.some(g=>g.powerSystem==='unifi-smartpower'),false);
 assert.ok(hardwareProfile(key,'selected506l-support-20261101-v1').groups.some(g=>g.powerSystem==='unifi-smartpower'));
 assert.equal(hardwareProfile(key,'latest'),undefined);
});
test('an enclosure creates a rack with no caller-supplied capacity or equipment',()=>{
 const p=choice('rackContainer'),project=fixture(),command=hardwareCreateCommand({...form(p),sizeU:999,capacityU:999},project);
 assert.deepEqual(command,{type:'rack.createHardware',payload:{profileKey:p.key,profileVersion:p.revision,name:'Nombre intacto Ω',roomId:'room'}});
 assert.equal(mountOccupancy(project.devices),0);
 assert.throws(()=>hardwareCreateCommand({...form(p),roomId:'another-room'},project));
});
test('wall and DIN objects use a room and cannot consume rack U',()=>{
 for(const kind of ['wall','din']){
  const p=choice(kind),command=hardwareCreateCommand(form(p),fixture());
  assert.equal(command.type,'device.createHardware');assert.equal(command.payload.roomId,'room');
  assert.equal(Object.hasOwn(command.payload,'rackId'),false);assert.equal(Object.hasOwn(command.payload,'sizeU'),false);
 }
});
test('vertical mounts enforce side uniqueness and real known height',()=>{
 const p=choice('vertical0U'),project=fixture(),f=form(p);
 assert.equal(hardwareCreateCommand(f,project).payload.mountSlotKey,'vertical-left');
 project.racks[0].sizeU=12;assert.throws(()=>hardwareCreateCommand(f,project));project.racks[0].sizeU=60;
 project.devices.push({rackId:'rack',mountSlotKey:'vertical-left',mountParentId:null});assert.throws(()=>hardwareCreateCommand(f,project));
 assert.equal(hardwareCreateCommand({...f,mountSlotKey:'vertical-right'},project).payload.mountSlotKey,'vertical-right');
 assert.throws(()=>hardwareCreateCommand({...f,mountSlotKey:'invented'},fixture()));
});
test('shared-U requires an exact root in the same rack and an unoccupied relationship',()=>{
 const p=choice('sharedU'),project=fixture(),parent={id:'parent',kind:'rackEquipment',rackId:'rack',sizeU:1,hardwareProfileKey:'switch-24',properties:{hardwareProfileVersion:'hw-reference-v1'}};
 project.devices.push(parent);
 const f={...form(p),mountParentId:'parent'};assert.equal(hardwareCreateCommand(f,project).payload.mountSlotKey,'shared');
 parent.rackId='other';assert.throws(()=>hardwareCreateCommand(f,project));parent.rackId='rack';
 project.devices.push({id:'child',mountParentId:'parent',mountSlotKey:'shared'});assert.throws(()=>hardwareCreateCommand(f,project));
});
test('snapshot zero-U is accepted only with the exact bound mounting and valid relationship',()=>{
 const p=choice('vertical0U'),project=fixture();
 const device={id:'pdu',kind:'rackEquipment',name:'pdu',rackId:'rack',roomId:null,sizeU:0,sortOrder:0,poeBudget:null,properties:{hardwareProfileVersion:p.revision},hardwareProfileKey:p.key,mountParentId:null,mountSlotKey:'vertical-left'};
 project.devices.push(device);assert.equal(validProject(project,'customer'),true);assert.equal(mountOccupancy(project.devices),0);
 device.hardwareProfileKey='unknown';assert.equal(validProject(project,'customer'),false);device.hardwareProfileKey=p.key;
 device.mountSlotKey='arbitrary';assert.equal(validProject(project,'customer'),false);
});
test('system, role and physical-face classifications require the same recorded revision and group',()=>{
 const p=hardwareChoices.find(p=>p.revision===revision&&p.groups.some(g=>g.powerSystem==='unifi-smartpower')),g=p.groups.find(g=>g.powerSystem==='unifi-smartpower');
 const device={hardwareProfileKey:p.key,properties:{hardwareProfileVersion:p.revision}},port={type:g.type,face:g.face,properties:{hardwareGroupKey:g.key,hardwarePowerSystem:g.powerSystem}};
 assert.equal(recordedGroupClassification(device,port,hardwareProfile,'powerSystem'),'unifi-smartpower');
 assert.equal(recordedGroupClassification(device,{...port,properties:{...port.properties,hardwarePowerSystem:'usb-pd'}},hardwareProfile,'powerSystem'),null);
 assert.equal(recordedGroupClassification({...device,properties:{hardwareProfileVersion:'latest'}},port,hardwareProfile,'powerSystem'),null);
 assert.equal(recordedGroupClassification(device,port,hardwareProfile,'arbitrary'),null);
});

test('the native renderer resolves both faces of all exact L revisions',()=>{
 for(const p of hardwareChoices.filter(p=>['selected506l-20261101-v1','selected506l-support-20261101-v1'].includes(p.revision))){
  const d={hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:p.identity,u:['wall','pole','din','floor'].includes(p.kind)?null:p.sizeU,mountParentId:['desktop','sharedU'].includes(p.kind)?'parent':null,mountSlotKey:p.kind==='desktop'?'main':p.kind==='sharedU'?'shared':p.kind==='vertical0U'?'vertical-left':null,ports:p.groups.flatMap((g,index)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+i,groupId:'group-'+index,type:g.type,gn:i+1,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPowerRole:g.powerRole,rackclickPhysicalConnector:g.physicalConnector})))};
  for(const face of ['front','rear']){const layout=hardwareShellLayout(d,face);assert.ok(layout,p.key+' '+face);assert.equal(layout.sockets.length,p.groups.filter(g=>g.face===face).reduce((n,g)=>n+g.count,0));}
 }
});
