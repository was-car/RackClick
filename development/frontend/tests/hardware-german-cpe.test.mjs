import test from 'node:test';
import assert from 'node:assert/strict';
import catalogues from '../src/hardware-german-cpe.generated.json' with {type:'json'};
import {hardwareChoices,hardwareProfile,hardwareCreateCommand} from '../src/hardware-mounting.ts';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {validConnectorDescriptor} from '../src/hardware-connector-classification.mjs';
const models=catalogues.flatMap(c=>c.profiles.map(p=>({...p,revision:c.version})));
function device(p){return {hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:{...p.identity},u:0,mountParentId:'shelf',mountSlotKey:'main',ports:p.groups.flatMap((g,index)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+(i+1),groupId:'g'+index,type:g.type,gn:i+1,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPowerRole:g.powerRole,rackclickPhysicalConnector:g.physicalConnector??null,rackclickPhysicalFace:g.physicalFace??null,rackclickInterfaceRole:g.interfaceRole??null,rackclickSignalRole:g.signalRole??null,rackclickPowerSystem:g.powerSystem??null,label:'',status:'free'})))}}
test('six German models are additional to868 revisions and exact versions only',()=>{
 assert.equal(models.length,6);assert.equal(hardwareChoices.length,884);
 for(const p of models){assert.equal(hardwareProfile(p.key,p.revision).identity.sku,p.identity.sku);assert.equal(hardwareProfile(p.key,'latest'),undefined)}
});
test('all twelve faces bind exactly51 unique UUID endpoints without changing instances',()=>{
 let count=0;
 for(const p of models){const d=device(p),before=structuredClone(d);
  for(const face of ['front','rear']){const layout=hardwareShellLayout(d,face);assert.ok(layout,p.key+'/'+face);assert.equal(layout.sockets.length,face==='front'?0:d.ports.length);for(const s of layout.sockets){assert.ok(d.ports.includes(s.port));count++}}
  assert.deepEqual(d,before);
 }assert.equal(count,51);
});
test('USB stays USB, TAE stays voice and unsupported descriptor families reject it',()=>{
 assert.equal(validConnectorDescriptor('telephony','voice-tae'),true);
 for(const type of ['rj45','dsl','console','usb_a'])assert.equal(validConnectorDescriptor(type,'voice-tae'),false);
 for(const p of models)for(const g of p.groups)if(g.key.startsWith('usb'))assert.equal(g.type,'usb_a');
});
test('all six require a fitted shelf and reject missing parent',()=>{
 const shelf={id:'shelf',rackId:'rack',hardwareProfileKey:'shelf-5u',properties:{hardwareProfileVersion:'mount-support-20261030-v1'}};
 const project={racks:[{id:'rack'}],devices:[shelf]};
 for(const p of models){const form={profileKey:p.key,profileVersion:p.revision,rackId:'rack',name:p.identity.model};assert.throws(()=>hardwareCreateCommand(form,project));assert.equal(hardwareCreateCommand({...form,mountParentId:'shelf'},project).payload.mountSlotKey,'main')}
});
test('revision, metadata, missing UUID and ports cannot borrow another face',()=>{
 for(const p of models)for(const mutate of [d=>d.hardwareProfileVersion='other',d=>d.hardwareIdentity.sku='other',d=>d.ports.pop(),d=>d.ports[0].id='',d=>d.mountParentId=null]){const d=device(p);mutate(d);assert.equal(hardwareShellLayout(d,'rear'),null,p.key)}
});

test('Vigor167 rearP2left/P1right retains each corresponding ordinal UUID',()=>{
 const p=models.find(p=>p.key==='draytek-vigor167'),d=device(p),layout=hardwareShellLayout(d,'rear');
 const sockets=layout.sockets.filter(s=>s.port.rackclickHardwareGroupKey==='lan').sort((a,b)=>a.x-b.x);
 assert.deepEqual(sockets.map(s=>s.port.gn),[2,1]);assert.deepEqual(sockets.map(s=>s.label),['P2','P1']);
});
