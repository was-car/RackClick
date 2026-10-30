import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi, allows, mutationRemainsUnconfirmed } from '../src/api.ts';
const response = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
const saved = operation => ({ resource: { id: 'customer-id', name: 'München 東京', revision: 1 }, systemhausRevision: 2, requestId: operation.requestId });
test('browser fetch receives the Window/global receiver instead of the adapter instance', async () => {
 const api = new RackClickApi(function () { assert.equal(this, globalThis); return Promise.resolve(response([])); });
 assert.deepEqual(await api.customers(), []);
});
test('lost response retries same immutable UUID/body/revision, without optimistic data', async () => {
 const requests = []; let operation;
 const api = new RackClickApi(async (url, init) => { requests.push({ url, ...init }); if (requests.length === 1) throw Error('lost after commit'); return response(saved(operation)); });
 api.actorId = 'actor-original'; api.csrf = 'session-token'; operation = api.prepare('create', 'München 東京', 1);
 await assert.rejects(api.execute(operation), e => e.uncertain && e.code === 'network_unconfirmed');
 const result = await api.execute(operation);
 assert.deepEqual(requests[0], requests[1]); assert.equal(result.resource.name, 'München 東京');
 assert.equal(requests[0].headers['If-Match'], '"1"'); assert.equal(requests[0].credentials, 'same-origin');
 assert.equal(requests[0].headers['X-RackClick-CSRF'], 'session-token'); assert.ok(Object.isFrozen(operation));
});
test('stale revision is conflict and remains a rejected mutation', async () => {
 const api = new RackClickApi(async () => response({ error: 'revision_conflict' }, 412)); api.actorId = 'actor-original'; api.csrf = 'csrf';
 await assert.rejects(api.execute(api.prepare('house', 'Draft', 2)), e => e.status === 412 && !e.uncertain);
});
for (const status of [401, 403]) test('lost commit response then ' + status + ' preserves original operation identity for recovery', async () => {
 const calls = []; let operation;
 const api = new RackClickApi(async (url, init) => { calls.push({ url, ...init }); if (calls.length === 1) throw Error('response lost after commit'); if (calls.length === 2) return response({ error: 'authorization_changed' }, status); return response(saved(operation)); });
 api.actorId = 'actor-original'; api.csrf = 'csrf'; operation = api.prepare('create', 'Only one customer', 1); let pending = false;
 for (let attempt = 0; attempt < 2; attempt++) { try { await api.execute(operation); assert.fail('Expected unconfirmed attempt'); } catch (error) { pending = mutationRemainsUnconfirmed(pending, error); if (!pending) operation = null; } }
 assert.equal(pending, true); assert.ok(operation); const result = await api.execute(operation);
 assert.equal(result.requestId, operation.requestId); assert.equal(new Set(calls.map(c => c.headers['Idempotency-Key'])).size, 1); assert.equal(new Set(calls.map(c => c.body)).size, 1);
});
test('503 write is unconfirmed and can retain its idempotency key', async () => {
 const api = new RackClickApi(async () => response({ error: 'service_unavailable' }, 503)); api.actorId = 'actor-original'; api.csrf = 'csrf';
 await assert.rejects(api.execute(api.prepare('create', 'Draft', 2)), e => e.uncertain && e.status === 503);
});
test('200 without committed resource never becomes success', async () => {
 const api = new RackClickApi(async () => response({ ok: true })); api.actorId = 'actor-original'; api.csrf = 'csrf';
 await assert.rejects(api.execute(api.prepare('house', 'Draft', 1)), e => e.uncertain && e.code === 'response_invalid');
});
test('a response for a different request ID never becomes success', async () => {
 let operation; const api = new RackClickApi(async () => response({ ...saved(operation), requestId: 'wrong-operation' })); api.actorId = 'actor-original'; api.csrf = 'csrf'; operation = api.prepare('create', 'Draft', 1);
 await assert.rejects(api.execute(operation), e => e.uncertain);
});
test('truncated successful JSON retains an unconfirmed write', async () => {
 const api = new RackClickApi(async () => new Response('{"resource":', { status: 200 })); api.actorId = 'actor-original'; api.csrf = 'csrf';
 await assert.rejects(api.execute(api.prepare('house', 'Draft', 1)), e => e.uncertain);
});
test('missing CSRF blocks sending a write', async () => {
 let sent = false; const api = new RackClickApi(async () => { sent = true; return response({}); });
 await assert.rejects(api.execute(api.prepare('house', 'Draft', 1)), e => e.status === 401); assert.equal(sent, false);
});
test('reauthenticated different actor cannot resend original pending mutation', async () => {
 const calls = []; let operation; const api = new RackClickApi(async (url, init) => { calls.push(init); if (calls.length === 1) throw Error('response lost'); return response(saved(operation)); });
 api.actorId = 'original'; api.csrf = 'original-csrf'; operation = api.prepare('create', 'Once only', 1);
 await assert.rejects(api.execute(operation), e => e.uncertain);
 api.actorId = 'different'; api.csrf = 'different-csrf';
 await assert.rejects(api.execute(operation), e => e.code === 'actor_changed'); assert.equal(calls.length, 1);
 api.actorId = 'original'; api.csrf = 'new-original-csrf'; await api.execute(operation);
 assert.equal(calls.length, 2); assert.equal(calls[0].headers['Idempotency-Key'], calls[1].headers['Idempotency-Key']); assert.equal(calls[1].headers['X-RackClick-Actor'], 'original');
});
test('customer IDs are encoded and used instead of duplicate names', () => {
 const api = new RackClickApi(); const a = api.prepare('customer', 'Equal', 1, 'first'); const b = api.prepare('customer', 'Equal', 1, 'second');
 assert.notEqual(a.path, b.path); assert.notEqual(a.requestId, b.requestId); assert.equal(a.body, b.body);
});
test('ETag must match Systemhaus DTO revision', async () => {
 const api = new RackClickApi(async () => response({ id: 'house', name: 'House', revision: 3 }, 200, { ETag: '"2"' }));
 await assert.rejects(api.house(), e => e.code === 'response_invalid');
});
test('effective permissions use capabilities and exact customer ID', () => {
 const session = { permissions: { systemhausCapabilities: ['systemhaus.read'], customers: [{ customerId: 'allowed', capabilities: ['inventory.read', 'customer.manage'] }] } };
 assert.equal(allows(session, 'systemhaus.read'), true); assert.equal(allows(session, 'systemhaus.manage'), false); assert.equal(allows(session, 'customer.manage', 'allowed'), true); assert.equal(allows(session, 'customer.manage', 'foreign'), false); assert.equal(allows(null, 'customer.manage', 'allowed'), false);
});
test('canonical login/logout route and session CSRF refresh', async () => {
 const calls = []; const api = new RackClickApi(async (url, init) => { calls.push({ url, init }); if (url.endsWith('/auth/login')) return response({ csrf: 'first' }); if (url.endsWith('/me')) return response({ user: { id: 'u' }, csrf: 'fresh', permissions: { systemhausCapabilities: [], customers: [] } }); return new Response(null, { status: 204 }); });
 await api.login('ÜSER', 'synthetic-password'); await api.logout();
 assert.deepEqual(calls.map(c => c.url), ['/api/v1/auth/login', '/api/v1/me', '/api/v1/auth/logout']); assert.equal(calls[2].init.headers['X-RackClick-CSRF'], 'fresh'); assert.equal(api.csrf, '');
});
test('dictionary keys remain complete in EN/DE/ES', async () => {
 const { words } = await import('../src/words.ts'); const keys = Object.keys(words.en).sort();
 for (const lang of ['de', 'es']) { assert.deepEqual(Object.keys(words[lang]).sort(), keys); assert.ok(Object.values(words[lang]).every(s => typeof s === 'string' && s.length)); }
});
