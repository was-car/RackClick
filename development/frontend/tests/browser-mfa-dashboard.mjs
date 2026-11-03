// Scoped Edge/CDP scenario for MFA dashboard against an explicit Kestrel/PG laboratory.
// CDP/field/TOTP helpers adapted from browser-mfa-login.mjs; that fixture remains unchanged.
// Artifacts contain only fixed check labels, route classes and status codes: no DOM, bodies, cookies, QR or credentials.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { once } from 'node:events';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { createHmac, randomUUID } from 'node:crypto';

const rawOrigin = process.env.RACKCLICK_TEST_ORIGIN, username = process.env.RACKCLICK_TEST_USERNAME;
const password = process.env.RACKCLICK_TEST_PASSWORD, ordinaryName = process.env.RACKCLICK_TEST_GRACE_USER;
const ordinaryId = process.env.RACKCLICK_TEST_GRACE_USER_ID, output = process.env.RACKCLICK_TEST_OUTPUT;
if (!rawOrigin || !username || !password || !ordinaryName || !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(ordinaryId || '') || !output) throw Error('Explicit isolated MFA dashboard laboratory required.');
const originUri = new URL(rawOrigin);
if (originUri.hostname !== '127.0.0.1' || originUri.protocol !== 'http:' || originUri.username || originUri.password || originUri.search || originUri.hash || originUri.pathname !== '/') throw Error('Explicit isolated MFA dashboard laboratory required.');
const origin = originUri.origin;
await mkdir(output, { recursive: true });
const root = path.resolve('../..'), profile = path.join(root, '.local', 'browser-mfa-dashboard', randomUUID());
await mkdir(profile, { recursive: true });
const endpoint = createServer(); endpoint.listen(0, '127.0.0.1'); await once(endpoint, 'listening');
const port = endpoint.address().port; await new Promise(resolve => endpoint.close(resolve));
const edge = spawn(process.env.RACKCLICK_EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', [
 '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-address=127.0.0.1',
 '--remote-debugging-port=' + port, '--user-data-dir=' + profile, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
const sockets = [], checks = [], responses = [], exceptions = [];
let ownIntention = null, browser, stage = 'browser_start', secretAdmin = '', secretOrdinary = '';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function poll(action, label, timeout = 25000) {
 const end = Date.now() + timeout;
 while (Date.now() < end) { try { const value = await action(); if (value) return value; } catch {} await delay(80); }
 throw Error('Fixed stage failed: ' + label);
}
function routeLabel(pathname) {
 if (pathname === '/api/v1/me/mfa') return 'self_status';
 if (pathname === '/api/v1/me') return 'current_session';
 if (pathname === '/api/v1/me/preferences') return 'preferences';
 if (pathname === '/api/v1/auth/login') return 'password_login';
 if (pathname.startsWith('/api/v1/auth/mfa/')) return 'mfa_authentication';
 if (/\/mfa\/(enable|disable|reset)$/.test(pathname)) return 'mfa_change';
 if (/\/mfa\/operations\//.test(pathname)) return 'mfa_operation_status';
 if (/\/admin\/users\/.+\/mfa$/.test(pathname)) return 'admin_status';
 return null;
}
class CDP {
 constructor(ws) {
  this.ws = ws; this.id = 0; this.pending = new Map();
  ws.addEventListener('message', event => {
   const message = JSON.parse(event.data);
   if (message.id) {
    const request = this.pending.get(message.id); if (!request) return;
    this.pending.delete(message.id); clearTimeout(request.timer);
    message.error ? request.reject(Error('CDP command failed')) : request.resolve(message.result);
   } else if (message.method === 'Runtime.exceptionThrown') exceptions.push('runtime_exception');
   else if (message.method === 'Network.responseReceived') {
    try {
     const url = new URL(message.params.response.url), route = routeLabel(url.pathname);
     if (url.origin === origin && route) responses.push({ route, status: message.params.response.status });
    } catch {}
   } else if (message.method === 'Network.requestWillBeSent') {
    const request = message.params.request;
    if (request.method !== 'POST' || request.url !== origin + '/api/v1/me/mfa/enable') return;
    const header = name => Object.entries(request.headers).find(([key]) => key.toLowerCase() === name.toLowerCase())?.[1];
    const actorId = header('X-RackClick-Actor'), requestId = header('Idempotency-Key'), rawRevision = header('If-Match');
    if (actorId && requestId && /^"[0-9]+"$/.test(rawRevision || '')) ownIntention = { actorId, userId: actorId, requestId, revision: Number(rawRevision.slice(1, -1)), action: 'enable', scope: 'self' };
   }
  });
 }
 static async connect(url) {
  const ws = new WebSocket(url);
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', () => reject(Error('CDP connection failed')), { once: true }); });
  sockets.push(ws); return new CDP(ws);
 }
 send(method, parameters = {}) {
  const id = ++this.id;
  return new Promise((resolve, reject) => {
   const timer = setTimeout(() => { this.pending.delete(id); reject(Error('CDP timeout')); }, 15000);
   this.pending.set(id, { resolve, reject, timer }); this.ws.send(JSON.stringify({ id, method, params: parameters }));
  });
 }
 async evaluate(expression) {
  const value = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (value.exceptionDetails) throw Error('Browser evaluation failed');
  return value.result.value;
 }
 wait(expression, label) { return poll(() => this.evaluate(expression), label); }
 field(selector, value) {
  return this.evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('field');const p=e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
 }
 click(selector) { return this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
}
function decodeBase32(secret) {
 const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'; let bits = 0, value = 0; const bytes = [];
 for (const character of secret.replace(/=+$/, '')) { const digit = alphabet.indexOf(character.toUpperCase()); if (digit < 0) throw Error('Invalid synthetic Base32'); value = (value << 5) | digit; bits += 5; if (bits >= 8) { bytes.push((value >>> (bits - 8)) & 255); bits -= 8; } }
 return Buffer.from(bytes);
}
function totp(secret, step = Math.floor(Date.now() / 30000)) {
 const key = decodeBase32(secret), counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(step));
 const mac = createHmac('sha1', key).update(counter).digest(); key.fill(0);
 const offset = mac[19] & 15; return String((mac.readUInt32BE(offset) & 0x7fffffff) % 1e6).padStart(6, '0');
}
async function context() {
 const context = await browser.send('Target.createBrowserContext');
 const target = await browser.send('Target.createTarget', { url: origin, browserContextId: context.browserContextId });
 const entry = await poll(async () => (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(value => value.id === target.targetId), 'target');
 const tab = await CDP.connect(entry.webSocketDebuggerUrl);
 for (const domain of ['Runtime', 'Network', 'Page']) await tab.send(domain + '.enable');
 await tab.wait(`!!document.querySelector('[name=username]')`, 'login form');
 return tab;
}
async function login(tab, name) {
 await tab.wait(`!!document.querySelector('[name=password]')&&!document.querySelector('[name=password]').form.querySelector('button[type=submit]').disabled`, 'ready password form');
 await tab.field('[name=username]', name); await tab.field('[name=password]', password);
 await tab.evaluate(`document.querySelector('[name=password]').form.requestSubmit()`);
}
async function ownPanel(tab) {
 await tab.wait(`!!document.querySelector('[data-mfa-settings-open]')`, 'security navigation');
 await tab.click('[data-mfa-settings-open]');
 await tab.wait(`!!document.querySelector('.rc-mfa-security-page [data-mfa-account-target]')`, 'own account status');
}
async function enroll(tab) {
 await tab.wait(`!!document.querySelector('[data-mfa-challenge][data-mfa-purpose="enroll"]')`, 'enrollment challenge');
 assert.equal(await tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`), 401);
 assert.ok(await tab.evaluate(`!document.querySelector('[data-mfa-secret]')`));
 await tab.click('[data-mfa-start]');
 await tab.wait(`!!document.querySelector('[data-mfa-secret]')&&!!document.querySelector('[data-mfa-qr]')`, 'local QR');
 const secret = await tab.evaluate(`document.querySelector('[data-mfa-secret]').textContent.trim()`);
 assert.ok(/^[A-Z2-7]{16,}$/i.test(secret), 'Synthetic enrollment key available');
 await tab.field('[data-mfa-code]', totp(secret));
 await tab.wait(`!document.querySelector('[data-mfa-submit]').disabled`, 'enrollment submit enabled');
 await tab.click('[data-mfa-submit]');
 await tab.wait(`!!document.querySelector('.ir-nav')&&!document.querySelector('[data-mfa-challenge]')`, 'enrolled session');
 assert.equal(await tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`), 200);
 assert.ok(await tab.evaluate(`(()=>{const value=${JSON.stringify(secret)};return [localStorage,sessionStorage].every(s=>Object.values(s).every(x=>!x.includes(value)&&!x.includes('otpauth://')))})()`));
 return secret;
}
async function confirmAction(tab, container, action, own) {
 await tab.wait(`!!document.querySelector(${JSON.stringify(container + ' [data-mfa-action="' + action + '"]')})&&!document.querySelector(${JSON.stringify(container + ' [data-mfa-action="' + action + '"]')}).disabled`, 'action available');
 await tab.click(container + ' [data-mfa-action="' + action + '"]');
 if (own) await tab.field(container + ' [data-mfa-password]', password);
 else assert.ok(await tab.evaluate(`!document.querySelector(${JSON.stringify(container + ' [data-mfa-password]')})`));
 await tab.click(container + ' [data-mfa-ack]');
 await tab.wait(`!document.querySelector(${JSON.stringify(container + ' [data-mfa-account-save]')}).disabled`, 'confirmation available');
 await tab.click(container + ' [data-mfa-account-save]');
}

try {
 const info = await poll(async () => { const response = await fetch(`http://127.0.0.1:${port}/json/version`); return response.ok ? response.json() : null; }, 'Edge startup');
 browser = await CDP.connect(info.webSocketDebuggerUrl);
 stage = 'ordinary_grace';
 const ordinary = await context(); await login(ordinary, ordinaryName);
 await ordinary.wait(`!!document.querySelector('.ir-nav')&&!!document.querySelector('[data-mfa-reminder]')`, 'ordinary grace session');
 await ownPanel(ordinary);
 assert.ok(await ordinary.evaluate(`document.querySelector('[data-mfa-account="self"] [data-mfa-grace-notice]').textContent.includes('35')`));
 assert.deepEqual(await ordinary.evaluate(`fetch('/api/v1/me/mfa').then(r=>r.json()).then(s=>({days:s.daysRemaining,exempt:s.globalAdministratorExempt,available:s.available}))`), { days: 35, exempt: false, available: true });
 checks.push('ordinary_password_session_has_server_derived_35_day_notice');

 stage = 'admin_exemption_languages';
 const admin = await context(); await login(admin, username); await admin.wait(`!!document.querySelector('.ir-nav')`, 'admin grace session');
 await ownPanel(admin);
 stage = 'admin_exemption_status';
 assert.equal(await admin.evaluate(`fetch('/api/v1/me/mfa').then(r=>r.json()).then(s=>s.globalAdministratorExempt)`), true);
 for (const [lang, title] of [['en', 'My security'], ['de', 'Meine Sicherheit'], ['es', 'Mi seguridad']]) {
  stage = 'admin_security_language_' + lang + '_ready';
  await admin.wait(`!!document.querySelector('.rc-mfa-security-page header select')&&!document.querySelector('.rc-mfa-security-page header select').disabled`, 'security language ready');
  await admin.field('.rc-mfa-security-page header select', lang);
  stage = 'admin_security_language_' + lang + '_commit';
  await admin.wait(`document.querySelector('.rc-mfa-security-page h1').textContent===${JSON.stringify(title)}`, 'security language');
  await admin.wait(`!document.querySelector('.rc-mfa-security-page header select').disabled&&!document.querySelector('[data-preferences-pending]')`, 'security language saved');
 }
 checks.push('global_admin_exemption_and_security_instructions_in_en_de_es');

 stage = 'admin_self_enable_enroll';
 await confirmAction(admin, '[data-mfa-account="self"]', 'enable', true);
 await admin.wait(`!!document.querySelector('[name=username]')&&!document.querySelector('.ir-nav')`, 'self activation ends session');
 await login(admin, username); secretAdmin = await enroll(admin);
 checks.push('self_activation_requires_password_and_server_commit_then_private_enrollment');

 stage = 'historical_receipt';
 assert.ok(ownIntention, 'Public original request metadata retained');
 await admin.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.MfaAccount.v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('pending',{keyPath:'actorId'});r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,tx=db.transaction('pending','readwrite');tx.objectStore('pending').put(${JSON.stringify(ownIntention)});tx.oncomplete=()=>{db.close();resolve(true)};tx.onerror=()=>reject(Error('journal'))}})`);
 await ownPanel(admin); await admin.wait(`!!document.querySelector('[data-mfa-account-pending]')`, 'restored historical intention');
 await admin.click('[data-mfa-account-check]');
 await admin.wait(`!document.querySelector('[data-mfa-account-pending]')&&!!document.querySelector('[data-mfa-factor-state="active"]')`, 'historical receipt resolves to current state');
 assert.ok(await admin.evaluate(`!!document.querySelector('.ir-nav')&&!document.querySelector('[name=username]')`));
 assert.equal(await admin.evaluate(`fetch('/api/v1/me').then(r=>r.status)`), 200);
 checks.push('historical_self_receipt_does_not_log_out_new_mfa_session');

 stage = 'admin_enable_ordinary';
 await admin.click('[data-admin-users]');
 await admin.wait(`!!document.querySelector('[name=adminSelectedUser]')&&!document.querySelector('[name=adminSelectedUser]').disabled`, 'shared user selection');
 await admin.field('[name=adminSelectedUser]', ordinaryId);
 await admin.wait(`!!document.querySelector('[data-mfa-account="admin"] [data-mfa-account-target="${ordinaryId}"]')`, 'selected user status');
 await confirmAction(admin, '[data-mfa-account="admin"]', 'enable', false);
 await admin.wait(`!!document.querySelector('[data-mfa-account="admin"] [data-mfa-account-result="saved"]')`, 'admin activation confirmed');
 assert.equal(await ordinary.evaluate(`fetch('/api/v1/me').then(r=>r.status)`), 401);
 checks.push('mfa_verified_admin_enables_selected_user_without_receiving_user_secrets_and_revokes_old_session');

 stage = 'ordinary_enrollment';
 await ordinary.send('Page.navigate', { url: origin }); await ordinary.wait(`!!document.querySelector('[name=username]')`, 'revoked ordinary reload');
 await login(ordinary, ordinaryName); secretOrdinary = await enroll(ordinary);
 assert.equal(await ordinary.evaluate(`fetch('/api/v1/me/mfa').then(r=>r.json()).then(s=>s.factorState)`), 'active');
 checks.push('ordinary_next_login_requires_and_completes_private_enrollment_before_access');

 // Password, enrollment and MFA-management POSTs intentionally share the existing 10/minute budget.
 // Pace this many-user harness before its next protected action; do not weaken or reset the product limiter.
 stage = 'rate_limit_window_before_reset';
 console.log(JSON.stringify({ stage, waitMilliseconds: 62000 }));
 await delay(30000); await delay(32000);
 stage = 'admin_reset_ordinary';
 await admin.click('[data-mfa-account="admin"] [data-mfa-account-refresh]');
 await admin.wait(`!!document.querySelector('[data-mfa-account="admin"] [data-mfa-factor-state="active"]')`, 'second session sees configured factor');
 await confirmAction(admin, '[data-mfa-account="admin"]', 'reset', false);
 await admin.wait(`!!document.querySelector('[data-mfa-account="admin"] [data-mfa-account-result="saved"]')&&!document.querySelector('[data-mfa-account="admin"] [data-mfa-account-confirm]')`, 'admin reset confirmed');
 assert.equal(await ordinary.evaluate(`fetch('/api/v1/me').then(r=>r.status)`), 401);
 await ordinary.send('Page.navigate', { url: origin }); await ordinary.wait(`!!document.querySelector('[name=username]')`, 'reset reload');
 await login(ordinary, ordinaryName);
 await ordinary.wait(`!!document.querySelector('[data-mfa-purpose="enroll"]')`, 'reset requires new setup');
 assert.ok(await ordinary.evaluate(`!document.querySelector('[data-mfa-secret]')&&!document.querySelector('.ir-nav')`));
 checks.push('administrator_reset_revokes_other_session_and_requires_new_private_setup');

 stage = 'subsequent_admin_verification';
 const secondAdmin = await context(); await login(secondAdmin, username);
 await secondAdmin.wait(`!!document.querySelector('[data-mfa-purpose="verify"]')`, 'subsequent verification challenge');
 await secondAdmin.field('[data-mfa-code]', totp(secretAdmin, Math.floor(Date.now() / 30000) + 1));
 await secondAdmin.wait(`!document.querySelector('[data-mfa-submit]').disabled`, 'verification submit available');
 await secondAdmin.click('[data-mfa-submit]'); await secondAdmin.wait(`!!document.querySelector('.ir-nav')`, 'subsequent MFA session');
 assert.equal(await secondAdmin.evaluate(`fetch('/api/v1/me').then(r=>r.status)`), 200);
 assert.equal(exceptions.length, 0, 'No runtime exception');
 checks.push('subsequent_admin_login_requires_totp_and_has_no_browser_runtime_exception');
 await writeFile(path.join(output, 'browser-mfa-dashboard-result.json'), JSON.stringify({ result: 'PASS', checks, responses, browser: info.Browser, provider: 'synthetic-test-DI', transport: 'real-Kestrel-loopback-HTTP', serviceTokenTested: false, productionOrQaEnabled: false }, null, 2) + '\n');
 console.log(JSON.stringify({ result: 'PASS', checks: checks.length, provider: 'synthetic-test-DI' }));
} catch {
 await writeFile(path.join(output, 'browser-mfa-dashboard-result.json'), JSON.stringify({ result: 'FAIL', checks, responses, failedStage: stage, runtimeExceptions: exceptions.length, provider: 'synthetic-test-DI', productionOrQaEnabled: false }, null, 2) + '\n');
 console.error('MFA dashboard browser scenario failed; sanitized stage retained.'); process.exitCode = 1;
} finally {
 secretAdmin = ''; secretOrdinary = ''; ownIntention = null;
 if (browser) try { await browser.send('Browser.close'); } catch {}
 for (const socket of sockets) socket.close();
 if (edge.exitCode === null) edge.kill();
}
