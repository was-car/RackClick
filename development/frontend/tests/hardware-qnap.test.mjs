import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareChoices,hardwareRegistry,hardwareProfile,hardwareCreateCommand,validMounts,mountOccupancy} from '../src/hardware-mounting.ts';
import {projectToRc9,validProject} from '../src/inventory-model.ts';
import {hardwareWords} from '../src/hardware-words.ts';
const key='qnap-ts464-8g',rev='qnap-20261030-v1',support='mount-support-20261030-v1';
const row=(id,k,u,v,extra={})=>({id,name:id,kind:'rackEquipment',rackId:'r',roomId:null,sizeU:u,sortOrder:0,poeBudget:null,hardwareProfileKey:k,properties:{hardwareProfileVersion:v},...extra});
function project(){return {customerId:'c',revision:1,sites:[],buildings:[],rooms:[],racks:[{id:'r',name:'Rack',sizeU:7,roomId:null,properties:{}}],devices:[row('tall','shelf-5u',5,support),row('low','shelf-2u',2,'hw-reference-v1'),row('nas',key,0,rev,{mountParentId:'tall',mountSlotKey:'main'})],portGroups:[],ports:[],connections:[]};}
function device(){return {hardwareProfileKey:key,hardwareProfileVersion:rev,hardwareIdentity:{manufacturer:'QNAP',family:'TS-x64',model:'TS-464',sku:'TS-464-8G'},u:0,mountParentId:'tall',mountSlotKey:'main',ports:[1,2].map(n=>({id:'p'+n,groupId:'lan',type:'rj45',gn:n,rackclickFace:'rear',rackclickHardwareGroupKey:'rear-lan',rackclickPowerRole:'unspecified',label:''}))};}
test('QNAP exact8G revision adds one profile without borrowing DS dimensions',()=>{
 assert.equal(hardwareChoices.length,884);assert.equal(hardwareRegistry.catalogues.length,29);
 const p=hardwareProfile(key,rev);assert.equal(p.kind,'desktop');assert.equal(p.sizeU,0);assert.deepEqual([p.widthMm,p.heightMm,p.depthMm],[170,165,226.5]);assert.equal(p.identity.sku,'TS-464-8G');assert.equal(p.groups.length,1);assert.equal(p.groups[0].count,2);assert.equal(p.groups[0].type,'rj45');assert.equal(p.groups[0].face,'rear');
 assert.deepEqual([hardwareProfile('synology-ds423plus','synology-ds423plus-20261030-v1').widthMm,hardwareProfile('synology-ds423plus','synology-ds423plus-20261030-v1').heightMm],[199,166]);
 for(const v of [null,undefined,'latest','hw-reference-v1','synology-ds423plus-20261030-v1'])assert.equal(hardwareProfile(key,v),undefined);
});
test('QNAP uses existing tall support and rejects60mm low support before dispatch',()=>{
 const p=project(),form={profileKey:key,profileVersion:rev,rackId:'r',name:'QNAP Ω',mountParentId:'tall'};
 assert.deepEqual(hardwareCreateCommand(form,p).payload,{profileKey:key,profileVersion:rev,rackId:'r',name:'QNAP Ω',mountParentId:'tall',mountSlotKey:'main'});
 assert.throws(()=>hardwareCreateCommand({...form,mountParentId:'low'},p),e=>e.code==='mount_dimensions_invalid');
 assert.equal(validProject(p,'c'),true);assert.equal(validMounts(p.devices),true);assert.equal(mountOccupancy(p.devices),7);
 p.devices[2].mountParentId='low';assert.equal(validProject(p,'c'),false);assert.equal(validMounts(p.devices),false);
});
test('QNAP keeps original two rear UUIDs, exact identity and no decorative connectors',()=>{
 const d=device(),original=structuredClone(d),front=hardwareShellLayout(d,'front'),rear=hardwareShellLayout(d,'rear');
 assert.equal(front.family,'qnap-ts464');assert.equal(front.ports.length,0);assert.deepEqual(rear.ports.map(p=>p.id),['p1','p2']);assert.equal(rear.ports[0],d.ports[0]);assert.deepEqual(d,original);assert.throws(()=>rear.ports.pop(),TypeError);
 for(const mutate of [d=>d.hardwareIdentity.sku='TS-464-4G',d=>d.hardwareIdentity.model='TS-664',d=>d.hardwareIdentity.manufacturer='Synology',d=>d.hardwareProfileVersion='latest',d=>d.u=1,d=>d.mountParentId=null,d=>d.mountSlotKey='other',d=>d.ports.pop(),d=>d.ports[0].id=d.ports[1].id,d=>d.ports[0].gn=2,d=>d.ports[0].groupId='other',d=>d.ports[0].rackclickHardwareGroupKey='usb',d=>d.ports[0].rackclickFace='front',d=>d.ports[0].type='power',d=>d.ports[0].rackclickPowerRole='inlet']){const x=device();mutate(x);assert.equal(hardwareShellLayout(x,'front'),null);assert.equal(hardwareShellLayout(x,'rear'),null);}
});
test('QNAP projection keeps mount and unknown recorded revision without substitution',()=>{
 const p=project();assert.equal(projectToRc9(p,'C').devices.get('nas').hardwareProfileVersion,rev);assert.equal(projectToRc9(p,'C').devices.get('nas').mountParentId,'tall');
 p.devices[2].properties.hardwareProfileVersion='unavailable';assert.equal(validProject(p,'c'),true);const d=projectToRc9(p,'C').devices.get('nas');assert.equal(d.hardwareProfileVersion,'unavailable');assert.equal(hardwareShellLayout(d,'rear'),null);
 for(const lang of ['en','de','es']){assert.match(hardwareWords[lang].qnapFront,/TS-464/);assert.match(hardwareWords[lang].qnapRear,/LAN1/);assert.match(hardwareWords[lang].qnapRear,/LAN2/);}
});
