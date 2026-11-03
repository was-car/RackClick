import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareChoices,hardwareChoiceValue,hardwareProfile,hardwareCreateCommand,hardwareReference} from '../src/hardware-mounting.ts';
import {hardwareWords,profileLabel} from '../src/hardware-words.ts';
import {projectToRc9} from '../src/inventory-model.ts';

test('commercial choice is an exact key/revision pair beside unchanged references',()=>{
 assert.equal(hardwareReference.profiles.length,4);assert.equal(hardwareChoices.length,884);
 const model=hardwareChoices.find(p=>p.key==='startech-c6panelutp241uft');
 assert.equal(model.revision,'startech-20261030-v1');assert.equal(model.heightMm,44.3);
 assert.equal(model.groups.reduce((sum,g)=>sum+g.count,0),48);
 assert.equal(hardwareChoiceValue(model),JSON.stringify([model.key,model.revision]));
 assert.equal(hardwareProfile(model.key,'hw-reference-v1'),undefined);
 assert.equal(hardwareProfile(model.key,'latest'),undefined);
 assert.equal(Object.isFrozen(model.identity),true);
 for(const words of Object.values(hardwareWords)) assert.equal(profileLabel(model,words),'StarTech.com · C6PANELUTP241UFT');
});
test('commercial creation requires explicit revision and never invents a shelf',()=>{
 const project={racks:[{id:'rack'}],devices:[]};
 const form={profileKey:'startech-c6panelutp241uft',profileVersion:'startech-20261030-v1',rackId:'rack',name:'Mi panel Ω'};
 assert.deepEqual(hardwareCreateCommand(form,project),{type:'device.createHardware',payload:form});
 const legacy={...form};delete legacy.profileVersion;assert.throws(()=>hardwareCreateCommand(legacy,project));
});
test('recorded identity and fractional dimensions survive projection without remote images',()=>{
 const identity={manufacturer:'StarTech.com',family:'Cat6 feed-through',model:'C6PANELUTP241UFT',sku:'C6PANELUTP241UFT'};
 const snapshot={customerId:'c',revision:0,sites:[],buildings:[],rooms:[],racks:[{id:'r',name:'Rack',sizeU:4,properties:{}}],devices:[{id:'d',kind:'rackEquipment',rackId:'r',roomId:null,name:'My panel',sizeU:1,sortOrder:0,poeBudget:null,hardwareProfileKey:'startech-c6panelutp241uft',mountParentId:null,mountSlotKey:null,properties:{hardwareIdentity:identity,hardwareProfileVersion:'startech-20261030-v1',physicalDimensionsMm:{width:483,height:44.3,depth:138}}}],portGroups:[],ports:[],connections:[]};
 const device=projectToRc9(snapshot,'Customer').devices.get('d');
 assert.deepEqual(device.hardwareIdentity,identity);assert.notEqual(device.hardwareIdentity,identity);
 assert.equal(device.physicalDimensionsMm.height,44.3);assert.equal('image' in device,false);
});
