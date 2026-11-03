import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareChoices,hardwareProfile,hardwareCreateCommand,mountOccupancy,validMounts} from '../src/hardware-mounting.ts';
import {validProject,projectToRc9} from '../src/inventory-model.ts';
const key='fortinet-fg60f',revision='fortinet-20261030-v1';
const root=(id,k,u,extra={})=>({id,name:id,kind:'rackEquipment',rackId:'r',roomId:null,sizeU:u,sortOrder:0,poeBudget:null,hardwareProfileKey:k,properties:{hardwareProfileVersion:k===key?revision:'hw-reference-v1'},...extra});
function project(){return {customerId:'c',revision:1,sites:[],buildings:[],rooms:[],racks:[{id:'r',name:'Rack',sizeU:4,roomId:null,properties:{}}],devices:[root('s','shelf-2u',2),root('fg',key,0,{mountParentId:'s',mountSlotKey:'main'})],portGroups:[],ports:[],connections:[]};}
function device(){return {hardwareProfileKey:key,hardwareProfileVersion:revision,hardwareIdentity:{manufacturer:'Fortinet',family:'FortiGate 60F Series',model:'FortiGate 60F',sku:'FG-60F'},u:0,mountParentId:'s',mountSlotKey:'main',ports:[['rear-lan',5],['rear-fortilink',2],['rear-dmz',1],['rear-wan',2]].flatMap(([group,count])=>Array.from({length:count},(_,i)=>({id:group+'-'+i,groupId:group,rackclickHardwareGroupKey:group,type:'rj45',gn:i+1,rackclickFace:'rear',rackclickPowerRole:'unspecified',label:''})))};}

test('FG-60F is a distinct exact desktop model, not generic firewall or 61F/WiFi',()=>{
 const p=hardwareProfile(key,revision);assert.equal(hardwareChoices.length,884);assert.equal(p.kind,'desktop');assert.equal(p.sizeU,0);assert.deepEqual([p.widthMm,p.heightMm,p.depthMm],[216,38.5,160]);assert.equal(p.groups.reduce((n,g)=>n+g.count,0),10);assert.ok(p.groups.every(g=>g.face==='rear'&&g.type==='rj45'));
 for(const version of [null,undefined,'latest','fortinet-20261030-v2','hw-reference-v1'])assert.equal(hardwareProfile(key,version),undefined);
 assert.equal(hardwareProfile('desktop-firewall-6','hw-reference-v1').groups.reduce((n,g)=>n+g.count,0),7);
});
test('Fortinet shape has zero front sockets, ten rear original IDs and no caller mutation',()=>{
 const d=device(),before=structuredClone(d),front=hardwareShellLayout(d,'front'),rear=hardwareShellLayout(d,'rear');assert.equal(front.family,'fortigate60f');assert.equal(front.ports.length,0);assert.equal(rear.ports.length,10);assert.deepEqual(d,before);assert.throws(()=>rear.ports.pop(),TypeError);assert.equal(new Set(rear.ports.map(p=>p.id)).size,10);assert.equal(rear.ports.filter(p=>p.gn===1).length,4);
});
test('Fortinet shell rejects mismatched identity, face, mounting, topology and group keys',()=>{
 for(const mutate of [d=>d.hardwareProfileVersion='latest',d=>d.hardwareIdentity.sku='FG-61F',d=>d.hardwareIdentity.model='FortiWiFi 60F',d=>d.hardwareIdentity.manufacturer='other',d=>d.u=1,d=>d.mountParentId=null,d=>d.mountSlotKey='other',d=>d.ports.pop(),d=>d.ports[0].id=d.ports[1].id,d=>d.ports[0].rackclickHardwareGroupKey='rear-wan',d=>d.ports[0].groupId='rear-wan',d=>d.ports[0].rackclickFace='front',d=>d.ports[0].type='power',d=>d.ports[0].rackclickPowerRole='inlet',d=>d.ports[0].gn=2]){
  const d=device();mutate(d);for(const face of ['front','rear'])assert.equal(hardwareShellLayout(d,face),null);
 }
 assert.equal(hardwareShellLayout(device(),'side'),null);
});
test('recorded FG child is accepted on a shelf; unavailable revisions stay recorded and generic',()=>{
 const p=project();assert.equal(validProject(p,'c'),true);assert.equal(validMounts(p.devices),true);assert.equal(mountOccupancy(p.devices),2);
 p.devices[1].properties.hardwareProfileVersion='unavailable';assert.equal(validProject(p,'c'),true);const d=projectToRc9(p,'C').devices.get('fg');assert.equal(d.hardwareProfileVersion,'unavailable');assert.equal(hardwareShellLayout(d,'rear'),null);
 for(const mutate of [p=>p.devices[1].mountParentId='missing',p=>p.devices[1].mountSlotKey='other',p=>p.devices[1].sizeU=1,p=>p.devices[1].rackId='other',p=>p.devices[0].hardwareProfileKey='switch-24',p=>p.devices.push({...p.devices[1],id:'second'})]){const x=project();mutate(x);assert.equal(validProject(x,'c'),false);assert.equal(validMounts(x.devices),false);}
});
test('creation carries explicit shelf and revision without accepting form dimensions',()=>{
 const p=project(),f={profileKey:key,profileVersion:revision,name:'FG Ω',rackId:'r',mountParentId:'s',sizeU:5};assert.deepEqual(hardwareCreateCommand(f,p).payload,{profileKey:key,profileVersion:revision,name:'FG Ω',rackId:'r',mountParentId:'s',mountSlotKey:'main'});
 for(const m of [{mountParentId:''},{mountParentId:'fg'},{profileVersion:null},{profileVersion:'latest'}])assert.throws(()=>hardwareCreateCommand({...f,...m},p));
});
test('projection preserves group identity independently from editable names and repeated gn',()=>{
 const p=project();p.portGroups=[{id:'wan',deviceId:'fg',type:'rj45',name:'renamed',prefix:'same',sortOrder:0},{id:'lan',deviceId:'fg',type:'rj45',name:'renamed',prefix:'same',sortOrder:1}];
 p.ports=['wan','lan'].map(group=>({id:'p-'+group,deviceId:'fg',groupId:group,type:'rj45',gn:1,sortOrder:0,label:'',status:'free',poe:false,watts:null,color:null,face:'rear',powerRole:'unspecified',properties:{hardwareGroupKey:'rear-'+group}}));
 const ports=projectToRc9(p,'C').devices.get('fg').ports;assert.equal(ports.find(p=>p.id==='p-wan').rackclickHardwareGroupKey,'rear-wan');assert.equal(ports.find(p=>p.id==='p-lan').rackclickHardwareGroupKey,'rear-lan');assert.notEqual(ports[0].id,ports[1].id);
});
