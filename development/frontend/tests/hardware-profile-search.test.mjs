import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHardwareProfiles,hardwareSearchText} from '../src/hardware-profile-search.ts';
import {hardwareChoices,hardwareCreateCommand} from '../src/hardware-mounting.ts';
const profiles=Object.freeze([
 Object.freeze({key:'a',revision:'v1',identity:{manufacturer:'Sophos',family:'XGS',model:'XGS 87',sku:'XGS87'}}),
 Object.freeze({key:'b',revision:'v2',identity:{manufacturer:'Fortinet',family:'FortiGate',model:'FG-60F',sku:'FG60F'}}),
 Object.freeze({key:'c',revision:'v1',identity:{manufacturer:'Aruba',model:'Instant On 1930',sku:'JL683A'}}),
 Object.freeze({key:'shelf-5u',revision:'v1'})]);
test('manufacturer alias, case and accents affect search only, not identity or revision',()=>{
 assert.deepEqual(searchHardwareProfiles(profiles,' SOFOS '),[profiles[0]]);
 assert.deepEqual(searchHardwareProfiles(profiles,'sophós xgs87'),[profiles[0]]);
 assert.equal(profiles[0].identity.manufacturer,'Sophos');assert.equal(profiles[0].revision,'v1');
 assert.deepEqual(searchHardwareProfiles(profiles,'FORTINET 60f'),[profiles[1]]);
 assert.deepEqual(searchHardwareProfiles(profiles,'Aruba JL683A'),[profiles[2]]);
});
test('all query tokens must match and unknown SKU does not select a nearby model',()=>{
 assert.deepEqual(searchHardwareProfiles(profiles,'Fortinet JL683A'),[]);
 assert.deepEqual(searchHardwareProfiles(profiles,'FG-61F'),[]);
 assert.deepEqual(searchHardwareProfiles(profiles,'<img src=x onerror=alert(1)>'),[]);
 assert.deepEqual(searchHardwareProfiles(profiles,'sofosx'),[]);
});
test('empty query exposes all choices; synthetic supports and revisions remain findable',()=>{
 assert.deepEqual(searchHardwareProfiles(profiles,'  '),profiles);
 assert.deepEqual(searchHardwareProfiles(profiles,'shelf-5u'),[profiles[3]]);
 assert.deepEqual(searchHardwareProfiles(profiles,'v2'),[profiles[1]]);
 assert.equal(hardwareSearchText('  Bandejá  '),'bandeja');
});
test('real catalogue filtering preserves exact objects; unresolved typed search cannot create hardware',()=>{
 for(const vendor of ['Aruba','Fortinet','Sophos']){
  const matches=searchHardwareProfiles(hardwareChoices,vendor==='Sophos'?'sofos':vendor);
  assert.ok(matches.length>0,vendor);
  for(const p of matches)assert.ok(hardwareChoices.includes(p));
 }
 assert.throws(()=>hardwareCreateCommand({profileKey:'',profileVersion:'',rackId:'rack',name:'typed'}, {racks:[{id:'rack'}],devices:[]}),e=>e.code==='hardware_profile_invalid');
});
