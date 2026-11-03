import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
const {buildSync}=createRequire(import.meta.url)('esbuild');
// The override is only a test fixture seam for the retained pre-change source.
const filename=process.env.RACKCLICK_SOCKET_REVIEW_SOURCE||fileURLToPath(new URL('../src/BatchHardwareFace.jsx',import.meta.url));
const compiled=buildSync({stdin:{contents:readFileSync(filename,'utf8'),resolveDir:path.dirname(filename),loader:'jsx'},bundle:true,format:'cjs',write:false,target:'es2020'}).outputFiles[0].text;
const module={exports:{}},React={createElement:(type,props,...children)=>({type,props:props||{},children})};
vm.runInNewContext(compiled,{module,exports:module.exports,React});
const socket=type=>JSON.parse(JSON.stringify(module.exports.BatchSocket({type})));
const nodes=element=>[element,...(element.children||[]).flat(Infinity).filter(c=>c&&typeof c==='object').flatMap(nodes)];
test('SFP28 is an optical cage with its own type, never the copper fallback',()=>{
 const s=socket('sfp28');assert.equal(s.props['data-hardware-connector'],'sfp28');
 assert.equal(s.type,'svg');assert.ok(nodes(s).some(n=>n.type==='text'&&n.children.includes('28')));
 assert.notDeepEqual(s,socket('rj45'));
});
test('QSFP retains a wider physical opening and distinct identity from SFP and SFP28',()=>{
 const q=socket('qsfp'),s=socket('sfp');assert.equal(q.props['data-hardware-connector'],'qsfp');
 const [,,width,height]=q.props.viewBox.split(' ').map(Number);assert.ok(width>height);
 assert.notEqual(q.props.viewBox,s.props.viewBox);assert.notDeepEqual(q,socket('sfp28'));
 assert.ok(nodes(q).some(n=>n.type==='text'&&n.children.includes('QSFP')));
});
test('the three established connector drawings remain distinct and passive',()=>{
 const old=['rj45','sfp','power'].map(socket);assert.equal(new Set(old.map(x=>JSON.stringify(x))).size,3);
 for(const s of old){assert.equal(s.props['aria-hidden'],'true');assert.equal(s.props['data-hardware-connector'],undefined);assert.ok(nodes(s).every(n=>!n.props?.onClick))}
});
