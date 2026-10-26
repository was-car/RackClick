// Windows Edge/CDP integration. No Playwright or additional npm dependency.
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { createServer } from 'node:net';
import { once } from 'node:events';
import path from 'node:path';
import assert from 'node:assert/strict';
const origin = process.env.RACKCLICK_TEST_ORIGIN;
const username = process.env.RACKCLICK_TEST_USERNAME, password = process.env.RACKCLICK_TEST_PASSWORD;
if (!origin || !username || !password || !['127.0.0.1', 'localhost', '[::1]'].includes(new URL(origin).hostname)) throw Error('Explicit loopback laboratory origin and locally supplied test credentials required.');
const root = path.resolve('../..'), evidence = process.env.RACKCLICK_TEST_OUTPUT || path.join(root, 'evidence/s1-20260928/frontend');
const run = new Date().toISOString().replaceAll(/[:.]/g, '-');
const profile = path.join(root, '.local/browser-test', run);
await mkdir(profile, { recursive: true }); await mkdir(evidence, { recursive: true });
const portServer = createServer(); portServer.listen(0, '127.0.0.1'); await once(portServer, 'listening'); const port = portServer.address().port; await new Promise(r => portServer.close(r));
const edge = process.env.RACKCLICK_EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const child = spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + port, '--user-data-dir=' + profile, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const clients = [], checks = [], errors = [], responses = [];
let lastTab;
const delay = ms => new Promise(r => setTimeout(r, ms));
async function poll(fn, label, duration = 15000) { const end = Date.now() + duration; let last; do { try { const v = await fn(); if (v) return v; } catch (e) { last = e; } await delay(100); } while (Date.now() < end); throw Error('Timed out: ' + label + (last ? ': ' + last.message : '')); }
class CDP {
 constructor(ws) { this.ws = ws; this.sequence = 0; this.pending = new Map(); ws.addEventListener('message', event => { const data = JSON.parse(event.data); if (data.id) { const pending = this.pending.get(data.id); if (!pending) return; this.pending.delete(data.id); clearTimeout(pending.timer); data.error ? pending.reject(Error(data.error.message)) : pending.resolve(data.result); } else if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text); else if (data.method === 'Log.entryAdded' && data.params.entry.level === 'error') { const entry = data.params.entry; errors.push((entry.url ? new URL(entry.url).pathname + ': ' : '') + entry.text); } else if (data.method === 'Network.responseReceived') responses.push({ path: new URL(data.params.response.url).pathname, status: data.params.response.status }); }); }
 static async open(url) { const ws = new WebSocket(url); await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); }); const c = new CDP(ws); clients.push(c); return c; }
 send(method, params = {}) { const id = ++this.sequence; return new Promise((resolve, reject) => { const timer = setTimeout(() => { this.pending.delete(id); reject(Error('CDP timeout: ' + method)); }, 15000); this.pending.set(id, { resolve, reject, timer }); this.ws.send(JSON.stringify({ id, method, params })); }); }
 async evaluate(expression) { const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error('Browser evaluation failed: ' + result.exceptionDetails.text); return result.result.value; }
 async wait(expression, label) { return poll(() => this.evaluate(expression), label); }
 async field(selector, value) { return this.evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});if(!el)throw Error('Field missing');const proto=el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return true})()`); }
 async click(selector) { await this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
 async button(text) { await this.evaluate(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!button)throw Error('Button missing');button.click()})()`); }
}
let browser;
try {
 const info = await poll(async () => (await fetch('http://127.0.0.1:' + port + '/json/version')).json(), 'Edge debugging endpoint');
 browser = await CDP.open(info.webSocketDebuggerUrl);
 async function session() {
  const context = await browser.send('Target.createBrowserContext');
  const target = await browser.send('Target.createTarget', { url: origin, browserContextId: context.browserContextId });
  const info = await poll(async () => (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.id === target.targetId), 'session target');
  const tab = await CDP.open(info.webSocketDebuggerUrl); lastTab = tab; await tab.send('Runtime.enable'); await tab.send('Log.enable'); await tab.send('Network.enable'); await tab.send('Page.enable'); await tab.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await tab.wait(`!!document.querySelector('input[name=username]') && !document.querySelector('button[type=submit]').disabled`, 'login screen');
  await tab.field('select', 'es'); await tab.field('input[name=username]', username); await tab.field('input[name=password]', password); await tab.evaluate(`document.querySelector('form').requestSubmit()`);
  await tab.wait(`!!document.querySelector('.ir-nav')`, 'authenticated RC9 navigation'); return tab;
 }
 const first = await session(); checks.push('Login real mediante GUI RC9');
 const houseName = 'Systemhaus CDP ' + run, customerName = 'Cliente CDP ' + run, renamed = customerName + ' · München 東京';
 await first.click('.ir-org'); await first.wait(`!!document.querySelector('dialog[open] input[name=name]')`, 'Systemhaus dialog'); await first.field('dialog input[name=name]', houseName); await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!document.querySelector('dialog[open]') && document.querySelector('.ir-org').textContent===${JSON.stringify(houseName)}`, 'committed Systemhaus'); checks.push('Renombrar Systemhaus confirmado');
 await first.button('Crear cliente'); await first.wait(`!!document.querySelector('dialog[open] input[name=name]')`, 'create dialog'); await first.field('dialog input[name=name]', customerName); await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!document.querySelector('dialog[open]') && [...document.querySelectorAll('.ir-client-card h2')].some(e=>e.textContent===${JSON.stringify(customerName)})`, 'committed customer');
 const customerId = await first.evaluate(`[...document.querySelectorAll('.ir-client-card')].find(e=>e.querySelector('h2').textContent===${JSON.stringify(customerName)}).dataset.customerId`);
 checks.push('Crear cliente confirmado y UUID estable');
 await first.click('[data-customer-id="' + customerId + '"]'); await first.button('Renombrar cliente'); await first.wait(`!!document.querySelector('dialog[open]')`, 'rename dialog'); await first.field('dialog input[name=name]', renamed); await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!document.querySelector('dialog[open]') && document.querySelector('.rc-detail h1').textContent===${JSON.stringify(renamed)}`, 'renamed customer'); checks.push('Renombrar cliente Unicode');
 await first.send('Page.reload'); await first.wait(`[...document.querySelectorAll('.ir-client-card h2')].some(e=>e.textContent===${JSON.stringify(renamed)})`, 'persisted reload'); checks.push('Recargar: lectura persistida');
 const second = await session(); await second.wait(`[...document.querySelectorAll('.ir-client-card h2')].some(e=>e.textContent===${JSON.stringify(renamed)}) && document.querySelector('.ir-org').textContent===${JSON.stringify(houseName)}`, 'second independent session'); checks.push('Segunda sesión aislada: mismo Systemhaus y cliente persistidos');
 const storage = await second.evaluate(`Object.keys(localStorage)`); assert.deepEqual(storage.sort(), ['rackclick_server_language', 'rackclick_server_theme']); checks.push('localStorage contiene solo preferencias, sin inventario ni secretos');
 await first.click('[data-customer-id="' + customerId + '"]'); await first.button('Renombrar cliente'); await first.wait(`!!document.querySelector('dialog[open]')`, 'conflict draft'); await first.field('dialog input[name=name]', renamed + ' borrador');
 await second.click('[data-customer-id="' + customerId + '"]'); await second.button('Renombrar cliente'); await second.wait(`!!document.querySelector('dialog[open]')`, 'concurrent dialog'); await second.field('dialog input[name=name]', renamed + ' remoto'); await second.evaluate(`document.querySelector('dialog form').requestSubmit()`); await second.wait(`!document.querySelector('dialog[open]')`, 'remote commit');
 await first.evaluate(`document.querySelector('dialog form').requestSubmit()`); await first.wait(`!!document.querySelector('dialog [role=alert]')`, 'revision conflict'); assert.equal(await first.evaluate(`document.querySelector('dialog input[name=name]').value`), renamed + ' borrador'); assert.ok((await first.evaluate(`document.querySelector('dialog [role=alert]').textContent`)).includes('Otra sesión')); checks.push('Conflicto entre sesiones: 412 visible y borrador conservado');
 await first.button('Cargar datos actuales'); await first.wait(`!document.querySelector('dialog [role=alert]')`, 'explicit conflict reload'); await first.evaluate(`document.querySelector('dialog form').requestSubmit()`); await first.wait(`!document.querySelector('dialog[open]')`, 'explicit draft commit'); checks.push('Recarga explícita de revisión y commit del borrador');
 await first.button('Renombrar cliente'); await first.wait(`!!document.querySelector('dialog[open]')`, 'network draft'); await first.field('dialog input[name=name]', renamed + ' red'); await first.send('Network.enable'); await first.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await first.evaluate(`document.querySelector('dialog form').requestSubmit()`);
 await first.wait(`!!document.querySelector('dialog [role=alert]')`, 'network uncertainty'); assert.equal(await first.evaluate(`document.querySelector('dialog input[name=name]').value`), renamed + ' red'); assert.equal(await first.evaluate(`document.querySelector('dialog input[name=name]').disabled`), true); assert.ok((await first.evaluate(`document.querySelector('dialog [role=alert]').textContent`)).includes('No llegó'));
 await first.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
 assert.equal(await first.evaluate(`(async()=>{const identity=await(await fetch('/api/v1/me')).json();return(await fetch('/api/v1/auth/logout',{method:'POST',headers:{'X-RackClick-CSRF':identity.csrf}})).status})()`), 204);
 await first.button('Reintentar confirmación'); await first.wait(`!!document.querySelector('dialog input[type=password]')`, 'pending operation after session revoked'); assert.equal(await first.evaluate(`document.querySelector('dialog input[name=name]').disabled`), true); assert.equal(await first.evaluate(`document.querySelector('dialog input[name=name]').value`), renamed + ' red');
 await first.field('dialog input[type=password]', password); await first.button('Iniciar sesión'); await first.wait(`!document.querySelector('dialog [role=alert]')`, 'original actor reauthenticated'); await first.button('Reintentar confirmación'); await first.wait(`!document.querySelector('dialog[open]')`, 'network retry commit'); checks.push('Red caída: ningún éxito falso, borrador inmutable y reintento confirmado'); checks.push('Pendiente seguida de 401: mismo actor reautenticado y confirmación sin perder operación');
 await first.button('Todos los clientes'); await first.evaluate(`document.querySelector('select').value`); await first.wait(`!document.querySelector('.rc-settings select').disabled`, 'personal settings ready'); await first.field('select', 'de'); await first.wait(`document.documentElement.lang==='de'&&!document.querySelector('.rc-settings select').disabled`, 'German preference confirmed'); assert.equal(await first.evaluate(`document.querySelector('h1').textContent`), 'Kunden'); await first.field('select', 'en'); await first.wait(`document.documentElement.lang==='en'&&!document.querySelector('.rc-settings select').disabled`, 'English preference confirmed'); assert.equal(await first.evaluate(`document.querySelector('h1').textContent`), 'Clients'); await first.field('select', 'es'); await first.wait(`document.documentElement.lang==='es'&&!document.querySelector('.rc-settings select').disabled`, 'Spanish preference confirmed'); checks.push('Idiomas EN/DE/ES sin traducción de nombres personalizados');
 await first.button('Tema claro'); await first.wait(`document.documentElement.dataset.rcTheme==='light'&&!document.querySelector('.rc-settings button').disabled`, 'light preference confirmed'); assert.equal(await first.evaluate(`document.documentElement.dataset.rcTheme`), 'light');
 const screenshot = await first.send('Page.captureScreenshot', { format: 'png' }); await writeFile(path.join(evidence, 'clientes-light-windows.png'), Buffer.from(screenshot.data, 'base64'));
 await first.button('Tema oscuro'); await first.wait(`document.documentElement.dataset.rcTheme==='dark'&&!document.querySelector('.rc-settings button').disabled`, 'dark preference confirmed'); const dark = await first.send('Page.captureScreenshot', { format: 'png' }); await writeFile(path.join(evidence, 'clientes-dark-windows.png'), Buffer.from(dark.data, 'base64')); checks.push('Temas claro/oscuro y capturas reales');
 await first.button('Cerrar sesión'); await first.wait(`!!document.querySelector('input[name=username]')`, 'logout'); checks.push('Logout real vuelve a login');
 const materialErrors = errors.filter(error => !/status of (401|412)|favicon\.ico|ERR_INTERNET_DISCONNECTED/.test(error)); assert.deepEqual(materialErrors, []);
 const report = { status: 'passed', run, platform: process.platform, browser: info.Browser, origin, customerId, checks, browserErrors: materialErrors, limitations: ['No certifica paridad completa de inventario RC9.', 'Un mismo usuario autorizado inicia dos sesiones con cookies aisladas; usuarios/grupos se verifican en pruebas API.'] };
 await writeFile(path.join(evidence, 'browser-windows.json'), JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2));
} catch (error) {
 let visibleText = '';
 if (lastTab) { try { visibleText = (await lastTab.evaluate(`document.body.innerText`)).replaceAll(password, '[redacted]').replaceAll(username, '[synthetic user]'); const shot = await lastTab.send('Page.captureScreenshot', { format: 'png' }); await writeFile(path.join(evidence, 'browser-failure.png'), Buffer.from(shot.data, 'base64')); } catch {} }
 await writeFile(path.join(evidence, 'browser-windows-failure.json'), JSON.stringify({ run, status: 'failed', checks, error: error.message, browserErrors: errors, responses, visibleText }, null, 2)); throw error;
} finally {
 if (browser) { try { await browser.send('Browser.close'); } catch {} }
 for (const client of clients) client.ws.close();
 if (child.exitCode === null) child.kill();
}
