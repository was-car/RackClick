import { ApiError, allows, type RackClickApi, type Session } from './api.ts';

export const INVENTORY_ARCHIVE_MAX_BYTES = 33554432;
export const inventoryDataCountKeys = ['customers','sites','buildings','rooms','racks','devices','portGroups','ports','connections'] as const;
type Counts = Record<typeof inventoryDataCountKeys[number], number>;
export type InventoryDataContext = { actorId: string; houseId: string; origin: string };
export type InventoryDataAction = 'backup' | 'demo50' | 'restore';
export type InventoryDataIntent = InventoryDataContext & { requestId: string; action: InventoryDataAction; revision: number; archiveSha256?: string; byteLength?: number };
export type InventoryDataFile = { archiveSha256: string; byteLength: number; contentBase64: string };
export type InventoryDataArchive = { format: 'RackClickInventoryBackup-v1'; filename: string; contentType: 'application/json; charset=utf-8'; encoding: 'utf-8'; byteLength: number; sha256: string; contentBase64: string };
export type InventoryDataResult = { kind: 'inventoryData'; action: InventoryDataAction; requestId: string; operationId: string; systemhausRevision: number; counts: Counts; archive: InventoryDataArchive | null };
export type InventoryDataCancelled = { state: 'cancelled'; requestId: string; operation: null };
const path = '/admin/inventory-data';
const uuid = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(x) && x !== '00000000-0000-0000-0000-000000000000';
const positive = (x: unknown): x is number => Number.isSafeInteger(x) && (x as number) > 0;
const digest = (x: unknown): x is string => typeof x === 'string' && /^[0-9a-f]{64}$/.test(x);
const exactKeys = (value: any, keys: readonly string[]) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join() === [...keys].sort().join();
const validOrigin = (x: unknown) => { try { const u = new URL(x as string); return ['http:','https:'].includes(u.protocol) && u.origin === x; } catch { return false; } };
const validContext = (x: any): x is InventoryDataContext => x && uuid(x.actorId) && uuid(x.houseId) && validOrigin(x.origin);
const sameContext = (a: InventoryDataContext, b: InventoryDataContext) => a.actorId === b.actorId && a.houseId === b.houseId && a.origin === b.origin;
function requireContext(api: RackClickApi, context: InventoryDataContext, intent?: InventoryDataIntent, uncertain = false) {
 if (!validContext(context) || api.actorId !== context.actorId || (intent && !sameContext(intent, context))) throw new ApiError(409,'actor_changed',uncertain);
}
function validCounts(value: any): value is Counts {
 return exactKeys(value,inventoryDataCountKeys) && inventoryDataCountKeys.every(key => Number.isSafeInteger(value[key]) && value[key] >= 0) && Number.isSafeInteger(inventoryDataCountKeys.reduce((sum,key) => sum + value[key],0));
}
export function inventoryDataAllowed(session: Session | null, action?: InventoryDataAction) {
 return allows(session,'systemhaus.manage') && allows(session,'security.manage') && (!action || (action === 'backup' ? allows(session,'inventory.read') && allows(session,'reports.export') : allows(session,'customer.create') && allows(session,'inventory.edit')));
}
export function validInventoryDataIntent(value: any): value is InventoryDataIntent {
 const keys = ['actorId','houseId','origin','requestId','action','revision',...(value?.action === 'restore' ? ['archiveSha256','byteLength'] : [])];
 return exactKeys(value,keys) && validContext(value) && uuid(value.requestId) && ['backup','demo50','restore'].includes(value.action) && positive(value.revision) && value.revision < Number.MAX_SAFE_INTEGER && (value.action !== 'restore' || (digest(value.archiveSha256) && positive(value.byteLength) && value.byteLength <= INVENTORY_ARCHIVE_MAX_BYTES));
}
export function prepareInventoryDataIntent(session: Session, action: InventoryDataAction, revision: number, preview: {archiveSha256: string; byteLength: number} | null, origin: string): InventoryDataIntent {
 if (!inventoryDataAllowed(session,action)) throw new ApiError(403,'inventory_data_forbidden');
 const value = {actorId:session.user.id,houseId:session.user.houseId,origin,requestId:crypto.randomUUID(),action,revision,...(action === 'restore' ? {archiveSha256:preview?.archiveSha256,byteLength:preview?.byteLength} : {})};
 if (!validInventoryDataIntent(value)) throw new ApiError(422,'request_invalid');
 return Object.freeze(value);
}
export async function readInventoryData(api: RackClickApi, context: InventoryDataContext) {
 requireContext(api,context);
 const {data} = await api.request(path);
 requireContext(api,context);
 if (!positive(data?.systemhausRevision) || typeof data.empty !== 'boolean' || !validCounts(data.counts) || data.empty !== inventoryDataCountKeys.every(k => data.counts[k] === 0) || typeof data.demo?.available !== 'boolean' || !validCounts(data.demo.counts) || !positive(data.maxArchiveBytes) || data.maxArchiveBytes > INVENTORY_ARCHIVE_MAX_BYTES) throw new ApiError(200,'response_invalid');
 return data;
}
async function sha256(bytes: Uint8Array) {
 if (!globalThis.crypto?.subtle) throw new ApiError(0,'inventory_crypto_unavailable');
 const value = await crypto.subtle.digest('SHA-256',bytes);
 return Array.from(new Uint8Array(value),byte => byte.toString(16).padStart(2,'0')).join('');
}
function decodeBase64(content: unknown, byteLength: number, code: string) {
 // Check length before atob allocates. Canonical base64 prevents ambiguous encodings.
 if (typeof content !== 'string' || content.length !== 4 * Math.ceil(byteLength / 3) || !/^[A-Za-z0-9+/]*={0,2}$/.test(content)) throw new ApiError(422,code);
 let binary: string;
 try { binary = atob(content); } catch { throw new ApiError(422,code); }
 if (binary.length !== byteLength || btoa(binary) !== content) throw new ApiError(422,code);
 return Uint8Array.from(binary,c => c.charCodeAt(0));
}
function encodeBase64(bytes: Uint8Array) {
 const parts: string[] = [];
 for (let n = 0; n < bytes.length; n += 32768) parts.push(String.fromCharCode(...bytes.subarray(n,n + 32768)));
 return btoa(parts.join(''));
}
export async function readInventoryDataFile(file: Blob, maxBytes: number): Promise<InventoryDataFile> {
 if (!positive(maxBytes) || maxBytes > INVENTORY_ARCHIVE_MAX_BYTES || !positive(file?.size) || file.size > maxBytes) throw new ApiError(422,'inventory_archive_size');
 const bytes = new Uint8Array(await file.arrayBuffer());
 if (bytes.byteLength !== file.size) throw new ApiError(422,'inventory_archive_changed');
 return {archiveSha256:await sha256(bytes),byteLength:bytes.byteLength,contentBase64:encodeBase64(bytes)};
}
async function requireFile(input: InventoryDataFile | null | undefined, expected?: InventoryDataIntent) {
 if (!input || !positive(input.byteLength) || input.byteLength > INVENTORY_ARCHIVE_MAX_BYTES || !digest(input.archiveSha256)) throw new ApiError(422,'inventory_archive_changed');
 const bytes = decodeBase64(input.contentBase64,input.byteLength,'inventory_archive_changed');
 if (await sha256(bytes) !== input.archiveSha256 || (expected && (expected.archiveSha256 !== input.archiveSha256 || expected.byteLength !== input.byteLength))) throw new ApiError(422,'inventory_archive_changed');
}
export async function previewInventoryData(api: RackClickApi, context: InventoryDataContext, input: InventoryDataFile) {
 requireContext(api,context);await requireFile(input);requireContext(api,context);
 if (!api.csrf) throw new ApiError(401,'authentication_required');
 const {data} = await api.request(path + '/preview',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':context.actorId},body:JSON.stringify({contentBase64:input.contentBase64})});
 requireContext(api,context);
 if (data?.archiveSha256 !== input.archiveSha256 || data?.byteLength !== input.byteLength || data?.format !== 'RackClickInventoryBackup-v1' || data.schemaVersion !== 48 || !validCounts(data.counts)) throw new ApiError(200,'response_invalid');
 return data;
}
function validArchive(archive: any, operationId: string): archive is InventoryDataArchive {
 return archive?.format === 'RackClickInventoryBackup-v1' && archive.filename === `rackclick-inventory-backup-${operationId}.json` && archive.contentType === 'application/json; charset=utf-8' && archive.encoding === 'utf-8' && positive(archive.byteLength) && archive.byteLength <= INVENTORY_ARCHIVE_MAX_BYTES && digest(archive.sha256) && typeof archive.contentBase64 === 'string' && archive.contentBase64.length === 4 * Math.ceil(archive.byteLength / 3);
}
export function confirmedInventoryData(data: any, intent: InventoryDataIntent): InventoryDataResult {
 if (!validInventoryDataIntent(intent) || data?.kind !== 'inventoryData' || data.action !== intent.action || data.requestId !== intent.requestId || !uuid(data.operationId) || data.systemhausRevision !== intent.revision + (intent.action === 'backup' ? 0 : 1) || !validCounts(data.counts) || (intent.action === 'backup' ? !validArchive(data.archive,data.operationId) : data.archive !== null)) throw new ApiError(200,'response_invalid',true);
 return data;
}
export async function verifyInventoryDataArchive(archive: InventoryDataArchive, operationId: string) {
 if (!uuid(operationId) || !validArchive(archive,operationId)) throw new ApiError(200,'response_invalid',true);
 const bytes = decodeBase64(archive.contentBase64,archive.byteLength,'inventory_archive_integrity');
 if (await sha256(bytes) !== archive.sha256) throw new ApiError(200,'inventory_archive_integrity',true);
 // Validate UTF-8 before presenting an inventory JSON file to the operator.
 try { new TextDecoder('utf-8',{fatal:true}).decode(bytes); } catch { throw new ApiError(200,'inventory_archive_integrity',true); }
 return {filename:archive.filename,blob:new Blob([bytes],{type:archive.contentType})};
}
export async function sendInventoryData(api: RackClickApi, intent: InventoryDataIntent, context: InventoryDataContext, input?: InventoryDataFile | null) {
 if (!validInventoryDataIntent(intent)) throw new ApiError(422,'request_invalid');
 requireContext(api,context,intent);
 if (intent.action === 'restore') await requireFile(input,intent);
 requireContext(api,context,intent);
 const body = intent.action === 'backup' ? {} : intent.action === 'demo50' ? {confirmation:'LOAD DEMO50'} : {contentBase64:input!.contentBase64,archiveSha256:intent.archiveSha256,confirmation:'RESTORE INVENTORY'};
 const data = await api.sendMutation({path:path + '/' + intent.action,method:'POST',actorId:intent.actorId,requestId:intent.requestId,etag:'"' + intent.revision + '"',body:JSON.stringify(body)});
 requireContext(api,context,intent,true);
 return confirmedInventoryData(data,intent);
}
function inventoryDataOutcome(data: any, intent: InventoryDataIntent): InventoryDataResult | InventoryDataCancelled | null {
 if (data?.requestId !== intent.requestId || !['committed','notRecorded','cancelled'].includes(data.state)) throw new ApiError(200,'response_invalid',true);
 if (data.state === 'committed') return confirmedInventoryData(data.operation,intent);
 if (data.operation !== null) throw new ApiError(200,'response_invalid',true);
 return data.state === 'cancelled' ? {state:'cancelled',requestId:intent.requestId,operation:null} : null;
}
export async function inventoryDataStatus(api: RackClickApi, intent: InventoryDataIntent, context: InventoryDataContext) {
 if (!validInventoryDataIntent(intent)) throw new ApiError(422,'request_invalid');
 requireContext(api,context,intent);
 const {data} = await api.request(path + '/operations/' + intent.requestId);
 requireContext(api,context,intent,true);
 return inventoryDataOutcome(data,intent);
}
export async function cancelInventoryData(api: RackClickApi, intent: InventoryDataIntent, context: InventoryDataContext) {
 if (!validInventoryDataIntent(intent)) throw new ApiError(422,'request_invalid');
 requireContext(api,context,intent);
 const data = await api.sendMutation({path:path + '/operations/' + intent.requestId + '/cancel',method:'POST',actorId:intent.actorId,requestId:intent.requestId,etag:'"' + intent.revision + '"',body:JSON.stringify({action:intent.action,archiveSha256:intent.action === 'restore' ? intent.archiveSha256 : null})});
 requireContext(api,context,intent,true);
 const result = inventoryDataOutcome(data,intent);
 if (!result) throw new ApiError(200,'response_invalid',true);
 return result;
}
// One small durable intention per origin/Systemhaus/actor. No archive, token,
// account, MFA material or inventory is ever written to browser storage.
export async function inventoryDataJournal(action: 'read' | 'write' | 'remove', context: InventoryDataContext, intent?: InventoryDataIntent): Promise<InventoryDataIntent | null> {
 const failure = () => new ApiError(0,'inventory_data_storage');
 if (!validContext(context) || !['read','write','remove'].includes(action) || (action !== 'read' && (!validInventoryDataIntent(intent) || !sameContext(intent,context)))) throw failure();
 const key = JSON.stringify([context.origin,context.houseId,context.actorId]);
 let db: IDBDatabase;
 try { db = await new Promise((resolve,reject) => {
  let blocked = false;const open = indexedDB.open('RackClick.AdminInventoryData.v1',1);
  open.onupgradeneeded = () => open.result.createObjectStore('pending',{keyPath:'key'});
  open.onsuccess = () => { if (blocked) open.result.close(); else resolve(open.result); };
  open.onerror = open.onblocked = () => { blocked = true;reject(failure()); };
 }); } catch { throw failure(); }
 try { return await new Promise((resolve,reject) => {
  const tx = db.transaction('pending',action === 'read' ? 'readonly' : 'readwrite',{durability:'strict'}), store = tx.objectStore('pending');let result: InventoryDataIntent | null = null;
  tx.oncomplete = () => resolve(result);tx.onerror = tx.onabort = () => reject(failure());
  const request = store.get(key);
  request.onsuccess = () => {
   const old = request.result;
   if (old && (!exactKeys(old,['key','intent']) || old.key !== key || !validInventoryDataIntent(old.intent) || !sameContext(old.intent,context))) { tx.abort();return; }
   if (action === 'read') { result = old?.intent || null;return; }
   if (old && JSON.stringify(old.intent) !== JSON.stringify(intent)) { tx.abort();return; }
   if (action === 'write') { store.put({key,intent});result = intent!; } else store.delete(key);
  };
 }); } catch { throw failure(); } finally { db.close(); }
}
export async function executeInventoryDataIntent(api: RackClickApi, intent: InventoryDataIntent, context: InventoryDataContext, input: InventoryDataFile | null, steps: {write: () => Promise<unknown>; pending: (intent: InventoryDataIntent) => void; current?: () => boolean}) {
 if (!validInventoryDataIntent(intent)) throw new ApiError(422,'request_invalid');
 requireContext(api,context,intent);
 await steps.write();
 requireContext(api,context,intent);
 if (steps.current && !steps.current()) throw new ApiError(409,'actor_changed');
 steps.pending(intent);
 // Exactly one send. A later query cannot prove an earlier lost response rolled back.
 return sendInventoryData(api,intent,context,input);
}
export async function completeInventoryDataIntent(result: InventoryDataResult | InventoryDataCancelled | null, intent: InventoryDataIntent, steps: {current: () => boolean; remember: (value: InventoryDataResult | null) => void; remove: () => Promise<unknown>; clear: () => void; reload: () => unknown; knownResult?: InventoryDataResult | null}) {
 if (!result || !steps.current()) return;
 let value: InventoryDataResult | null;
 if ('state' in result) {
  if (result.state !== 'cancelled' || result.requestId !== intent.requestId || result.operation !== null || steps.knownResult) throw new ApiError(200,'response_invalid',true);
  value = null;
 } else value = confirmedInventoryData(result,intent);
 steps.remember(value);
 await steps.remove();
 if (!steps.current()) return;
 steps.clear();await steps.reload();
}
