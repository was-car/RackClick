import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {additionalConnectorMetadata,extendRc9ConnectorContract,physicalConnectorLabel} from '../src/connector-contract7.mjs';
const {buildSync}=createRequire(import.meta.url)('esbuild');
const directory=fileURLToPath(new URL('../src/',import.meta.url)),generated=fileURLToPath(new URL('../generated/',import.meta.url));
const source=readFileSync(new URL('../rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/evidence/integrated-source.jsx',import.meta.url),'utf8');
const metadata=source.slice(source.indexOf('const PT ='),source.indexOf('const ICONS ='));
const start=source.indexOf('function IRPortShape({type,role}){'),oldShape=source.slice(start,source.indexOf('\n',start));
const React={Fragment:'fragment',createElement:(type,props,...children)=>({type,props:props||{},children})};
function load(contents,resolveDir=directory){const code=buildSync({stdin:{contents,resolveDir,loader:'jsx'},bundle:true,format:'cjs',write:false,target:'es2020'}).outputFiles[0].text;const module={exports:{}};vm.runInNewContext(code,{module,exports:module.exports,React});return module.exports;}
function resolve(x){if(Array.isArray(x))return x.map(resolve);if(!x||typeof x!=='object')return x;if(typeof x.type==='function')return resolve(x.type({...x.props,children:x.children}));return {type:x.type,props:{...x.props},children:(x.children||[]).map(resolve)};}
const plain=x=>JSON.parse(JSON.stringify(resolve(x))),nodes=x=>[x,...(x?.children||[]).flat(Infinity).filter(x=>x&&typeof x==='object').flatMap(nodes)];
const old=load(metadata+'\n'+oldShape+'\nmodule.exports={PT,IRPortShape};');
const adapted=extendRc9ConnectorContract(metadata,oldShape);
const current=load(adapted.metadataSource+'\n'+adapted.physicalSource+'\nmodule.exports={PT,IRPortShape};',generated);
const batch=load(readFileSync(path.join(directory,'BatchHardwareFace.jsx'),'utf8'));
const batchSocket=type=>plain(batch.BatchSocket({type}));
const generic=type=>plain(current.IRPortShape({type,role:'unspecified'}));

test('RC9 metadata adaptation preserves every original value and order, adds only SFP56 and QSFP-DD',()=>{
 assert.deepEqual(Object.keys(current.PT),[...Object.keys(old.PT),'sfp56','qsfpdd']);
 for(const key of Object.keys(old.PT))assert.deepEqual(JSON.parse(JSON.stringify(current.PT[key])),JSON.parse(JSON.stringify(old.PT[key])));
 assert.equal(current.PT.sfp56.label,'SFP56');assert.equal(current.PT.qsfpdd.label,'QSFP-DD');assert.equal(physicalConnectorLabel('qsfpdd'),'QSFP-DD');assert.equal(physicalConnectorLabel('sfp56'),'SFP56');assert.equal(physicalConnectorLabel('sfp28'),'sfp28');
 assert.ok(Object.isFrozen(additionalConnectorMetadata));assert.ok(!('poe' in additionalConnectorMetadata.sfp56));assert.ok(!('speed' in additionalConnectorMetadata.qsfpdd));
});
test('generic old glyphs remain structurally identical for all ten prior types and power roles',()=>{
 for(const type of Object.keys(old.PT))for(const role of ['unspecified','inlet','outlet'])assert.deepEqual(genericWithRole(type,role),plain(old.IRPortShape({type,role})),type+role);
 function genericWithRole(type,role){return plain(current.IRPortShape({type,role}));}
});
for(const type of ['sfp56','qsfpdd'])test(type+' generic and chassis glyph have exact DOM identity and visible distinct marker',()=>{
 for(const node of [generic(type),batchSocket(type)]){
  const marked=nodes(node).filter(n=>n.props?.['data-physical-media']===type);assert.equal(marked.length,1);assert.equal(marked[0].props['data-hardware-connector'],type);
  assert.ok(nodes(node).some(n=>n.type==='text'&&n.children.includes(type==='sfp56'?'56':'DD')));
  assert.ok(nodes(node).some(n=>n.type==='rect'&&n.props.fill==='#101923'));
 }
});
for(const [left,right] of [['sfp','sfp28'],['sfp28','sfp56'],['qsfp','qsfpdd']])test('chassis glyph pair '+left+'/'+right+' is distinguishable without changing types',()=>{
 assert.notDeepEqual(batchSocket(left),batchSocket(right));
 if(['sfp56','qsfpdd'].includes(right))assert.notDeepEqual(generic(left),generic(right));
});
test('adaptation rejects missing or duplicate anchors instead of silently losing glyph integration',()=>{
 for(const [meta,physical] of [['',oldShape],[metadata,''],[metadata,oldShape+oldShape],[metadata+metadata,oldShape]])assert.throws(()=>extendRc9ConnectorContract(meta,physical),/anchor mismatch/);
});
test('batch prior glyphs are identical against the saved pre-change source',()=>{
 const baseline=JSON.parse(readFileSync(new URL('./fixtures/connector-contract7-legacy-sockets.json',import.meta.url),'utf8'));
 assert.equal(baseline.recordedBeforeChange,true);
 for(const type of ['rj45','sfp','sfp28','qsfp','power'])assert.deepEqual(batchSocket(type),baseline.sockets[type],type);
});
