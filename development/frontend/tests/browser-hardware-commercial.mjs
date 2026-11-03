import {chooseHardware} from './browser-hardware-picker-support.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize} from './browser-quince-support.mjs';

await runScenario(async({first,session,checks,fixture:f,out,shot})=>{
 await infrastructure(first);await first.click(`[data-rack-id="${f.rack}"] .rc-rack-open`);
 const key='startech-c6panelutp241uft',revision='startech-20261030-v1',ids=[];
 for(const name of ['Panel StarTech A Ω','Panel StarTech B']){
  await first.click('[data-add-hardware]');await first.wait(`!!document.querySelector('dialog[open] [data-hardware-profile]')`,'hardware selector');
  await chooseHardware(first,key,revision);
  assert.equal(await first.evaluate(`document.querySelector('[data-hardware-preview]').textContent.includes('44.3')`),true);
  assert.equal(await first.evaluate(`document.querySelector('[data-commercial-source]').href`),'https://media.startech.com/cms/pdfs/c6panelutp241uft_datasheet.pdf');
  await first.field('[data-hardware-name]',name);await first.field('[data-hardware-rack]',f.rack);await submit(first);await saved(first);
  const p=await snapshot(first),device=p.devices.find(d=>d.name===name);assert.ok(device);ids.push(device.id);
  assert.equal(device.properties.hardwareProfileVersion,revision);assert.equal(device.properties.physicalDimensionsMm.height,44.3);
  assert.equal(device.properties.hardwareIdentity.model,'C6PANELUTP241UFT');
  assert.equal(p.ports.filter(port=>port.deviceId===device.id).length,48);
 }
 assert.notEqual(...ids);let p=await snapshot(first);
 const port=(id,face,gn)=>p.ports.find(port=>port.deviceId===id&&port.face===face&&port.gn===gn).id;
 assert.notEqual(port(ids[0],'front',1),port(ids[0],'rear',1));
 checks.push('GUI selector sends exact commercial revision; two independent 1U instances have48ports each, identity and44.3mm height');
 async function connect(a,b){await first.click(`[data-vport="${a}"]`);await first.click(`[data-vport="${b}"]`);await saved(first);}
 await connect(port(ids[0],'front',1),port(f.firewall,'front',1));
 await first.evaluate(`document.querySelector('[data-hardware-key="${key}"]').scrollIntoView({block:'start'})`);await shot(first,'commercial-front.png');
 await first.click('[data-face="rear"]');
 assert.equal(await first.evaluate(`document.querySelectorAll('[data-devid="${ids[0]}"] [data-vport]').length`),24);
 // Both ends are visible on the current face; rear logical ordinals retain IDs.
 await connect(port(ids[0],'rear',1),port(f.firewall,'rear',1));
 await first.evaluate(`document.querySelector('[data-hardware-key="${key}"]').scrollIntoView({block:'start'})`);await shot(first,'commercial-rear.png');
 p=await snapshot(first);assert.equal(p.connections.length,2);
 assert.equal(await first.evaluate(`document.querySelector('[data-mounted-rack]').textContent.includes('4/4 U')`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-commercial-identity]').textContent.includes('C6PANELUTP241UFT')`),true);
 checks.push('Front/rear Click-Click saves two independent cables; known old firewall and shelf remain intact; rack4U exact');
 const physical=p.devices.find(d=>d.id===ids[0]),physicalPorts=p.ports.filter(port=>port.deviceId===ids[0]);
 await first.click(`[data-hardware-edit="${ids[0]}"]`);await first.field('dialog [name=name]','Panel editado <img> Ω');await first.field('dialog [name=notes]','Cliente sintético, no fotografía');await submit(first);await saved(first);
 p=await snapshot(first);const edited=p.devices.find(d=>d.id===ids[0]);
 assert.deepEqual(edited.properties.hardwareIdentity,physical.properties.hardwareIdentity);assert.deepEqual(edited.properties.physicalDimensionsMm,physical.properties.physicalDimensionsMm);
 assert.deepEqual(p.ports.filter(port=>port.deviceId===ids[0]),physicalPorts);assert.equal(p.connections.length,2);
 assert.equal(await first.evaluate(`!!document.querySelector('[data-devid="${ids[0]}"] img')`),false);
 // A rejected capacity write must not create a third model or report success.
 const before=normalize(p);await first.click('[data-add-hardware]');await chooseHardware(first,key,revision);await first.field('[data-hardware-name]','No debe caber');await submit(first);
 await first.wait(`!!document.querySelector('dialog[open] [role=alert]')`,'capacity rejection');assert.deepEqual(normalize(await snapshot(first)),before);await first.button('Cancelar');
 // Keep the same form usable on a small viewport; labels and names are not translated.
 await first.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 await first.click('[data-add-hardware]');await chooseHardware(first,key,revision);
 assert.equal(await first.evaluate(`(()=>{const d=document.querySelector('dialog[open]');return d.scrollWidth<=d.clientWidth+2})()`),true);await shot(first,'commercial-mobile-form.png');await first.button('Cancelar');
 await first.send('Emulation.clearDeviceMetricsOverride',{});
 const expected=normalize(await snapshot(first));
 await first.send('Page.reload',{ignoreCache:true});await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reload clients');await infrastructure(first);assert.deepEqual(normalize(await snapshot(first)),expected);
 const second=await session('hardware-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),expected);
 const reader=await session('hardware-reader');await infrastructure(reader);assert.deepEqual(normalize(await snapshot(reader)),expected);assert.equal(await reader.evaluate(`!!document.querySelector('[data-add-hardware]')`),false);
 checks.push('Rename/notes preserve identity/ports/cables; capacity rejects without ghost success;390pxform, reload, another account and reader verified');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(expected,null,2)+'\n');
});
