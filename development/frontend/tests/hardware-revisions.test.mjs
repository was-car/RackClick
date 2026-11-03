import test from 'node:test';
import assert from 'node:assert/strict';
import {createHardwareRegistry} from '../src/hardware-registry.ts';
import {hardwareReference,hardwareRegistry,hardwareProfile,hardwareCreateCommand} from '../src/hardware-mounting.ts';
import {projectToRc9} from '../src/inventory-model.ts';
const v1={version:'test-v1',profiles:[{key:'same-key',kind:'desktop',widthMm:220,heightMm:38,depthMm:200,groups:[{key:'front',count:6}]}]};
const v2={version:'test-v2',profiles:[{key:'same-key',kind:'rack',widthMm:400,heightMm:80,depthMm:300,groups:[{key:'front',count:24}]}]};
test('two revisions of one model remain distinct regardless of registration order',()=>{
 for(const definitions of [[v1,v2],[v2,v1]]){
  const registry=createHardwareRegistry(definitions);assert.equal(registry.find('same-key','test-v1').groups[0].count,6);assert.equal(registry.find('same-key','test-v2').groups[0].count,24);
  for(const version of [undefined,null,'latest','unknown','TEST-V1','test-v1 '])assert.equal(registry.find('same-key',version),undefined);
 }
});
test('duplicate key/revision is rejected instead of overwriting an accepted definition',()=>{
 assert.throws(()=>createHardwareRegistry([v1,structuredClone(v1)]),/duplicate_revision/);
});
test('catalogue snapshots resist changes through source data and nested exposed arrays',()=>{
 const input=structuredClone(v1),registry=createHardwareRegistry([input]);input.profiles[0].widthMm=999;input.profiles[0].groups[0].count=99;
 const actual=registry.find('same-key','test-v1');assert.equal(actual.widthMm,220);assert.equal(actual.groups[0].count,6);
 assert.throws(()=>actual.groups[0].count=99,TypeError);assert.throws(()=>registry.catalogues[0].profiles.push({key:'bad'}),TypeError);assert.throws(()=>registry.catalogues[0].version='bad',TypeError);
});
test('product v1 reference is frozen and exact revision is required for its lookup',()=>{
 assert.equal(hardwareProfile('desktop-firewall-6','hw-reference-v1').heightMm,38);assert.equal(hardwareProfile('desktop-firewall-6',null),undefined);assert.equal(hardwareProfile('desktop-firewall-6','hw-reference-v2'),undefined);
 assert.equal(hardwareRegistry.catalogues.length,29);assert.equal(hardwareReference.profiles.length,4);assert.equal(hardwareReference.version,'hw-reference-v1');assert.throws(()=>hardwareReference.profiles[0].slot.heightMm=999,TypeError);
});
test('new requests carry an exact revision; missing old form remains pinned to v1',()=>{
 const project={racks:[{id:'r'}],devices:[]},form={profileKey:'switch-24',rackId:'r',name:'Switch'};
 assert.equal(hardwareCreateCommand(form,project).payload.profileVersion,'hw-reference-v1');assert.equal(hardwareCreateCommand({...form,profileVersion:'hw-reference-v1'},project).payload.profileVersion,'hw-reference-v1');
 for(const profileVersion of [null,undefined,'','latest','hw-reference-v2'])assert.throws(()=>hardwareCreateCommand({...form,profileVersion},project));
});
test('projection retains recorded version/dimensions without substituting a current template',()=>{
 const project={customerId:'c',revision:1,sites:[],buildings:[],rooms:[],racks:[{id:'r',name:'R',sizeU:4,roomId:null,location:''}],devices:[{id:'d',name:'Recorded',kind:'rackEquipment',rackId:'r',roomId:null,sizeU:1,sortOrder:0,poeBudget:null,hardwareProfileKey:'same-key',properties:{hardwareProfileVersion:'test-v1',physicalDimensionsMm:{width:220,height:38,depth:200}}}],portGroups:[],ports:[],connections:[]};
 const result=projectToRc9(project,'Client').devices.get('d');assert.equal(result.hardwareProfileVersion,'test-v1');assert.deepEqual(result.physicalDimensionsMm,{width:220,height:38,depth:200});result.physicalDimensionsMm.width=999;assert.equal(project.devices[0].properties.physicalDimensionsMm.width,220);
 project.devices[0].properties.hardwareProfileVersion='unavailable';assert.equal(projectToRc9(project,'Client').devices.get('d').hardwareProfileVersion,'unavailable');
 project.devices[0].properties.physicalDimensionsMm.width='<img>';assert.equal(projectToRc9(project,'Client').devices.get('d').physicalDimensionsMm,null);
});
