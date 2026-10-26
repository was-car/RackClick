import { ApiError, type Mutation } from './api.ts';
export type PendingRecord = { requestId: string; actorId: string; customerId?: string; operation: Mutation & { customerId?: string }; label: string; summary: string; createdAt: string };
const name = 'RackClick.PendingOperations.v1';
const uuid = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
export function validPendingRecord(value: any, actorId: string): value is PendingRecord {
 if (!value || value.actorId !== actorId || !uuid(value.requestId) || value.operation?.actorId !== actorId || value.operation?.requestId !== value.requestId || typeof value.label !== 'string' || typeof value.summary !== 'string' || typeof value.createdAt !== 'string') return false;
 const op = value.operation;
 if (!/^"[1-9][0-9]*"$/.test(op.etag) || typeof op.body !== 'string') return false;
 try {
  const body = JSON.parse(op.body);
  if (value.customerId) return uuid(value.customerId) && op.customerId === value.customerId && op.method === 'POST' && op.path === '/customers/' + value.customerId + '/commands' && typeof body.type === 'string' && body.payload && typeof body.payload === 'object' && !Array.isArray(body.payload);
  return !op.customerId && typeof body.name === 'string' && ((op.method === 'PUT' && (op.path === '/systemhaus' || /^\/customers\/[0-9a-f-]{36}$/i.test(op.path))) || (op.method === 'POST' && op.path === '/customers'));
 } catch { return false; }
}
// This journal contains only commands awaiting confirmation, never an inventory snapshot or credentials.
export function pendingRecord(operation: Mutation & { customerId?: string }, label: string, summary: string): PendingRecord {
 const clean = { path: operation.path, method: operation.method, body: operation.body, etag: operation.etag, requestId: operation.requestId, actorId: operation.actorId, ...(operation.customerId ? { customerId: operation.customerId } : {}) };
 return { requestId: clean.requestId, actorId: clean.actorId, ...(operation.customerId ? { customerId: operation.customerId } : {}), operation: clean, label, summary, createdAt: new Date().toISOString() };
}
async function open(): Promise<IDBDatabase> {
 return new Promise((resolve, reject) => {
  const request = indexedDB.open(name, 1);
  request.onupgradeneeded = () => { const store = request.result.createObjectStore('pending', { keyPath: 'requestId' }); store.createIndex('actorId', 'actorId'); };
  request.onsuccess = () => resolve(request.result);
  request.onerror = () => reject(new ApiError(0, 'draft_storage_unavailable'));
  request.onblocked = () => reject(new ApiError(0, 'draft_storage_unavailable'));
 });
}
export const pendingJournal = {
 async put(value: PendingRecord) {
  if (!validPendingRecord(value, value.actorId)) throw new ApiError(0, 'draft_storage_unavailable');
  const db = await open();
  try { await new Promise<void>((resolve, reject) => {
   const tx = db.transaction('pending', 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
   tx.oncomplete = () => resolve(); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
   const read = store.get(value.requestId);
   read.onsuccess = () => { const previous = read.result; if (previous && (previous.actorId !== value.actorId || JSON.stringify(previous.operation) !== JSON.stringify(value.operation))) { tx.abort(); return; } store.put(previous || value); };
  }); } finally { db.close(); }
 },
 async list(actorId: string): Promise<PendingRecord[]> {
  const db = await open();
  try { return await new Promise((resolve, reject) => { const read = db.transaction('pending', 'readonly').objectStore('pending').index('actorId').getAll(actorId); read.onsuccess = () => read.result.every((value: unknown) => validPendingRecord(value, actorId)) ? resolve(read.result) : reject(new ApiError(0, 'draft_storage_unavailable')); read.onerror = () => reject(new ApiError(0, 'draft_storage_unavailable')); }); } finally { db.close(); }
 },
 async remove(requestId: string, actorId: string) {
  const db = await open();
  try { await new Promise<void>((resolve, reject) => {
   const tx = db.transaction('pending', 'readwrite', { durability: 'strict' }), store = tx.objectStore('pending');
   tx.oncomplete = () => resolve(); tx.onerror = tx.onabort = () => reject(new ApiError(0, 'draft_storage_unavailable'));
   const read = store.get(requestId); read.onsuccess = () => { if (read.result?.actorId === actorId) store.delete(requestId); };
  }); } finally { db.close(); }
 }
};
