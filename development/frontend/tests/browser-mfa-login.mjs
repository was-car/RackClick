// Real Edge/CDP against a Kestrel + PostgreSQL laboratory. No new npm dependency.
// Deliberately does not capture screenshots, body text, requests, cookies, QR or secret values in its artifacts.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {once} from 'node:events';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createHmac,randomUUID} from 'node:crypto';

const origin=process.env.RACKCLICK_TEST_ORIGIN,username=process.env.RACKCLICK_TEST_USERNAME,password=process.env.RACKCLICK_TEST_PASSWORD;
const out=process.env.RACKCLICK_TEST_OUTPUT;
if(!origin||!username||!password||!out||new URL(origin).hostname!=='127.0.0.1')throw Error('Explicit isolated loopback laboratory required.');
await mkdir(out,{recursive:true});
const root=path.resolve('../..'),profile=path.join(root,'.local','browser-mfa',randomUUID());
await mkdir(profile,{recursive:true});
const probe=createServer();probe.listen(0,'127.0.0.1');await once(probe,'listening');const port=probe.address().port;await new Promise(r=>probe.close(r));
const edge=spawn(process.env.RACKCLICK_EDGE_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',[
 '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1',
 '--remote-debugging-port='+port,'--user-data-dir='+profile,'about:blank'
],{windowsHide:true,stdio:'ignore'});
const sockets=[],checks=[],responses=[],exceptions=[];
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function poll(fn,label,ms=20000){const end=Date.now()+ms;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch{}await delay(80);}throw Error('Timeout at '+label);}
class CDP {
 constructor(ws){this.ws=ws;this.id=0;this.pending=new Map();ws.addEventListener('message',event=>{
  const m=JSON.parse(event.data);if(m.id){const p=this.pending.get(m.id);if(!p)return;this.pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error('CDP command failed')):p.resolve(m.result);}
  else if(m.method==='Runtime.exceptionThrown')exceptions.push('runtime_exception');
  else if(m.method==='Network.responseReceived'){const u=new URL(m.params.response.url);if(u.origin===origin)responses.push({path:u.pathname,status:m.params.response.status});}
 });}
 static async connect(url){const ws=new WebSocket(url);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',()=>reject(Error('CDP connection failed')),{once:true});});sockets.push(ws);return new CDP(ws);}
 send(method,params={}){const id=++this.id;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP timeout at '+method));},15000);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));});}
 async evaluate(expression){const result=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error('Browser evaluation failed');return result.result.value;}
 wait(expression,label){return poll(()=>this.evaluate(expression),label);}
 async field(selector,value){return this.evaluate(`(()=>{const el=document.querySelector(${JSON.stringify(selector)});if(!el)throw Error('field');const p=el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);}
 async click(selector){await this.evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
}

function decodeBase32(secret){const chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';let bits=0,value=0;const bytes=[];for(const c of secret.replace(/=+$/,'')){const n=chars.indexOf(c.toUpperCase());if(n<0)throw Error('Unexpected Base32 fixture encoding');value=(value<<5)|n;bits+=5;if(bits>=8){bytes.push((value>>>(bits-8))&255);bits-=8;}}return Buffer.from(bytes);}
function totp(secret,step=Math.floor(Date.now()/30000)){const key=decodeBase32(secret),counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(step));const mac=createHmac('sha1',key).update(counter).digest();key.fill(0);const offset=mac[19]&15;return String((mac.readUInt32BE(offset)&0x7fffffff)%1e6).padStart(6,'0');}
function invalidCode(secret){const step=Math.floor(Date.now()/30000),valid=new Set([-1,0,1].map(offset=>totp(secret,step+offset)));for(let n=0;n<10;n++){const code=String(n).padStart(6,'0');if(!valid.has(code))return code;}throw Error('No invalid code candidate');}
function privateStorageCheck(tab,secret){return tab.evaluate(`(()=>{const forbidden=${JSON.stringify(secret)};return [localStorage,sessionStorage].every(s=>Object.values(s).every(v=>!v.includes(forbidden)&&!v.includes('otpauth://')))})()`);}

let browser,tab,secret='';
try {
 const info=await poll(async()=>{const r=await fetch(`http://127.0.0.1:${port}/json/version`);return r.ok?r.json():null;},'Edge startup');
 browser=await CDP.connect(info.webSocketDebuggerUrl);
 const context=await browser.send('Target.createBrowserContext');
 const target=await browser.send('Target.createTarget',{url:origin,browserContextId:context.browserContextId});
 const entry=await poll(async()=>(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t=>t.id===target.targetId),'page target');
 tab=await CDP.connect(entry.webSocketDebuggerUrl);
 for(const domain of ['Runtime','Network','Page'])await tab.send(domain+'.enable');
 await tab.wait(`!!document.querySelector('[name=username]')`,'password form');
 await tab.field('select','es');
 async function submitPassword(){await tab.wait(`!!document.querySelector('[name=password]')&&!document.querySelector('[name=password]').form.querySelector('button[type=submit]').disabled`,'password form ready');await tab.field('[name=username]',username);await tab.field('[name=password]',password);await tab.evaluate(`document.querySelector('[name=password]').form.requestSubmit()`);}
 await tab.wait(`!document.querySelector('[name=password]').form.querySelector('button[type=submit]').disabled`,'initial authentication lookup complete');
 const meBefore=responses.filter(x=>x.path==='/api/v1/me').length;
 await submitPassword();
 await tab.wait(`!!document.querySelector('[data-mfa-challenge][data-mfa-purpose="enroll"]')`,'enrollment challenge');
 assert.ok(await tab.evaluate(`!document.querySelector('.ir-nav')&&!document.querySelector('[name=password]')`),'challenge cannot open authenticated UI');
 assert.ok(await tab.evaluate(`!document.querySelector('[data-mfa-secret]')`),'enrollment does not start automatically');
 assert.ok(responses.filter(x=>x.path==='/api/v1/me').length===meBefore,'client does not treat challenge as session');
 const cookies=(await tab.send('Network.getAllCookies')).cookies;
 assert.ok(cookies.some(c=>c.name==='RackClick.MfaChallenge'&&c.httpOnly&&c.path==='/api/v1/auth/mfa'&&c.sameSite==='Strict'),'restricted challenge cookie');
 assert.ok(!cookies.some(c=>c.name==='RackClick.Session'),'no session before second factor');
 assert.equal(await tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`),401);
 checks.push('Password login enters enrollment without session, API authority or automatic start.');

 const titles={en:'Set up your authenticator',de:'Authenticator einrichten',es:'Configura tu autenticador'};
 for(const lang of ['en','de','es']){await tab.field('dialog[open] select',lang);await tab.wait(`document.querySelector('[data-mfa-challenge]').textContent.includes(${JSON.stringify(titles[lang])})`,'enrollment language '+lang);}
 checks.push('Enrollment instructions are available in English, German and Spanish.');
 await tab.click('[data-mfa-start]');
 await tab.wait(`!!document.querySelector('[data-mfa-secret]')&&!!document.querySelector('[data-mfa-qr]')`,'local QR and manual key');
 secret=await tab.evaluate(`document.querySelector('[data-mfa-secret]').textContent.trim()`);
 assert.ok(/^[A-Z2-7]{16,}$/i.test(secret),'manual enrollment key is Base32');
 assert.ok(await tab.evaluate(`document.querySelector('[data-mfa-qr]').tagName.toLowerCase()==='svg'&&!document.querySelector('[data-mfa-qr] image')`),'QR renders locally');
 assert.ok(await privateStorageCheck(tab,secret),'secret never stored in local/session storage');
 await tab.field('[data-mfa-code]',invalidCode(secret));await tab.click('[data-mfa-submit]');
 await poll(()=>responses.some(x=>x.path==='/api/v1/auth/mfa/enroll/confirm'&&x.status===401),'invalid code response');
 await tab.wait(`!!document.querySelector('[data-mfa-code]')&&!document.querySelector('[data-mfa-code]').disabled`,'code retry ready');
 assert.ok(await tab.evaluate(`!document.querySelector('.ir-nav')&&!!document.querySelector('[data-mfa-secret]')`),'invalid code keeps enrollment restricted');
 checks.push('Invalid TOTP is rejected; enrollment remains restricted and retryable.');
 await tab.field('[data-mfa-code]',totp(secret));await tab.click('[data-mfa-submit]');
 await tab.wait(`!!document.querySelector('.ir-nav')`,'confirmed enrollment session');
 assert.ok(await tab.evaluate(`!document.querySelector('[data-mfa-secret]')&&!document.querySelector('[data-mfa-qr]')`),'enrollment material removed after confirmation');
 assert.equal(await tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`),200);
 assert.ok(await privateStorageCheck(tab,secret),'confirmed session does not persist enrollment material');
 checks.push('Valid code creates confirmed API session and removes enrollment material.');

 await tab.evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(b=>['Sign out','Abmelden','Cerrar sesión'].includes(b.textContent.trim()));if(!b)throw Error('logout');b.click()})()`);
 await tab.wait(`!!document.querySelector('[name=password]')`,'logout password form');
 await submitPassword();
 await tab.wait(`!!document.querySelector('[data-mfa-challenge][data-mfa-purpose="verify"]')`,'verification challenge');
 assert.ok(await tab.evaluate(`!document.querySelector('[data-mfa-start]')&&!document.querySelector('[data-mfa-secret]')`),'next login verifies instead of enrolling');
 await tab.send('Page.reload',{ignoreCache:true});
 await tab.wait(`!!document.querySelector('[name=password]')`,'reload returns to password sign-in');
 assert.ok(await tab.evaluate(`!document.querySelector('[data-mfa-challenge]')&&!document.querySelector('.ir-nav')`),'transient challenge not restored after reload');
 assert.ok(await privateStorageCheck(tab,secret),'reload has no stored MFA material');
 checks.push('Next login requires verification; reload discards the transient challenge without granting access.');
 await submitPassword();
 await tab.wait(`!!document.querySelector('[data-mfa-challenge][data-mfa-purpose="verify"]')`,'fresh verification challenge');
 const verifyTitles={en:'Verify your sign-in',de:'Anmeldung bestätigen',es:'Verifica tu inicio de sesión'};
 for(const lang of ['en','de','es']){await tab.field('dialog[open] select',lang);await tab.wait(`document.querySelector('[data-mfa-challenge]').textContent.includes(${JSON.stringify(verifyTitles[lang])})`,'verify language '+lang);}
 // One future step is inside the server's documented ±1 window and is distinct from the enrollment-consumed step.
 await tab.field('[data-mfa-code]',totp(secret,Math.floor(Date.now()/30000)+1));await tab.click('[data-mfa-submit]');
 await tab.wait(`!!document.querySelector('.ir-nav')`,'verified second-factor session');
 assert.equal(await tab.evaluate(`fetch('/api/v1/me').then(r=>r.status)`),200);
 assert.ok(await privateStorageCheck(tab,secret),'verification does not persist MFA material');
 assert.ok(!exceptions.length,'no browser runtime exceptions');
 checks.push('Fresh second-factor verification creates a session, with EN/DE/ES instructions and no persisted secrets.');
 const report={result:'PASS',checks,responses,browser:info.Browser,provider:'synthetic-test-DI',transport:'real-Kestrel-loopback-HTTP',serviceTokenTested:false,productionOrQaEnabled:false};
 await writeFile(path.join(out,'browser-mfa-result.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({result:'PASS',checks:checks.length,provider:'synthetic-test-DI'}));
} catch(error) {
 // Store only fixed diagnostic locations. Do not serialize error objects/assertion actual values, DOM, or screenshots.
 await writeFile(path.join(out,'browser-mfa-result.json'),JSON.stringify({result:'FAIL',checks,responses,diagnostic:String(error?.message||'fixture_failure').replaceAll(password,'[redacted]').replaceAll(secret||'__no_secret__','[redacted]'),runtimeExceptions:exceptions.length,provider:'synthetic-test-DI'},null,2)+'\n');
 console.error('Browser MFA scenario failed; sanitized result retained.');process.exitCode=1;
} finally {
 secret='';
 if(browser)try{await browser.send('Browser.close');}catch{}
 for(const socket of sockets)socket.close();
 if(edge.exitCode===null)edge.kill();
}
