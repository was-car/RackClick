import test from 'node:test';
import assert from 'node:assert/strict';
import catalogues from '../src/hardware-selected506a.generated.json' with {type:'json'};
import chosen from '../../hardware/selected-models-506.json' with {type:'json'};
import {hardwareChoices,hardwareProfile,hardwareCreateCommand} from '../src/hardware-mounting.ts';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
const models=catalogues.flatMap(c=>c.profiles.map(p=>({...p,revision:c.version})));
const revision='selected506a-20261101-v1';
function device(p){return {hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:{...p.identity},u:p.sizeU,
 mountParentId:p.kind==='desktop'?'shelf':null,mountSlotKey:p.kind==='desktop'?'main':null,
 ports:p.groups.flatMap((g,index)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+(i+1),groupId:'g'+index,
  type:g.type,gn:i+1,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPowerRole:g.powerRole,label:'',status:'free'})))}}

test('all seventeen are exact selected identities and retain immutable revisions',()=>{
 assert.equal(models.length,17);assert.equal(hardwareChoices.length,884);
 for(const p of models){const original=chosen.models.find(m=>'selected-'+m.id===p.key);assert.ok(original);
  assert.equal(p.identity.manufacturer,original.manufacturer);assert.equal(p.identity.model,original.model);
  assert.equal(p.revision,revision);assert.equal(hardwareProfile(p.key,revision).identity.sku,p.identity.sku);
  for(const bad of ['latest','batch100c-20261031-v1',null])assert.equal(hardwareProfile(p.key,bad),undefined);
 }
});

test('both physical faces preserve every original group, ordinal and UUID',()=>{
 for(const p of models){const d=device(p),before=structuredClone(d);let count=0;
  for(const face of ['front','rear']){const layout=hardwareShellLayout(d,face);assert.ok(layout,p.key+' '+face);
   for(const s of layout.sockets){assert.equal(s.port,d.ports.find(x=>x.rackclickHardwareGroupKey===s.groupKey&&x.gn===s.ordinal));assert.equal(s.port.rackclickFace,face)}
   assert.equal(new Set(layout.sockets.map(s=>s.port.id)).size,layout.sockets.length);count+=layout.sockets.length;
  }
  assert.equal(count,d.ports.length);assert.deepEqual(d,before);
 }
});

test('an invalid revision, type, role, identity or duplicate UUID cannot borrow a specific face',()=>{
 for(const p of models)for(const change of [d=>d.hardwareProfileVersion='unknown',d=>d.hardwareIdentity.sku='neighbour',
  d=>d.ports[0].type='console',d=>d.ports[0].rackclickPowerRole='outlet',d=>d.ports[0].rackclickFace='rear',
  d=>d.ports[0].rackclickHardwareGroupKey='other',d=>d.ports[0].id=d.ports[1].id,d=>d.ports.pop()]){
   const d=device(p);change(d);assert.equal(hardwareShellLayout(d,'front'),null,p.key);assert.equal(hardwareShellLayout(d,'rear'),null,p.key);
 }
});

test('creation sends the exact server profile and views cannot mutate catalogue or instances',()=>{
 for(const p of models){const parent={id:'shelf',rackId:'r',hardwareProfileKey:'shelf-2u',properties:{hardwareProfileVersion:'hw-reference-v1'}};
  const request=hardwareCreateCommand({profileKey:p.key,profileVersion:revision,rackId:'r',name:p.identity.model,...(p.kind==='desktop'?{mountParentId:'shelf'}:{})},{racks:[{id:'r'}],devices:[parent]});
  assert.deepEqual(request,{type:'device.createHardware',payload:{profileKey:p.key,profileVersion:revision,rackId:'r',name:p.identity.model,...(p.kind==='desktop'?{mountParentId:'shelf',mountSlotKey:'main'}:{})}});
  const d=device(p),view=hardwareShellLayout(d,'front'),fill=view.visual.plate.fill;
  assert.throws(()=>view.visual.plate.fill='#ff0000',TypeError);assert.equal(hardwareShellLayout(d,'front').visual.plate.fill,fill);
  d.ports[0].label='<svg onload=invalid> Ω';assert.equal(hardwareShellLayout(d,d.ports[0].rackclickFace).ports.find(x=>x.id===d.ports[0].id).label,d.ports[0].label);
 }
});

test('enabling PoE preserves the original RJ45 geometry and both faces',()=>{
 for(const p of models){const d=device(p),port=d.ports.find(x=>x.type==='rj45'),id=port.id;
  port.type='rj45_poe';port.poe=true;
  for(const side of ['front','rear'])assert.ok(hardwareShellLayout(d,side),p.key+' '+side);
  assert.equal(hardwareShellLayout(d,port.rackclickFace).sockets.find(x=>x.port.id===id).port,port);
 }
});
