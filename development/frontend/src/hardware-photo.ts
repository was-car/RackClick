// Optional local reference, not a redistribution grant. No image bytes in source.
export const hardwarePhoto = Object.freeze({
 shell:'startech-c6panelutp241uft-front-v1',
 sha256:'3f526223398462f5c3de6bca7bfb1527b693f92bc781cbaf2b07bec70a947d45',
 bytes:155227,width:2000,height:2000,hitSize:50,
 path:'/hardware-media/startech-c6panelutp241uft-3f5262233984.jpg',
 rightsStatus:'private_reference_pending_review',
 view:'perspective-front',viewBox:'150 650 1710 790',
 // Manual calibration on this exact image; ordinals bind existing UUIDs only.
 centers:Object.freeze([[277,876],[328,892],[378,908],[428,924],[479,940],[530,957],
  [598,979],[650,995],[703,1012],[758,1029],[811,1046],[866,1063],
  [937,1086],[992,1103],[1046,1121],[1103,1139],[1161,1158],[1218,1176],
  [1291,1200],[1349,1218],[1409,1237],[1469,1256],[1528,1275],[1592,1295]].map(Object.freeze))
});
export function privatePhotoEnabled(marker: unknown) { return marker===hardwarePhoto.sha256; }

// Bounded same-origin read. A missing/altered reference uses the schematic fallback.
export async function readHardwarePhoto(fetcher: typeof fetch = fetch, signal?: AbortSignal) {
 const response=await fetcher(hardwarePhoto.path,{credentials:'omit',mode:'same-origin',redirect:'error',signal});
 if (!response.ok || response.redirected || !response.body ||
     (response.headers.has('content-length') && response.headers.get('content-length')!==String(hardwarePhoto.bytes))) throw Error('hardware_photo_unavailable');
 const reader=response.body.getReader(),bytes=new Uint8Array(hardwarePhoto.bytes);let offset=0;
 try {
  while(true){const {done,value}=await reader.read();if(done)break;
   if(offset+value.byteLength>bytes.length)throw Error('hardware_photo_unavailable');
   bytes.set(value,offset);offset+=value.byteLength;
  }
 } catch(error){await reader.cancel().catch(()=>{});throw error;} finally {reader.releaseLock();}
 if(offset!==bytes.length || bytes[0]!==255 || bytes[1]!==216 || bytes[2]!==255 || !globalThis.crypto?.subtle)throw Error('hardware_photo_unavailable');
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
 if(hash!==hardwarePhoto.sha256)throw Error('hardware_photo_unavailable');
 return new Blob([bytes],{type:'image/jpeg'});
}
