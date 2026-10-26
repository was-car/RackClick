import {ApiError} from './api.ts';
import {portColorsUuid,validPortColorsDraft,samePortColors,type PortColorsDraft} from './user-port-colors.ts';
// A separate family and one durable original intention per authenticated actor.
export async function portColorsJournal(action:'read'|'write'|'remove',actorId:string,draft?:PortColorsDraft):Promise<PortColorsDraft|null>{
 if(!portColorsUuid(actorId)||!['read','write','remove'].includes(action)||(action!=='read'&&(!validPortColorsDraft(draft)||draft.actorId!==actorId)))throw new ApiError(0,'port_colors_storage_unavailable');
 const same=(a:PortColorsDraft,b:PortColorsDraft)=>a.actorId===b.actorId&&samePortColors(a.colors,b.colors)&&a.revision===b.revision&&a.requestId===b.requestId;
 const db:IDBDatabase=await new Promise((resolve,reject)=>{let blocked=false;const r=indexedDB.open('RackClick.UserPortColors.v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('pending',{keyPath:'actorId'});r.onsuccess=()=>{if(blocked)r.result.close();else resolve(r.result)};r.onerror=r.onblocked=()=>{blocked=true;reject(new ApiError(0,'port_colors_storage_unavailable'))}});
 try{return await new Promise((resolve,reject)=>{const tx=db.transaction('pending',action==='read'?'readonly':'readwrite',{durability:'strict'}),store=tx.objectStore('pending');let value:PortColorsDraft|null=null;tx.oncomplete=()=>resolve(value);tx.onerror=tx.onabort=()=>reject(new ApiError(0,'port_colors_storage_unavailable'));const r=store.get(actorId);r.onsuccess=()=>{const old=r.result;if(old&&(!validPortColorsDraft(old)||old.actorId!==actorId)){tx.abort();return}if(action==='read'){value=old||null;return}if(old&&!same(old,draft!)){tx.abort();return}if(action==='write'){store.put(draft);value=draft!}else store.delete(actorId)}})}finally{db.close()}
}
