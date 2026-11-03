import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareChoices,hardwareProfile,hardwareCreateCommand,mountOccupancy} from '../src/hardware-mounting.ts';
const key='synology-rs1221plus',revision='synology-20261030-v1';
function device(){return {hardwareProfileKey:key,hardwareProfileVersion:revision,hardwareIdentity:{manufacturer:'Synology',family:'RackStation',model:'RS1221+',sku:'RS1221+'},u:2,mountParentId:null,mountSlotKey:null,ports:[['rear-lan','rj45',4,'unspecified'],['rear-power','power',1,'inlet']].flatMap(([group,type,count,role])=>Array.from({length:count},(_,i)=>({id:group+'-'+i,groupId:group,rackclickHardwareGroupKey:group,type,gn:i+1,rackclickFace:'rear',rackclickPowerRole:role,label:''})))};}
test('RS1221+ is exact rack2U with server-ear dimensions, not redundant RP+',()=>{
 const p=hardwareProfile(key,revision);assert.equal(hardwareChoices.length,884);assert.equal(p.kind,'rack');assert.equal(p.sizeU,2);assert.deepEqual([p.widthMm,p.heightMm,p.depthMm],[482,88,306.6]);assert.equal(p.groups.reduce((n,g)=>n+g.count,0),5);assert.equal(p.identity.sku,'RS1221+');
 assert.equal(p.groups[0].count,4);assert.equal(p.groups[1].powerRole,'inlet');assert.ok(p.groups.every(g=>g.face==='rear'));assert.equal(hardwareProfile('synology-rs1221rpplus',revision),undefined);
 for(const version of [null,undefined,'latest','hw-reference-v1','synology-20261030-v2'])assert.equal(hardwareProfile(key,version),undefined);
});
test('Synology faces keep zero front sockets and five existing rear UUIDs without mutation',()=>{
 const d=device(),before=structuredClone(d),front=hardwareShellLayout(d,'front'),rear=hardwareShellLayout(d,'rear');assert.equal(front.family,'synology-rs1221plus');assert.equal(front.ports.length,0);assert.equal(rear.ports.length,5);assert.deepEqual(d,before);assert.throws(()=>rear.ports.pop(),TypeError);assert.equal(new Set(rear.ports.map(p=>p.id)).size,5);assert.notEqual(rear.ports[0].id,rear.ports[4].id);assert.equal(rear.ports[0].gn,rear.ports[4].gn);
});
test('Synology visual identity fails closed on wrong SKU/revision/mount/type/role/group/ordinal',()=>{
 for(const mutate of [d=>d.hardwareProfileVersion='latest',d=>d.hardwareIdentity.model='RS1221RP+',d=>d.hardwareIdentity.sku='RS1221RP+',d=>d.hardwareIdentity.manufacturer='other',d=>d.u=1,d=>d.mountParentId='shelf',d=>d.mountSlotKey='main',d=>d.ports.pop(),d=>d.ports[0].id=d.ports[1].id,d=>d.ports[0].groupId='rear-power',d=>d.ports[0].rackclickHardwareGroupKey='rear-power',d=>d.ports[0].rackclickFace='front',d=>d.ports[0].type='sfp',d=>d.ports[0].gn=2,d=>d.ports[4].rackclickPowerRole='outlet',d=>d.ports[4].gn=2]){
  const d=device();mutate(d);for(const face of ['front','rear'])assert.equal(hardwareShellLayout(d,face),null);
 }
 assert.equal(hardwareShellLayout(device(),'side'),null);
});
test('NAS creation stays a2U root and never adopts a stale caller shelf or size',()=>{
 const project={racks:[{id:'r'}],devices:[]},form={profileKey:key,profileVersion:revision,rackId:'r',name:'NAS Ω',mountParentId:'stale',sizeU:0};assert.deepEqual(hardwareCreateCommand(form,project).payload,{profileKey:key,profileVersion:revision,rackId:'r',name:'NAS Ω'});assert.equal(mountOccupancy([{sizeU:2},{sizeU:2}]),4);
 assert.throws(()=>hardwareCreateCommand({...form,profileVersion:'latest'},project));assert.throws(()=>hardwareCreateCommand({...form,rackId:'missing'},project));
});
test('the four previous synthetic profiles and three commercial models keep their types and counts',()=>{
 assert.equal(hardwareProfile('desktop-firewall-6','hw-reference-v1').groups.reduce((n,g)=>n+g.count,0),7);assert.equal(hardwareProfile('startech-c6panelutp241uft','startech-20261030-v1').groups.reduce((n,g)=>n+g.count,0),48);assert.equal(hardwareProfile('aruba-jl682a','aruba-20261030-v1').groups.reduce((n,g)=>n+g.count,0),29);assert.equal(hardwareProfile('fortinet-fg60f','fortinet-20261030-v1').groups.reduce((n,g)=>n+g.count,0),10);assert.equal(hardwareProfile('switch-24','hw-reference-v1').groups[1].face,'rear');
});
