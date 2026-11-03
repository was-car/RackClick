import test from 'node:test';
import assert from 'node:assert/strict';
import {socketFaceMinimum,specializedFaceMinimum,mountedDeviceWidthStyle} from '../src/hardware-face-sizing.ts';
import {searchHardwareProfiles} from '../src/hardware-profile-search.ts';

test('empty faces shrink, sparse faces use only the actual socket minimum',()=>{
 assert.equal(socketFaceMinimum(1000,[]),0);
 assert.equal(socketFaceMinimum(1000,[{w:50,h:50}]),480);
 assert.equal(socketFaceMinimum(320,[{w:18,h:23}]),427);
 assert.equal(socketFaceMinimum(1200,[{w:24,h:32},{w:32,h:32}]),1200);
});
test('every specialized face preserves 24px targets without a universal rack width',()=>{
 for(const [family,width,w,h] of [['aruba1930',1280,51,52],['fortigate60f',1000,50,50],['synology-rs1221plus',1280,39,39],['diskstation-ds423plus',320,18,23],['qnap-ts464',320,24,28]]){
  assert.equal(specializedFaceMinimum({family,face:'front',ports:[]}),0,family);
  const min=specializedFaceMinimum({family,face:'rear',ports:[{type:'rj45'}]});
  assert.ok(min/width*Math.min(w,h)>=24,family);
  assert.ok(min/width*Math.min(w,h)<25,family);
 }
 assert.equal(specializedFaceMinimum({family:'synology-rs1221plus',face:'rear',ports:[{type:'power'}]}),311);
});
test('measured child width scales against usable support, not an arbitrary 550px',()=>{
 const child=Object.freeze({width:216}),parent=Object.freeze({width:440});
 const small=mountedDeviceWidthStyle(child.width,parent.width),large=mountedDeviceWidthStyle(300,440);
 assert.ok(Math.abs(parseFloat(small.width)-49.0909)<0.001);
 assert.ok(parseFloat(small.width)<parseFloat(large.width));
 assert.equal(mountedDeviceWidthStyle(440,440).width,'100%');
 for(const args of [[undefined,440],[216,null],[NaN,440],[-1,440],[500,440]])assert.equal(mountedDeviceWidthStyle(...args).width,'min(100%, 550px)');
 assert.deepEqual(child,{width:216});assert.deepEqual(parent,{width:440});
});
test('German manufacturer spelling aliases only filter exact profile objects',()=>{
 const fritz=Object.freeze({key:'fb',revision:'exact-v1',identity:{manufacturer:'FRITZ!',family:'FRITZ!Box',model:'7530 AX',sku:'20002930'}});
 const dray=Object.freeze({key:'vigor',revision:'exact-v1',identity:{manufacturer:'DrayTek',family:'Vigor',model:'167',sku:'Vigor167'}});
 const values=Object.freeze([fritz,dray]);
 for(const q of ['fritzbox','Fritz!Box','fritz box 7530','AVM 7530'])assert.deepEqual(searchHardwareProfiles(values,q),[fritz],q);
 for(const q of ['Drytek','draytek 167'])assert.deepEqual(searchHardwareProfiles(values,q),[dray],q);
 assert.deepEqual(searchHardwareProfiles(values,'fritz 7590'),[]);
 assert.deepEqual(searchHardwareProfiles(values,'drytek 7530'),[]);
 assert.equal(fritz.revision,'exact-v1');assert.equal(dray.identity.manufacturer,'DrayTek');
});
