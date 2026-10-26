import {catalogMatches} from './inventory-catalog.ts';
import {catalogWords} from './inventory-catalog-words.ts';
import {inventoryWords} from './inventory-words.ts';
import {Fields} from './OperationDialog.jsx';
import {InventoryCatalogBrowser} from './InventoryCatalogBrowser.jsx';
import {InventoryPrivateTemplateFields} from './InventoryPrivateTemplateFields.jsx';
import {privateTemplateWords} from './private-template-words.ts';
import {PT} from '../generated/rc9.jsx';
export function ManualPortGroups({form,setForm,disabled,w}){
 function update(index,values){setForm({...form,groups:form.groups.map((g,i)=>i===index?{...g,...values}:g)})}
 return <section className="rc-port-groups" data-manual-groups><h3>{w.groups}</h3>{form.groups.map((g,index)=><div key={index}><label>{w.type}<select disabled={disabled} value={g.type} onChange={e=>update(index,{type:e.target.value})}>{Object.entries(PT).map(([type,p])=><option key={type} value={type}>{p.label}</option>)}</select></label><label>{w.count}<input type="number" min={1} max={96} value={g.count} disabled={disabled} onChange={e=>update(index,{count:Number(e.target.value)})}/></label><label>{w.name}<input value={g.name} disabled={disabled} onChange={e=>update(index,{name:e.target.value})}/></label><label>{w.prefix}<input value={g.prefix} disabled={disabled} onChange={e=>update(index,{prefix:e.target.value})}/></label><button type="button" disabled={disabled} onClick={()=>setForm({...form,groups:form.groups.filter((_,i)=>i!==index)})}>{w.remove}</button></div>)}<button type="button" disabled={disabled} onClick={()=>setForm({...form,groups:[...form.groups,{type:'rj45',count:1,name:'',prefix:''}]})}>{w.addGroup}</button></section>;
}
export function InventoryCatalogFields({api,actorId,userName,project,lang,form,setForm,disabled,onRefresh}){
 const w=inventoryWords[lang],c=catalogWords[lang];
 const catalogMode=form.creationMode==='catalog',privateMode=form.creationMode==='private',current=catalogMatches(form.catalogue,actorId,api,project,lang,form.catalogueActor),catalog=current?form.catalogue:null;
 const privateDefinition=form.privateActor===actorId&&api.actorId===actorId&&form.privateDetail?.customerId===project.customerId?form.privateDetail.template.definition:null;
 const selected=catalog?.presets.find(p=>p.key===form.catalogKey),kind=privateMode?(privateDefinition?.kind||form.kind):catalogMode?(selected?.key==='ap'?'endDevice':form.catalogKind):form.kind;
 const options=items=>items.map(x=>({value:x.id,label:x.name+' · '+x.id}));
 const fields=[{key:'name',required:!catalogMode},
  ...(kind==='rackEquipment'?[{key:'rackId',label:'rack',type:'select',required:true,options:options(project.racks)}]:[{key:'roomId',label:'room',type:'select',required:true,options:project.rooms.map(r=>{const b=project.buildings.find(b=>b.id===r.buildingId),s=project.sites.find(s=>s.id===b?.siteId);return {value:r.id,label:[s?.name,b?.name,r.name].filter(Boolean).join(' / ')+' · '+r.id}})}]),
  ...(!catalogMode&&!privateMode&&kind==='rackEquipment'?[{key:'sizeU',type:'number',min:1,max:1000,required:true}]:[]),
  {key:'poeBudget',type:'number',min:0,max:9999,step:'any'},
  ...(catalogMode||privateMode?[{key:'color',label:c.color}]:[]),{key:'sn',label:'serial'},{key:'model'},{key:'ip'},{key:'firmware'},{key:'notes',type:'textarea'}];
 return <section data-inventory-catalog style={{minWidth:0,overflowWrap:'anywhere'}}><div className="ir-face-controls" role="group" aria-label={w.preset}>{['catalog','manual','private'].map(mode=><button type="button" key={mode} data-create-mode={mode} disabled={disabled} aria-pressed={form.creationMode===mode} onClick={()=>setForm({...form,creationMode:mode})}>{mode==='private'?privateTemplateWords[lang].mode:c[mode]}</button>)}</div>
  <div hidden={!catalogMode}><p>{c.immutable}</p><InventoryCatalogBrowser api={api} actorId={actorId} userName={userName} project={project} lang={lang} form={form} setForm={setForm} disabled={disabled} onRefresh={onRefresh} enabled={catalogMode}/><p>{c.nameHint}</p></div>
  <div hidden={!privateMode}><InventoryPrivateTemplateFields api={api} actorId={actorId} project={project} lang={lang} form={form} setForm={setForm} disabled={disabled} enabled={privateMode}/></div>
  <label>{w.kind}<select name={catalogMode?'catalogKind':'kind'} disabled={disabled||privateMode||catalogMode&&selected?.key==='ap'} value={kind} onChange={e=>setForm({...form,[catalogMode?'catalogKind':'kind']:e.target.value})}>{['rackEquipment','dose','endDevice'].map(k=><option key={k} value={k}>{w[k]}</option>)}</select></label>
  <Fields fields={fields} form={form} setForm={setForm} disabled={disabled} w={w}/>
  {!catalogMode&&!privateMode&&<ManualPortGroups form={form} setForm={setForm} disabled={disabled} w={w}/>}
 </section>;
}
