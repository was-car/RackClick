import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareChoices,hardwareCreateCommand,hardwareProfile} from '../src/hardware-mounting.ts';
const key='aruba-jl682a',revision='aruba-20261030-v1';
function model(){return {u:1,hardwareProfileKey:key,hardwareProfileVersion:revision,hardwareIdentity:{manufacturer:'HPE Aruba Networking',model:'JL682A',sku:'JL682A'},ports:[['rj45','front',24],['sfp','front',4],['power','rear',1]].flatMap(([type,face,count])=>Array.from({length:count},(_,i)=>({id:type+'-'+(i+1),groupId:type+'-group',type,rackclickFace:face,rackclickPowerRole:type==='power'?'inlet':'unspecified',gn:i+1})))};}
test('new exact model coexists with the five old profiles without changing their topology',()=>{
 assert.equal(hardwareChoices.length,884);assert.equal(hardwareProfile('switch-24','hw-reference-v1').groups[1].face,'rear');
 assert.equal(hardwareProfile('startech-c6panelutp241uft','startech-20261030-v1').groups.reduce((n,g)=>n+g.count,0),48);
 const p=hardwareProfile(key,revision);assert.equal(p.sizeU,1);assert.equal(p.heightMm,43.9);assert.equal(p.groups.reduce((n,g)=>n+g.count,0),29);assert.equal(p.groups[2].powerRole,'inlet');
 assert.deepEqual(hardwareCreateCommand({profileKey:key,profileVersion:revision,rackId:'r',name:'Aruba Ω'},{racks:[{id:'r'}],devices:[]}).payload,{profileKey:key,profileVersion:revision,rackId:'r',name:'Aruba Ω'});
 assert.throws(()=>hardwareCreateCommand({profileKey:key,rackId:'r',name:'Wrong'},{racks:[{id:'r'}],devices:[]}));
});
test('two faces retain29UUIDs with repeated group ordinals and no input mutation',()=>{
 const d=model(),before=structuredClone(d),f=hardwareShellLayout(d,'front'),r=hardwareShellLayout(d,'rear');
 assert.equal(f.family,'aruba1930');assert.equal(f.ports.length,28);assert.equal(r.ports.length,1);assert.equal(r.ports[0],d.ports[28]);
 assert.notEqual(f.ports[0].id,f.ports[24].id);assert.equal(f.ports[0].gn,f.ports[24].gn);assert.deepEqual(d,before);assert.equal(Object.isFrozen(d.ports[0]),false);assert.ok(Object.isFrozen(f.ports));
});
test('wrong revision, adjacent PoE SKU, missing power role and inconsistent identities fall back without guessing',()=>{
 const changes=[d=>d.hardwareProfileVersion='latest',d=>d.hardwareIdentity.model='JL683A',d=>d.hardwareIdentity.sku='JL684A',d=>d.hardwareIdentity.manufacturer='Other',d=>d.u=2,d=>d.ports.pop(),d=>d.ports[28].rackclickPowerRole='outlet',d=>d.ports[28].rackclickPowerRole=undefined,d=>d.ports[24].rackclickFace='rear',d=>d.ports[24].type='rj45',d=>d.ports[0].gn=2,d=>d.ports[0].id=d.ports[1].id,d=>d.ports[0].groupId='mixed',d=>d.ports[0].rackclickPowerRole='inlet'];
 for(const change of changes){const d=model();change(d);const before=structuredClone(d);for(const side of ['front','rear'])assert.equal(hardwareShellLayout(d,side),null);assert.deepEqual(d,before);}
 assert.equal(hardwareShellLayout(model(),'side'),null);
});
