// I-04.04: offered arrow, HTML5 drag and emulated-touch controls in real Edge.
// Python owns the isolated SQL fixture, exact durable comparison and restart.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,delay,poll,fixture as ids} from './browser-quince-support.mjs';

const writeJson=(out,name,value)=>writeFile(path.join(out,name),JSON.stringify(value,null,2)+'\n');
const changes=(previous,patches)=>{
 const next=structuredClone(previous);next.revision++;
 for(const [id,patch] of Object.entries(patches))Object.assign(next.devices.find(d=>d.id===id),patch);
 return next;
};

await runScenario(async({first,session,checks,shot,out,origin,responses})=>{
 await infrastructure(first);
 const initial=await snapshot(first),writes=[],commandPath='/api/v1/customers/'+ids.customer+'/commands';
 const requestedActions=[],touchEvents=[];
 first.ws.addEventListener('message',event=>{
  const data=JSON.parse(event.data),request=data.params?.request;
  if(data.method==='Network.requestWillBeSent'&&request?.method==='POST'&&request.url===origin+commandPath){
   const headers=Object.fromEntries(Object.entries(request.headers).map(([key,value])=>[key.toLowerCase(),value]));
   writes.push({...JSON.parse(request.postData),revision:headers['if-match']});
  }
 });
 let expected=structuredClone(initial);
 assert.equal(initial.devices.length,3);assert.equal(initial.ports.length,6);
 assert.equal(initial.connections.length,1);assert.equal(initial.portGroups.length,3);
 await writeJson(out,'initial-project.json',initial);
 const second=await session('move-second');await infrastructure(second);
 assert.deepEqual(normalize(await snapshot(second)),normalize(expected));

 async function openRack(tab,id){
  if(!await tab.evaluate(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`))await tab.button('Gestionar infraestructura');
  await tab.wait(`!!document.querySelector('[data-rack-id="${id}"] .rc-rack-open')`,'rack card');
  await tab.click(`[data-rack-id="${id}"] .rc-rack-open`);
  await tab.wait(`!!document.querySelector('#rack-detail-export')`,'physical rack');
 }
 const order=tab=>tab.evaluate(`[...document.querySelectorAll('#rack-detail-export [data-devid]')].map(e=>e.dataset.devid)`);
 async function exact(label){assert.deepEqual(normalize(await snapshot(first)),normalize(expected),label)}
 async function committed(next,label){
  await poll(async()=>(await snapshot(first)).revision===next.revision,'Committed project revision: '+label);
  await saved(first);expected=next;await exact(label);
  assert.equal(writes.length,expected.revision-initial.revision,'One GUI command per committed revision');
 }
 async function noop(action,label){
  const count=writes.length;await action();await delay(120);await exact(label);
  assert.equal(writes.length,count,label+': no command POST');
 }
 async function drag(source,target){
  return first.evaluate(`(()=>{
   const source=document.querySelector('[data-devid="${source}"]'),target=document.querySelector('[data-devid="${target}"]');
   if(!source||!target||!source.draggable)throw Error('Offered draggable rows missing');
   const transfer=new DataTransfer(),events=[];
   for(const [element,type] of [[source,'dragstart'],[target,'dragenter'],[target,'dragover'],[target,'drop'],[source,'dragend']]){
    element.dispatchEvent(new DragEvent(type,{bubbles:true,cancelable:true,dataTransfer:transfer}));events.push(type);
   }
   return {source:source.dataset.devid,target:target.dataset.devid,payload:transfer.getData('text/plain'),events};
  })()`);
 }
 async function touch(source,target,endType='touchEnd'){
  await first.send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:1});
  const points=await first.evaluate(`(()=>{
   const source=document.querySelector('[data-devid="${source}"] .ir-drag'),target=document.querySelector('[data-devid="${target}"] .ir-drag');
   if(!source||!target)throw Error('Offered touch handles missing');source.scrollIntoView({block:'center'});
   const point=element=>{const r=element.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}};
   window.__orderVariantTouch=[];
   for(const type of ['touchstart','touchmove','touchend','touchcancel'])if(window.__orderVariantTouchListener)document.removeEventListener(type,window.__orderVariantTouchListener,true);
   window.__orderVariantTouchListener=e=>window.__orderVariantTouch.push({type:e.type,isTrusted:e.isTrusted,device:e.target.closest('[data-devid]')?.dataset.devid||null});
   for(const type of ['touchstart','touchmove','touchend','touchcancel'])document.addEventListener(type,window.__orderVariantTouchListener,{capture:true});
   return {start:point(source),end:point(target),height:innerHeight,width:innerWidth};
  })()`);
  for(const point of [points.start,points.end])assert.ok(point.x>0&&point.y>0&&point.x<points.width&&point.y<points.height,'Both touch handles visible');
  const contact=point=>[{...point,id:0,radiusX:2,radiusY:2,force:1}];
  await first.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:contact(points.start)});
  for(const fraction of [.25,.5,.75,1]){
   const point={x:points.start.x+(points.end.x-points.start.x)*fraction,y:points.start.y+(points.end.y-points.start.y)*fraction};
   await first.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:contact(point)});
  }
  await first.send('Input.dispatchTouchEvent',{type:endType,touchPoints:[]});
  const observed=await first.evaluate('window.__orderVariantTouch');
  touchEvents.push(...observed.map(e=>({...e,gestureEnd:endType})));
  await first.send('Emulation.setTouchEmulationEnabled',{enabled:false,maxTouchPoints:1});
  assert.ok(observed.some(e=>e.type==='touchstart'&&e.isTrusted&&e.device===source),'Trusted CDP touch starts on actual source handle');
  assert.ok(observed.some(e=>e.type==='touchmove'&&e.isTrusted),'Trusted touch movement reaches product');
  if(endType==='touchCancel')assert.ok(observed.some(e=>e.type==='touchcancel'&&e.isTrusted),'Native touchCancel was delivered');
  else{
   assert.ok(observed.some(e=>e.type==='touchend'&&e.isTrusted),'Trusted touch end reaches product');
   assert.equal(observed.some(e=>e.type==='touchcancel'),false,'Gesture was not cancelled by browser scrolling');
  }
  return points;
 }

 await openRack(first,ids.rackA);
 assert.deepEqual(await order(first),[ids.a,ids.b]);
 await noop(()=>touch(ids.a,ids.b,'touchCancel'),'Cancelled touch drag preserves state');
 await noop(async()=>{
  await first.send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:1});
  const point=await first.evaluate(`(()=>{const el=document.querySelector('[data-devid="${ids.a}"] .ir-units');el.scrollIntoView({block:'center'});const b=el.getBoundingClientRect();return{x:b.x+b.width/2,y:b.y+b.height/2}})()`);
  await first.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...point,id:0,radiusX:2,radiusY:2,force:1}]});
  await first.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await first.send('Emulation.setTouchEmulationEnabled',{enabled:false,maxTouchPoints:1});
 },'Ordinary tap after cancellation cannot commit a retained drag');
 requestedActions.push('cancel-touch-then-normal-tap');
 checks.push('Native touchCancel discards the drag: no POST immediately or on a later ordinary tap inside the rack');
 await noop(async()=>{
  const result=await first.evaluate(`(()=>{const port=document.querySelector('[data-vport="${ids.pa}"]'),dataTransfer=new DataTransfer(),event=new DragEvent('dragstart',{bubbles:true,cancelable:true,dataTransfer});if(!port)throw Error('Source port missing');port.dispatchEvent(event);return{prevented:event.defaultPrevented,payload:dataTransfer.getData('text/plain')}})()`);
  assert.deepEqual(result,{prevented:true,payload:''},'Dragging a port cannot start a device reorder');
 },'Port drag is blocked without a command');
 assert.equal(await first.evaluate(`document.querySelector('[data-devid="${ids.a}"] button[title="Subir"]').disabled`),true);
 assert.equal(await first.evaluate(`document.querySelector('[data-devid="${ids.b}"] button[title="Bajar"]').disabled`),true);
 await noop(()=>first.click(`[data-devid="${ids.a}"] button[title="Subir"]`),'Disabled boundary arrow');
 checks.push('Boundary arrows are disabled; activation writes no POST and leaves complete snapshot/revision unchanged');

 await first.click(`[data-devid="${ids.a}"] button[title="Bajar"]`);
 await committed(changes(expected,{[ids.a]:{sortOrder:1},[ids.b]:{sortOrder:0}}),'Bajar changes documentary order only');
 assert.deepEqual(await order(first),[ids.b,ids.a]);requestedActions.push('arrow-down');
 await shot(first,'order-arrow-down.png');

 const dragged=await drag(ids.a,ids.b);
 assert.equal(dragged.payload,ids.a,'Source UUID comes from product dragstart handler');
 await committed(changes(expected,{[ids.a]:{sortOrder:0},[ids.b]:{sortOrder:1}}),'HTML5 drop changes documentary order only');
 assert.deepEqual(await order(first),[ids.a,ids.b]);requestedActions.push('html5-drag-events');
 await noop(()=>drag(ids.a,ids.a),'Drop onto the same row');
 await shot(first,'order-html5-drop.png');
 checks.push('Product draggable row writes UUID to DataTransfer; HTML5 dragstart/enter/over/drop/end reorders; same-row drop is no-op');

 const touchPoints=await touch(ids.a,ids.b);
 await committed(changes(expected,{[ids.a]:{sortOrder:1},[ids.b]:{sortOrder:0}}),'Emulated touch reorder changes documentary order only');
 assert.deepEqual(await order(first),[ids.b,ids.a]);requestedActions.push('cdp-touch-handle');
 await shot(first,'order-touch-drop.png');
 checks.push('Trusted CDP touch gesture on offered drag handle reorders by UUID; original attributes, ports and cable remain exact');

 await first.click(`[data-devid="${ids.b}"] button[title="Opciones del equipo"]`);
 await first.wait(`document.querySelector('dialog #operation-title')?.textContent==='Mover'`,'move dialog');
 await first.field('dialog select[name=rackId]',ids.rackB);
 const beforeCancel=writes.length;
 await first.button('Cancelar');await first.wait(`!document.querySelector('dialog[open]')`,'cancelled move');
 await delay(120);await exact('Cancelled cross-rack move leaves full state unchanged');assert.equal(writes.length,beforeCancel);
 await first.click(`[data-devid="${ids.b}"] button[title="Opciones del equipo"]`);
 await first.wait(`!!document.querySelector('dialog select[name=rackId]')`,'move dialog reopened');
 await first.field('dialog select[name=rackId]',ids.rackB);await submit(first);
 await committed(changes(expected,{[ids.b]:{rackId:ids.rackB,sortOrder:1}}),'Cross-rack move appends to destination, preserves source order values');
 assert.deepEqual(await order(first),[ids.a]);requestedActions.push('move-cross-rack-append');
 await first.wait(`document.querySelector('[data-wire="${ids.cable}"]')?.getAttribute('stroke-dasharray')==='5 3'`,'origin cross-rack cable stub');
 await shot(first,'order-cross-rack-origin.png');

 await openRack(first,ids.rackB);assert.deepEqual(await order(first),[ids.c,ids.b]);
 await first.click(`[data-devid="${ids.b}"] button[title="Subir"]`);
 await committed(changes(expected,{[ids.b]:{sortOrder:0},[ids.c]:{sortOrder:1}}),'Destination local arrow changes sortOrder only');
 assert.deepEqual(await order(first),[ids.b,ids.c]);requestedActions.push('arrow-up-after-cross');
 await first.wait(`document.querySelector('[data-wire="${ids.cable}"]')?.getAttribute('stroke-dasharray')==='5 3'`,'destination cross-rack cable stub');
 await shot(first,'order-cross-rack-destination.png');
 checks.push('Mover exposes destination rack only: appends after existing C; local Subir yields B,C. Cancel writes nothing; cable UUID/endpoints preserved with cross-rack stubs');

 assert.deepEqual(writes.map(w=>w.type),['device.reorder','device.reorder','device.reorder','device.move','device.reorder']);
 const wantedPayloads=[{rackId:ids.rackA,deviceIds:[ids.b,ids.a]},
  {rackId:ids.rackA,deviceIds:[ids.a,ids.b]},
  {rackId:ids.rackA,deviceIds:[ids.b,ids.a]},
  {id:ids.b,rackId:ids.rackB},
  {rackId:ids.rackB,deviceIds:[ids.b,ids.c]}];
 assert.deepEqual(writes.map(w=>w.payload),wantedPayloads,'Complete IDs and closed command payloads; no guessed U or position field');
 assert.deepEqual(writes.map(w=>w.revision),wantedPayloads.map((_,i)=>'"'+(initial.revision+i)+'"'));
 assert.equal(expected.revision,initial.revision+5);
 for(const tab of [first,second]){
  await tab.send('Page.reload');await tab.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'reload clients');await infrastructure(tab);
  assert.deepEqual(normalize(await snapshot(tab)),normalize(expected));await openRack(tab,ids.rackB);
  assert.deepEqual(await order(tab),[ids.b,ids.c]);
  await tab.wait(`document.querySelector('[data-wire="${ids.cable}"]')?.getAttribute('stroke-dasharray')==='5 3'`,'reloaded cross cable');
 }
 assert.deepEqual(responses.filter(r=>r.path===commandPath&&r.status>=400),[]);
 checks.push('Five committed GUI commands and ETags exact; full reload and separate authorized actor preserve complete snapshot, documentary order and cross-rack cable');
 await writeJson(out,'expected-project.json',expected);
 await writeJson(out,'order-variants-details.json',{writes,requestedActions,expectedCommits:5,
  noOpChecks:{cancelledTouchThenOrdinaryTap:true,portDragBlocked:true,boundaryArrow:true,sameRowDrop:true,cancelledMove:true},dragged,touchEvents,touchPoints,
  sourceFinalOrder:[ids.a],destinationFinalOrder:[ids.b,ids.c],
  limits:['HTML5 drag events are dispatched through DOM DataTransfer, not a physical mouse drag.',
   'Touch is trusted Edge/CDP emulation, not physical touchscreen hardware.',
   'Touchcancel then ordinary-tap state is tested; no touch hardware matrix or positionU is invented.',
   'Python separately checks all nine SQL tables, permission rejections and server-process restart.']});
});
