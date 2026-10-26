import { ApiError, type RackClickApi } from './api.ts';
export type UserDraft = { actorId: string; requestId: string; username: string; revision: number };
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x);
const valid = (x: any) => x && uuid(x.actorId) && uuid(x.requestId) && typeof x.username === 'string' && Number.isSafeInteger(x.revision) && x.revision > 0 && Object.keys(x).sort().join() === 'actorId,requestId,revision,username';
export async function userJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: UserDraft): Promise<UserDraft | null> {
 if (action !== 'read' && (!valid(draft) || draft!.actorId !== actorId)) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  const r = indexedDB.open('RackClick.AdminUsers.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => resolve(r.result); r.onerror = r.onblocked = () => reject(new ApiError(0, 'draft_storage_unavailable'));
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: UserDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!valid(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.username !== draft!.username || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}
export async function readUsers(api: RackClickApi) {
 const { data, etag } = await api.request('/admin/users');
 if (!Number.isSafeInteger(data?.revision) || data.revision < 1 || etag !== '"' + data.revision + '"' || !Array.isArray(data.users) || !data.users.every(validUser)) throw new ApiError(200, 'response_invalid');
 return data;
}
function validUser(u: any) { return u && uuid(u.id) && typeof u.userName === 'string' && typeof u.active === 'boolean'; }
export function confirmedUser(data: any, draft: UserDraft) {
 if (!validUser(data?.resource) || data.requestId !== draft.requestId || !Number.isSafeInteger(data.systemhausRevision) || data.systemhausRevision !== draft.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
export async function createUser(api: RackClickApi, draft: UserDraft, password: string) {
 if (!valid(draft)) throw new ApiError(422, 'request_invalid');
 return confirmedUser(await api.sendMutation({ path: '/admin/users', method: 'POST', actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify({ username: draft.username, password }) }), draft);
}
export async function userStatus(api: RackClickApi, draft: UserDraft) {
 if (api.actorId !== draft.actorId) throw new ApiError(409, 'actor_changed');
 const { data } = await api.request('/admin/users/operations/' + draft.requestId);
 return userOutcome(data, draft);
}
function userOutcome(data: any, draft: UserDraft) {
 if (data?.requestId !== draft.requestId || !['committed', 'notRecorded', 'cancelled'].includes(data.state)) throw new ApiError(200, 'response_invalid');
 if (data.state === 'committed') return confirmedUser(data.operation, draft);
 if (data.operation !== null) throw new ApiError(200, 'response_invalid');
 return data.state === 'cancelled' ? data : null;
}
export async function cancelUser(api: RackClickApi, draft: UserDraft) {
 if (!valid(draft)) throw new ApiError(422, 'request_invalid');
 const data = await api.sendMutation({ path: '/admin/users/operations/' + draft.requestId + '/cancel', method: 'POST', actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify({ username: draft.username }) });
 const result = userOutcome(data, draft);
 if (!result) throw new ApiError(200, 'response_invalid', true);
 return result;
}
