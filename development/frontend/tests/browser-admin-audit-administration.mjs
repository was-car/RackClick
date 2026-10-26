// Isolated case6:18 administrative writer shapes, existing account fixtures only.
import assert from 'node:assert/strict';
import {writeFile,readFile} from 'node:fs/promises';
import path from 'node:path';

export async function runAuditAdministration(c){
 const {fixture,first,session,audit,refresh,reload,pending,fulfill,noStale,poll,delay,origin,evidence,checks}=c;
 const entries=fixture.administration,signals=process.env.RACKCLICK_SIGNALS;
 const second=await session(),reader=await session('audit-reader'),authority=await session(fixture.name);
 await audit(second);
 const selector=id=>'[data-open-audit-detail="'+id+'"]';
 const route=id=>'/api/v1/admin/audit/'+id+'/administrative-detail';
 const entry=action=>entries.find(e=>e.action===action);
 const title={es:'Campos administrativos registrados',en:'Recorded administrative fields',de:'Protokollierte Verwaltungsfelder'};
 const nullText={es:'Sin valor publicado / no aplica',en:'No published value / not applicable',de:'Kein veröffentlichter Wert / nicht zutreffend'};
 const flag={es:{true:'Sí',false:'No'},en:{true:'Yes',false:'No'},de:{true:'Ja',false:'Nein'}};
 async function ready(tab,id){await tab.wait(`document.querySelector('[data-audit-detail]')?.dataset.auditDetail==='${id}'&&!!document.querySelector('[data-admin-detail-fields]')&&document.querySelector('[data-audit-detail]').getAttribute('aria-busy')==='false'`,'administrative fields '+id);}
 async function open(tab,item){await tab.click(selector(item.id));await ready(tab,item.id);}
 const values=tab=>tab.evaluate(`[...document.querySelectorAll('[data-admin-field]')].map(el=>({field:el.dataset.adminField,before:el.querySelector('[data-admin-before]').textContent,after:el.querySelector('[data-admin-after]').textContent}))`);
 const expected=(item,lang='es')=>item.fields.map(f=>({field:f.field,before:f.before===null?nullText[lang]:f.type==='boolean'?flag[lang][f.before]:f.before,after:f.after===null?nullText[lang]:f.type==='boolean'?flag[lang][f.after]:f.after}));
 async function intercept(tab,stage='Response'){tab.paused=null;await tab.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/admin/audit/*/administrative-detail',requestStage:stage}]});}
 async function error(){await first.wait(`!!document.querySelector('[data-detail-error]')&&!document.querySelector('[data-detail-result]')`,'administrative error no old fields');}
 assert.equal(await reader.evaluate(`fetch('${route(entries[0].id)}').then(r=>r.status)`),403);
 await writeFile(path.join(signals,'readonly.begin'),'begin');await poll(()=>readFile(path.join(signals,'readonly.ready'),'utf8'),'admin baseline');
 assert.equal(entries.length,18);
 for(const item of entries){
  await open(first,item);assert.deepEqual(await values(first),expected(item));
  assert.equal(await first.evaluate(`document.querySelector('[data-audit-detail] h4').textContent`),title.es);
  assert.equal(await first.evaluate(`!!document.querySelector('[data-admin-cancel-notice]')`),item.action.endsWith('.cancel'));
 }
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-admin-audit] img').length`),0);
 assert.equal(await first.evaluate(`document.querySelector('[data-admin-audit]').textContent.includes('synthetic-hidden-audit')`),false);
 const status=entry('user.state.set'),grant=entry('userGroup.grant.set'),reset=entry('user.password.reset');
 await open(first,status);await open(second,status);assert.deepEqual(await values(first),await values(second));
 await first.click('[data-close-audit-detail]');assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);assert.equal(await first.evaluate('document.activeElement.dataset.openAuditDetail'),status.id);
 const payload=await first.evaluate(`fetch('${route(status.id)}').then(r=>r.json())`),etag='"'+payload.revision+'"';
 for(const code of [401,403,404]){
  await open(first,status);await intercept(first);await first.click(selector(status.id));await fulfill(first,await pending(first),code,{error:'synthetic'});await first.send('Fetch.disable');
  if(code===404)await error();else{await noStale(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-admin-detail-fields]')`),false);await refresh(first);}
 }
 await intercept(first,'Request');await first.click(selector(status.id));await first.send('Fetch.failRequest',{requestId:(await pending(first)).requestId,errorReason:'Failed'});await first.send('Fetch.disable');await error();
 for(const kind of ['fieldExtra','wrongTarget','wrongBoolean','etag']){
  const bad=structuredClone(payload);if(kind==='fieldExtra')bad.detail.fields[0].secret='synthetic-hidden-audit';if(kind==='wrongTarget')bad.detail.fields[0].after=fixture.admin;if(kind==='wrongBoolean')bad.detail.fields[2].after=false;
  await intercept(first);await first.click(selector(status.id));await fulfill(first,await pending(first),200,bad,kind==='etag'?'"999"':etag);await first.send('Fetch.disable');await error();
 }
 await intercept(first);await first.click(selector(status.id));const old=await pending(first);await first.click(selector(grant.id));const newer=await pending(first,old.requestId);await first.send('Fetch.continueResponse',{requestId:newer.requestId});await ready(first,grant.id);await first.send('Fetch.continueResponse',{requestId:old.requestId});await first.send('Fetch.disable');await delay(150);assert.deepEqual(await values(first),expected(grant));
 await intercept(first);await first.click(selector(status.id));const oldSame=await pending(first);await first.click(selector(status.id));const newSame=await pending(first,oldSame.requestId);await first.send('Fetch.continueResponse',{requestId:newSame.requestId});await ready(first,status.id);const stale=structuredClone(payload);stale.detail.fields[2].after='true';await fulfill(first,oldSame,200,stale,etag);await first.send('Fetch.disable');await delay(150);assert.deepEqual(await values(first),expected(status));
 await intercept(first);await first.click(selector(status.id));const closing=await pending(first);await first.click('[data-close-audit-detail]');await first.send('Fetch.continueResponse',{requestId:closing.requestId});await first.send('Fetch.disable');await delay(100);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);
 await open(first,status);await refresh(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);
 for(const lang of ['en','de','es']){
  await first.click('.rc-admin-audit-page header button');await first.wait(`!!document.querySelector('.rc-settings select')`,'language');await first.field('.rc-settings select',lang);await audit(first);await open(first,reset);assert.equal(await first.evaluate(`document.querySelector('[data-audit-detail] h4').textContent`),title[lang]);assert.deepEqual(await values(first),expected(reset,lang));
 }
 await first.evaluate(`document.querySelector('[data-audit-detail]').scrollIntoView({block:'start'})`);assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 await writeFile(path.join(evidence,'audit-admin-es-1440x1000.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await first.evaluate(`document.querySelector('[data-audit-detail]').scrollIntoView({block:'start'})`);assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await writeFile(path.join(evidence,'audit-admin-es-390x844.png'),Buffer.from((await first.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await reload(first);await first.wait(`!!document.querySelector('.ir-nav')`,'reload');await audit(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-audit-detail]')`),false);await open(first,status);assert.deepEqual(await values(first),await values(second));
 await writeFile(path.join(signals,'readonly.end'),'end');const equality=await poll(async()=>JSON.parse(await readFile(path.join(signals,'readonly.result'),'utf8')),'admin read-only tables');assert.equal(equality.unchanged,true);
 const revoked=await authority.evaluate(`(async()=>{const m=await fetch('/api/v1/me').then(r=>r.json()),s=await fetch('/api/v1/admin/users').then(r=>r.json());return(await fetch('/api/v1/admin/user-groups/${fixture.group}/members',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':m.csrf,'X-RackClick-Actor':m.user.id,'If-Match':'"'+s.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({userId:${JSON.stringify(fixture.admin)},assigned:false})})).status})()`);assert.equal(revoked,200);await first.click(selector(status.id));await noStale(first);assert.equal(await first.evaluate(`!!document.querySelector('[data-admin-detail-fields]')`),false);
 checks.push('18 formas administrativas reales de escritores sembradas por SQL: campos históricos tipados/valores nulos explícitos, cancelación no deshace commit, Unicode/BOM yHTML como texto, sin JSON privado. No se presentan como18comandosHTTP del navegador.');
 checks.push('Lectura segunda sesión/recarga y EN/DE/ES, foco/cierre/refresh, errores401403404/red/DTO/ETag y respuestas antiguas deotro/mismoID sin campos obsoletos; tablas idénticas tras logins, lector403 y revocación403 reales; capturas escritorio/móvil sin overflow.');
}
