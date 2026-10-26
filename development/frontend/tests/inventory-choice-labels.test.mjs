import test from 'node:test';
import assert from 'node:assert/strict';
import { inventoryEntityOption, inventoryOptionLabel } from '../src/inventory-choice-labels.ts';
import { inventoryWords } from '../src/inventory-words.ts';

const one='00000000-0000-4000-8000-000000000001';
const two='00000000-0000-4000-8000-000000000002';

test('homonymous entity labels and tooltips retain complete distinct UUIDs',()=>{
 const a=inventoryEntityOption(one,'room'),b=inventoryEntityOption(two,'room');
 assert.equal(a.value,one);assert.equal(b.value,two);
 assert.notEqual(a.label,b.label);
 assert.equal(a.title,'room · '+one);assert.equal(b.title,'room · '+two);
 assert.equal(a.literal,true);assert.equal(b.literal,true);
});

test('entity names remain literal in EN DE ES, including words that are UI translation keys',()=>{
 for(const lang of ['en','de','es'])for(const name of ['room','building','site','yes','unassigned','constructor','__proto__']){
  const choice=inventoryEntityOption(one,name);
  assert.equal(inventoryOptionLabel(choice,inventoryWords[lang]),name+' · '+one,lang+':'+name);
 }
});

test('literal flag also preserves an exact custom name without a UUID suffix',()=>{
 assert.equal(inventoryOptionLabel({label:'room',literal:true},inventoryWords.es),'room');
});

test('closed UI options still translate the placeholder, yes/no, and patch choices',()=>{
 for(const lang of ['en','de','es'])for(const label of ['unassigned','yes','no','none','planned','progress','done','tested']){
  assert.equal(inventoryOptionLabel({value:label,label},inventoryWords[lang]),inventoryWords[lang][label]||label);
 }
});

test('prototype properties cannot become React labels or functions',()=>{
 for(const label of ['__proto__','constructor','toString']){
  assert.equal(inventoryOptionLabel({label},inventoryWords.es),label);
 }
});

test('Unicode and HTML-looking names are data, not normalized or translated; inputs stay unchanged',()=>{
 const name='Sala Ω 東京 <img src=x onerror=alert(1)>';
 const words=Object.freeze({...inventoryWords.es});const choice=Object.freeze(inventoryEntityOption(one,name));
 const before=JSON.stringify(choice);
 assert.equal(inventoryOptionLabel(choice,words),name+' · '+one);
 assert.equal(JSON.stringify(choice),before);
});
