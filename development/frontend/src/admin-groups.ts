import { ApiError, type RackClickApi } from './api.ts';
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x);
const target = (x: any) => x && uuid(x.id) && typeof x.name === 'string';
const member = (x: any) => x && uuid(x.id) && typeof x.userName === 'string' && typeof x.active === 'boolean';
const grant = (x: any) => x && uuid(x.id) && typeof x.capability === 'string' &&
 (x.scope === 'systemhaus' ? x.target === null : ['customer', 'customerGroup'].includes(x.scope) && target(x.target));
const snapshot = (x: any) => x && Number.isSafeInteger(x.revision) && x.revision > 0 && Array.isArray(x.groups);
export async function readAdminGroups(api: RackClickApi) {
 const actor = api.actorId;
 const [users, customers] = await Promise.all([api.request('/admin/user-groups'), api.request('/admin/customer-groups')]);
 if (api.actorId !== actor) throw new ApiError(409, 'actor_changed');
 const u = users.data, c = customers.data;
 if (!snapshot(u) || !snapshot(c) ||
     !u.groups.every((g: any) => target(g) && Array.isArray(g.members) && g.members.every(member) && Array.isArray(g.grants) && g.grants.every(grant)) ||
     !c.groups.every((g: any) => target(g) && Array.isArray(g.customers) && g.customers.every(target))) throw new ApiError(200, 'response_invalid');
 if (u.revision !== c.revision) throw new ApiError(409, 'groups_changed');
 return { revision: u.revision, userGroups: u.groups, customerGroups: c.groups };
}

export type GroupDraft = { actorId: string; requestId: string; kind: 'userGroup' | 'customerGroup'; name: string; revision: number };
const validDraft = (x: any): x is GroupDraft => x && uuid(x.actorId) && uuid(x.requestId) &&
 ['userGroup', 'customerGroup'].includes(x.kind) && typeof x.name === 'string' && Number.isSafeInteger(x.revision) && x.revision > 0 &&
 Object.keys(x).sort().join() === 'actorId,kind,name,requestId,revision';
const groupPath = (draft: GroupDraft) => '/admin/' + (draft.kind === 'userGroup' ? 'user-groups' : 'customer-groups');
function requireDraft(api: RackClickApi, draft: GroupDraft) {
 if (!validDraft(draft)) throw new ApiError(422, 'request_invalid');
 if (api.actorId !== draft.actorId) throw new ApiError(409, 'actor_changed');
}
export function confirmedGroup(data: any, draft: GroupDraft) {
 // Names.Validate uses .NET Char.IsWhiteSpace: Unicode White_Space, including NEL but excluding BOM.
 const name = validDraft(draft) ? draft.name.replace(/^\p{White_Space}+|\p{White_Space}+$/gu, '') : null;
 if (!validDraft(draft) || !target(data?.resource) || data.resource.kind !== draft.kind || data.resource.name !== name ||
     data.requestId !== draft.requestId || !Number.isSafeInteger(data.systemhausRevision) || data.systemhausRevision !== draft.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
function groupOutcome(data: any, draft: GroupDraft) {
 if (data?.requestId !== draft.requestId || !['committed', 'notRecorded', 'cancelled'].includes(data.state)) throw new ApiError(200, 'response_invalid', true);
 if (data.state === 'committed') return confirmedGroup(data.operation, draft);
 if (data.operation !== null) throw new ApiError(200, 'response_invalid', true);
 return data.state === 'cancelled' ? data : null;
}
export async function createGroup(api: RackClickApi, draft: GroupDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: groupPath(draft), method: 'POST', actorId: draft.actorId, requestId: draft.requestId,
  etag: '"' + draft.revision + '"', body: JSON.stringify({ name: draft.name }) });
 requireDraft(api, draft);
 return confirmedGroup(data, draft);
}
export async function groupStatus(api: RackClickApi, draft: GroupDraft) {
 requireDraft(api, draft);
 const { data } = await api.request(groupPath(draft) + '/operations/' + draft.requestId);
 requireDraft(api, draft);
 return groupOutcome(data, draft);
}
export async function cancelGroup(api: RackClickApi, draft: GroupDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: groupPath(draft) + '/operations/' + draft.requestId + '/cancel', method: 'POST',
  actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify({ name: draft.name }) });
 requireDraft(api, draft);
 const result = groupOutcome(data, draft);
 if (!result) throw new ApiError(200, 'response_invalid', true);
 return result;
}
// One pending intention per actor, shared by tabs and both group types. Compare before writing/removing.
export async function groupJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: GroupDraft): Promise<GroupDraft | null> {
 if (!uuid(actorId) || (action !== 'read' && (!validDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const r = indexedDB.open('RackClick.AdminGroups.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => { if (blocked) r.result.close(); else resolve(r.result); };
  r.onerror = r.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: GroupDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!validDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.name !== draft!.name || old.kind !== draft!.kind || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}
