import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,submit,saved,normalize} from './browser-client-changes-support.mjs';

// Datos sinteticos y literales con caracteres no ASCII para comprobar escape y persistencia.
const dose={name:'Dose editada literal <img> Ω 東京',sn:'serial-dose-editado',note:'nota editada de dose Ω'};
const end={name:'Dispositivo final editado literal <img> Ω',sn:'serial-end-editado',note:'nota editada de end 東京'};

const editedDevice=(before,data)=>{
 const v=structuredClone(before);v.name=data.name;v.properties??={};v.properties.notes??={};
 for(const key of ['model','ip','firmware'])v.properties.notes[key]??='';
 Object.assign(v.properties.notes,{sn:data.sn,text:data.note});return v;
};

await runScenario(async({first,session,checks,fixture:f,out,shot,responses})=>{
 const writes=[];
 first.ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Network.requestWillBeSent'&&m.params.request.method==='POST'&&m.params.request.url.endsWith('/commands'))writes.push(m.params.request)});

 async function openDevice(tab,id,label,probe){
  await tab.evaluate(`(()=>{const a=document.querySelector('[data-room-device-id="${id}"]');if(!a)throw Error('room device missing');[...a.querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(label)}).click()})()`);
  await tab.wait(`!!document.querySelector('dialog[open] ${probe}')`,'dialog '+label);
 }
 async function editDevice(tab,id,data){
  await openDevice(tab,id,'Editar','[name=name]');
  await tab.field('dialog [name=name]',data.name);
  await tab.field('dialog [name=sn]',data.sn);
  await tab.field('dialog [name=notes]',data.note);
  await submit(tab);
  await tab.wait(`!document.querySelector('dialog[open]')`,'device committed');
  await saved(tab);
 }
 // Los puertos RJ45 de prueba no admiten rol de energia (solo tipo power): se edita su estado, que el editor ofrece.
 async function setPortStatus(tab,pid){
  await tab.evaluate(`document.querySelector('[data-room-port="${pid}"]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))`);
  await tab.wait(`!!document.querySelector('dialog[open] select')`,'port editor');
  await pick(tab,'status','status');
  await tab.wait(`[...document.querySelectorAll('dialog[open] select')].some(s=>[...s.options].some(o=>o.value==='reserved'))`,'status choices');
  await pick(tab,'reserved','reserved');
  await submit(tab);
  await tab.wait(`!document.querySelector('dialog[open]')`,'port committed');
  await saved(tab);
 }
 // Elige en el select cuyas opciones contienen `probe` (el de campo o el de valor del editor de puertos).
 function pick(tab,probe,value){
  return tab.evaluate(`(()=>{const s=[...document.querySelectorAll('dialog[open] select')].find(s=>[...s.options].some(o=>o.value===${JSON.stringify(probe)}));if(!s)throw Error('select missing');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(s,${JSON.stringify(value)});s.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
 }

 await first.field('.rc-settings select','es');
 await infrastructure(first);
 const base=await snapshot(first);

 await editDevice(first,f.dose,dose);
 await setPortStatus(first,f.pdose);
 await editDevice(first,f.end,end);
 await setPortStatus(first,f.pend);

 const sent=writes.map(r=>JSON.parse(r.postData));
 assert.deepEqual(sent.map(c=>c.type),['device.update','ports.update','device.update','ports.update']);
 assert.equal(sent[0].payload.id,f.dose);assert.equal(sent[2].payload.id,f.end);
 assert.equal(sent[0].payload.name,dose.name);assert.equal(sent[2].payload.name,end.name);
 assert.equal(sent[1].payload.deviceId,f.dose);assert.equal(sent[3].payload.deviceId,f.end);
 const commandStatuses=responses.filter(r=>r.path.endsWith('/commands')).map(r=>r.status);
 assert.deepEqual(commandStatuses,[200,200,200,200],'four accepted commands');
 checks.push('Dose y dispositivo final: nombre y notas editados por GUI (device.update), un puerto por objeto con estado reserved (ports.update). Cuatro comandos aceptados, estado 200.');

 const after=await snapshot(first);
 const dB=base.devices.find(d=>d.id===f.dose),dA=after.devices.find(d=>d.id===f.dose);
 assert.equal(dA.name,dose.name);assert.equal(dA.properties.notes.sn,dose.sn);assert.equal(dA.properties.notes.text,dose.note);
 assert.deepEqual(dA,editedDevice(dB,dose),'dose keeps all unedited attributes and complete properties');
 const eB=base.devices.find(d=>d.id===f.end),eA=after.devices.find(d=>d.id===f.end);
 assert.equal(eA.name,end.name);assert.equal(eA.properties.notes.sn,end.sn);assert.equal(eA.properties.notes.text,end.note);
 assert.deepEqual(eA,editedDevice(eB,end),'end device keeps all unedited attributes and complete properties');
 assert.equal(after.revision,base.revision+4,'exactly four inventory revisions');
 for(const device of [f.dose,f.end]){
  const pB=base.ports.filter(p=>p.deviceId===device),pA=after.ports.filter(p=>p.deviceId===device);
  assert.deepEqual(pA.map(p=>p.id).sort(),pB.map(p=>p.id).sort(),'same ports');
  for(const pa of pA){const pb=pB.find(p=>p.id===pa.id);const exp=structuredClone(pb);if(pa.id===f.pdose||pa.id===f.pend)exp.status="reserved";assert.deepEqual(pa,exp,'only the chosen port status changes');}
 }
 assert.deepEqual(after.portGroups,base.portGroups,'port groups unchanged');
 assert.deepEqual(after.connections,base.connections,'cables unchanged');
 checks.push('Campos no editados (id, sala, orden, presupuesto, tipo, grupos, puertos, cables) iguales antes y despues; solo cambian nombre, notas y el estado del puerto elegido.');

 // Otra cuenta autorizada lee el resultado persistido.
 const second=await session(f.secondName);
 await infrastructure(second);
 assert.deepEqual(normalize(await snapshot(second)),normalize(after),'second authorized account reads the committed state');
 assert.equal(await second.evaluate(`document.querySelector('[data-room-device-id="${f.dose}"]').textContent.includes(${JSON.stringify(dose.name)})`),true);

 // Una cuenta de solo lectura ve el resultado pero no tiene el boton de edicion disponible.
 const reader=await session('move-reader');
 await infrastructure(reader);
 assert.deepEqual(normalize(await snapshot(reader)),normalize(after),'reader reads the committed state');
 assert.equal(await reader.evaluate(`[...(document.querySelector('[data-room-device-id="${f.dose}"]')?.querySelectorAll('button')||[])].some(b=>b.textContent.trim()==='Editar'&&!b.disabled)`),false,'reader has no enabled edit button');
 checks.push('Segunda cuenta autorizada y cuenta de solo lectura leen el mismo snapshot; el lector no tiene boton de edicion activo.');

 // Recarga completa de la sesion que escribio.
 await first.send('Page.reload');
 await first.wait(`!!document.querySelector('[data-customer-id="${f.customer}"]')`,'reloaded clients');
 await infrastructure(first);
 assert.deepEqual(normalize(await snapshot(first)),normalize(after),'reloaded session keeps the committed state');
 assert.equal(await first.evaluate(`document.querySelector('[data-room-device-id="${f.end}"]').textContent.includes(${JSON.stringify(end.name)})`),true);
 checks.push('Recarga completa tras guardar: el snapshot coincide y los nombres editados aparecen en la sala.');

 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(after,null,2));
});
