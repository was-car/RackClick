import { ApiError, type RackClickApi } from './api.ts';
import { readCustomerMemberTargets } from './admin-customer-group-members.ts';
export const capabilities = ['systemhaus.read','systemhaus.manage','customer.create','customer.manage','inventory.read','inventory.edit','inventory.delete','security.manage','reports.export','templates.publish'];
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x);
export type GrantDraft = { actorId: string; requestId: string; groupId: string; grantId: string; capability: string; scope: 'systemhaus' | 'customer' | 'customerGroup'; targetId: string | null; assigned: boolean; revision: number };
const validDraft = (x: any): x is GrantDraft => x && uuid(x.actorId) && uuid(x.requestId) &&
 uuid(x.groupId) && uuid(x.grantId) && capabilities.includes(x.capability) && (x.scope === 'systemhaus' ? x.targetId === null : ['customer', 'customerGroup'].includes(x.scope) && uuid(x.targetId)) && typeof x.assigned === 'boolean' && Number.isSafeInteger(x.revision) && x.revision > 0 &&
 Object.keys(x).sort().join() === 'actorId,assigned,capability,grantId,groupId,requestId,revision,scope,targetId';
const memberPath = (draft: GrantDraft) => '/admin/user-groups/' + draft.groupId + '/grants';
function requireDraft(api: RackClickApi, draft: GrantDraft) {
 if (!validDraft(draft)) throw new ApiError(422, 'request_invalid');
 if (api.actorId !== draft.actorId) throw new ApiError(409, 'actor_changed');
}
export function confirmedGrant(data: any, draft: GrantDraft) {
 if (!validDraft(draft) || data?.resource?.groupId !== draft.groupId || data.resource.grantId !== draft.grantId || data.resource.assigned !== draft.assigned || data.resource.capability !== draft.capability || data.resource.scope !== draft.scope || data.resource.targetId !== draft.targetId ||
     data.requestId !== draft.requestId || !Number.isSafeInteger(data.systemhausRevision) || data.systemhausRevision !== draft.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
function memberOutcome(data: any, draft: GrantDraft) {
 if (data?.requestId !== draft.requestId || !['committed', 'notRecorded', 'cancelled'].includes(data.state)) throw new ApiError(200, 'response_invalid', true);
 if (data.state === 'committed') return confirmedGrant(data.operation, draft);
 if (data.operation !== null) throw new ApiError(200, 'response_invalid', true);
 return data.state === 'cancelled' ? data : null;
}
export async function setGrant(api: RackClickApi, draft: GrantDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: memberPath(draft), method: 'POST', actorId: draft.actorId, requestId: draft.requestId,
  etag: '"' + draft.revision + '"', body: JSON.stringify({ grantId: draft.grantId, capability: draft.capability, scope: draft.scope, targetId: draft.targetId, assigned: draft.assigned }) });
 requireDraft(api, draft);
 return confirmedGrant(data, draft);
}
export async function grantStatus(api: RackClickApi, draft: GrantDraft) {
 requireDraft(api, draft);
 const { data } = await api.request(memberPath(draft) + '/operations/' + draft.requestId);
 requireDraft(api, draft);
 return memberOutcome(data, draft);
}
export async function cancelGrant(api: RackClickApi, draft: GrantDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: memberPath(draft) + '/operations/' + draft.requestId + '/cancel', method: 'POST',
  actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify({ grantId: draft.grantId, capability: draft.capability, scope: draft.scope, targetId: draft.targetId, assigned: draft.assigned }) });
 requireDraft(api, draft);
 const result = memberOutcome(data, draft);
 if (!result) throw new ApiError(200, 'response_invalid', true);
 return result;
}
// One pending intention per actor, shared by tabs for membership changes. Compare before writing/removing.
export async function grantJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: GrantDraft): Promise<GrantDraft | null> {
 if (!uuid(actorId) || (action !== 'read' && (!validDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const r = indexedDB.open('RackClick.AdminGrants.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => { if (blocked) r.result.close(); else resolve(r.result); };
  r.onerror = r.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: GrantDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!validDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.groupId !== draft!.groupId || old.grantId !== draft!.grantId || old.capability !== draft!.capability || old.scope !== draft!.scope || old.targetId !== draft!.targetId || old.assigned !== draft!.assigned || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}

export async function readGrantTargets(api: RackClickApi) {
 const actor = api.actorId;
 const [groups, response] = await Promise.all([readCustomerMemberTargets(api), api.request('/admin/capabilities')]);
 if (actor !== api.actorId) throw new ApiError(409, 'actor_changed');
 const catalog = response.data;
 if (!Number.isSafeInteger(catalog?.revision) || catalog.revision < 1 || !Array.isArray(catalog.capabilities) ||
     catalog.capabilities.length !== capabilities.length || new Set(catalog.capabilities).size !== capabilities.length || !catalog.capabilities.every((c: any) => capabilities.includes(c))) throw new ApiError(200, 'response_invalid');
 if (groups.revision !== catalog.revision) throw new ApiError(409, 'groups_changed');
 for (const group of groups.userGroups) if (new Set(group.grants.map((g: any)=>g.id)).size !== group.grants.length || group.grants.some((g: any)=>!capabilities.includes(g.capability))) throw new ApiError(200,'response_invalid');
 return {...groups, capabilities: catalog.capabilities};
}
