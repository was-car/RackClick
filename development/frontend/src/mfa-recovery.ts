import { ApiError, type RackClickApi } from './api.ts';
export type RecoveryDraft = Readonly<{ actorId: string; requestId: string; revision: number }>;
export type RecoveryStatus = Readonly<{ userId: string; remaining: number; revision: number; canGenerate: boolean; sessionMfaVerified: boolean }>;
export type RecoveryGeneration = Readonly<{ userId: string; requestId: string; remaining: number; systemhausRevision: number; codesAvailable: boolean; codes: string[] | null }>;
const uuid = (v: any) => typeof v === 'string' && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(v) && !/^0{8}-0{4}-0{4}-0{4}-0{12}$/.test(v);
const revision = (v: any) => Number.isSafeInteger(v) && v > 0 && v < Number.MAX_SAFE_INTEGER;
export const recoveryCodeFormat = (v: any) => typeof v === 'string' && /^(?:[a-f0-9]{32}|(?:[a-f0-9]{4}-){7}[a-f0-9]{4})$/i.test(v.trim());
export function validRecoveryDraft(v: any): v is RecoveryDraft {
 return !!v && Object.keys(v).sort().join() === 'actorId,requestId,revision' && uuid(v.actorId) && uuid(v.requestId) && revision(v.revision);
}
function actor(api: RackClickApi, id: string) { if (!uuid(id) || api.actorId !== id) throw new ApiError(409, 'actor_changed'); }
export function validateRecoveryStatus(value: any, id: string): RecoveryStatus {
 if (value?.userId !== id || !uuid(id) || !revision(value?.revision) || !Number.isInteger(value.remaining) || value.remaining < 0 || value.remaining > 10 || typeof value.canGenerate !== 'boolean' || typeof value.sessionMfaVerified !== 'boolean') throw new ApiError(200, 'response_invalid');
 return value;
}
export function validateRecoveryGeneration(value: any, draft: RecoveryDraft, receipt = false): RecoveryGeneration {
 if (!validRecoveryDraft(draft) || value?.userId !== draft.actorId || value?.requestId !== draft.requestId || !revision(value?.systemhausRevision) || !Number.isInteger(value.remaining) || value.remaining < 0 || value.remaining > 10 || typeof value.codesAvailable !== 'boolean') throw new ApiError(200, 'response_invalid', true);
 if (value.codesAvailable) {
  if (receipt || value.remaining !== 10 || !Array.isArray(value.codes) || value.codes.length !== 10 || new Set(value.codes.map((c: any) => String(c).replaceAll('-', '').toUpperCase())).size !== 10 || !value.codes.every(recoveryCodeFormat)) throw new ApiError(200, 'response_invalid', true);
 } else if (value.codes !== null) throw new ApiError(200, 'response_invalid', true);
 return value;
}
export async function readRecoveryStatus(api: RackClickApi): Promise<RecoveryStatus> {
 const id = api.actorId; actor(api,id); const { data } = await api.request('/me/mfa/recovery-codes'); actor(api,id);
 return validateRecoveryStatus(data,id);
}
export async function generateRecoveryCodes(api: RackClickApi, draft: RecoveryDraft, password: string): Promise<RecoveryGeneration> {
 if (!validRecoveryDraft(draft) || typeof password !== 'string' || !password || password.length > 1024) throw new ApiError(422,'request_invalid');
 actor(api,draft.actorId);
 const { data } = await api.request('/me/mfa/recovery-codes', { method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':draft.actorId,'If-Match':'"'+draft.revision+'"','Idempotency-Key':draft.requestId},body:JSON.stringify({password}) });
 actor(api,draft.actorId);return validateRecoveryGeneration(data,draft);
}
export async function recoveryCodesReceipt(api: RackClickApi,draft:RecoveryDraft):Promise<RecoveryGeneration|null> {
 if (!validRecoveryDraft(draft)) throw new ApiError(422,'request_invalid'); actor(api,draft.actorId);
 const {data}=await api.request('/me/mfa/recovery-codes/operations/'+draft.requestId);actor(api,draft.actorId);
 if (data?.requestId!==draft.requestId || typeof data?.recorded!=='boolean') throw new ApiError(200,'response_invalid');
 if (!data.recorded) return null;return validateRecoveryGeneration(data.result,draft,true);
}
// Journal only opaque intent, never password, recovery values, or TOTP material.
export function recoveryCodesJournal(action:'read'|'write'|'remove',id:string,draft?:RecoveryDraft,storage?:Storage):RecoveryDraft|null {
 if (!uuid(id) || (draft && (!validRecoveryDraft(draft)||draft.actorId!==id))) throw new ApiError(422,'request_invalid');
 try {
  const target=storage||globalThis.sessionStorage,key='RackClick.mfa-recovery.intent.v1.'+id;
  if (!target) throw new Error();
  if(action==='write'){if(!draft)throw new Error();target.setItem(key,JSON.stringify(draft));return draft;}
  if(action==='remove'){target.removeItem(key);return null;}
  const raw=target.getItem(key);if(!raw)return null;const value=JSON.parse(raw);
  if(!validRecoveryDraft(value)||value.actorId!==id)throw new Error();return value;
 } catch {throw new ApiError(0,'journal_unavailable');}
}
