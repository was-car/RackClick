// Case5 of the isolated Edge/PostgreSQL audit harness. No user browser or QA profile.
import assert from 'node:assert/strict';
import {writeFile,readFile} from 'node:fs/promises';
import path from 'node:path';

export async function runAuditDetail(c){
 const {fixture,first,session,audit,stable,refresh,reload,pending,fulfill,noStale,poll,delay,origin,evidence,checks}=c;
 const d=fixture.details,signals=process.env.RACKCLICK_SIGNALS;
 const second=await session(),reader=await session('audit-reader'),authority=await session(fixture.name);
 await audit(second);
 assert.equal(await reader.evaluate(`!!document.querySelector('[data-audit-navigation]')`),false);
 assert.equal(await reader.evaluate(`fetch('/api/v1/admin/audit/${d.rename}').then(r=>r.status)`),403);
 const selector=id=>'[data-open-audit-detail="'+id+'"]';
 const region=id=>'[data-audit-detail="'+id+'"]';
 async function ready(tab,id){await tab.wait(`!!document.querySelector('${region(id)} [data-detail-result]')&&document.querySelector('${region(id)}').getAttribute('aria-busy')==='false'`,'detail ready '+id)}
 async function open(tab,id){await tab.click(selector(id));await ready(tab,id)}
 async function names(tab){return tab.evaluate(`[...document.querySelectorAll('[data-audit-detail] [data-recorded-name]')].map(n=>n.textContent)`)}
 async function intercept(tab,stage='Response'){tab.paused=null;await tab.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/audit/*',requestStage:stage}]})}
 async function error(tab){await tab.wait(`!!document.querySelector('[data-detail-error]')&&!document.querySelector('[data-detail-result]')`,'detail error without old values')}
 await writeFile(path.join(signals,'readonly.begin'),'begin');await poll(()=>readFile(path.join(signals,'readonly.ready'),'utf8'),'read-only detail baseline');
 await open(first,d.rename);assert.deepEqual(await names(first),[d.names.before,d.names.after]);
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('[data-recorded-revision]')].map(n=>n.textContent)`),['1','2']);
 assert.equal(await first.evaluate(`document.querySelector('[data-detail-scope]').textContent`),'Revisiones históricas del cliente');
 assert.equal(await first.evaluate(`document.querySelector('[data-audit-detail]').textContent.includes(${JSON.stringify(fixture.resource)})`),true);
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-admin-audit] img').length`),0);
 assert.equal(await first.evaluate(`document.querySelector('[data-admin-audit]').textContent.includes('synthetic-hidden-audit')`),false);
 await intercept(first);await first.click(selector(d.create));const creation=await pending(first);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-detail-result]')`),false);
 assert.equal(await first.evaluate(`document.querySelector('[data-audit-detail]').dataset.auditDetail`),d.create);
 await first.send('Fetch.continueResponse',{requestId:creation.requestId});await first.send('Fetch.disable');await ready(first,d.create);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-created-before]')`),true);assert.deepEqual(await names(first),[d.names.before]);
 await open(first,d.house);assert.deepEqual(await names(first),[d.names.houseBefore,d.names.houseAfter]);
 assert.equal(await first.evaluate(`document.querySelector('[data-detail-scope]').textContent`),'Revisiones históricas de Systemhaus');
 assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('[data-recorded-revision]')].map(n=>n.textContent)`),['3','4']);
 await open(first,d.unavailable);assert.equal(await first.evaluate(`!!document.querySelector('[data-detail-unavailable]')`),true);assert.deepEqual(await names(first),[]);
 await open(second,d.rename);await open(first,d.rename);assert.deepEqual(await names(first),await names(second));
 await first.click('[data-close-audit-detail]');assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);assert.equal(await first.evaluate(`document.activeElement?.dataset.openAuditDetail`),d.rename);
 await open(first,d.rename);await refresh(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);
 await open(first,d.rename);await first.field('[name=auditActorId]',fixture.secondary);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);await first.click('[data-clear-audit]');await stable(first);
 await open(first,d.rename);await first.click('[data-older-audit]');await stable(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);await refresh(first);
 const payload=await first.evaluate(`fetch('/api/v1/admin/audit/${d.rename}').then(r=>r.json())`),etag='"'+payload.revision+'"';
 for(const status of [401,403,404]){
  await open(first,d.rename);await intercept(first);await first.click(selector(d.rename));const req=await pending(first);
  assert.equal(await first.evaluate(`!!document.querySelector('[data-detail-result]')`),false);await fulfill(first,req,status,{error:'synthetic'});await first.send('Fetch.disable');
  if(status===404)await error(first);else{await noStale(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);await refresh(first)}
 }
 await intercept(first,'Request');await first.click(selector(d.rename));await first.send('Fetch.failRequest',{requestId:(await pending(first)).requestId,errorReason:'Failed'});await first.send('Fetch.disable');await error(first);
 for(const kind of ['extra','otherId','revisions','etag']){
  const altered=structuredClone(payload);
  if(kind==='extra')altered.raw_json={secret:'synthetic-hidden-audit'};
  if(kind==='otherId')altered.event.id=d.create;
  if(kind==='revisions')altered.detail.after.revision=99;
  await intercept(first);await first.click(selector(d.rename));await fulfill(first,await pending(first),200,altered,kind==='etag'?'"999"':etag);await first.send('Fetch.disable');await error(first);
 }
 await open(first,d.rename);
 // Different IDs: the later selection owns the panel, even if A finishes last.
 await intercept(first);await first.click(selector(d.rename));const old=await pending(first);
 await first.click(selector(d.house));const recent=await pending(first,old.requestId);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-detail-result]')`),false);
 await first.send('Fetch.continueResponse',{requestId:recent.requestId});await ready(first,d.house);
 await first.send('Fetch.continueResponse',{requestId:old.requestId});await first.send('Fetch.disable');await delay(200);assert.deepEqual(await names(first),[d.names.houseBefore,d.names.houseAfter]);
 // Same ID read twice: a stale but valid DTO must also be discarded by sequence.
 await intercept(first);await first.click(selector(d.rename));const oldSame=await pending(first);
 await first.click(selector(d.rename));const recentSame=await pending(first,oldSame.requestId);
 await first.send('Fetch.continueResponse',{requestId:recentSame.requestId});await ready(first,d.rename);
 const stale=structuredClone(payload);stale.detail.before.name='stale synthetic response';await fulfill(first,oldSame,200,stale,etag);
 await first.send('Fetch.disable');await delay(200);assert.deepEqual(await names(first),[d.names.before,d.names.after]);
 await intercept(first);await first.click(selector(d.rename));const closed=await pending(first);
 await first.click('[data-close-audit-detail]');await first.send('Fetch.continueResponse',{requestId:closed.requestId});await first.send('Fetch.disable');await delay(200);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);
 await intercept(first);await first.click(selector(d.rename));const unmounted=await pending(first);
 await first.click('.rc-admin-audit-page header button');await first.wait(`!document.querySelector('[data-admin-audit]')`,'audit unmounted');
 await first.send('Fetch.continueResponse',{requestId:unmounted.requestId});await first.send('Fetch.disable');await audit(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);
 for(const [lang,title,label] of [['en','Recorded name detail','View detail'],['de','Protokollierte Namensdetails','Details anzeigen'],['es','Detalle de nombres registrados','Ver detalle']]){
  await first.click('.rc-admin-audit-page header button');await first.wait(`!!document.querySelector('.rc-settings select')`,'language setting');await first.field('.rc-settings select',lang);await audit(first);
  assert.equal(await first.evaluate(`document.querySelector('${selector(d.rename)}').textContent`),label);await open(first,d.rename);
  assert.equal(await first.evaluate(`document.querySelector('[data-audit-detail] h4').textContent`),title);assert.deepEqual(await names(first),[d.names.before,d.names.after]);
 }
 await first.evaluate(`document.querySelector('[data-audit-detail]').scrollIntoView({block:'start'})`);assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 await writeFile(path.join(evidence,'audit-detail-es-1440x1000.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await first.evaluate(`document.querySelector('[data-audit-detail]').scrollIntoView({block:'start'})`);assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 await writeFile(path.join(evidence,'audit-detail-es-390x844.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await reload(first);await first.wait(`!!document.querySelector('.ir-nav')`,'reloaded session');await audit(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);await open(first,d.rename);assert.deepEqual(await names(first),await names(second));
 await writeFile(path.join(signals,'readonly.end'),'end');const equality=await poll(async()=>JSON.parse(await readFile(path.join(signals,'readonly.result'),'utf8')),'read-only detail result');assert.equal(equality.unchanged,true);
 // Genuine revocation is deliberately outside the read-only monitor window.
 const changed=await authority.evaluate(`(async()=>{const m=await fetch('/api/v1/me').then(r=>r.json()),s=await fetch('/api/v1/admin/users').then(r=>r.json());return(await fetch('/api/v1/admin/user-groups/${fixture.group}/members',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':m.csrf,'X-RackClick-Actor':m.user.id,'If-Match':'"'+s.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({userId:${JSON.stringify(fixture.admin)},assigned:false})})).status})()`);
 assert.equal(changed,200);await first.click(selector(d.rename));await noStale(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);
 checks.push('Detalle API46/RC9: tres formas históricas con nombres Unicode/HTML como texto y revisiones del recurso; creación sin antes, unsupported explícito, sin JSON secreto; segunda sesión/recarga, EN/DE/ES, foco al cerrar y capturas escritorio/móvil sin overflow.');
 checks.push('Errores detalle401/403 limpian lista y detalle,404/red/DTO/ETag incompatibles retiran detalle; selección/filtros/página/refresh/cierre/unmount invalidan; respuestas tardías de otros IDs y mismo ID descartadas. Tablas iguales entre logins y revocación final real; lector403 y revocación403 real sin datos antiguos.');
}
