import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {RackClickApi,ApiError} from '../src/api.ts';
import {validPrivateTemplateName,preparePrivateTemplate,validPrivateDraft,confirmedPrivateTemplate,mutatePrivateTemplate,privateTemplateStatus,cancelPrivateTemplate} from '../src/private-templates.ts';
import {privateTemplateWords} from '../src/private-template-words.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),actor=id(1),customer=id(2),template=id(3),other=id(4),hash='a'.repeat(64);
const list=(revision=7)=>({kind:'privateTemplates',customerId:customer,ownerId:actor,revision,templates:[{id:template,name:'Original Ω',active:true,definitionVersion:1,definitionSha256:hash,kind:'rackEquipment',sizeU:1,groupCount:0,portCount:0}]});
const body=(name='  Nuevo 東京 e\u0301  ')=>({type:'rename',templateId:template,name});
const draft=(name)=>preparePrivateTemplate(actor,list(),body(name));
const receipt=(d,changed=true)=>({kind:'privateTemplates',customerId:customer,ownerId:actor,revision:d.revision+(changed?1:0),requestId:d.requestId,operationId:id(5),result:{type:'rename',templateId:template,name:JSON.parse(d.body).name.trim(),active:true,changed,definitionVersion:1,definitionSha256:hash}});
const response=(value,revision=value.revision)=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json',ETag:'"templates-'+revision+'"'}});
test('rename intention accepts Names Unicode/trim boundaries without NFC and remains a closed public intention',()=>{
 for(const name of ['東京 e\u0301','𐀀'.repeat(100),' \t'+ '𐀀'.repeat(100)+'\u0085','\u0085Ω\u3000','\ufeffΩ\ufeff'])assert.equal(validPrivateTemplateName(name),true,name);
 for(const name of ['', ' \u0085\u3000','𐀀'.repeat(101),'x\u0000','x\ny','x\ud800'])assert.equal(validPrivateTemplateName(name),false,name);
 const d=draft();assert.equal(Object.isFrozen(d),true);assert.deepEqual(JSON.parse(d.body),body());assert.equal(validPrivateDraft(d),true);
 for(const extra of [{ownerId:actor},{definition:{}},{definitionSha256:hash},{active:true}])assert.throws(()=>preparePrivateTemplate(actor,list(),{...body(),...extra}));
 assert.equal(validPrivateDraft({...d,body:JSON.stringify({type:'rename',templateId:template})}),false);
 assert.equal(validPrivateDraft({...d,body:JSON.stringify({...body(),templateId:other,name:'bad\u0001'})}),false);
});
test('rename confirms exact active template/name and changed versus no-op revisions; malformed success retains uncertainty',()=>{
 const d=draft();assert.equal(confirmedPrivateTemplate(receipt(d),d).result.name,'Nuevo 東京 e\u0301');assert.equal(confirmedPrivateTemplate(receipt(d,false),d).revision,7);
 for(const mutate of [x=>x.result.name='Nuevo 東京 é',x=>x.result.templateId=other,x=>x.result.active=false,x=>x.result.type='deactivate',x=>x.revision=9,x=>x.result.definitionVersion=2,x=>x.result.definitionSha256='bad',x=>x.ownerId=other,x=>x.result.extra=true]){const x=receipt(d);mutate(x);assert.throws(()=>confirmedPrivateTemplate(x,d),e=>e.uncertain===true)}
 const x=receipt(d);x.result.changed=false;assert.throws(()=>confirmedPrivateTemplate(x,d),e=>e.uncertain);
});
test('lost rename preserves original key/body/revision for replay/status/cancel and rejects actor switches after await',async()=>{
 const d=draft(),calls=[],a=Object.assign(new RackClickApi(async(url,init)=>{calls.push({url,body:init.body,headers:init.headers});if(calls.length===1)throw Error('lost');if(url.includes('/operations/'))return response({state:'committed',customerId:customer,ownerId:actor,revision:12,requestId:d.requestId,operation:receipt(d)});return response(receipt(d))}),{actorId:actor,csrf:'synthetic'});
 await assert.rejects(mutatePrivateTemplate(a,d),e=>e.uncertain);await mutatePrivateTemplate(a,d);assert.deepEqual(calls[0],calls[1]);await privateTemplateStatus(a,d);await cancelPrivateTemplate(a,d);assert.deepEqual(calls[3].headers,calls[1].headers);assert.equal(calls[3].body,d.body);assert.equal(calls[1].headers['If-Match'],'"templates-7"');
 const b=Object.assign(new RackClickApi(async()=>{b.actorId=other;return response(receipt(d))}),{actorId:actor,csrf:'synthetic'});await assert.rejects(mutatePrivateTemplate(b,d),e=>e.code==='actor_changed'&&e.uncertain);
});
test('rename hook never commits an A→B→A stale response or unlocks the current task; labels exist in three languages',async()=>{
 for(const lang of ['en','de','es']){assert.ok(privateTemplateWords[lang].renameName);assert.ok(privateTemplateWords[lang].rename)}
 const source=await readFile(new URL('../src/InventoryPrivateTemplates.jsx',import.meta.url),'utf8'),hookSource=source.slice(source.indexOf('export function usePrivateTemplates('),source.indexOf('\nexport function PrivateTemplatePreview(')).replace('export function','function');
 const slots=[],effects=[],reads=[],writes=[],mutations=[];let cursor=0;
 const useState=initial=>{const i=cursor++;if(!(i in slots))slots[i]=initial;return[slots[i],value=>{slots[i]=typeof value==='function'?value(slots[i]):value}]},useRef=initial=>{const i=cursor++;return slots[i]??=({current:initial})},useEffect=(callback,deps)=>{const i=cursor++,old=slots[i];if(!old||deps.some((v,j)=>v!==old.deps[j]))effects.push(()=>{old?.cleanup?.();slots[i]={deps,cleanup:callback()}})};
 const read=(_api,context)=>new Promise(resolve=>reads.push({context,resolve})),journal=async(action,_actor,d)=>{if(action==='write')writes.push(d);return null},mutate=(_api,d)=>new Promise(resolve=>mutations.push({d,resolve}));
 const hook=new Function('useState','useEffect','useRef','readPrivateTemplates','privateTemplateJournal','preparePrivateTemplate','mutatePrivateTemplate','ApiError',hookSource+';return usePrivateTemplates')(useState,useEffect,useRef,read,journal,preparePrivateTemplate,mutate,ApiError);
 const a={actorId:actor},props={api:a,actorId:actor,customerId:customer,userName:'synthetic'},render=p=>{cursor=0;const result=hook(p);while(effects.length)effects.shift()();return result},flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve()};
 render(props);await flush();reads[0].resolve(list());await flush();const old=render(props).mutate(body('Old intention'));await flush();assert.equal(mutations.length,1);
 render({...props,customerId:other});await flush();reads[1].resolve({...list(9),customerId:other});await flush();render(props);await flush();reads[2].resolve(list(10));await flush();const current=render(props).mutate(body('Current intention'));await flush();assert.equal(mutations.length,2);assert.equal(render(props).busy,true);
 mutations[0].resolve(receipt(mutations[0].d));await flush();reads[3].resolve(list(8));await old;await flush();assert.equal(render(props).data.revision,10);assert.equal(render(props).busy,true);assert.equal(JSON.parse(render(props).pending.body).name,'Current intention');
 mutations[1].resolve(receipt(mutations[1].d));await flush();reads[4].resolve(list(11));await current;await flush();assert.equal(render(props).busy,false);assert.equal(render(props).data.revision,11);assert.equal(render(props).pending,null);assert.equal(writes.length,2);
});
