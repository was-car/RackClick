import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHardwareProfiles} from '../src/hardware-profile-search.ts';
import {repeaterRoomWidth} from '../src/hardware-room-sizing.ts';

const profiles=Object.freeze([
 Object.freeze({key:'fritz600',revision:'fixed',identity:{manufacturer:'FRITZ!',family:'Mesh WLAN Repeater',model:'FRITZ!Repeater 600',sku:'20002853'}}),
 Object.freeze({key:'devolo',revision:'fixed',identity:{manufacturer:'devolo',family:'WiFi Repeater Mesh',model:'WiFi 6 Repeater 3000',sku:'3000'}}),
 Object.freeze({key:'router',revision:'fixed',identity:{manufacturer:'DrayTek',family:'Vigor router',model:'Vigor 167',sku:'167'}})
]);
test('ES/DE/FR spelling and a common typo find repeaters without changing identity',()=>{
 for(const query of ['repetidor','repetidores','repeter','répéteur','Verstärker','WLAN-Verstärker'])assert.deepEqual(searchHardwareProfiles(profiles,query),profiles.slice(0,2),query);
 for(const query of ['FRITZ!Repeater','fritz repeater 600','fritzrepeater 600','AVM repetidor'])assert.deepEqual(searchHardwareProfiles(profiles,query),[profiles[0]],query);
 assert.deepEqual(searchHardwareProfiles(profiles,'repetidor drytek'),[]);
 assert.equal(profiles[0].revision,'fixed');assert.equal(profiles[0].identity.model,'FRITZ!Repeater 600');
});
test('room display stays bounded and monotonic without inventing recorded dimensions',()=>{
 let previous=0;
 for(let width=10;width<=600;width+=5){const result=repeaterRoomWidth(width);assert.ok(result>=180&&result<=340);assert.ok(result>=previous);previous=result}
 for(const width of [null,undefined,NaN,Infinity,-1,0,'80'])assert.ok(Number.isFinite(repeaterRoomWidth(width))&&repeaterRoomWidth(width)>0);
 const record=Object.freeze({width:80,height:80,depth:37});repeaterRoomWidth(record.width);assert.deepEqual(record,{width:80,height:80,depth:37});
});
