import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
const sourcePath = fileURLToPath(new URL('../src/mfa-words.ts', import.meta.url));
const compiled = await build({ entryPoints: [sourcePath], bundle: true, write: false, format: 'esm', platform: 'node' });
const { mfaWords, mfaErrorState } = await import('data:text/javascript;base64,' + Buffer.from(compiled.outputFiles[0].contents).toString('base64'));

test('an invalid TOTP retains the challenge instead of restarting enrollment', () => {
 assert.deepEqual(mfaErrorState({ status: 401, code: 'mfa_code_invalid' }), { key: 'codeInvalid', restart: false });
});
test('expired or wrong-purpose challenges require a new login', () => {
 for (const code of ['mfa_challenge_invalid', 'mfa_enrollment_not_started', 'mfa_enrollment_required', 'mfa_step_stale']) {
  assert.deepEqual(mfaErrorState({ status: 401, code }), { key: 'expired', restart: true });
 }
});
test('CSRF or origin rejection cannot keep a usable confirmation form', () => {
 assert.deepEqual(mfaErrorState({ status: 403, code: 'csrf_invalid' }), { key: 'rejected', restart: true });
 assert.deepEqual(mfaErrorState({ status: 403, code: 'origin_invalid' }), { key: 'rejected', restart: true });
});
test('an uncertain response clears setup and requires checking by a new login', () => {
 for (const error of [{ status: 0 }, { code: 'network_unconfirmed' }, { status: 200, uncertain: true }]) {
  assert.deepEqual(mfaErrorState(error), { key: 'uncertain', restart: true });
 }
});
test('a rejected setup start cannot automatically create another pending factor', () => {
 assert.deepEqual(mfaErrorState({ status: 429, code: 'rate_limited' }, true), { key: 'limited', restart: true });
 assert.deepEqual(mfaErrorState({ status: 429, code: 'rate_limited' }), { key: 'limited', restart: false });
});
test('known service-unavailable errors are displayed without claiming success', () => {
 for (const code of ['mfa_unavailable', 'service_unavailable']) {
  assert.deepEqual(mfaErrorState({ status: 503, code, uncertain: true }), { key: 'unavailable', restart: true });
 }
});
test('malformed responses require a new login and never emit raw server text', () => {
 assert.deepEqual(mfaErrorState({ status: 200, code: 'response_invalid' }), { key: 'responseInvalid', restart: true });
 assert.deepEqual(mfaErrorState({ code: 'CANARY-PRIVATE-TEXT' }), { key: 'error', restart: true });
});
test('all three languages contain the same complete MFA message catalog', () => {
 const keys = Object.keys(mfaWords.en).sort();
 for (const lang of ['en', 'de', 'es']) {
  assert.deepEqual(Object.keys(mfaWords[lang]).sort(), keys);
  assert.ok(Object.values(mfaWords[lang]).every(value => typeof value === 'string' && value.length > 0));
 }
});
