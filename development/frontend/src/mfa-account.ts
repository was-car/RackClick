import { ApiError, type RackClickApi } from './api.ts';

export type MfaAccountAction = 'enable' | 'disable' | 'reset';
export type MfaAccountStatus = Readonly<{
 userId: string; userName: string; available: boolean; required: boolean; enrollmentPending: boolean;
 factorState: 'none' | 'pending' | 'active' | 'disabled'; globalPolicyEnabled: boolean;
 graceDays: number | null; deadlineUtc: string | null; daysRemaining: number | null; deadlineReached: boolean;
 globalAdministratorExempt: boolean; sessionMfaVerified: boolean; canEnable: boolean; canDisable: boolean;
 canReset: boolean; revision: number; serverNowUtc: string;
}>;
export type MfaAccountDraft = Readonly<{
 actorId: string; userId: string; requestId: string; revision: number; action: MfaAccountAction; scope: 'self' | 'admin';
}>;
export type MfaAccountReceipt = Readonly<{
 userId: string; action: MfaAccountAction; requestId: string; systemhausRevision: number;
 signInRequired: boolean; resource: MfaAccountStatus;
}>;

// A recovered receipt describes its original session, not the caller's later authenticated session.
export function mfaChangeRequiresReauthentication(receipt: MfaAccountReceipt, recovered: boolean) {
 return receipt.signInRequired && !recovered;
}

const uuid = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value) && value !== '00000000-0000-0000-0000-000000000000';
const revision = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 1;
const action = (value: unknown): value is MfaAccountAction => value === 'enable' || value === 'disable' || value === 'reset';
const utc = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?(?:Z|\+00:00)$/.test(value) && Number.isFinite(Date.parse(value));
export function validMfaAccountDraft(value: any): value is MfaAccountDraft {
 return !!value && uuid(value.actorId) && uuid(value.userId) && uuid(value.requestId) && revision(value.revision) && value.revision < Number.MAX_SAFE_INTEGER && action(value.action) && ['self', 'admin'].includes(value.scope) && (value.scope !== 'self' || value.actorId === value.userId) && Object.keys(value).sort().join() === 'action,actorId,requestId,revision,scope,userId';
}
export function mfaAccountPath(userId?: string) {
 if (userId === undefined) return '/me/mfa';
 if (!uuid(userId)) throw new ApiError(422, 'request_invalid');
 return '/admin/users/' + userId + '/mfa';
}
export function validateMfaAccountStatus(value: any, expectedUserId: string): MfaAccountStatus {
 const flags = ['available', 'required', 'enrollmentPending', 'globalPolicyEnabled', 'deadlineReached', 'globalAdministratorExempt', 'sessionMfaVerified', 'canEnable', 'canDisable', 'canReset'];
 if (!uuid(expectedUserId) || value?.userId !== expectedUserId || typeof value.userName !== 'string' || !value.userName || value.userName.length > 200 || !revision(value.revision) || !['none', 'pending', 'active', 'disabled'].includes(value.factorState) || !flags.every(name => typeof value[name] === 'boolean') || !utc(value.serverNowUtc) || !(value.graceDays === null || (Number.isSafeInteger(value.graceDays) && value.graceDays > 0)) || !(value.deadlineUtc === null || utc(value.deadlineUtc)) || !(value.daysRemaining === null || (Number.isSafeInteger(value.daysRemaining) && value.daysRemaining >= 0)) || ((value.deadlineUtc === null) !== (value.daysRemaining === null))) throw new ApiError(200, 'response_invalid');
 return value;
}
function requireActor(api: RackClickApi, actorId: string) {
 if (!uuid(actorId) || api.actorId !== actorId) throw new ApiError(409, 'actor_changed');
}
function requireDraft(api: RackClickApi, draft: MfaAccountDraft) {
 if (!validMfaAccountDraft(draft)) throw new ApiError(422, 'request_invalid');
 requireActor(api, draft.actorId);
}
const draftPath = (draft: MfaAccountDraft) => mfaAccountPath(draft.scope === 'self' ? undefined : draft.userId);
export async function readMfaAccount(api: RackClickApi, userId?: string): Promise<MfaAccountStatus> {
 const actorId = api.actorId;
 requireActor(api, actorId);
 const expected = userId === undefined ? actorId : userId;
 const { data, etag } = await api.request(mfaAccountPath(userId));
 requireActor(api, actorId);
 const status = validateMfaAccountStatus(data, expected);
 if (etag !== null && etag !== '"' + status.revision + '"') throw new ApiError(200, 'response_invalid');
 return status;
}
export function confirmedMfaAccountChange(data: any, draft: MfaAccountDraft): MfaAccountReceipt {
 if (!validMfaAccountDraft(draft) || data?.userId !== draft.userId || data.action !== draft.action || data.requestId !== draft.requestId || data.systemhausRevision !== draft.revision + 1 || typeof data.signInRequired !== 'boolean' || data.signInRequired !== (draft.userId === draft.actorId)) throw new ApiError(200, 'response_invalid', true);
 try {
  const status = validateMfaAccountStatus(data.resource, draft.userId);
  if (status.revision !== data.systemhausRevision) throw new ApiError(200, 'response_invalid');
  if ((draft.action === 'enable' && !status.required) || (draft.action === 'disable' && (status.required || status.enrollmentPending || status.factorState === 'active')) || (draft.action === 'reset' && (!status.required || !status.enrollmentPending))) throw new ApiError(200, 'response_invalid');
 } catch { throw new ApiError(200, 'response_invalid', true); }
 return data;
}
export async function changeMfaAccount(api: RackClickApi, draft: MfaAccountDraft, password = ''): Promise<MfaAccountReceipt> {
 requireDraft(api, draft);
 if (draft.scope === 'self' && (typeof password !== 'string' || password.length < 1 || password.length > 1024)) throw new ApiError(422, 'password_length');
 const data = await api.sendMutation({ path: draftPath(draft) + '/' + draft.action, method: 'POST', actorId: draft.actorId, requestId: draft.requestId, etag: '"' + draft.revision + '"', body: JSON.stringify(draft.scope === 'self' ? { password } : {}) });
 requireDraft(api, draft);
 return confirmedMfaAccountChange(data, draft);
}
export async function mfaAccountChangeStatus(api: RackClickApi, draft: MfaAccountDraft): Promise<MfaAccountReceipt | null> {
 requireDraft(api, draft);
 const { data } = await api.request(draftPath(draft) + '/operations/' + draft.requestId);
 requireDraft(api, draft);
 if (data?.requestId !== draft.requestId || !['committed', 'notRecorded'].includes(data.state)) throw new ApiError(200, 'response_invalid', true);
 if (data.state === 'committed') return confirmedMfaAccountChange(data.operation, draft);
 if (data.operation !== null) throw new ApiError(200, 'response_invalid', true);
 return null; // Not recorded never means cancelled or permission to send another request ID.
}

// Only public intention is durable. Passwords, TOTP codes, cookies and setup material never enter this journal.
export async function mfaAccountJournal(operation: 'read' | 'write' | 'remove', actorId: string, draft?: MfaAccountDraft): Promise<MfaAccountDraft | null> {
 if (!uuid(actorId) || (operation !== 'read' && (!validMfaAccountDraft(draft) || draft.actorId !== actorId))) throw new ApiError(0, 'draft_storage_unavailable');
 const db: IDBDatabase = await new Promise((resolve, reject) => {
  let blocked = false;
  const request = indexedDB.open('RackClick.MfaAccount.v1', 1);
  request.onupgradeneeded = () => request.result.createObjectStore('pending', { keyPath: 'actorId' });
  request.onsuccess = () => { if (blocked) request.result.close(); else resolve(request.result); };
  request.onerror = request.onblocked = () => { blocked = true; reject(new ApiError(0, 'draft_storage_unavailable')); };
 });
 try {
  return await new Promise((resolve, reject) => {
   const tx = db.transaction('pending', operation === 'read' ? 'readonly' : 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
   let result: MfaAccountDraft | null = null;
   tx.oncomplete = () => resolve(result);
   tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
   const request = store.get(actorId);
   request.onsuccess = () => {
    const old = request.result;
    if (old && (!validMfaAccountDraft(old) || old.actorId !== actorId)) { tx.abort(); return; }
    if (operation === 'read') { result = old || null; return; }
    if (old && (Object.keys(old) as (keyof MfaAccountDraft)[]).some(name => old[name] !== draft![name])) { tx.abort(); return; }
    if (operation === 'write') { store.put(draft); result = draft!; } else store.delete(actorId);
   };
  });
 } finally { db.close(); }
}
