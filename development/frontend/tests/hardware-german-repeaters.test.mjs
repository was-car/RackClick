import test from 'node:test';
import assert from 'node:assert/strict';
import catalogues from '../src/hardware-german-repeaters.generated.json' with {type:'json'};
import {hardwareChoices,hardwareProfile,hardwareCreateCommand} from '../src/hardware-mounting.ts';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {validConnectorDescriptor} from '../src/hardware-connector-classification.mjs';
import {verifyGermanRepeatersHardwareCatalog} from '../verify-hardware-catalog.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const models=catalogues.flatMap(c=>c.profiles.map(p=>({...p,revision:c.version})));
function device(p){return {hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:{...p.identity},u:null,mountParentId:null,mountSlotKey:null,ports:p.groups.flatMap((g,index)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+(i+1),groupId:'g'+index,type:g.type,gn:i+1,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPowerRole:g.powerRole,rackclickPhysicalConnector:g.physicalConnector??null,rackclickPhysicalFace:g.physicalFace??null,rackclickInterfaceRole:g.interfaceRole??null,rackclickSignalRole:g.signalRole??null,rackclickPowerSystem:g.powerSystem??null,label:'',status:'free'})))}}
test('ten new repeaters extend874 historical definitions to884',()=>{
 assert.equal(models.length,10);assert.equal(hardwareChoices.length,884);
 for(const p of models){assert.equal(hardwareProfile(p.key,p.revision).identity.sku,p.identity.sku);assert.equal(hardwareProfile(p.key,'latest'),undefined)}
});
test('20 faces map23 real UUID endpoints once and preserve saved objects',()=>{
 let count=0;
 for(const p of models){const d=device(p),before=structuredClone(d);
  for(const face of ['front','rear']){const layout=hardwareShellLayout(d,face);assert.ok(layout,p.key+'/'+face);assert.equal(layout.sockets.length,face==='front'?0:d.ports.length);for(const s of layout.sockets){assert.ok(d.ports.includes(s.port));count++}}
  assert.deepEqual(d,before);
 }assert.equal(count,23);
});
test('600 exposes power only; radios and LEDs never become network endpoints',()=>{
 const p=models.find(p=>p.key==='fritz-repeater600-de');assert.deepEqual(p.groups.map(g=>g.type),['power']);assert.equal(hardwareShellLayout(device(p),'rear').sockets.length,1);
 for(const p of models)assert.ok(p.groups.every(g=>['rj45','power','power_dc'].includes(g.type)));
});
test('all ten create in a room without rack parent or U',()=>{
 const project={rooms:[{id:'room'}],devices:[],racks:[]};
 for(const p of models){const command=hardwareCreateCommand({profileKey:p.key,profileVersion:p.revision,roomId:'room',name:p.identity.model},project);assert.equal(command.type,'device.createHardware');assert.equal(command.payload.roomId,'room');for(const key of ['rackId','mountParentId','mountSlotKey','sizeU'])assert.equal(command.payload[key],undefined);assert.throws(()=>hardwareCreateCommand({profileKey:p.key,profileVersion:p.revision,rackId:'rack',name:p.identity.model},project))}
});
test('tabletop or wall geometry rejects false rack U, identity, version and missing endpoints',()=>{
 for(const p of models)for(const mutate of [d=>d.u=0,d=>d.hardwareProfileVersion='other',d=>d.hardwareIdentity.sku='other',d=>d.ports.pop(),d=>d.ports[0].id='',d=>d.mountParentId='shelf']){const d=device(p);mutate(d);assert.equal(hardwareShellLayout(d,'rear'),null,p.key)}
});
test('EU plug classification is power only; no false data or DC classification',()=>{
 assert.equal(validConnectorDescriptor('power','eu-2pin-plug'),true);for(const type of ['rj45','power_dc','usb_a','console'])assert.equal(validConnectorDescriptor(type,'eu-2pin-plug'),false);assert.equal(validConnectorDescriptor('telephony','voice-tae'),true);
});
test('manifest and all closed source/output hashes verify',async()=>{await verifyGermanRepeatersHardwareCatalog(path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'))});
