import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {hardwareWords} from '../src/hardware-words.ts';

function panel() {
 return {id:'panel-id',u:1,hardwareProfileKey:'startech-c6panelutp241uft',hardwareProfileVersion:'startech-20261030-v1',
  hardwareIdentity:{manufacturer:'StarTech.com',model:'C6PANELUTP241UFT',sku:'C6PANELUTP241UFT'},
  ports:['front','rear'].flatMap(face=>Array.from({length:24},(_,i)=>({id:face+'-'+(i+1),groupId:face+'-uuid',rackclickFace:face,type:'rj45',gn:i+1,label:'My label'})))};
}
test('specific front binds four blocks of six original UUID-bound controls, never fabricated ports',()=>{
 const d=panel(),before=structuredClone(d),layout=hardwareShellLayout(d,'front');
 assert.equal(layout.id,'startech-c6panelutp241uft-front-v1');assert.equal(layout.blocks.length,4);
 assert.deepEqual(layout.blocks.map(b=>b.map(p=>p.gn)),Array.from({length:4},(_,i)=>Array.from({length:6},(_,j)=>i*6+j+1)));
 assert.deepEqual(layout.blocks.flat().map(p=>p.id),d.ports.slice(0,24).map(p=>p.id));
 assert.equal(layout.blocks[0][0],d.ports[0]);assert.deepEqual(d,before);
 assert.ok(Object.isFrozen(layout)&&Object.isFrozen(layout.blocks)&&layout.blocks.every(Object.isFrozen));
 assert.equal(Object.isFrozen(d.ports[0]),false);
});
test('unknown face, missing or unknown revision, generic and neighbouring models never borrow a specific shell',()=>{
 assert.equal(hardwareShellLayout(panel(),'side'),null);assert.equal(hardwareShellLayout(panel(),'auto'),null);
 for(const [field,value] of [['hardwareProfileVersion',null],['hardwareProfileVersion','latest'],['hardwareProfileVersion','startech-20261030-v2'],['hardwareProfileKey','patchpanel-24'],['hardwareProfileKey','startech-c6panelutp241u'],['u',0]]){
  const d=panel();d[field]=value;assert.equal(hardwareShellLayout(d,'front'),null);
 }
 for(const field of ['manufacturer','model','sku']){const d=panel();d.hardwareIdentity[field]='other';assert.equal(hardwareShellLayout(d,'front'),null);}
 assert.equal(hardwareShellLayout(null,'front'),null);
});
test('port identity, group, type, face or count mismatch falls back rather than hiding or guessing connectors',()=>{
 for(const change of [d=>d.ports.pop(),d=>d.ports.push({...d.ports[0],id:'new'}),d=>d.ports[0].id=d.ports[1].id,d=>d.ports[0].id='',d=>d.ports[0].type='sfp',d=>d.ports[0].rackclickFace='auto',d=>d.ports[0].groupId='',d=>d.ports[0].groupId='extra',d=>d.ports.forEach(p=>p.groupId='same'),d=>d.ports[0].gn=2,d=>d.ports[0].gn=0,d=>d.ports[0].gn=1.5]){
  const d=panel();change(d);const before=structuredClone(d);assert.equal(hardwareShellLayout(d,'front'),null);assert.deepEqual(d,before);
 }
});
test('layout order is logical, never input order, label or a repeated rear ordinal',()=>{
 const d=panel();d.ports.reverse();const before=structuredClone(d);const layout=hardwareShellLayout(d,'front');
 assert.equal(layout.blocks[0][0].id,'front-1');assert.equal(layout.blocks[3][5].id,'front-24');assert.deepEqual(d,before);
});
test('visual wording exists in EN/DE/ES without changing the model name',()=>{
 for(const lang of ['en','de','es'])for(const key of ['specificShell','genericShell','shellScroll'])assert.ok(hardwareWords[lang][key].length>10);
});

test('rear uses the same recorded rear UUIDs in exterior pair order without changing the front or mutating ports',()=>{
 const d=panel(),before=structuredClone(d),layout=hardwareShellLayout(d,'rear');
 assert.equal(layout.id,'startech-c6panelutp241uft-rear-v1');assert.equal(layout.face,'rear');assert.equal(layout.blocks.length,4);
 assert.deepEqual(layout.blocks.flat().map(p=>p.id),Array.from({length:24},(_,i)=>'rear-'+(24-i)));
 assert.equal(layout.blocks[0][0],d.ports[47]);assert.deepEqual(d,before);
 assert.ok(Object.isFrozen(layout)&&layout.blocks.every(Object.isFrozen));
 assert.equal(hardwareShellLayout(d,'front').blocks[0][0].id,'front-1');
 for(const lang of ['en','de','es'])assert.ok(hardwareWords[lang].interactiveRear.length>20);
});
