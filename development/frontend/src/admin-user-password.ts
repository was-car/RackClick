import { ApiError, type RackClickApi } from './api.ts';
export type UserPasswordDraft = { actorId: string; requestId: string; userId: string; revision: number };
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x) && x !== '00000000-0000-0000-0000-000000000000';
const validDraft = (x: any): x is UserPasswordDraft => x && uuid(x.actorId) && uuid(x.requestId) && uuid(x.userId) && Number.isSafeInteger(x.revision) && x.revision > 0 && Object.keys(x).sort().join() === 'actorId,requestId,revision,userId';
const passwordPath = (d: UserPasswordDraft) => '/admin/users/' + d.userId + '/password';
function requireDraft(api: RackClickApi, d: UserPasswordDraft) {
 if (!validDraft(d)) throw new ApiError(422, 'request_invalid');
 if (api.actorId !== d.actorId) throw new ApiError(409, 'actor_changed');
}
export function confirmedPassword(data: any, d: UserPasswordDraft) {
 if (!validDraft(d) || data?.resource?.id !== d.userId || typeof data.resource.userName !== 'string' || typeof data.resource.active !== 'boolean' || data.resource.passwordReset !== true || data.requestId !== d.requestId || data.systemhausRevision !== d.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
function outcome(data: any, d: UserPasswordDraft) {
 if (data?.requestId !== d.requestId || !['committed','notRecorded','cancelled'].includes(data.state)) throw new ApiError(200,'response_invalid',true);
 if (data.state === 'committed') return confirmedPassword(data.operation,d);
 if (data.operation !== null) throw new ApiError(200,'response_invalid',true);
 return data.state === 'cancelled' ? data : null;
}
export async function resetUserPassword(api: RackClickApi, d: UserPasswordDraft, password: string) {
 requireDraft(api,d);
 if (typeof password !== 'string' || password.length < 16 || password.length > 1024) throw new ApiError(422,'password_length');
 const data = await api.sendMutation({path:passwordPath(d),method:'POST',actorId:d.actorId,requestId:d.requestId,etag:'"'+d.revision+'"',body:JSON.stringify({password})});
 requireDraft(api,d);return confirmedPassword(data,d);
}
export async function passwordStatus(api: RackClickApi, d: UserPasswordDraft) {
 requireDraft(api,d);const {data}=await api.request(passwordPath(d)+'/operations/'+d.requestId);requireDraft(api,d);return outcome(data,d);
}
export async function cancelPassword(api: RackClickApi, d: UserPasswordDraft) {
 requireDraft(api,d);
 const data=await api.sendMutation({path:passwordPath(d)+'/operations/'+d.requestId+'/cancel',method:'POST',actorId:d.actorId,requestId:d.requestId,etag:'"'+d.revision+'"',body:JSON.stringify({})});
 requireDraft(api,d);const result=outcome(data,d);if(!result)throw new ApiError(200,'response_invalid',true);return result;
}
// One pending intention per actor, shared by tabs for password resets; secrets never enter this journal. Compare before writing/removing.
export async function passwordJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: UserPasswordDraft): Promise<UserPasswordDraft | null> {
 if (!uuid(actorId) || (action !== 'read' && (!validDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const r = indexedDB.open('RackClick.AdminUserPassword.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => { if (blocked) r.result.close(); else resolve(r.result); };
  r.onerror = r.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: UserPasswordDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!validDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.userId !== draft!.userId || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}
