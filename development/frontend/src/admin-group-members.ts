import { ApiError, type RackClickApi } from './api.ts';
import { readAdminGroups } from './admin-groups.ts';
import { readUsers } from './admin-users.ts';
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x);
export type MemberDraft = { actorId: string; requestId: string; groupId: string; userId: string; assigned: boolean; revision: number };
const validDraft = (x: any): x is MemberDraft => x && uuid(x.actorId) && uuid(x.requestId) &&
 uuid(x.groupId) && uuid(x.userId) && typeof x.assigned === 'boolean' && Number.isSafeInteger(x.revision) && x.revision > 0 &&
 Object.keys(x).sort().join() === 'actorId,assigned,groupId,requestId,revision,userId';
const memberPath = (draft: MemberDraft) => '/admin/user-groups/' + draft.groupId + '/members';
function requireDraft(api: RackClickApi, draft: MemberDraft) {
 if (!validDraft(draft)) throw new ApiError(422, 'request_invalid');
 if (api.actorId !== draft.actorId) throw new ApiError(409, 'actor_changed');
}
export function confirmedMember(data: any, draft: MemberDraft) {
 if (!validDraft(draft) || data?.resource?.groupId !== draft.groupId || data.resource.userId !== draft.userId || data.resource.assigned !== draft.assigned ||
     data.requestId !== draft.requestId || !Number.isSafeInteger(data.systemhausRevision) || data.systemhausRevision !== draft.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
function memberOutcome(data: any, draft: MemberDraft) {
 if (data?.requestId !== draft.requestId || !['committed', 'notRecorded', 'cancelled'].includes(data.state)) throw new ApiError(200, 'response_invalid', true);
 if (data.state === 'committed') return confirmedMember(data.operation, draft);
 if (data.operation !== null) throw new ApiError(200, 'response_invalid', true);
 return data.state === 'cancelled' ? data : null;
}
export async function assignMember(api: RackClickApi, draft: MemberDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: memberPath(draft), method: 'POST', actorId: draft.actorId, requestId: draft.requestId,
  etag: '"' + draft.revision + '"', body: JSON.stringify({ userId: draft.userId, assigned: draft.assigned }) });
 requireDraft(api, draft);
 return confirmedMember(data, draft);
}
export async function memberStatus(api: RackClickApi, draft: MemberDraft) {
 requireDraft(api, draft);
 const { data } = await api.request(memberPath(draft) + '/operations/' + draft.requestId);
 requireDraft(api, draft);
 return memberOutcome(data, draft);
}
export async function cancelMember(api: RackClickApi, draft: MemberDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: memberPath(draft) + '/operations/' + draft.requestId + '/cancel', method: 'POST',
  actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify({ userId: draft.userId, assigned: draft.assigned }) });
 requireDraft(api, draft);
 const result = memberOutcome(data, draft);
 if (!result) throw new ApiError(200, 'response_invalid', true);
 return result;
}
// One pending intention per actor, shared by tabs for membership changes. Compare before writing/removing.
export async function memberJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: MemberDraft): Promise<MemberDraft | null> {
 if (!uuid(actorId) || (action !== 'read' && (!validDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const r = indexedDB.open('RackClick.AdminGroupMembers.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => { if (blocked) r.result.close(); else resolve(r.result); };
  r.onerror = r.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: MemberDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!validDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.groupId !== draft!.groupId || old.userId !== draft!.userId || old.assigned !== draft!.assigned || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}

export async function readMemberTargets(api: RackClickApi) {
 const actor = api.actorId;
 const [groups, users] = await Promise.all([readAdminGroups(api), readUsers(api)]);
 if (actor !== api.actorId) throw new ApiError(409, 'actor_changed');
 if (groups.revision !== users.revision) throw new ApiError(409, 'groups_changed');
 for (const entries of [groups.userGroups, users.users]) if (new Set(entries.map((x: any) => x.id)).size !== entries.length) throw new ApiError(200, 'response_invalid');
 return {...groups, users:users.users};
}
