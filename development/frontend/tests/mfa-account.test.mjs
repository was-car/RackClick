import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { RackClickApi } from '../src/api.ts';
import { changeMfaAccount, confirmedMfaAccountChange, mfaAccountChangeStatus, mfaAccountJournal, mfaChangeRequiresReauthentication, mfaAccountPath, readMfaAccount, validMfaAccountDraft, validateMfaAccountStatus } from '../src/mfa-account.ts';
import { mfaAccountError, mfaAccountNotice, mfaAccountWords } from '../src/mfa-account-words.ts';

const actor = '12345678-1234-1234-1234-123456789abc', user = '22345678-1234-1234-1234-123456789abc';
const requestId = '32345678-1234-1234-1234-123456789abc';
const status = (userId = user, changes = {}) => ({ userId, userName: 'Synthetic <user>', available: true, required: false, enrollmentPending: false, factorState: 'none', globalPolicyEnabled: true, graceDays: 45, deadlineUtc: '2026-12-13T10:00:00+00:00', daysRemaining: 45, deadlineReached: false, globalAdministratorExempt: false, sessionMfaVerified: true, canEnable: true, canDisable: false, canReset: false, revision: 3, serverNowUtc: '2026-10-29T10:00:00Z', ...changes });
const draft = { actorId: actor, userId: user, requestId, revision: 3, action: 'enable', scope: 'admin' };
const receipt = (d = draft) => ({ userId: d.userId, action: d.action, requestId: d.requestId, systemhausRevision: 4, signInRequired: d.userId === d.actorId, resource: status(d.userId, { required: true, enrollmentPending: true, revision: 4 }) });
const json = (data, extraHeaders = {}) => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json', ...extraHeaders } });
const apiFor = fn => { const api = new RackClickApi(fn); api.actorId = actor; api.csrf = 'synthetic-session-csrf'; return api; };

test('self and selected-user status paths are distinct and target-bound', async () => {
 const calls = [], api = apiFor(async url => { calls.push(url); return json(status(url.endsWith('/me/mfa') ? actor : user), { ETag: '"3"' }); });
 assert.equal((await readMfaAccount(api)).userId, actor);
 assert.equal((await readMfaAccount(api, user)).userId, user);
 assert.deepEqual(calls, ['/api/v1/me/mfa', '/api/v1/admin/users/' + user + '/mfa']);
 assert.equal(mfaAccountPath(), '/me/mfa');
 assert.throws(() => mfaAccountPath('bad'), error => error.code === 'request_invalid');
});

for (const change of [
 { userId: actor }, { revision: 0 }, { revision: Number.MAX_SAFE_INTEGER + 1 }, { available: 'true' },
 { factorState: 'unexpected' }, { userName: null }, { userName: '' }, { serverNowUtc: 'invalid' },
 { deadlineUtc: 'invalid' }, { deadlineUtc: null }, { daysRemaining: -1 }, { daysRemaining: 2.5 },
 { graceDays: 0 }, { sessionMfaVerified: 'true' }, { canReset: undefined },
]) test('malformed status is not displayed as authoritative: ' + JSON.stringify(change), () => {
 assert.throws(() => validateMfaAccountStatus(status(user, change), user), error => error.code === 'response_invalid');
});

test('no activated policy and exempt accounts can have no deadline without inventing one', () => {
 const noDeadline = status(user, { deadlineUtc: null, daysRemaining: null, globalPolicyEnabled: false, graceDays: null });
 assert.equal(validateMfaAccountStatus(noDeadline, user), noDeadline);
 const exempt = { ...noDeadline, globalPolicyEnabled: true, graceDays: 45, globalAdministratorExempt: true };
 assert.equal(validateMfaAccountStatus(exempt, user), exempt);
 assert.equal(mfaAccountNotice(noDeadline), 'noPolicy');
 assert.equal(mfaAccountNotice(exempt), 'exempt');
});

test('status mismatching the response ETag is rejected', async () => {
 await assert.rejects(readMfaAccount(apiFor(async () => json(status(), { ETag: '"4"' })), user), error => error.code === 'response_invalid');
});

test('actor changes invalidate status reads and mutation results', async () => {
 const api = apiFor(async () => { api.actorId = user; return json(status()); });
 await assert.rejects(readMfaAccount(api, user), error => error.code === 'actor_changed');
 api.actorId = actor;
 await assert.rejects(changeMfaAccount(api, draft), error => error.code === 'actor_changed');
});

test('admin mutations retain actor, target, revision and request while never sending a password', async () => {
 const calls = [], api = apiFor(async (url, init) => { calls.push({ url, init }); return json(receipt()); });
 assert.deepEqual(await changeMfaAccount(api, draft, 'MUST_NOT_BE_SENT'), receipt());
 assert.equal(calls[0].url, '/api/v1/admin/users/' + user + '/mfa/enable');
 assert.equal(calls[0].init.body, '{}');
 assert.equal(calls[0].init.headers['If-Match'], '"3"');
 assert.equal(calls[0].init.headers['Idempotency-Key'], requestId);
 assert.equal(calls[0].init.headers['X-RackClick-Actor'], actor);
 assert.equal(calls[0].init.headers['X-RackClick-CSRF'], 'synthetic-session-csrf');
});

test('self confirmation sends the current password only in this request body', async () => {
 const own = { ...draft, scope: 'self', userId: actor }, calls = [];
 const api = apiFor(async (url, init) => { calls.push({ url, init }); return json(receipt(own)); });
 const before = JSON.stringify(own);
 assert.deepEqual(await changeMfaAccount(api, own, 'current-private-password'), receipt(own));
 assert.equal(calls[0].url, '/api/v1/me/mfa/enable');
 assert.deepEqual(JSON.parse(calls[0].init.body), { password: 'current-private-password' });
 assert.equal(JSON.stringify(own), before);
 assert.ok(!JSON.stringify(own).includes('password'));
});

for (const change of [
 { userId: actor }, { action: 'disable' }, { requestId: actor }, { systemhausRevision: 8 },
 { signInRequired: true }, { resource: status(user, { revision: 4 }) },
 { resource: status(user, { available: 'bad', revision: 4 }) },
 { resource: status(actor, { revision: 4 }) },
]) test('an incoherent committed receipt is uncertain, never success: ' + JSON.stringify(change), () => {
 const value = { ...receipt(), ...change };
 assert.throws(() => confirmedMfaAccountChange(value, draft), error => error.code === 'response_invalid' && error.uncertain);
});

test('a receipt confirms the effect of disable and reset as well as its identifiers', () => {
 const disabling = { ...draft, action: 'disable' };
 const disabled = { ...receipt(disabling), resource: status(user, { revision: 4, factorState: 'disabled', enrollmentPending: false, required: false }) };
 assert.equal(confirmedMfaAccountChange(disabled, disabling), disabled);
 assert.throws(() => confirmedMfaAccountChange({ ...disabled, resource: { ...disabled.resource, factorState: 'active' } }, disabling), error => error.uncertain);
 assert.throws(() => confirmedMfaAccountChange({ ...disabled, resource: { ...disabled.resource, required: true } }, disabling), error => error.uncertain);
 const reset = { ...draft, action: 'reset' };
 assert.ok(confirmedMfaAccountChange(receipt(reset), reset));
 assert.throws(() => confirmedMfaAccountChange({ ...receipt(reset), resource: status(user, { revision: 4, required: true, enrollmentPending: false }) }, reset), error => error.uncertain);
});

for (const change of [
 { actorId: user }, { userId: 'bad' }, { requestId: 'bad' }, { revision: 0 }, { revision: Number.MAX_SAFE_INTEGER },
 { action: 'bogus' }, { scope: 'self' }, { password: 'MUST_NOT_ENTER_JOURNAL' },
]) test('invalid intent sends no mutation: ' + JSON.stringify(change), async () => {
 let sent = false;
 const api = apiFor(async () => { sent = true; return json(receipt()); });
 const bad = { ...draft, ...change };
 await assert.rejects(changeMfaAccount(api, bad), error => ['request_invalid', 'actor_changed'].includes(error.code));
 assert.equal(sent, false);
});

test('self requests without a valid password send nothing', async () => {
 const own = { ...draft, scope: 'self', userId: actor };
 for (const password of ['', 'a'.repeat(1025), 123]) {
  let sent = false;
  await assert.rejects(changeMfaAccount(apiFor(async () => { sent = true; return json(receipt(own)); }), own, password), error => error.code === 'password_length');
  assert.equal(sent, false);
 }
});

test('operation lookup recovers the exact receipt; notRecorded is not cancellation', async () => {
 let value = { state: 'committed', requestId, operation: receipt() }, called;
 const api = apiFor(async url => { called = url; return json(value); });
 assert.deepEqual(await mfaAccountChangeStatus(api, draft), receipt());
 assert.equal(called, '/api/v1/admin/users/' + user + '/mfa/operations/' + requestId);
 value = { state: 'notRecorded', requestId, operation: null };
 assert.equal(await mfaAccountChangeStatus(api, draft), null);
 for (const invalid of [{ ...value, requestId: actor }, { ...value, state: 'cancelled' }, { ...value, operation: receipt() }]) {
  value = invalid;
  await assert.rejects(mfaAccountChangeStatus(api, draft), error => error.code === 'response_invalid' && error.uncertain);
 }
});

test('a recovered historical receipt cannot expel a later authenticated session', () => {
 const own = { ...draft, scope: 'self', userId: actor }, saved = receipt(own);
 assert.equal(saved.signInRequired, true);
 assert.equal(mfaChangeRequiresReauthentication(saved, false), true);
 assert.equal(mfaChangeRequiresReauthentication(saved, true), false);
 assert.equal(mfaChangeRequiresReauthentication(receipt(), false), false);
 assert.equal(mfaChangeRequiresReauthentication(receipt(), true), false);
});

test('deadline notices use only server decisions and days, with no local clock arithmetic', () => {
 assert.equal(mfaAccountNotice(status()), 'grace');
 assert.equal(mfaAccountNotice(status(user, { daysRemaining: 0, deadlineReached: true })), 'deadline');
 assert.equal(mfaAccountNotice(status(user, { factorState: 'active' })), 'active');
 assert.equal(mfaAccountNotice(status(user, { available: false })), 'unavailable');
 assert.equal(mfaAccountNotice(status(user, { deadlineUtc: null, daysRemaining: null, enrollmentPending: true })), 'pending');
});

test('an exempt global administrator is never shown a mandatory deadline or grace warning', () => {
 assert.equal(mfaAccountNotice(status(user, { globalAdministratorExempt: true, deadlineReached: true, daysRemaining: 0 })), 'exempt');
 assert.equal(mfaAccountNotice(status(user, { globalAdministratorExempt: true, daysRemaining: 35 })), 'exempt');
});

test('pending enrollment is immediate even during grace or for an exempt administrator', () => {
 assert.equal(mfaAccountNotice(status(user, { enrollmentPending: true, daysRemaining: 35 })), 'pending');
 assert.equal(mfaAccountNotice(status(user, { enrollmentPending: true, globalAdministratorExempt: true, daysRemaining: 35 })), 'pending');
 assert.equal(mfaAccountNotice(status(user, { enrollmentPending: true, factorState: 'active' })), 'pending');
});

test('three languages expose the same complete catalog and notification placeholder', () => {
 const keys = Object.keys(mfaAccountWords.en).sort();
 for (const lang of ['en', 'de', 'es']) {
  assert.deepEqual(Object.keys(mfaAccountWords[lang]).sort(), keys);
  assert.ok(Object.values(mfaAccountWords[lang]).every(value => typeof value === 'string' && value.length > 0));
  assert.ok(mfaAccountWords[lang].grace.includes('{days}'));
 }
});

test('errors display bounded catalog messages rather than raw server strings', () => {
 assert.equal(mfaAccountError({ code: 'private-server-message' }), 'error');
 assert.equal(mfaAccountError({ status: 412 }), 'conflict');
 assert.equal(mfaAccountError({ code: 'mfa_reauthentication_required' }), 'passwordInvalid');
 assert.equal(mfaAccountError({ code: 'mfa_required_by_policy' }), 'policyRequired');
 assert.equal(mfaAccountError({ code: 'mfa_use_self_service' }), 'selfService');
 assert.equal(mfaAccountError({ code: 'mfa_verification_required' }), 'verifySession');
 assert.equal(mfaAccountError({ status: 0, uncertain: true }), 'uncertain');
});

test('the new component bundles with the existing React-global contract and no runtime dependency', async () => {
 const result = await build({ entryPoints: [fileURLToPath(new URL('../src/MfaAccountPanel.jsx', import.meta.url))], bundle: true, write: false, format: 'iife', platform: 'browser' });
 assert.equal(result.errors.length, 0);
 assert.ok(result.outputFiles[0].text.includes('MfaAccountPanel'));
});

test('journal rejects secret-bearing intentions before opening storage', async () => {
 const previous = globalThis.indexedDB; let opened = false;
 globalThis.indexedDB = { open() { opened = true; throw new Error('should not open'); } };
 try {
  await assert.rejects(mfaAccountJournal('write', actor, { ...draft, password: 'MUST_NOT_ENTER_JOURNAL' }), error => error.code === 'draft_storage_unavailable');
  assert.equal(opened, false);
  assert.ok(validMfaAccountDraft(draft));
 } finally { globalThis.indexedDB = previous; }
});
