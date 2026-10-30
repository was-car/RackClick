import { ApiError, type RackClickApi } from './api.ts';
import { readMemberTargets } from './admin-group-members.ts';
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x);
export type CustomerMemberDraft = { actorId: string; requestId: string; groupId: string; customerId: string; assigned: boolean; revision: number };
const validDraft = (x: any): x is CustomerMemberDraft => x && uuid(x.actorId) && uuid(x.requestId) &&
 uuid(x.groupId) && uuid(x.customerId) && typeof x.assigned === 'boolean' && Number.isSafeInteger(x.revision) && x.revision > 0 &&
 Object.keys(x).sort().join() === 'actorId,assigned,customerId,groupId,requestId,revision';
const memberPath = (draft: CustomerMemberDraft) => '/admin/customer-groups/' + draft.groupId + '/members';
function requireDraft(api: RackClickApi, draft: CustomerMemberDraft) {
 if (!validDraft(draft)) throw new ApiError(422, 'request_invalid');
 if (api.actorId !== draft.actorId) throw new ApiError(409, 'actor_changed');
}
export function confirmedCustomerMember(data: any, draft: CustomerMemberDraft) {
 if (!validDraft(draft) || data?.resource?.groupId !== draft.groupId || data.resource.customerId !== draft.customerId || data.resource.assigned !== draft.assigned ||
     data.requestId !== draft.requestId || !Number.isSafeInteger(data.systemhausRevision) || data.systemhausRevision !== draft.revision + 1) throw new ApiError(200, 'response_invalid', true);
 return data;
}
function memberOutcome(data: any, draft: CustomerMemberDraft) {
 if (data?.requestId !== draft.requestId || !['committed', 'notRecorded', 'cancelled'].includes(data.state)) throw new ApiError(200, 'response_invalid', true);
 if (data.state === 'committed') return confirmedCustomerMember(data.operation, draft);
 if (data.operation !== null) throw new ApiError(200, 'response_invalid', true);
 return data.state === 'cancelled' ? data : null;
}
export async function assignCustomerMember(api: RackClickApi, draft: CustomerMemberDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: memberPath(draft), method: 'POST', actorId: draft.actorId, requestId: draft.requestId,
  etag: '"' + draft.revision + '"', body: JSON.stringify({ customerId: draft.customerId, assigned: draft.assigned }) });
 requireDraft(api, draft);
 return confirmedCustomerMember(data, draft);
}
export async function customerMemberStatus(api: RackClickApi, draft: CustomerMemberDraft) {
 requireDraft(api, draft);
 const { data } = await api.request(memberPath(draft) + '/operations/' + draft.requestId);
 requireDraft(api, draft);
 return memberOutcome(data, draft);
}
export async function cancelCustomerMember(api: RackClickApi, draft: CustomerMemberDraft) {
 requireDraft(api, draft);
 const data = await api.sendMutation({ path: memberPath(draft) + '/operations/' + draft.requestId + '/cancel', method: 'POST',
  actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify({ customerId: draft.customerId, assigned: draft.assigned }) });
 requireDraft(api, draft);
 const result = memberOutcome(data, draft);
 if (!result) throw new ApiError(200, 'response_invalid', true);
 return result;
}
// One pending intention per actor, shared by tabs for membership changes. Compare before writing/removing.
export async function customerMemberJournal(action: 'read' | 'write' | 'remove', actorId: string, draft?: CustomerMemberDraft): Promise<CustomerMemberDraft | null> {
 if (!uuid(actorId) || (action !== 'read' && (!validDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const r = indexedDB.open('RackClick.AdminCustomerGroupMembers.v1', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('pending', { keyPath: 'actorId' });
  r.onsuccess = () => { if (blocked) r.result.close(); else resolve(r.result); };
  r.onerror = r.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try { return await new Promise((resolve, reject) => {
  const tx = db.transaction('pending', action === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
  let value: CustomerMemberDraft | null = null;
  tx.oncomplete = () => resolve(value); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  const r = store.get(actorId); r.onsuccess = () => {
   const old = r.result;
   if (old && (!validDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
   if (action === 'read') { value = old || null; return; }
   if (old && (old.requestId !== draft!.requestId || old.groupId !== draft!.groupId || old.customerId !== draft!.customerId || old.assigned !== draft!.assigned || old.revision !== draft!.revision)) { tx.abort(); return; }
   if (action === 'write') { store.put(draft); value = draft!; } else store.delete(actorId);
  };
 }); } finally { db.close(); }
}

export async function readCustomerMemberTargets(api: RackClickApi) {
 const actor = api.actorId;
 const [groups, response] = await Promise.all([readMemberTargets(api), api.request('/admin/customers')]);
 if (actor !== api.actorId) throw new ApiError(409, 'actor_changed');
 const customers = response.data;
 if (!Number.isSafeInteger(customers?.revision) || customers.revision < 1 || !Array.isArray(customers.customers) ||
     !customers.customers.every((c: any) => c && uuid(c.id) && typeof c.name === 'string')) throw new ApiError(200, 'response_invalid');
 if (groups.revision !== customers.revision) throw new ApiError(409, 'groups_changed');
 for (const entries of [groups.customerGroups, customers.customers]) if (new Set(entries.map((x: any) => x.id)).size !== entries.length) throw new ApiError(200, 'response_invalid');
 return {...groups, customers:customers.customers};
}
