import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareCreateCommand,hardwareReference,mountOccupancy,validMounts,expandMountOrder} from '../src/hardware-mounting.ts';
import {validProject,projectToRc9} from '../src/inventory-model.ts';
const root=(id,key,sizeU,extra={})=>({id,hardwareProfileKey:key,sizeU,rackId:'rack',roomId:null,kind:'rackEquipment',name:id,properties:key?{hardwareProfileVersion:'hw-reference-v1'}:{},sortOrder:0,poeBudget:null,mountParentId:null,mountSlotKey:null,...extra});
function fixture(){return {customerId:'customer',revision:1,sites:[],buildings:[],rooms:[],racks:[{id:'rack',name:'Rack',roomId:null,sizeU:4,location:'',properties:{}}],devices:[root('shelf','shelf-2u',2),root('fw','desktop-firewall-6',0,{mountParentId:'shelf',mountSlotKey:'main'}),root('sw','switch-24',1),root('pp','patchpanel-24',1)],portGroups:[],ports:[],connections:[]};}
test('reference version clearly separates four synthetic profiles from historical presets',()=>{
 assert.equal(hardwareReference.version,'hw-reference-v1');assert.equal(hardwareReference.synthetic,true);assert.equal(hardwareReference.profiles.length,4);
 assert.equal(new Set(hardwareReference.profiles.map(p=>p.key)).size,4);
 assert.equal(hardwareReference.profiles.find(p=>p.key==='patchpanel-24').passthrough.tracingAvailable,false);
});
test('4U assembly reserves 2 + 0 + 1 + 1, preserving an independent child',()=>{
 const p=fixture();assert.equal(mountOccupancy(p.devices),4);assert.equal(validMounts(p.devices),true);assert.equal(validProject(p,'customer'),true);
 const projected=projectToRc9(p,'Client');assert.equal(projected.devices.get('fw').mountParentId,'shelf');assert.equal(projected.devices.get('fw').u,0);assert.equal(projected.racks[0].devs.length,4);
});
test('invalid mounts never become an accepted snapshot',()=>{
 for(const mutation of [p=>p.devices[1].mountParentId='absent',p=>p.devices[1].mountParentId='fw',p=>p.devices[1].rackId='other',p=>p.devices[1].mountSlotKey='other',p=>p.devices[1].sizeU=1,p=>p.devices[0].hardwareProfileKey='switch-24',p=>p.devices.push(root('fw2','desktop-firewall-6',0,{mountParentId:'shelf',mountSlotKey:'main'})),p=>p.devices[0].sizeU=0]){
  const p=fixture();mutation(p);assert.equal(validProject(p,'customer'),false);
 }
});
test('root hardware command carries no guessed parent or caller supplied dimensions',()=>{
 const p=fixture(),form={profileKey:'switch-24',rackId:'rack',name:'Keep my name',mountParentId:'stale',sizeU:900};
 assert.deepEqual(hardwareCreateCommand(form,p),{type:'device.createHardware',payload:{profileKey:'switch-24',profileVersion:'hw-reference-v1',rackId:'rack',name:'Keep my name'}});
});
test('desktop hardware requires an explicit shelf ID and slot, never a display name',()=>{
 const p=fixture();assert.deepEqual(hardwareCreateCommand({profileKey:'desktop-firewall-6',rackId:'rack',name:'Firewall',mountParentId:'shelf'},p).payload,{profileKey:'desktop-firewall-6',profileVersion:'hw-reference-v1',rackId:'rack',name:'Firewall',mountParentId:'shelf',mountSlotKey:'main'});
 for(const form of [{profileKey:'unknown',rackId:'rack'},{profileKey:'switch-24',rackId:'missing'},{profileKey:'desktop-firewall-6',rackId:'rack',mountParentId:'sw'},{profileKey:'desktop-firewall-6',rackId:'rack',mountParentId:'Shelf name'}])assert.throws(()=>hardwareCreateCommand(form,p));
});
test('front/rear template numbers repeat but instance UUIDs and group IDs do not',()=>{
 const p=fixture();p.portGroups=[{id:'gf',deviceId:'pp',type:'rj45',name:'Front',prefix:'F ',sortOrder:0},{id:'gr',deviceId:'pp',type:'rj45',name:'Rear',prefix:'R ',sortOrder:1}];
 p.ports=[{id:'pf',groupId:'gf',face:'front'},{id:'pr',groupId:'gr',face:'rear'}].map(v=>({...v,deviceId:'pp',type:'rj45',gn:1,sortOrder:0,label:'',status:'free',poe:false,watts:null,color:null,powerRole:'unspecified',properties:{}}));
 assert.equal(validProject(p,'customer'),true);const v=projectToRc9(p,'Client');assert.notEqual(v.serverEndpoints.pf,v.serverEndpoints.pr);assert.equal(v.devices.get('pp').ports.length,2);assert.equal(new Set(v.devices.get('pp').ports.map(p=>p.id)).size,2);
});
test('moving a visible root never swaps only with a hidden child',()=>{
 const devices=[root('shelf','shelf-2u',2),root('fw','desktop-firewall-6',0,{mountParentId:'shelf',mountSlotKey:'main'}),root('NAS',null,2)];
 assert.deepEqual(expandMountOrder(devices,['NAS','shelf']),['NAS','shelf','fw']);
 assert.deepEqual(expandMountOrder(devices,['shelf','NAS']),['shelf','fw','NAS']);
});
