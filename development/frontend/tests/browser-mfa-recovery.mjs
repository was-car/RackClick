// Recovery-code GUI against an explicit isolated MFA/PG laboratory. Reuses the approved dashboard CDP harness.
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
if (!rawOrigin || !username || !password || !output) throw Error('Explicit isolated MFA dashboard laboratory required.');
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
let ownIntention = null, browser, stage = 'browser_start', secretAdmin = '', secretOrdinary = '', recoveryCode = '';
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
 const info=await poll(async()=>{const r=await fetch(`http://127.0.0.1:${port}/json/version`);return r.ok?r.json():null;},'Edge startup');browser=await CDP.connect(info.webSocketDebuggerUrl);
 stage='initial_enrollment';const first=await context();await login(first,username);secretAdmin=await enroll(first);checks.push('first_enrollment_required_before_session');
 await ownPanel(first);await first.wait(`!!document.querySelector('[data-mfa-recovery-panel]')`,'recovery panel');await first.click('[data-mfa-recovery-panel] summary');
 await first.wait(`!!document.querySelector('[data-mfa-recovery-password]')`,'verified session can generate');
 assert.equal(await first.evaluate(`document.querySelector('[data-mfa-recovery-generate]').disabled`),true);
 stage='generate_codes';await first.field('[data-mfa-recovery-password]',password);await first.click('[data-mfa-recovery-ack]');await first.click('[data-mfa-recovery-generate]');
 await first.wait(`document.querySelectorAll('[data-mfa-recovery-values] li code').length===10`,'ten codes after server confirmation');
 const codes=await first.evaluate(`([...document.querySelectorAll('[data-mfa-recovery-values] li code')]).map(e=>e.textContent)`);assert.equal(new Set(codes).size,10);assert.ok(codes.every(c=>/^(?:[A-F0-9]{4}-){7}[A-F0-9]{4}$/.test(c)));
 recoveryCode=codes[0];
 assert.equal(await first.evaluate(`(()=>{const codes=${JSON.stringify(codes)};return[localStorage,sessionStorage].every(s=>Object.values(s).every(v=>codes.every(c=>!v.includes(c))))})()`),true);
 await first.click('[data-mfa-recovery-hide]');assert.equal(await first.evaluate(`!!document.querySelector('[data-mfa-recovery-values]')`),false);checks.push('ten_private_one_time_values_never_in_browser_storage');
 stage='lost_authenticator';const second=await context();await login(second,username);await second.wait(`!!document.querySelector('[data-mfa-purpose="verify"]')`,'verify challenge');await second.click('[data-mfa-use-recovery]');
 await second.wait(`!!document.querySelector('[data-mfa-recovery-code="true"]')`,'recovery input');await second.field('[data-mfa-code]',recoveryCode);await second.click('[data-mfa-submit]');
 await second.wait(`!!document.querySelector('[data-mfa-purpose="enroll"]')`,'fresh enrollment challenge');assert.equal(await second.evaluate(`fetch('/api/v1/me').then(r=>r.status)`),401);assert.equal(await first.evaluate(`fetch('/api/v1/me').then(r=>r.status)`),401);checks.push('recovery_revokes_old_session_and_grants_no_api_authority');
 stage='new_factor';secretOrdinary=await enroll(second);assert.notEqual(secretAdmin,secretOrdinary);await ownPanel(second);await second.click('[data-mfa-recovery-panel] summary');await second.wait(`document.querySelector('[data-mfa-recovery-remaining]')?.textContent.includes('0')`,'old codes retired');
 assert.equal(await second.evaluate(`fetch('/api/v1/me').then(r=>r.status)`),200);assert.equal(exceptions.length,0);checks.push('only_confirmed_new_authenticator_restores_full_access');
 await writeFile(path.join(output,'browser-mfa-recovery-result.json'),JSON.stringify({result:'PASS',checks,responses,browser:info.Browser,provider:'synthetic-test-DI',transport:'Kestrel-loopback-HTTP',serviceTokenTested:false,productionOrQaEnabled:false,runtimeExceptions:exceptions.length},null,2)+'\n');
 console.log(JSON.stringify({result:'PASS',checks:checks.length}));
} catch {
 await writeFile(path.join(output,'browser-mfa-recovery-result.json'),JSON.stringify({result:'FAIL',checks,responses,failedStage:stage,runtimeExceptions:exceptions.length,productionOrQaEnabled:false},null,2)+'\n');console.error('Recovery browser scenario failed; sanitized stage retained.');process.exitCode=1;
} finally {
 secretAdmin='';secretOrdinary='';recoveryCode='';ownIntention=null;
 if(browser)try{await browser.send('Browser.close');}catch{}
 for(const socket of sockets)socket.close();if(edge.exitCode===null)edge.kill();
}
