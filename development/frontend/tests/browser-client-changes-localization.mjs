// Focal for the failed EN→DE selector step; fresh lab, no claim of a full scenario.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,delay} from './browser-client-changes-support.mjs';
await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 const second=await session(f.secondName),requests=[];
 first.ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Network.requestWillBeSent'&&m.params.request.url.includes('/changes?'))requests.push(m.params.request.url)});
 for(const [lang,title]of[['en','Changes confirmed on the server'],['de','Vom Server bestätigte Änderungen'],['es','Cambios confirmados en el servidor']]){
  await first.send('Page.bringToFront');await first.field('.rc-settings select',lang);await infrastructure(first);
  await second.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json()),p=await fetch('/api/v1/customers/${f.customer}/project').then(r=>r.json());const r=await fetch('/api/v1/customers/${f.customer}/commands',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':me.user.id,'If-Match':'"'+p.revision+'"','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({type:'ports.update',payload:{deviceId:'${f.b}',groupId:'${f.gb}',groupType:'rj45',portIds:['${f.pb2}'],changes:{label:'Etiqueta ${lang}'}}})});if(!r.ok)throw Error('Synthetic command '+r.status)})()`);
  await first.wait(`!!document.querySelector('[data-client-change-notice]')`,'localized notice');assert.equal(await first.evaluate(`document.querySelector('[data-client-change-notice] h3').textContent`),title);
  if(lang==='es'){await first.evaluate(`document.querySelector('[data-client-change] details').open=true;scrollTo(0,document.querySelector('[data-client-change-notice]').getBoundingClientRect().top+scrollY-64)`);await shot(first,'notice-desktop.png');await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await first.evaluate(`scrollTo(0,document.querySelector('[data-client-change-notice]').getBoundingClientRect().top+scrollY-64)`);assert.equal(await first.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await shot(first,'notice-mobile.png');await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false})}
  await first.click('[data-refresh-changed-client]');await first.wait(`!document.querySelector('[data-client-change-notice]')`,'applied refresh');await first.click('.ir-all-clients');await first.wait(`!!document.querySelector('.rc-settings select')`,'home settings');
 }
 await infrastructure(first);const expected=await snapshot(first);await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2));await first.button('Cerrar sesión');await first.wait(`!!document.querySelector('[name=username]')`,'logout');const stopped=requests.length;await delay(5200);assert.equal(requests.length,stopped);
 checks.push('Focal idiomas EN/DE/ES, tres comandosHTTP yavisos reales, selector home independiente delidioma; Actualizar vista aplica yretira,390px sinoverflow, logoutconfirmado sin máslecturas. No repetición de red/roles/Click-Click del escenario parcial anterior.');
});
