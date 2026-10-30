import { ApiError, type RackClickApi } from './api.ts';
export type UserSessionDraft = { actorId: string; requestId: string; userId: string; sessionId: string; revision: number };
const keys=(x:any,k:string)=>!!x && typeof x==='object' && !Array.isArray(x) && Object.keys(x).sort().join()===k;
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x) && x !== '00000000-0000-0000-0000-000000000000';
const validDraft = (x: any): x is UserSessionDraft => x && uuid(x.actorId) && uuid(x.requestId) && uuid(x.userId) && uuid(x.sessionId) && Number.isSafeInteger(x.revision) && x.revision > 0 && Object.keys(x).sort().join() === 'actorId,requestId,revision,sessionId,userId';
const sessionPath = (d: UserSessionDraft) => '/admin/users/' + d.userId + '/sessions/' + d.sessionId + '/revoke';
function requireDraft(api: RackClickApi, d: UserSessionDraft) {
 if (!validDraft(d)) throw new ApiError(422, 'request_invalid');
 if (api.actorId !== d.actorId) throw new ApiError(409, 'actor_changed');
}
export function confirmedSession(data: any, d: UserSessionDraft) {
 if (!validDraft(d) || !keys(data,'requestId,resource,systemhausRevision') || !keys(data.resource,'revoked,sessionId,userId,wasCurrent') || data.resource.userId !== d.userId || data.resource.sessionId !== d.sessionId || data.resource.revoked !== true || typeof data.resource.wasCurrent !== 'boolean' || data.requestId !== d.requestId || data.systemhausRevision !== d.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
function outcome(data: any, d: UserSessionDraft) {
 if (!keys(data,'operation,requestId,state') || data?.requestId !== d.requestId || !['committed','notRecorded','cancelled'].includes(data.state)) throw new ApiError(200,'response_invalid',true);
 if (data.state === 'committed') return confirmedSession(data.operation,d);
 if (data.operation !== null) throw new ApiError(200,'response_invalid',true);
 return data.state === 'cancelled' ? data : null;
}
export async function revokeUserSession(api: RackClickApi, d: UserSessionDraft) {
 requireDraft(api,d);

 const data = await api.sendMutation({path:sessionPath(d),method:'POST',actorId:d.actorId,requestId:d.requestId,etag:'"'+d.revision+'"',body:JSON.stringify({})});
 requireDraft(api,d);return confirmedSession(data,d);
}
export async function sessionStatus(api: RackClickApi, d: UserSessionDraft) {
 requireDraft(api,d);const {data}=await api.request(sessionPath(d)+'/operations/'+d.requestId);requireDraft(api,d);return outcome(data,d);
}
export async function cancelSession(api: RackClickApi, d: UserSessionDraft) {
 requireDraft(api,d);
 const data=await api.sendMutation({path:sessionPath(d)+'/operations/'+d.requestId+'/cancel',method:'POST',actorId:d.actorId,requestId:d.requestId,etag:'"'+d.revision+'"',body:JSON.stringify({})});
 requireDraft(api,d);const result=outcome(data,d);if(!result)throw new ApiError(200,'response_invalid',true);return result;
}
// One pending intention per actor, shared by tabs for session revocations; secrets never enter this journal. Compare before writing/removing.
export async function sessionJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: UserSessionDraft): Promise<UserSessionDraft | null> {
 if (!uuid(actorId) || (action !== 'read' && (!validDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const r = indexedDB.open('RackClick.AdminUserSessions.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => { if (blocked) r.result.close(); else resolve(r.result); };
  r.onerror = r.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: UserSessionDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!validDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.userId !== draft!.userId || old.sessionId !== draft!.sessionId || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}

export async function readUserSessions(api: RackClickApi,userId:string) {
 if(!uuid(userId))throw new ApiError(422,'request_invalid');
 const actor=api.actorId,{data,etag}=await api.request('/admin/users/'+userId+'/sessions');
 if(api.actorId!==actor)throw new ApiError(409,'actor_changed');
 if(!keys(data,'revision,sessions,user') || !Number.isSafeInteger(data.revision) || data.revision<1 || etag!=='"'+data.revision+'"' || !keys(data.user,'active,id,userName') || data.user.id!==userId || typeof data.user.userName!=='string' || typeof data.user.active!=='boolean' || !Array.isArray(data.sessions))throw new ApiError(200,'response_invalid');
 const ids=new Set(),currents=data.sessions.filter((s:any)=>s?.current).length;
 if(currents>1 || (!data.user.active&&data.sessions.length) || !data.sessions.every((s:any)=>{if(!keys(s,'current,expiresAt,id')||!uuid(s.id)||ids.has(s.id)||typeof s.current!=='boolean'||(s.current&&userId!==actor)||typeof s.expiresAt!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|\+00:00)$/.test(s.expiresAt)||!Number.isFinite(Date.parse(s.expiresAt)))return false;ids.add(s.id);return true}))throw new ApiError(200,'response_invalid');
 return data;
}
