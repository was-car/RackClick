import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {extendedConnectorDescriptors,extendedConnectorMetadata} from '../src/hardware-connector-family-l.mjs';
import {validConnectorDescriptor,connectorDescriptors} from '../src/hardware-connector-classification.mjs';
const {buildSync}=createRequire(import.meta.url)('esbuild');
const React={Fragment:'fragment',createElement:(type,props,...children)=>({type,props:props||{},children})};
const resolve=x=>Array.isArray(x)?x.map(resolve):!x||typeof x!=='object'?x:typeof x.type==='function'?resolve(x.type({...x.props,children:x.children})):{...x,children:x.children?.map(resolve)};
function load(){const code=buildSync({stdin:{contents:"export {BatchSocket} from './BatchHardwareFace.jsx';",resolveDir:fileURLToPath(new URL('../src/',import.meta.url)),loader:'jsx'},bundle:true,format:'cjs',write:false}).outputFiles[0].text;const module={exports:{}};vm.runInNewContext(code,{module,exports:module.exports,React,Object});return module.exports.BatchSocket;}
const shape=load();
test('L vocabulary is preserved with exactly the two reviewed German45 connector additions',()=>{
 const contract=JSON.parse(readFileSync(new URL('../../../tools/hardware_family_l_contract.json',import.meta.url),'utf8'));
 const expected={...contract.typeDescriptors,
  power:[...contract.typeDescriptors.power,'eu-2pin-plug'],
  telephony:[...contract.typeDescriptors.telephony,'voice-tae']};
 assert.deepEqual(extendedConnectorDescriptors,expected);
 assert.deepEqual(Object.keys(extendedConnectorMetadata),contract.additionalHardwareTypes);
});
test('L extends rather than rewrites the 23 K physical descriptors',()=>{
 assert.equal(Object.values(connectorDescriptors).flat().length,23);
 for(const [type,values] of Object.entries(extendedConnectorDescriptors))for(const value of values){
  assert.equal(validConnectorDescriptor(type,value),true);
  for(const other of Object.keys(extendedConnectorMetadata).filter(other=>other!==type))assert.equal(validConnectorDescriptor(other,value),false);
 }
 assert.equal(validConnectorDescriptor('rj45','unifi-smartpower'),false);
 assert.equal(validConnectorDescriptor('power','usb-c-pd'),false);
 assert.equal(validConnectorDescriptor('fiber','lc-unknown'),false);
});
test('every L media has its own drawing and keeps its explicit type',()=>{
 for(const type of Object.keys(extendedConnectorMetadata)){
  const tree=resolve(shape({type}));
  assert.equal(tree.props['data-physical-media'],type);
  assert.equal(tree.props['data-hardware-connector'],type);
 }
 for(const [type,values] of Object.entries(extendedConnectorDescriptors))for(const physicalConnector of values){
  const tree=resolve(shape({type,physicalConnector}));
  assert.equal(tree.props['data-physical-media'],type);
  assert.equal(tree.props['data-hardware-connector'],physicalConnector);
  assert.equal(tree.props['data-connector-known'],'true');
 }
});
test('LC, SC, SAS, SmartPower and USB-PD are visibly different drawings',()=>{
 const examples=[['fiber','lc-simplex-upc'],['fiber','lc-duplex-upc'],['fiber','sc-simplex-apc'],['sas','sff-8644'],['power_dc','unifi-smartpower'],['power_dc','usb-c-pd']];
 const trees=examples.map(([type,physicalConnector])=>JSON.stringify(resolve(shape({type,physicalConnector})).children));
 assert.equal(new Set(trees).size,examples.length);
});
