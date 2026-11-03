import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareChoices,hardwareRegistry,hardwareProfile,hardwareCreateCommand,hardwareFitsShelf,hardwareShelfProfile,validMounts,mountOccupancy} from '../src/hardware-mounting.ts';
import {validProject,projectToRc9} from '../src/inventory-model.ts';
import {hardwareWords,profileLabel,hardwareSlotLabel} from '../src/hardware-words.ts';
const key='synology-ds423plus',revision='synology-ds423plus-20261030-v1',supportRevision='mount-support-20261030-v1';
const row=(id,k,u,rev,extra={})=>({id,name:id,kind:'rackEquipment',rackId:'r',roomId:null,sizeU:u,sortOrder:0,poeBudget:null,hardwareProfileKey:k,properties:{hardwareProfileVersion:rev},...extra});
function project(){return {customerId:'c',revision:1,sites:[],buildings:[],rooms:[],racks:[{id:'r',name:'Rack',sizeU:12,roomId:null,properties:{}}],devices:[row('tall','shelf-5u',5,supportRevision),row('low','shelf-2u',2,'hw-reference-v1'),row('nas',key,0,revision,{mountParentId:'tall',mountSlotKey:'main'})],portGroups:[],ports:[],connections:[]};}
function device(){return {hardwareProfileKey:key,hardwareProfileVersion:revision,hardwareIdentity:{manufacturer:'Synology',family:'DiskStation',model:'DS423+',sku:'DS423+'},u:0,mountParentId:'tall',mountSlotKey:'main',ports:[1,2].map(n=>({id:'p'+n,groupId:'lan',type:'rj45',gn:n,rackclickFace:'rear',rackclickHardwareGroupKey:'rear-lan',rackclickPowerRole:'unspecified',label:''}))};}
test('DS423+ and synthetic tall shelf have independent exact revisions beside eight old profiles',()=>{
 assert.equal(hardwareChoices.length,884);assert.equal(hardwareRegistry.catalogues.length,29);assert.equal(hardwareProfile(key,revision).kind,'desktop');assert.deepEqual([hardwareProfile(key,revision).widthMm,hardwareProfile(key,revision).heightMm,hardwareProfile(key,revision).depthMm],[199,166,223]);assert.equal(hardwareProfile(key,revision).sizeU,0);
 const shelf=hardwareProfile('shelf-5u',supportRevision);assert.equal(shelf.kind,'shelf');assert.equal(shelf.sizeU,5);assert.equal(shelf.identity,undefined);assert.equal(shelf.slot.heightMm,190);assert.equal(hardwareProfile('shelf-2u','hw-reference-v1').slot.heightMm,60);
 for(const wrong of [null,undefined,'latest','hw-reference-v1',supportRevision])assert.equal(hardwareProfile(key,wrong),undefined);assert.equal(hardwareProfile('shelf-5u',revision),undefined);
});
test('real166mm height fits tall slot and rejects the old60mm shelf before a command',()=>{
 const p=project(),nas=hardwareProfile(key,revision);assert.equal(hardwareFitsShelf(nas,hardwareShelfProfile(p.devices[0])),true);assert.equal(hardwareFitsShelf(nas,hardwareShelfProfile(p.devices[1])),false);
 const form={profileKey:key,profileVersion:revision,rackId:'r',name:'DS Ω',mountParentId:'tall'};assert.deepEqual(hardwareCreateCommand(form,p).payload,{profileKey:key,profileVersion:revision,rackId:'r',name:'DS Ω',mountParentId:'tall',mountSlotKey:'main'});
 assert.throws(()=>hardwareCreateCommand({...form,mountParentId:'low'},p),e=>e.code==='mount_dimensions_invalid');assert.throws(()=>hardwareCreateCommand({...form,mountParentId:'missing'},p));
 p.devices[0].properties.hardwareProfileVersion='unavailable';assert.equal(hardwareShelfProfile(p.devices[0]),undefined);assert.throws(()=>hardwareCreateCommand(form,p),e=>e.code==='mount_parent_invalid');
});
test('recorded tall-shelf snapshot and projection preserve IDs without borrowing unknown dimensions',()=>{
 const p=project();assert.equal(validProject(p,'c'),true);assert.equal(validMounts(p.devices),true);assert.equal(mountOccupancy(p.devices),7);assert.equal(projectToRc9(p,'C').devices.get('nas').mountParentId,'tall');
 p.devices[2].mountParentId='low';assert.equal(validProject(p,'c'),false);assert.equal(validMounts(p.devices),false);
 p.devices[2].mountParentId='tall';p.devices[0].properties.hardwareProfileVersion='unavailable';assert.equal(validProject(p,'c'),true);assert.equal(validMounts(p.devices),true);assert.equal(projectToRc9(p,'C').devices.get('tall').hardwareProfileVersion,'unavailable');
});
test('mount shape rejects wrong rack, fake support, duplicate slot and cycles',()=>{
 for(const mutate of [p=>p.devices[2].mountParentId='missing',p=>p.devices[2].mountSlotKey='other',p=>p.devices[2].sizeU=1,p=>p.devices[2].rackId='other',p=>p.devices[0].hardwareProfileKey='switch-24',p=>p.devices.push({...p.devices[2],id:'second'}),p=>p.devices[0].mountParentId='nas']){const p=project();mutate(p);assert.equal(validProject(p,'c'),false);assert.equal(validMounts(p.devices),false);}
});
test('shelf labels and preview dimensions come from each profile in all three languages',()=>{
 const tall=hardwareProfile('shelf-5u',supportRevision),low=hardwareProfile('shelf-2u','hw-reference-v1');
 for(const lang of ['en','de','es']){const w=hardwareWords[lang];assert.match(profileLabel(tall,w),/5/);assert.match(profileLabel(low,w),/2/);assert.match(hardwareSlotLabel(tall,w),/440 × 190 × 300/);assert.match(hardwareSlotLabel(low,w),/440 × 60 × 300/);assert.equal(hardwareSlotLabel(undefined,w),w.recordedSlot);}
});
test('DS423+ views preserve only the two rear UUIDs and never infer USB/DC as Ethernet',()=>{
 const d=device(),before=structuredClone(d);assert.equal(hardwareShellLayout(d,'front').ports.length,0);assert.equal(hardwareShellLayout(d,'rear').ports.length,2);assert.deepEqual(d,before);assert.throws(()=>hardwareShellLayout(d,'rear').ports.pop(),TypeError);
 for(const mutate of [d=>d.hardwareProfileVersion='latest',d=>d.hardwareIdentity.sku='DS423',d=>d.hardwareIdentity.model='DS425+',d=>d.u=1,d=>d.mountParentId=null,d=>d.mountSlotKey='other',d=>d.ports.pop(),d=>d.ports[0].id=d.ports[1].id,d=>d.ports[0].gn=2,d=>d.ports[0].groupId='other',d=>d.ports[0].rackclickHardwareGroupKey='dc',d=>d.ports[0].rackclickFace='front',d=>d.ports[0].type='power',d=>d.ports[0].rackclickPowerRole='inlet']){const x=device();mutate(x);assert.equal(hardwareShellLayout(x,'front'),null);assert.equal(hardwareShellLayout(x,'rear'),null);}
});
