import {ApiError} from './api.ts';
import {preferenceUuid,validPreferenceDraft,type PreferenceDraft} from './user-preferences.ts';
// One public intention per actor. Deliberately separate from inventory/favourites journals.
export async function preferenceJournal(action:'read'|'write'|'remove',actorId:string,draft?:PreferenceDraft):Promise<PreferenceDraft|null>{
 if(!preferenceUuid(actorId)||!['read','write','remove'].includes(action)||(action!=='read'&&(!validPreferenceDraft(draft)||draft.actorId!==actorId)))throw new ApiError(0,'preferences_storage_unavailable');
 const same=(a:PreferenceDraft,b:PreferenceDraft)=>a.actorId===b.actorId&&a.key===b.key&&a.value===b.value&&a.revision===b.revision&&a.requestId===b.requestId;
 const db:IDBDatabase=await new Promise((resolve,reject)=>{let blocked=false;const r=indexedDB.open('RackClick.UserPreferences.v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('pending',{keyPath:'actorId'});r.onsuccess=()=>{if(blocked)r.result.close();else resolve(r.result)};r.onerror=r.onblocked=()=>{blocked=true;reject(new ApiError(0,'preferences_storage_unavailable'))}});
 try{return await new Promise((resolve,reject)=>{const tx=db.transaction('pending',action==='read'?'readonly':'readwrite',{durability:'strict'}),store=tx.objectStore('pending');let value:PreferenceDraft|null=null;tx.oncomplete=()=>resolve(value);tx.onerror=tx.onabort=()=>reject(new ApiError(0,'preferences_storage_unavailable'));const r=store.get(actorId);r.onsuccess=()=>{const old=r.result;if(old&&(!validPreferenceDraft(old)||old.actorId!==actorId)){tx.abort();return}if(action==='read'){value=old||null;return}if(old&&!same(old,draft!)){tx.abort();return}if(action==='write'){store.put(draft);value=draft!}else store.delete(actorId)}})}finally{db.close()}
}
