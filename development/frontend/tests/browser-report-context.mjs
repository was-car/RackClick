import assert from 'node:assert/strict';
import {runScenario,infrastructure,snapshot,normalize,fixture as ids} from './browser-quince-support.mjs';
import {reportUiWords} from '../src/report-ui-words.ts';

const baseline=process.env.RACKCLICK_LAYOUT_BASELINE==='1';
const panels=[
 {kind:'print',toggle:'data-print-toggle',rack:'data-print-rack',generate:'data-print-generate',download:'data-print-download'},
 {kind:'rack-svg',toggle:'data-rack-svg-toggle',rack:'data-rack-svg-rack',generate:'data-rack-svg-generate',download:'data-rack-svg-download'},
 {kind:'rc9-excel',toggle:'data-rc9-excel-toggle',rack:'data-rc9-excel-rack',generate:'data-rc9-excel-generate',download:'data-rc9-excel-download'}
];
const technical=kind=>`[data-report-technical="${kind}"]`;
await runScenario(async({first,session,checks,shot,origin})=>{
 await infrastructure(first);const original=normalize(await snapshot(first));
 await first.click(`[data-rack-id="${ids.rack}"] .rc-rack-open`);
 await first.wait(`!!document.querySelector('[data-face="rear"]')`,'physical rack');
 await first.click('[data-face="rear"]');await first.click('[data-secondary-tools]');
 for(const p of panels)await first.click('['+p.toggle+']');
 if(baseline){
  for(const p of panels)assert.equal(await first.evaluate(`document.querySelector('[${p.rack}]').value`),'');
  assert.equal(await first.evaluate(`document.querySelectorAll('[data-report-technical]').length`),0);
  await first.evaluate(`document.querySelector('[data-inventory-rack-svg]').scrollIntoView({block:'start'})`);
  await shot(first,'before-report.png');
  checks.push('Before build has no open-rack proposal and exposes technical metadata in the expanded forms');return;
 }
 for(const p of panels){
  await first.wait(`document.querySelector('[${p.rack}]').value===${JSON.stringify(ids.rack)}`,'first-open rack '+p.kind);
  assert.equal(await first.evaluate(`document.querySelector('${technical(p.kind)}').open`),false);
 }
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-face]').value`),'rear');
 await first.evaluate(`document.querySelector('[data-inventory-rack-svg]').scrollIntoView({block:'start'})`);
 await shot(first,'after-report-desktop.png');
 checks.push('All three exporters propose the open rack on first open; SVG also proposes the visible rear face; metadata starts collapsed');

 for(const p of panels){
  await first.field('['+p.rack+']','');await first.click('['+p.toggle+']');await first.click('['+p.toggle+']');
  assert.equal(await first.evaluate(`document.querySelector('[${p.rack}]').value`),'');
  assert.equal(await first.evaluate(`document.querySelector('[${p.generate}]').disabled`),true);
  await first.click(`[data-use-open-rack="${p.kind}"]`);
  await first.wait(`document.querySelector('[${p.rack}]').value===${JSON.stringify(ids.rack)}`,'explicit context '+p.kind);
 }
 await first.field('[data-print-kind]','client');await first.click('[data-print-toggle]');await first.click('[data-print-toggle]');
 assert.equal(await first.evaluate(`document.querySelector('[data-print-kind]').value`),'client');
 await first.field('[data-print-kind]','rack');
 checks.push('Explicitly cleared rack stays empty across close/reopen until Use open rack; print client scope is not overwritten');

 await first.send('Page.bringToFront');await first.evaluate(`document.querySelector('${technical('rack-svg')}>summary').focus()`);
 await first.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});
 await first.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await first.wait(`document.querySelector('${technical('rack-svg')}').open`,'technical keyboard open');
 await first.click(technical('rack-svg')+'>summary');
 await first.send('Network.setBlockedURLs',{urls:[origin+'/api/v1/customers/'+ids.customer+'/reports/rack-svg']});
 await first.click('[data-rack-svg-generate]');
 await first.wait(`!!document.querySelector('[data-rack-svg-pending]')&&!!document.querySelector('[data-rack-svg-error]')`,'uncertain SVG');
 const pending=await first.evaluate(`document.querySelector('[data-rack-svg-request]').textContent`);
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-pending]').closest('[data-report-technical]')===null&&document.querySelector('[data-rack-svg-error]').closest('[data-report-technical]')===null`),true);
 assert.equal(await first.evaluate(`document.querySelector('${technical('rack-svg')}').open`),false);
 await first.click('.rc-inventory-toolbar>button:first-child');
 await first.wait(`document.querySelector('[data-hierarchy-details]').open`,'manage hierarchy');
 await first.click(`[data-rack-id="${ids.otherRack}"] .rc-rack-open`);await first.click('[data-secondary-tools]');
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-rack]').value`),ids.rack);
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-request]').textContent`),pending);
 assert.equal(await first.evaluate(`document.querySelector('[data-use-open-rack="rack-svg"]').disabled`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-face]').value`),'rear');
 await first.click(technical('rack-svg')+'>summary');
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-request]').textContent`),pending);
 await first.click(technical('rack-svg')+'>summary');
 await first.send('Network.setBlockedURLs',{urls:[]});await first.click('[data-rack-svg-retry]');
 await first.wait(`!!document.querySelector('[data-rack-svg-download]')&&!document.querySelector('[data-rack-svg-pending]')`,'original SVG retry confirmed');
 assert.match(await first.evaluate(`document.querySelector('${technical('rack-svg')}').textContent`),/SHA256: [a-f0-9]{64}/);
 await first.click('[data-rack-svg-toggle]');await first.click('[data-rack-svg-toggle]');
 assert.equal(await first.evaluate(`document.querySelector('[data-rack-svg-rack]').value`),ids.rack);
 await first.click('[data-use-open-rack="rack-svg"]');
 await first.wait(`document.querySelector('[data-rack-svg-rack]').value===${JSON.stringify(ids.otherRack)}`,'deliberate rack switch after recovery');
 assert.equal(await first.evaluate(`!!document.querySelector('[data-rack-svg-download]')`),false);
 checks.push('Pending/error/action controls remain outside closed metadata; navigating to another rack cannot overwrite scope or request ID; same request retries and confirms; only explicit context switch clears the old confirmation');

 for(const p of panels.filter(p=>p.kind!=='rack-svg')){
  await first.click(`[data-use-open-rack="${p.kind}"]`);
  await first.click('['+p.generate+']');await first.wait(`!!document.querySelector('[${p.download}]')`,'confirmed '+p.kind);
  assert.equal(await first.evaluate(`document.querySelector('${technical(p.kind)}').open`),false);
  assert.match(await first.evaluate(`document.querySelector('${technical(p.kind)}').textContent`),/SHA256: [a-f0-9]{64}/);
 }
 assert.match(await first.evaluate(`document.querySelector('[data-rc9-excel-format]').textContent`),/HTML/);
 assert.deepEqual(normalize(await snapshot(first)),original);
 checks.push('Print and RC9 Excel confirm through the real server; technical hashes are retained, download controls visible and XLS remains honestly identified as HTML; ten-table inventory unchanged');

 for(const lang of ['en','de','es']){
  await first.click('.ir-all-clients');await first.wait(`!!document.querySelector('.rc-settings select')`,'language');await first.field('.rc-settings select',lang);
  await infrastructure(first);await first.click(`[data-rack-id="${ids.rack}"] .rc-rack-open`);await first.click('[data-secondary-tools]');
  for(const p of panels){await first.click('['+p.toggle+']');assert.equal(await first.evaluate(`document.querySelector('${technical(p.kind)}>summary').textContent`),reportUiWords[lang].technical);}
 }
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await first.evaluate(`document.querySelector('[data-inventory-rack-svg]').scrollIntoView({block:'start'})`);
 assert.ok(await first.evaluate('document.documentElement.scrollWidth<=innerWidth+2'));
 await shot(first,'after-report-mobile.png');
 await first.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 const second=await session();await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),original);
 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'reload');await infrastructure(first);
 assert.deepEqual(normalize(await snapshot(first)),original);
 checks.push('EN/DE/ES, native keyboard, 390px without horizontal overflow, reload and a separate browser session pass without inventory changes');
});
