import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,poll,delay,submit,normalize} from './browser-client-changes-support.mjs';

await runScenario(async({first,session,checks,fixture:f,out,shot,responses})=>{
 const second=await session(f.secondName),writes=[],secondWrites=[];
 second.ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Network.requestWillBeSent'&&m.params.request.method==='POST'&&m.params.request.url.endsWith('/commands'))secondWrites.push(m.params.request)});
 first.ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Network.requestWillBeSent'&&m.params.request.method==='POST'&&m.params.request.url.endsWith('/commands'))writes.push(m.params.request)});
 async function open(tab,id,move='Mover'){await tab.evaluate(`(()=>{const a=document.querySelector('[data-room-device-id="${id}"]');[...a.querySelectorAll('button')].find(b=>b.textContent===${JSON.stringify(move)}).click()})()`);await tab.wait(`!!document.querySelector('[data-room-move]')`,'room move modal')}
 async function close(tab){await tab.evaluate(`document.querySelector('dialog footer button[type=button]').click()`);await tab.wait(`!document.querySelector('dialog[open]')`,'dialog closed')}
 for(const [lang,move,current,destination]of[['en','Move','Current room','Destination room'],['de','Verschieben','Aktueller Raum','Zielraum'],['es','Mover','Sala actual','Sala de destino']]){
  await first.field('.rc-settings select',lang);await infrastructure(first);await open(first,f.dose,move);
  assert.equal(await first.evaluate(`document.querySelector('dialog select[name=roomId]').value`),'');
  assert.deepEqual(await first.evaluate(`[...document.querySelector('dialog select[name=roomId]').options].map(o=>o.value)`),['',f.roomB]);
  const text=await first.evaluate(`document.querySelector('[data-room-move]').textContent`);
  for(const literal of [current,destination,'Objeto dose literal <img> Ω','Sede A literal <img> Ω','Edificio A 東京',f.roomA,'Sede B literal <img> Ω',f.roomB])assert.ok(text.includes(literal),literal);
  await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  assert.equal(await first.evaluate(`(()=>{const d=document.querySelector('dialog'),s=d.querySelector('select'),b=s.getBoundingClientRect();return d.scrollWidth<=d.clientWidth+1&&b.left>=0&&b.right<=innerWidth})()`),true,'390px modal controls fit');
  await shot(first,'room-move-390-'+lang+'.png');
  await submit(first);await delay(150);assert.equal(writes.length,0,'empty required destination sends no command');
  await close(first);await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await first.click('.ir-all-clients');
 }
 checks.push('EN/DE/ES at390px: current literal name/path/UUID and destination path/UUID fit; empty required choice excludes current/foreign rooms, zero commands.');
 await infrastructure(first);await infrastructure(second);let expected=await snapshot(first);
 const pathA='Sede A literal <img> Ω / Edificio A 東京 / Sala homónima Ω',pathB='Sede B literal <img> Ω / Edificio B 東京 / Sala homónima Ω';
 const title=(tab,p)=>tab.evaluate(`document.querySelector('[data-room-port="${p}"]').title`);
 const originalTitle=await title(first,f.pdose);assert.ok(originalTitle.startsWith(pathA));
 await open(first,f.dose);await first.field('dialog select[name=roomId]',f.roomB);
 // A genuine concurrent customer rename changes revision, outside all nine inventory tables.
 await second.button('Renombrar cliente');await second.field('dialog [name=name]','Cliente renombrado por segunda cuenta Ω');await submit(second);await second.wait(`!document.querySelector('dialog[open]')`,'other actor committed rename');
 expected.revision++;await submit(first);await first.wait(`!!document.querySelector('dialog [role=alert]')`,'stale412');
 assert.equal(writes.length,1);assert.equal(await first.evaluate(`document.querySelector('dialog select[name=roomId]').value`),f.roomB);assert.equal(await first.evaluate(`document.querySelector('dialog button[type=submit]').disabled`),true);assert.deepEqual(normalize(await snapshot(first)),normalize(expected));await shot(first,'room-move-conflict.png');
 await first.button('Cargar datos actuales');await first.wait(`!document.querySelector('dialog [role=alert]')`,'reload current revision');assert.equal(await first.evaluate(`document.querySelector('dialog select[name=roomId]').value`),f.roomB);
 // The second actor now moves this exact object to the chosen destination.
 await open(second,f.dose);await second.field('dialog select[name=roomId]',f.roomB);await submit(second);await second.wait(`!document.querySelector('dialog[open]')`,'remote dose committed');expected.revision++;Object.assign(expected.devices.find(d=>d.id===f.dose),{roomId:f.roomB,sortOrder:4});
 await submit(first);await first.wait(`!!document.querySelector('dialog [role=alert]')`,'second stale412');assert.equal(writes.length,2);
 await first.button('Cargar datos actuales');await first.wait(`!document.querySelector('dialog [role=alert]')&&document.querySelector('[data-current-room]')?.textContent.includes('${f.roomB}')`,'current room changes after refresh');
 assert.ok((await first.evaluate(`document.querySelector('[data-current-room]').textContent`)).includes(pathB));
 assert.deepEqual(await first.evaluate(`[...document.querySelector('dialog select[name=roomId]').options].map(o=>o.value)`),['',f.roomA]);
 await submit(first);await delay(150);assert.equal(writes.length,2,'already remotely moved destination sends no no-op');await close(first);
 await first.wait(`document.querySelector('[data-room-port="${f.pdose}"]')?.title.startsWith(${JSON.stringify(pathB)})`,'current endpoint after remote move');assert.deepEqual(normalize(await snapshot(first)),normalize(expected));
 await open(first,f.end);await first.field('dialog select[name=roomId]',f.roomB);await submit(first);await first.wait(`!document.querySelector('dialog[open]')`,'end device committed');expected.revision++;Object.assign(expected.devices.find(d=>d.id===f.end),{roomId:f.roomB,sortOrder:5});assert.deepEqual(normalize(await snapshot(first)),normalize(expected));
 assert.equal(writes.length,3);assert.deepEqual(writes.map(r=>JSON.parse(r.postData)),[{type:'device.move',payload:{id:f.dose,roomId:f.roomB}},{type:'device.move',payload:{id:f.dose,roomId:f.roomB}},{type:'device.move',payload:{id:f.end,roomId:f.roomB}}]);
 assert.equal(new Set(writes.map(r=>Object.entries(r.headers).find(([k])=>k.toLowerCase()==='idempotency-key')?.[1])).size,3);
 assert.equal(secondWrites.length,1);assert.deepEqual(JSON.parse(secondWrites[0].postData),{type:'device.move',payload:{id:f.dose,roomId:f.roomB}});
 const commandResponses=responses.filter(r=>r.path.endsWith('/commands'));assert.deepEqual(commandResponses.map(r=>r.status),[412,200,412,200]);
 checks.push('Second actor renames client; stale412 preserves selected destination and full snapshot. First reload retains choice. A remote move then causes another412; refresh shows current roomB and excludes it from targets; no-op submission sends nothing. Exactly one successful request per room move (second actor Dose, first actor end), fresh keys after rejected412, no rack/U/kind payload. Existing destination object order3 untouched; moved Dose4/end5.');
 for(const tab of [first,second]){
  await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reloaded clients');await infrastructure(tab);assert.deepEqual(normalize(await snapshot(tab)),normalize(expected));
  for(const p of [f.pdose,f.pdose2,f.pend])assert.ok((await title(tab,p)).startsWith(pathB));
  assert.equal(await tab.evaluate(`document.querySelector('[data-room-device-id="${f.dose}"]').textContent.includes('no ocupa U')`),true);
 }
 // Click-Click still selects/clears explicit ports, without creating or changing cables.
 await first.click(`[data-room-port="${f.pdose3}"]`);assert.equal(await first.evaluate(`document.querySelector('[data-room-port="${f.pdose3}"]').getAttribute('aria-pressed')`),'true');await first.button('Quitar selección');
 checks.push('Full reload for two authorized actors gives exact snapshot/current endpoint labels. Original two distinct Dose ports and two external cables retained; no implicit Dose circuit. Click-Click selection/clear retained.');
 await first.click('.ir-all-clients');await first.click(`[data-customer-id="${f.other}"]`);await first.wait(`!!document.querySelector('[data-room-device-id="${f.onlyRoomDevice}"]')`,'single room client');await open(first,f.onlyRoomDevice);assert.equal(await first.evaluate(`document.querySelector('dialog select[name=roomId]').disabled`),true);assert.ok((await first.evaluate(`document.querySelector('[data-room-move] [role=status]').textContent`)).includes('No hay otra sala'));await submit(first);await first.wait(`!!document.querySelector('dialog [role=alert]')`,'no destination refused locally');assert.equal(writes.length,3);await shot(first,'room-move-no-destination.png');await close(first);
 checks.push('Client with one room: clear unavailable message/disabled destination; even direct form submission produces local validation, zero extra requests/success.');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2));
});
