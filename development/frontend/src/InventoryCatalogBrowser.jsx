import {readInventoryCatalog,catalogMatches,filterCatalog} from './inventory-catalog.ts';
import {catalogWords} from './inventory-catalog-words.ts';
import {inventoryWords} from './inventory-words.ts';
import {inventoryError} from './OperationDialog.jsx';
import {InventoryCatalogFavorites,useCatalogFavorites} from './InventoryCatalogFavorites.jsx';
import {PT,irPortFace} from '../generated/rc9.jsx';
const {useState,useEffect}=React;
// Shared by catalogue consultation and equipment creation; the equipment draft remains with its owner.
export function InventoryCatalogBrowser({api,actorId,userName,project,lang,form,setForm,disabled,onRefresh,enabled=true}){
 const w=inventoryWords[lang],c=catalogWords[lang],[loading,setLoading]=useState(false),[error,setError]=useState(null),[retry,setRetry]=useState(0);
 const current=catalogMatches(form.catalogue,actorId,api,project,lang,form.catalogueActor),catalog=current?form.catalogue:null;
 const favorites=useCatalogFavorites({api,actorId,customerId:project.customerId,userName,lang});
 useEffect(()=>{if(!enabled||current)return;let active=true;const controller=new AbortController();setLoading(true);setError(null);
  readInventoryCatalog(api,project.customerId,project.revision,lang,actorId,controller.signal).then(data=>{if(active)setForm(previous=>({...previous,catalogue:data,catalogueActor:actorId}))}).catch(e=>{if(active&&!controller.signal.aborted)setError(e)}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false;controller.abort()};
 },[api,actorId,project.customerId,project.revision,lang,enabled,retry]);
 const selected=catalog?.presets.find(p=>p.key===form.catalogKey),favoriteKeys=favorites.data?.presetKeys||[];
 const filtered=catalog?filterCatalog(catalog,form.catalogCategory||'',form.catalogQuery||'').filter(p=>!form.catalogOnlyFavorites||favoriteKeys.includes(p.key)):[],outside=selected&&!filtered.some(p=>p.key===selected.key);
 const label=p=>(favoriteKeys.includes(p.key)?'★ ':'')+p.label;
 return <section data-catalog-browser style={{minWidth:0,maxWidth:'100%',overflowWrap:'anywhere'}}><p className="rc8-catalogue-note">{c.generic}</p>{loading&&<p role="status">{c.loading}</p>}{error&&<div role="alert" className="rc-error">{inventoryError(error,w)} {c.refresh}{error.status===412?<button type="button" disabled={disabled||loading||!onRefresh} data-catalog-refresh onClick={onRefresh}>{w.reload}</button>:<button type="button" disabled={disabled||loading} data-catalog-retry onClick={()=>setRetry(n=>n+1)}>{c.retry}</button>}</div>}
  <label>{c.category}<select name="catalogCategory" style={{width:'100%',maxWidth:'100%',minWidth:0}} disabled={disabled||!catalog} value={form.catalogCategory||''} onChange={e=>setForm({...form,catalogCategory:e.target.value})}><option value="">{c.all}</option>{catalog?.categories.map(category=><option key={category.key} value={category.key}>{category.label}</option>)}</select></label>
  <label>{c.search}<input name="catalogQuery" style={{maxWidth:'100%',minWidth:0}} disabled={disabled||!catalog} value={form.catalogQuery||''} onChange={e=>setForm({...form,catalogQuery:e.target.value})}/></label>
  <label>{c.choose}<select name="catalogKey" style={{width:'100%',maxWidth:'100%',minWidth:0}} required={enabled} disabled={disabled||!enabled} value={catalog?form.catalogKey:''} onChange={e=>setForm({...form,catalogKey:e.target.value})}><option value="">{c.choose}</option>{outside&&<option value={selected.key}>{label(selected)}</option>}{filtered.map(p=><option key={p.key} value={p.key}>{label(p)}</option>)}</select></label>{catalog&&!filtered.length&&<p role="status">{c.empty}</p>}{outside&&<p data-catalog-outside>{c.selected}</p>}
  <InventoryCatalogFavorites state={favorites} selected={selected} onlyFavorites={!!form.catalogOnlyFavorites} onOnlyFavorites={value=>setForm(previous=>({...previous,catalogOnlyFavorites:value}))} disabled={disabled||!enabled} lang={lang}/>
  {catalog&&<p data-catalog-scope>{c.scope}: {catalog.revision} · {catalog.catalogVersion} · <small>{catalog.catalogSha256}</small></p>}
  {selected&&<section data-catalog-preview={selected.key}><h3>{selected.icon} {selected.label}</h3><p>{c.reference}: {selected.sizeU} · {c.ports}: {selected.portGroups.reduce((n,g)=>n+g.ports.length,0)}</p>{selected.key==='ap'&&<p>{c.ap}</p>}<p>{c.defaults}</p><h4>{c.preview}</h4>{!selected.portGroups.length&&<p>{c.noPorts}</p>}{selected.portGroups.map(g=><details key={g.key} open data-catalog-group={g.key}><summary>{c.group} {g.sortOrder+1} · {PT[g.type]?.label||g.type} · {g.ports.length}</summary><div style={{overflowX:'auto',maxWidth:'100%'}}><table><thead><tr><th>#</th><th>{w.type}</th><th>{w.label}</th><th>{w.face}</th><th>{w.powerRole}</th><th>PoE</th></tr></thead><tbody>{g.ports.map(p=><tr key={p.gn} data-catalog-port={g.key+':'+p.gn}><td>{p.gn}</td><td>{PT[p.type]?.label||p.type}</td><td>{p.label||'—'}</td><td>{w[p.face]}{p.face==='auto'?' · '+w[irPortFace({preset:selected.label},{type:p.type})]:''}</td><td>{w[p.powerRole]}</td><td>{p.poe?'ON':'OFF'}</td></tr>)}</tbody></table></div></details>)}</section>}
 </section>;
}
