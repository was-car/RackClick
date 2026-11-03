import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {connectorDescriptors,recordedConnectorDescriptor,connectorDescriptorLabel} from '../src/hardware-connector-classification.mjs';
import {extendRc9ConnectorContract} from '../src/connector-contract-family.mjs';
import {extendRc9ConnectorContract as seven} from '../src/connector-contract7.mjs';
const {buildSync}=createRequire(import.meta.url)('esbuild');
const dir=fileURLToPath(new URL('../src/',import.meta.url));
const React={Fragment:'fragment',createElement:(type,props,...children)=>({type,props:props||{},children})};
function load(contents,resolveDir=dir){const code=buildSync({stdin:{contents,resolveDir,loader:'jsx'},bundle:true,format:'cjs',write:false,target:'es2020'}).outputFiles[0].text;const module={exports:{}};vm.runInNewContext(code,{module,exports:module.exports,React,structuredClone,Object});return module.exports;}
function resolve(x){if(Array.isArray(x))return x.map(resolve);if(!x||typeof x!=='object')return x;if(typeof x.type==='function')return resolve(x.type({...x.props,children:x.children}));return {type:x.type,props:x.props,children:(x.children||[]).map(resolve)};}
const plain=x=>JSON.parse(JSON.stringify(x)),nodes=x=>[x,...(x?.children||[]).flat(Infinity).filter(n=>n&&typeof n==='object').flatMap(nodes)];
const shape=load("export {FamilyConnectorShape} from './FamilyConnectorShape.jsx';").FamilyConnectorShape;
test('23 descriptors are a closed typed classification, not aliases for Ethernet',()=>{
 assert.equal(Object.values(connectorDescriptors).flat().length,23);
 for(const [type,descriptors] of Object.entries(connectorDescriptors))for(const descriptor of descriptors){
  const tree=resolve(shape({type,physicalConnector:descriptor}));assert.equal(tree.props['data-physical-media'],type);assert.equal(tree.props['data-hardware-connector'],descriptor);assert.equal(tree.props['data-connector-known'],'true');
  assert.equal(nodes(tree).some(n=>n.props?.['data-physical-media']==='rj45'),false);
 }
 assert.ok(Object.isFrozen(connectorDescriptors.power));
});
test('frontend, domain, SQL and approved family contract share exactly the same 23 forms',()=>{
 const contract=JSON.parse(readFileSync(new URL('../../../evidence/s1-20261101/integracion506k/contract/CONTRATO-K.json',import.meta.url),'utf8'));
 assert.deepEqual(connectorDescriptors,contract.physicalConnector.allowedByRawType);
 const expected=Object.values(connectorDescriptors).flat().sort();
 for(const name of ['../../server/src/RackClick.Domain/PhysicalConnectors.cs','../../server/database/040-hardware-families.sql']){
  const text=readFileSync(new URL(name,import.meta.url),'utf8'),forms=[...new Set(text.match(/\b(?:iec-c(?:13|14|19|20)|iec60309-[a-z0-9-]+|nema-[a-z0-9-]+|serial-[a-z0-9-]+|idc-(?:110|dual-110-krone))\b/g))].sort();
  assert.deepEqual(forms,expected,name);
 }
});
test('serial ten-contact socket has ten visible contacts, DE9 nine and RJ12 six',()=>{
 for(const [pc,count] of [['serial-10p10c',10],['serial-8p8c',8],['serial-rj12',6]]){
  const tree=resolve(shape({type:'console',physicalConnector:pc}));assert.equal(nodes(tree).filter(n=>n.type==='path'&&n.props.stroke==='#d9c47e').length,count);
 }
 assert.equal(nodes(resolve(shape({type:'console',physicalConnector:'serial-de9'}))).filter(n=>n.type==='circle').length,9);
});
test('unknown and wrongly typed descriptors never produce a falsely precise connector',()=>{
 assert.equal(shape({type:'power',physicalConnector:'serial-8p8c'}),null);
 const serial=resolve(shape({type:'console',physicalConnector:'iec-c14'}));assert.equal(serial.props['data-connector-known'],'false');assert.equal(serial.props['data-hardware-connector'],'console');
 const idc=resolve(shape({type:'idc',physicalConnector:null}));assert.equal(idc.props['data-hardware-connector'],'idc');
 assert.equal(connectorDescriptorLabel('console','serial-10p10c'),'SERIAL 10P10C');
});
test('catalogue classification requires a known revision, same group, media, face and reserved value',()=>{
 const d={hardwareProfileKey:'test',properties:{hardwareProfileVersion:'reviewed'}};
 const p={type:'console',face:'rear',properties:{hardwareGroupKey:'serial',hardwarePhysicalConnector:'serial-10p10c'}};
 const profile={key:'test',groups:[{key:'serial',type:'console',face:'rear',physicalConnector:'serial-10p10c'}]};
 const find=(key,revision)=>key==='test'&&revision==='reviewed'?profile:undefined;
 assert.equal(recordedConnectorDescriptor(d,p,find),'serial-10p10c');
 for(const changed of [{...d,hardwareProfileKey:null},{...d,properties:{}},{...d,properties:{hardwareProfileVersion:'missing'}}])assert.equal(recordedConnectorDescriptor(changed,p,find),null);
 for(const changed of [{...p,type:'rj45'},{...p,face:'front'},{...p,properties:{...p.properties,hardwareGroupKey:'other'}},{...p,properties:{...p.properties,hardwarePhysicalConnector:'serial-8p8c'}}])assert.equal(recordedConnectorDescriptor(d,changed,find),null);
 assert.equal(recordedConnectorDescriptor({...d,hardwareProfileKey:'legacy'},p,find),null);
});
test('family adaptation preserves all seven-media metadata and glyphs; only IDC is added',()=>{
 const source=readFileSync(new URL('../rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/evidence/integrated-source.jsx',import.meta.url),'utf8');
 const meta=source.slice(source.indexOf('const PT ='),source.indexOf('const ICONS =')),start=source.indexOf('function IRPortShape({type,role}){'),physical=source.slice(start,source.indexOf('\n',start));
 const resolveDir=fileURLToPath(new URL('../generated/',import.meta.url));
 const construct=fn=>{const a=fn(meta,physical);return load(a.metadataSource+'\n'+a.physicalSource+'\nmodule.exports={PT,IRPortShape};',resolveDir);};
 const old=construct(seven),now=construct(extendRc9ConnectorContract);
 assert.deepEqual(Object.keys(now.PT),[...Object.keys(old.PT),'idc']);
 for(const type of Object.keys(old.PT)){
  assert.deepEqual(plain(now.PT[type]),plain(old.PT[type]));
  for(const role of ['inlet','outlet','unspecified'])assert.deepEqual(plain(resolve(now.IRPortShape({type,role}))),plain(resolve(old.IRPortShape({type,role}))));
 }
 assert.equal(resolve(now.IRPortShape({type:'idc'})).props['data-physical-media'],'idc');
});
test('legacy batch glyphs retain bytes-equivalent trees; new console and IDC do not fall back to RJ45',()=>{
 const {BatchSocket}=load("export {BatchSocket} from './BatchHardwareFace.jsx';");
 const baseline=JSON.parse(readFileSync(new URL('./fixtures/connector-contract7-legacy-sockets.json',import.meta.url),'utf8'));
 for(const type of ['rj45','sfp','sfp28','qsfp','power'])assert.deepEqual(plain(resolve(BatchSocket({type}))),baseline.sockets[type]);
 for(const type of ['console','idc'])assert.equal(resolve(BatchSocket({type})).props['data-physical-media'],type);
 const inlet=plain(resolve(BatchSocket({type:'power',physicalConnector:'iec-c14'}))),outlet=plain(resolve(BatchSocket({type:'power',physicalConnector:'iec-c13'})));assert.notDeepEqual(inlet,outlet);
});
test('creation preview exposes exact population and dimensional caveats inside a closed disclosure',()=>{
 const {HardwareCreationFields}=load("export {HardwareCreationFields} from './HardwareCreationFields.jsx';");
 const form={profileKey:'selected-nb-47531f3ce888df83',profileVersion:'selected506j-20261101-v1',rackId:'rack',name:''};
 for(const lang of ['en','de','es']){
  const tree=HardwareCreationFields({form,setForm:()=>{},project:{devices:[],racks:[{id:'rack',name:'rack'}]},lang,disabled:false});
  const all=nodes(tree),details=all.find(n=>n.props?.['data-hardware-preview']!==undefined);assert.ok(details);assert.notEqual(details.props.open,true);
  const configuration=nodes(details).find(n=>n.props?.['data-hardware-configuration']!==undefined);assert.ok(configuration);assert.ok(JSON.stringify(configuration).includes('48 CC688BL'));
  assert.ok(nodes(details).some(n=>n.props?.['data-hardware-review-limits']!==undefined));
 }
});
