import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,poll} from './browser-quince-support.mjs';

await runScenario(async({first,session,checks,shot,out,origin,fixture,password})=>{
 const route='/api/v1/me/port-colors', panel='[data-port-colors-panel]';
 const read=tab=>tab.evaluate(`fetch('${route}').then(r=>r.json())`);
 const ready=tab=>tab.wait(`!!document.querySelector('${panel}')&&!document.querySelector('[data-port-colors-save]').disabled&&!document.querySelector('[data-port-colors-pending]')`,'palette ready');
 const open=async tab=>{await tab.wait(`!!document.querySelector('[data-port-colors-open]')&&!document.querySelector('[data-port-colors-open]').disabled`,'open available');await tab.click('[data-port-colors-open]');await ready(tab)};
 const close=async tab=>{await tab.click('[data-port-colors-close]');await tab.wait(`!document.querySelector('dialog[open]')`,'closed')};
 const save=async(tab,wanted)=>{await tab.click('[data-port-colors-save]');await tab.wait(`!document.querySelector('[data-port-colors-pending]')&&!document.querySelector('[data-port-colors-save]').disabled`,'confirmed palette');assert.deepEqual((await read(tab)).colors,wanted)};
 const color=async(tab,type,value)=>tab.field(`[data-port-colors-input="${type}"]`,value);
 const rack=async(tab,id=fixture.rackA)=>{await tab.click(`[data-customer-id="${fixture.customer}"]`);await tab.wait(`!!document.querySelector('[data-rack-id="${id}"]')`,'rack card');await tab.click(`[data-rack-id="${id}"] .rc-rack-open`);await tab.wait(`!!document.querySelector('[data-vport="${id===fixture.rackA?fixture.pa2:fixture.pc2}"]')`,'physical rack')};
 const home=async tab=>{await tab.click('.ir-crumb-home');await tab.wait(`!!document.querySelector('[data-port-colors-open]')`,'home')};
 const strokes=tab=>tab.evaluate(`Object.fromEntries(${JSON.stringify([fixture.pa,fixture.pb,fixture.pa2,fixture.pb2,fixture.pc2])}.map(id=>[id,[...document.querySelectorAll('[data-vport="'+id+'"] [stroke]')].map(e=>e.getAttribute('stroke'))]))`);
 const palette={rj45:'#123456',rj45_poe:'#654abc'};
 await open(first);assert.deepEqual((await read(first)).colors,{});
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-port-colors-input]').length`),10);
 await color(first,'rj45',palette.rj45);await color(first,'rj45_poe',palette.rj45_poe);
 assert.deepEqual((await read(first)).colors,{},'draft is not a database write');
 await save(first,palette);await shot(first,'palette-reader-desktop.png');await close(first);
 await rack(first);let visual=await strokes(first);
 assert.ok(visual[fixture.pa].includes('#654321'),'explicit port color wins');
 assert.ok(visual[fixture.pb].includes('#abcdef'),'connected cable color wins');
 assert.ok(visual[fixture.pa2].includes('#123456'),'plain type uses personal palette');
 assert.ok(visual[fixture.pb2].includes('#654abc'),'PoE type is independently customized');
 await shot(first,'palette-rack-precedence.png');
 checks.push('Lector guarda dos tipos con POST y GET; el borrador no escribe. Rack real conserva color explícito y cable sobre paleta, y distingue RJ45/PoE.');

 const second=await session('move-reader');await open(second);assert.deepEqual((await read(second)).colors,palette);await close(second);await rack(second);assert.ok((await strokes(second))[fixture.pa2].includes('#123456'));
 checks.push('Otra sesión del mismo usuario carga y representa la paleta desde PostgreSQL.');
 const none=await session('colors-none');await open(none);assert.deepEqual((await read(none)).colors,{});await color(none,'rj45','#112233');await save(none,{rj45:'#112233'});assert.deepEqual((await read(second)).colors,palette);
 const noneExpected=await read(none);await close(none);
 await none.click('.ir-nav .ir-settings:last-of-type');await none.wait(`!!document.querySelector('[name=username]')`,'logout');
 await none.field('[name=username]','move-reader');await none.field('[name=password]',password);await none.evaluate(`document.querySelector('form').requestSubmit()`);await none.wait(`!!document.querySelector('.ir-nav')`,'login another actor');await open(none);assert.deepEqual((await read(none)).colors,palette);await close(none);
 checks.push('Usuario sin clientes guarda su propia paleta; no modifica la del lector. Logout y cambio de cuenta no heredan colores.');

 await home(first);await open(first);await first.click('[data-port-colors-reset="rj45"]');await save(first,{rj45_poe:'#654abc'});await first.click('[data-port-colors-reset-all]');await save(first,{});await color(first,'rj45','#123456');await color(first,'rj45_poe','#654abc');await save(first,palette);await close(first);
 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-port-colors-open]')`,'reload persisted');await open(first);assert.deepEqual((await read(first)).colors,palette);
 checks.push('Restaurar un tipo y todos genera cambios explícitos confirmados; recargar conserva la configuración final.');

 // A POST deliberately never reaches the server. It must remain recoverable, not report success.
 await first.send('Fetch.enable',{patterns:[{urlPattern:origin+route,requestStage:'Request'}]});
 await color(first,'sfp','#222333');await first.click('[data-port-colors-save]');
 const held=await poll(()=>first.paused?.shift(),'palette POST intercepted');assert.equal(held.request.method,'POST');
 await first.send('Fetch.fulfillRequest',{requestId:held.requestId,responseCode:503,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from('{"error":"synthetic_unavailable"}').toString('base64')});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('[data-port-colors-pending]')&&!document.querySelector('[data-port-colors-query]').disabled`,'uncertain original intent retained');assert.deepEqual((await read(first)).colors,palette);
 await first.click('[data-port-colors-query]');await first.wait(`!!document.querySelector('[data-port-colors-pending]')&&!document.querySelector('[data-port-colors-cancel]').disabled`,'query notRecorded remains pending');
 await first.click('[data-port-colors-cancel]');await ready(first);assert.deepEqual((await read(first)).colors,palette);
 checks.push('Error503 sin envío conserva diario original; consulta notRecorded no inventa éxito, cancelación mantiene la paleta confirmada.');

 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 assert.equal(await first.evaluate(`document.documentElement.scrollWidth<=window.innerWidth+2`),true);
 assert.equal(await first.evaluate(`document.querySelector('${panel}').scrollWidth<=document.querySelector('${panel}').clientWidth+2`),true);
 await first.evaluate(`document.querySelector('[data-port-colors-input="rj45"]').focus();true`);await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
 assert.equal(await first.evaluate(`!!document.activeElement?.closest('${panel}')`),true);await shot(first,'palette-mobile-keyboard.png');
 checks.push('Panel390px sin desbordamiento, controles nativos alcanzables por Tab; sin prueba de voz de lector.');
 const reader=await read(first);await close(first);await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 for(const lang of ['en','de','es']){await first.wait(`!document.querySelector('.rc-settings select').disabled`,'language ready');await first.field('.rc-settings select',lang);await first.wait(`document.documentElement.lang===${JSON.stringify(lang)}&&!document.querySelector('.rc-settings select').disabled`,'language saved');await open(first);const text=await first.evaluate(`document.querySelector('${panel}').innerText`);assert.ok(text.includes(lang==='es'?'Guardar':lang==='de'?'Speichern':'Save'));assert.ok(!text.includes('undefined'));await close(first)}
 checks.push('Textos del editor disponibles en EN/DE/ES con los nombres técnicos conservados.');
 await writeFile(path.join(out,'expected-colors.json'),JSON.stringify({reader,none:noneExpected},null,2)+'\n');
});
