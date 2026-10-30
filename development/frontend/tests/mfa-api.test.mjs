import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi } from '../src/api.ts';

const response = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const session = { user: { id: 'actor', houseId: 'house', userName: 'usuario' }, csrf: 'session-csrf', permissions: { systemhausCapabilities: [], customers: [] } };
const challengeReply = purpose => response({ mfaRequired: true, purpose, csrf: 'challenge-csrf' }, 202);
const enrollment = { secret: 'JBSWY3DPEHPK3PXP', otpauth: 'otpauth://totp/RackClick:usuario?secret=JBSWY3DPEHPK3PXP&issuer=RackClick&algorithm=SHA1&digits=6&period=30' };

test('202 pauses login, grants no actor/session CSRF and does not call me', async () => {
 const calls = []; let challenge, rejectPrompt;
 const api = new RackClickApi(async (path, init) => { calls.push(path); return challengeReply('verify'); });
 api.csrf = 'old-session'; api.actorId = 'old-actor';
 api.onMfaRequired = step => { challenge = step; return new Promise((resolve, reject) => { rejectPrompt = reject; }); };
 const login = api.login('usuario', 'not-persisted');
 await new Promise(resolve => setTimeout(resolve, 0));
 assert.equal(challenge?.purpose, 'verify'); assert.deepEqual(calls, ['/api/v1/auth/login']);
 assert.equal(api.actorId, ''); assert.equal(api.csrf, '');
 api.cancelAuthentication(); rejectPrompt(Object.assign(new Error(), { code: 'mfa_cancelled' }));
 await assert.rejects(login);
});

test('enrollment uses challenge CSRF and installs authority only after final response and me', async () => {
 const calls = [];
 const api = new RackClickApi(async (path, init) => {
  calls.push({ path, init });
  if (path.endsWith('/auth/login')) return challengeReply('enroll');
  if (path.endsWith('/enroll/start')) return response(enrollment);
  if (path.endsWith('/enroll/confirm')) { assert.equal(api.csrf, ''); assert.equal(api.actorId, ''); return response({ csrf: 'session-csrf' }); }
  if (path.endsWith('/me')) return response(session);
  throw Error('unexpected endpoint');
 });
 api.onMfaRequired = async step => {
  assert.equal((await api.startMfaEnrollment(step)).secret, enrollment.secret);
  return api.confirmMfaEnrollment(step, '012345');
 };
 assert.deepEqual(await api.login('usuario', 'not-persisted'), session);
 assert.equal(api.csrf, 'session-csrf'); assert.equal(api.actorId, 'actor');
 for (const call of calls.filter(c => c.path.includes('/mfa/'))) assert.equal(call.init.headers['X-RackClick-CSRF'], 'challenge-csrf');
 assert.equal(calls.find(c => c.path.endsWith('/confirm')).init.body, '{"code":"012345"}');
 assert.equal(calls.filter(c => c.path.endsWith('/me')).length, 1);
});

test('invalid code can be corrected without a session, restart or automatic duplicate POST', async () => {
 let verifies = 0; let me = 0;
 const api = new RackClickApi(async path => {
  if (path.endsWith('/auth/login')) return challengeReply('verify');
  if (path.endsWith('/verify')) return ++verifies === 1 ? response({ error: 'mfa_code_invalid' }, 401) : response({ csrf: 'session-csrf' });
  if (path.endsWith('/me')) { me++; return response(session); }
 });
 api.onMfaRequired = async step => {
  await assert.rejects(api.verifyMfa(step, '000000'), e => e.code === 'mfa_code_invalid');
  assert.equal(api.actorId, ''); assert.equal(api.csrf, ''); assert.equal(me, 0);
  return api.verifyMfa(step, '012345');
 };
 await api.login('usuario', 'not-persisted'); assert.equal(verifies, 2); assert.equal(me, 1);
});

test('purpose cannot be crossed and enrollment start cannot silently regenerate a pending secret', async () => {
 let starts = 0;
 const api = new RackClickApi(async path => {
  if (path.endsWith('/auth/login')) return challengeReply('enroll');
  if (path.endsWith('/enroll/start')) { starts++; return response(enrollment); }
  if (path.endsWith('/confirm')) return response({ csrf: 'session-csrf' });
  if (path.endsWith('/me')) return response(session);
 });
 api.onMfaRequired = async step => {
  await assert.rejects(api.verifyMfa(step, '012345'), e => e.code === 'mfa_challenge_invalid');
  await api.startMfaEnrollment(step);
  await assert.rejects(api.startMfaEnrollment(step), e => e.code === 'mfa_enrollment_already_started');
  return api.confirmMfaEnrollment(step, '012345');
 };
 await api.login('usuario', 'not-persisted'); assert.equal(starts, 1);
});

test('invalid challenge contract is rejected before me or authority assignment', async () => {
 let calls = 0;
 const api = new RackClickApi(async () => { calls++; return response({ mfaRequired: true, purpose: 'admin-bypass', csrf: 'challenge' }, 202); });
 await assert.rejects(api.login('usuario', 'not-persisted'), e => e.code === 'response_invalid');
 assert.equal(calls, 1); assert.equal(api.actorId, ''); assert.equal(api.csrf, '');
});

test('missing challenge UI fails closed instead of treating challenge CSRF as a session', async () => {
 let calls = 0;
 const api = new RackClickApi(async () => { calls++; return challengeReply('verify'); });
 await assert.rejects(api.login('usuario', 'not-persisted'), e => e.code === 'mfa_required');
 assert.equal(calls, 1); assert.equal(api.csrf, ''); assert.equal(api.actorId, '');
});

test('public me cannot restore an old cookie session during a pending challenge', async () => {
 let calls = 0; let rejectPrompt;
 const api = new RackClickApi(async () => { calls++; return challengeReply('verify'); });
 api.onMfaRequired = () => new Promise((resolve, reject) => { rejectPrompt = reject; });
 const login = api.login('usuario', 'not-persisted'); await new Promise(resolve => setTimeout(resolve, 0));
 await assert.rejects(api.me(), e => e.code === 'authentication_required'); assert.equal(calls, 1);
 api.cancelAuthentication(); rejectPrompt(new Error('cancelled')); await assert.rejects(login);
});

test('cancelled verification cannot install a late success or make a me request', async () => {
 let release, pending, me = 0;
 const api = new RackClickApi(async path => {
  if (path.endsWith('/auth/login')) return challengeReply('verify');
  if (path.endsWith('/verify')) return new Promise(resolve => { release = resolve; });
  if (path.endsWith('/me')) { me++; return response(session); }
 });
 api.onMfaRequired = step => (pending = api.verifyMfa(step, '012345'));
 const login = api.login('usuario', 'not-persisted'); await new Promise(resolve => setTimeout(resolve, 0));
 api.cancelAuthentication(); release(response({ csrf: 'session-csrf' }));
 await assert.rejects(login, e => e.code === 'authentication_changed');
 assert.equal(api.actorId, ''); assert.equal(api.csrf, ''); assert.equal(me, 0);
});

test('lost confirmation response is not retried and does not assign session authority', async () => {
 let posts = 0;
 const api = new RackClickApi(async path => {
  if (path.endsWith('/auth/login')) return challengeReply('verify');
  if (path.endsWith('/verify')) { posts++; throw Error('synthetic lost response'); }
  throw Error('must not request me');
 });
 api.onMfaRequired = step => api.verifyMfa(step, '012345');
 await assert.rejects(api.login('usuario', 'not-persisted'), e => e.code === 'network_unconfirmed' && e.uncertain);
 assert.equal(posts, 1); assert.equal(api.actorId, ''); assert.equal(api.csrf, '');
});

test('ASCII length validation preserves leading zero and rejects non-ASCII digits before POST', async () => {
 let posts = 0;
 const api = new RackClickApi(async path => {
  if (path.endsWith('/auth/login')) return challengeReply('verify');
  if (path.endsWith('/verify')) { posts++; return response({ csrf: 'session-csrf' }); }
  if (path.endsWith('/me')) return response(session);
 });
 api.onMfaRequired = async step => {
  for (const code of ['１２３４５６', '12345', '1234567', ' 123456']) await assert.rejects(api.verifyMfa(step, code), e => e.code === 'mfa_code_invalid');
  return api.verifyMfa(step, '012345');
 };
 await api.login('usuario', 'not-persisted'); assert.equal(posts, 1);
});
