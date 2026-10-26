import {ApiError} from './api.ts';
import {templateUuid} from './private-templates.ts';
import {validSharedDraft,type SharedTemplateDraft} from './shared-templates.ts';
// Public request intention only. No blueprint, source snapshot, passwords or session credentials.
export async function sharedTemplateJournal(action:'read'|'write'|'remove',actorId:string,draft?:SharedTemplateDraft):Promise<SharedTemplateDraft|null>{
 if(!templateUuid(actorId)||(action!=='read'&&(!validSharedDraft(draft)||draft.actorId!==actorId)))throw new ApiError(0,'draft_storage_unavailable');
 const db:IDBDatabase=await new Promise((resolve,reject)=>{let blocked=false;const r=indexedDB.open('RackClick.SharedTemplates.v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('pending',{keyPath:'actorId'});r.onsuccess=()=>{if(blocked)r.result.close();else resolve(r.result)};r.onerror=r.onblocked=()=>{blocked=true;reject(new ApiError(0,'draft_storage_unavailable'))}});
 try{return await new Promise((resolve,reject)=>{const tx=db.transaction('pending',action==='read'?'readonly':'readwrite',{durability:'strict'}),store=tx.objectStore('pending');let value:SharedTemplateDraft|null=null;tx.oncomplete=()=>resolve(value);tx.onerror=tx.onabort=()=>reject(new ApiError(0,'draft_storage_unavailable'));const r=store.get(actorId);r.onsuccess=()=>{const old=r.result;if(old&&(!validSharedDraft(old)||old.actorId!==actorId)){tx.abort();return}if(action==='read'){value=old||null;return}if(old&&JSON.stringify(old)!==JSON.stringify(draft)){tx.abort();return}if(action==='write'){store.put(draft);value=draft!}else store.delete(actorId)}})}finally{db.close()}
}
