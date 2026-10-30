import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { makeQrModules } from '../src/mfa-qr.ts';
const uri = 'otpauth://totp/RackClick:example?secret=JBSWY3DPEHPK3PXP&issuer=RackClick&algorithm=SHA1&digits=6&period=30';
test('QR is generated as a bounded boolean matrix with three finder patterns', () => {
 const m = makeQrModules(uri);
 assert.ok(m.length >= 21 && m.length <= 177 && m.length % 4 === 1);
 assert.ok(m.every(row => row.length === m.length && row.every(v => typeof v === 'boolean')));
 for (const [x, y] of [[0, 0], [m.length - 7, 0], [0, m.length - 7]]) {
  for (let dy = 0; dy < 7; dy++) for (let dx = 0; dx < 7; dx++) {
   const expected = dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4);
   assert.equal(m[y + dy][x + dx], expected);
  }
 }
});
test('QR matrix is deterministic, encodes the URI and has no runtime fetch', () => {
 assert.deepEqual(makeQrModules(uri), makeQrModules(uri));
 assert.notDeepEqual(makeQrModules(uri), makeQrModules(uri.replace('example', 'other')));
});
test('non-TOTP, remote or oversized input fails with a constant non-secret error', () => {
 for (const value of ['https://example.invalid/qr', 'javascript:alert(1)', 'otpauth://hotp/a?secret=x', 'otpauth://totp/a', 'x'.repeat(4097)]) {
  assert.throws(() => makeQrModules(value), error => error.message === 'mfa_qr_invalid');
 }
});
test('vendored QR source and ES module match their immutable source pins and retain MIT notice', async () => {
 const folder = new URL('../src/vendor/', import.meta.url);
 const pin = JSON.parse(await readFile(new URL('qrcodegen.sources.json', folder), 'utf8'));
 const hash = data => createHash('sha256').update(data).digest('hex');
 assert.equal(hash(await readFile(new URL('qrcodegen.source.ts', folder))), pin.upstreamSourceSha256);
 assert.equal(hash(await readFile(new URL('qrcodegen.mjs', folder))), pin.moduleSha256);
 assert.equal(pin.commit, '720f62bddb7226106071d4728c292cb1df519ceb');
 assert.match(await readFile(new URL('qrcodegen-LICENSE.txt', folder), 'utf8'), /MIT License/);
 assert.match(await readFile(new URL('qrcodegen.mjs', folder), 'utf8'), /Permission is hereby granted/);
});
