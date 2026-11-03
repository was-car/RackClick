import test from 'node:test';
import assert from 'node:assert/strict';
import catalogues from '../src/hardware-batch50.generated.json' with {type:'json'};
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareChoices,hardwareProfile,hardwareCreateCommand} from '../src/hardware-mounting.ts';
import {expandHardwareBanks} from '../src/batch-hardware-shells.ts';
const models=catalogues.flatMap(c=>c.profiles.filter(p=>p.visual).map(p=>({...p,revision:c.version})));
function device(p){return {hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:{...p.identity},u:p.sizeU,mountParentId:p.kind==='desktop'?'shelf':null,mountSlotKey:p.kind==='desktop'?'main':null,ports:p.groups.flatMap((g,index)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+(i+1),groupId:'g'+index,type:g.type,gn:i+1,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPowerRole:g.powerRole,label:'',status:'free'})))}}
test('50 new exact models share a reviewed batch without replacing six previous commercial profiles',()=>{
 assert.equal(models.length,50);assert.equal(new Set(models.map(p=>p.key)).size,50);assert.equal(hardwareChoices.length,884);
 for(const p of models){assert.equal(hardwareProfile(p.key,p.revision).identity.sku,p.identity.sku);for(const v of ['latest','hw-reference-v1',null])assert.equal(hardwareProfile(p.key,v),undefined)}
 for(const [k,v]of [['aruba-jl682a','aruba-20261030-v1'],['fortinet-fg60f','fortinet-20261030-v1'],['synology-rs1221plus','synology-20261030-v1'],['synology-ds423plus','synology-ds423plus-20261030-v1'],['qnap-ts464-8g','qnap-20261030-v1'],['startech-c6panelutp241uft','startech-20261030-v1']])assert.ok(hardwareProfile(k,v));
});
test('all100 faces bind each bank to original UUID/group/ordinal/type/role with no instance mutation',()=>{
 for(const p of models){const d=device(p),before=structuredClone(d);let shown=0;
  for(const face of ['front','rear']){const layout=hardwareShellLayout(d,face);assert.ok(layout,p.key);const banks=expandHardwareBanks(p.visual.faces[face]);assert.equal(layout.sockets.length,banks.length);
   for(let i=0;i<banks.length;i++){const b=banks[i],s=layout.sockets[i];assert.equal(s.port,d.ports.find(x=>x.rackclickHardwareGroupKey===b.groupKey&&x.gn===b.ordinal));assert.equal(s.port.rackclickFace,face);assert.equal(s.x,b.x);assert.equal(s.y,b.y)}shown+=layout.ports.length;
  }assert.equal(shown,d.ports.length);assert.deepEqual(d,before);
 }
});
test('batch geometry is immutable while labels and other instance data remain owned by RC9',()=>{
 for(const p of models){const d=device(p),layout=hardwareShellLayout(d,'front'),fill=layout.visual.plate.fill;assert.throws(()=>layout.visual.plate.fill='#ff0000',TypeError);assert.throws(()=>layout.visual.decorations.push({kind:'image'}),TypeError);assert.equal(hardwareShellLayout(d,'front').visual.plate.fill,fill);assert.equal(Object.isFrozen(d.ports[0]),false);d.ports[0].label='<svg> Ω';assert.equal(hardwareShellLayout(d,d.ports[0].rackclickFace).ports.some(x=>x.label==='<svg> Ω'),true)}
});
test('all50 reject inconsistent revision/identity/mount/UUID/group/face/role before specific rendering',()=>{
 for(const p of models){for(const mutate of [d=>d.hardwareProfileVersion='batch50-unknown',d=>d.hardwareIdentity.sku='other',d=>d.ports.pop(),d=>d.ports[0].id='',d=>d.ports[0].rackclickHardwareGroupKey='other',d=>d.ports[0].rackclickFace='invalid',d=>d.ports[0].rackclickPowerRole='outlet',d=>d.u=99]){const d=device(p);mutate(d);assert.equal(hardwareShellLayout(d,'front'),null,p.key);assert.equal(hardwareShellLayout(d,'rear'),null,p.key)}
  const shelf= p.heightMm<=60&&p.depthMm<=300?'shelf-2u':'shelf-5u',revision=shelf==='shelf-2u'?'hw-reference-v1':'mount-support-20261030-v1';const project={racks:[{id:'r'}],devices:[{id:'shelf',rackId:'r',hardwareProfileKey:shelf,properties:{hardwareProfileVersion:revision}}]};const form={profileKey:p.key,profileVersion:p.revision,rackId:'r',name:p.identity.model,...(p.kind==='desktop'?{mountParentId:'shelf'}:{})};assert.equal(hardwareCreateCommand(form,project).payload.profileKey,p.key);
 }
});
