import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {readFamilies,expectedReadPort} from '../src/inventory-read-views.ts';
import {prepareReport} from '../src/inventory-reports.ts';
import {configurationTypes,configurationFamily,newConfigurationPort,resizeConfigurationGroup,configurationDefinition,emptyConfiguration} from '../src/private-template-config-editor.ts';
import {validTemplateDefinition} from '../src/private-templates.ts';
import {defaultPortColors,validPortColors} from '../src/user-port-colors.ts';
import {validateChangePage} from '../src/client-changes.ts';
import {projectToRc9,batchPortIds} from '../src/inventory-model.ts';

const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(1),customer=id(2),device=id(3),group=id(4),port=id(5),rack=id(6);
const fresh=type=>({kind:'rackEquipment',sizeU:1,poeBudget:null,icon:'▦',color:'#64748b',visualFamily:'panel',portGroups:[{key:'g1',type,name:'Physical',prefix:'',sortOrder:0,ports:[{gn:1,sortOrder:0,type,label:'literal <img>',poe:false,color:null,face:'front',powerRole:'unspecified'}]}]});
const page=type=>({customerId:customer,currentRevision:5,nextRevision:5,hasMore:false,refreshRequired:false,events:[{id:id(10),actor:{id:actor,userNameCurrent:'Lab'},action:'inventory.ports.update',resourceId:device,revisionBefore:4,revisionAfter:5,occurredAt:'2026-11-01T01:23:45.123Z',context:{status:'captured',beforePorts:[{id:port,deviceId:device,groupId:group,type,gn:1}],afterPorts:[{id:port,deviceId:device,groupId:group,type,gn:1}],beforeConnections:[],afterConnections:[]}}]});
for(const type of ['sfp56','qsfpdd']){
 test(type+' is a distinct filter and report family without normalizing its request',()=>{
  assert.ok(readFamilies.includes(type));const api=Object.assign(new RackClickApi(),{actorId:actor});const f={reportKind:'ports',query:'',status:'all',family:type,rackId:null};const before=JSON.stringify(f);const prepared=prepareReport(api,actor,customer,7,f);assert.equal(prepared.body,before);assert.equal(JSON.stringify(f),before);
  for(const invalid of [type.toUpperCase(),type==='sfp56'?'sfp112':'qsfp-dd'])assert.throws(()=>prepareReport(api,actor,customer,7,{...f,family:invalid}));
 });
 test(type+' private template permits physical family but rejects PoE, power role and another cage family',()=>{
  const d=fresh(type);assert.equal(validTemplateDefinition(d),true);
  for(const mutate of [d=>d.portGroups[0].ports[0].poe=true,d=>d.portGroups[0].ports[0].powerRole='inlet',d=>d.portGroups[0].ports[0].type=type==='sfp56'?'sfp28':'qsfp']){const other=structuredClone(d);mutate(other);assert.equal(validTemplateDefinition(other),false)}
 });
 test(type+' editor adds a port in its exact family and retains current identifiers',()=>{
  assert.ok(configurationTypes.includes(type));assert.equal(configurationFamily(type),type);const first=newConfigurationPort(1,type);const g={key:'g1',type,name:'',prefix:'',sortOrder:0,ports:[first]};const resized=resizeConfigurationGroup(g,2);assert.equal(resized.ports[0].localId,first.localId);assert.equal(resized.ports[1].type,type);assert.equal(resized.ports[1].poe,false);assert.equal(resized.ports[1].powerRole,'unspecified');const d=configurationDefinition({...emptyConfiguration(),portGroups:[resized]});assert.equal(validTemplateDefinition(d),true);
 });
 test(type+' recorded port change preserves UUID group ordinal and rejects conversion to a prior optical type',()=>{
  const p=page(type);assert.deepEqual(validateChangePage(p,'"5"',customer,4),p);const wrong=structuredClone(p);wrong.events[0].context.afterPorts[0].type=type==='sfp56'?'sfp28':'qsfp';assert.throws(()=>validateChangePage(wrong,'"5"',customer,4));
 });
 test(type+' DTO projection preserves type, UUID, group, ordinal, face and role',()=>{
  const p={customerId:customer,revision:7,sites:[],buildings:[],rooms:[],racks:[{id:rack,name:'R',sizeU:42,roomId:null,location:''}],devices:[{id:device,name:'D',kind:'rackEquipment',rackId:rack,roomId:null,sizeU:1,sortOrder:0,properties:{}}],portGroups:[{id:group,deviceId:device,name:'G',prefix:'',type,sortOrder:0}],ports:[{id:port,deviceId:device,groupId:group,gn:1,sortOrder:0,type,label:'',status:'free',poe:false,watts:null,color:null,face:'rear',powerRole:'unspecified',properties:{}}],connections:[]};
  const before=JSON.stringify(p),v=projectToRc9(p,'Client'),q=v.devices.get(device).ports[0];assert.equal(q.id,port);assert.equal(q.groupId,group);assert.equal(q.type,type);assert.equal(q.gn,1);assert.equal(q.rackclickFace,'rear');assert.equal(q.rackclickPowerRole,'unspecified');assert.equal(batchPortIds(p,device,group,[port]).expectedType,type);assert.equal(expectedReadPort(p,port).family,type);assert.equal(JSON.stringify(p),before);
 });
}
test('personal palette retains ten prior defaults and accepts exactly three additional keys, including IDC',()=>{
 const before={rj45:'#3b82f6',rj45_poe:'#3b82f6',sfp:'#a855f7',sfp28:'#ef4444',qsfp:'#10b981',mgmt:'#f59e0b',console:'#6b7280',power:'#ef4444',usb_a:'#9ca3af',usb_c:'#9ca3af'};
 for(const [k,v] of Object.entries(before))assert.equal(defaultPortColors[k],v);assert.deepEqual(Object.keys(defaultPortColors).slice(0,10),Object.keys(before));assert.equal(Object.keys(defaultPortColors).length,23);assert.equal(defaultPortColors.sfp56,'#06b6d4');assert.equal(defaultPortColors.qsfpdd,'#f97316');assert.equal(defaultPortColors.idc,'#a3b86c');assert.equal(validPortColors(defaultPortColors),true);assert.equal(validPortColors({...defaultPortColors,qsfp112:'#123456'}),false);
});
