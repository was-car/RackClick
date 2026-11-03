import test from 'node:test';
import assert from 'node:assert/strict';
import {hardwarePhoto,privatePhotoEnabled,readHardwarePhoto} from '../src/hardware-photo.ts';

test('photo is an optional local reference, never a redistribution approval or external URL',()=>{
 assert.equal(hardwarePhoto.rightsStatus,'private_reference_pending_review');
 assert.match(hardwarePhoto.path,/^\/hardware-media\/[a-z0-9-]+\.jpg$/);
 assert.equal(hardwarePhoto.sha256.length,64);assert.equal(hardwarePhoto.bytes,155227);
 for(const marker of [undefined,null,'',true,1,'approved','latest',' '+hardwarePhoto.sha256])assert.equal(privatePhotoEnabled(marker),false);
 assert.equal(privatePhotoEnabled(hardwarePhoto.sha256),true);
 assert.ok(Object.isFrozen(hardwarePhoto)&&Object.isFrozen(hardwarePhoto.centers));
});
test('24 calibrated hit regions have unique centers within the unmodified image viewport',()=>{
 assert.equal(hardwarePhoto.centers.length,24);assert.equal(new Set(hardwarePhoto.centers.map(JSON.stringify)).size,24);
 const half=hardwarePhoto.hitSize/2;
 for(const [x,y] of hardwarePhoto.centers)assert.ok(x-half>=150&&x+half<=1860&&y-half>=650&&y+half<=1440);
 for(let i=1;i<24;i++)assert.ok(hardwarePhoto.centers[i][0]-hardwarePhoto.centers[i-1][0]>=hardwarePhoto.hitSize);
 assert.equal(hardwarePhoto.view,'perspective-front');assert.equal(hardwarePhoto.viewBox,'150 650 1710 790');
});
test('reference fetch omits cookies, disallows cross-origin redirects and preserves the AbortSignal',async()=>{
 const c=new AbortController();let called=false;
 await assert.rejects(()=>readHardwarePhoto(async(url,options)=>{called=true;assert.equal(url,hardwarePhoto.path);assert.deepEqual(options,{credentials:'omit',mode:'same-origin',redirect:'error',signal:c.signal});return new Response(null,{status:404});},c.signal));
 assert.ok(called);
});
test('missing, redirected or wrong declared length rejects without consuming the image',async()=>{
 for(const response of [{ok:false},{ok:true,redirected:true},{ok:true,redirected:false,body:null},{ok:true,redirected:false,body:{},headers:new Headers({'content-length':'1'})}])await assert.rejects(()=>readHardwarePhoto(async()=>response));
});
test('a short, non-JPEG or equal-length altered reference never becomes a displayed Blob',async()=>{
 for(const length of [0,20,hardwarePhoto.bytes]){
  const bytes=new Uint8Array(length);if(length>3)bytes.set([255,216,255]);
  await assert.rejects(()=>readHardwarePhoto(async()=>new Response(bytes)));
 }
 await assert.rejects(()=>readHardwarePhoto(async()=>new Response(new Uint8Array(hardwarePhoto.bytes))));
});
test('an oversized stream is cancelled as soon as it exceeds the fixed bound',async()=>{
 let cancelled=false;
 const stream=new ReadableStream({start(c){c.enqueue(new Uint8Array(hardwarePhoto.bytes+1));},cancel(){cancelled=true;}});
 await assert.rejects(()=>readHardwarePhoto(async()=>new Response(stream)));
 assert.equal(cancelled,true);
});
test('transport failure is propagated to the component fallback without alternate-source fetching',async()=>{
 let calls=0;await assert.rejects(()=>readHardwarePhoto(async()=>{calls++;throw Error('offline')}));assert.equal(calls,1);
});
