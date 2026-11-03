import { InventorySpreadsheetExport } from './InventorySpreadsheetExport.jsx';
import { InventoryReportExport } from './InventoryReportExport.jsx';
import { spreadsheetWords } from './inventory-spreadsheet-words.ts';
import { allows } from './api.ts';
import { loadInventoryRead,readKinds,readFamilies,readStatuses } from './inventory-read-views.ts';
import { inventoryReadWords } from './inventory-read-words.ts';
import { physicalConnectorLabel } from './connector-contract-l.mjs';
import {connectorDescriptorLabel} from './hardware-connector-classification.mjs';
const {useState,useEffect,useRef}=React;
export function InventoryReadViews({api,session,project,lang,onRefresh,onNavigate,blocked=false,authorityLost=false}){
 const w=inventoryReadWords[lang], [expanded,setExpanded]=useState(false),[view,setView]=useState('search'),[filters,setFilters]=useState({query:'',kind:'all',status:'all',family:'all',offset:0,limit:25}),[result,setResult]=useState(null),[failure,setFailure]=useState(null),[loading,setLoading]=useState(false),generation=useRef(0),[csvLocked,setCsvLocked]=useState(false),[spreadsheetLocked,setSpreadsheetLocked]=useState(false),[reportRack,setReportRack]=useState('');
 const reportLocked=csvLocked||spreadsheetLocked;
 const actor=session.user.id,authorized=!authorityLost&&allows(session,'inventory.read',project.customerId)&&api.actorId===actor;
 const token=JSON.stringify([actor,api.actorId,project.customerId,project.revision,filters,view,expanded,authorized]);
 const current=useRef(token);current.current=token;
 const appliedRevision=useRef(project.revision);
 useEffect(()=>{
  const seq=++generation.current,controller=new AbortController();setResult(null);setFailure(null);
  if(appliedRevision.current!==project.revision){appliedRevision.current=project.revision;if(filters.offset!==0){setFilters(f=>({...f,offset:0}));return ()=>controller.abort();}}
  if(!expanded||!authorized){setLoading(false);return ()=>controller.abort();}
  setLoading(true);
  loadInventoryRead(api,actor,project,view,filters,controller.signal).then(data=>{if(seq===generation.current&&current.current===token)setResult({token,data});}).catch(error=>{if(!controller.signal.aborted&&seq===generation.current&&current.current===token)setFailure({token,error});}).finally(()=>{if(seq===generation.current&&current.current===token)setLoading(false)});
  return ()=>{generation.current++;controller.abort();};
 },[token,api,project]);
 const data=result?.token===token?result.data:null,error=failure?.token===token?failure.error:null;
 function change(key,value){if(reportLocked)return;setResult(null);setFailure(null);setFilters(f=>({...f,[key]:value,offset:0}));}
 function choose(next){if(reportLocked)return;setResult(null);setFailure(null);setView(next);setFilters(f=>({...f,offset:0}));}
 function select(label,key,options){return <label>{label}<select disabled={reportLocked} style={{maxWidth:'100%'}} data-read-filter={key} value={filters[key]} onChange={e=>change(key,e.target.value)}>{options.map(v=><option key={v} value={v}>{w[v]||physicalConnectorLabel(v)}</option>)}</select></label>}
 function route(path){return <span>{path.map((p,i)=><React.Fragment key={p.kind+':'+p.id}>{i>0?' / ':''}{p.name} <small>({p.id})</small></React.Fragment>)}</span>}
 function port(p){return <div data-read-port={p.id}>{route(p.path)}<p>{p.deviceName} · {p.deviceKind} · {p.deviceId}<br/>{w.group}: {p.groupName} · {p.groupId} · {physicalConnectorLabel(p.type)} #{p.gn}{p.physicalConnector?' · '+connectorDescriptorLabel(p.type,p.physicalConnector):''}<br/>{w.status}: {w[p.status]||p.status} · {w.face}: {w[p.face]||p.face} · PoE: {p.poe?w.yes:w.no} · W: {p.watts??w.unknown}<br/>{w.label}: {p.label} · {w.color}: {p.color??w.unknown}<br/>{w.connected}: {p.connected?w.yes:w.no} · {p.connectionIds.join(', ')} · {p.peerPortIds.join(', ')}</p></div>}
 return <section className="ir-location" data-inventory-read style={{minWidth:0,maxWidth:'100%',overflowWrap:'anywhere'}}><button type="button" data-read-toggle disabled={reportLocked} aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{w.title}</button>{expanded&&authorized&&<div>
 <div role="tablist" aria-label={w.title} onKeyDown={e=>{const tabs=['search','ports','connections'],index=tabs.indexOf(view),next=e.key==='ArrowRight'?tabs[(index+1)%3]:e.key==='ArrowLeft'?tabs[(index+2)%3]:e.key==='Home'?tabs[0]:e.key==='End'?tabs[2]:null;if(next){e.preventDefault();choose(next);document.getElementById('read-tab-'+next)?.focus();}}}>{['search','ports','connections'].map(v=><button type="button" role="tab" tabIndex={view===v?0:-1} id={'read-tab-'+v} aria-controls="read-results" key={v} data-read-tab={v} disabled={reportLocked} aria-selected={view===v} onClick={()=>choose(v)}>{w[v]}</button>)}</div>
 <div className="rc-inline-buttons"><label>{w.query}<input style={{maxWidth:'100%'}} type="search" data-read-filter="query" disabled={reportLocked} value={filters.query} maxLength={200} onChange={e=>change('query',e.target.value)}/></label>{view==='search'&&select(w.kind,'kind',readKinds)}{view==='ports'&&<>{select(w.status,'status',readStatuses)}{select(w.family,'family',readFamilies)}</>}</div>
 {view!=='search'&&authorized&&allows(session,'reports.export',project.customerId)&&<div data-report-scope><label style={{display:'block',minWidth:0}}>{spreadsheetWords[lang].sharedRack}<select style={{maxWidth:'100%',width:'100%'}} data-report-rack disabled={reportLocked} value={reportRack} onChange={e=>setReportRack(e.target.value)}><option value="">{spreadsheetWords[lang].all}</option>{project.racks.map(r=><option key={r.id} value={r.id}>{r.name} · {r.id}</option>)}</select></label><p>{spreadsheetWords[lang].sharedScope}</p><InventoryReportExport key={'report:'+actor+':'+project.customerId} api={api} session={session} project={project} filter={{reportKind:view,query:filters.query,status:view==='ports'?filters.status:'all',family:view==='ports'?filters.family:'all',rackId:reportRack||null}} lang={lang} onRefresh={onRefresh} onLock={setCsvLocked} blocked={blocked||spreadsheetLocked} authorityLost={authorityLost}/><InventorySpreadsheetExport key={'spreadsheet:'+actor+':'+project.customerId} api={api} session={session} project={project} filter={{reportKind:view,query:filters.query,status:view==='ports'?filters.status:'all',family:view==='ports'?filters.family:'all',rackId:reportRack||null}} lang={lang} onRefresh={onRefresh} onLock={setSpreadsheetLocked} blocked={blocked||csvLocked} authorityLost={authorityLost}/></div>}
 <div id="read-results" role="tabpanel" aria-labelledby={'read-tab-'+view} aria-busy={loading}>
 {loading&&!data&&<p role="status">{w.loading}</p>}{error&&<div role="alert" data-read-error><p>{error.status===412?w.stale:w.error}</p><button type="button" data-read-refresh disabled={blocked} onClick={()=>onRefresh()}>{w.refresh}</button></div>}
 {data&&<><p role="status" data-read-summary>{w.revision}: {data.revision} · {w.total}: {data.total} · {data.offset+1>data.total?0:data.offset+1}–{data.offset+data.items.length}</p>{!data.items.length&&<p>{w.empty}</p>}
 <ul style={{paddingInlineStart:18}}>{data.items.map(item=><li key={item.id} data-read-row={item.id} style={{marginBottom:16}}>{view==='search'?<>{w[item.kind]}: {item.name} · {item.id}<div>{route(item.path)}</div><button type="button" data-read-navigate={item.id} disabled={blocked||!item.path.length} onClick={()=>onNavigate(item)}>{w.open}</button></>:view==='ports'?port(item):<><strong>{item.id}</strong>{port(item.from)}<span>↔</span>{port(item.to)}<p>{w.note}: {item.note} · {w.color}: {item.color??w.unknown} · {w.patch}: {item.patch} · {w.crossRack}: {item.crossRack===null?w.unknown:item.crossRack?w.yes:w.no}</p></>}</li>)}</ul>
 <div className="rc-inline-buttons"><button type="button" data-read-previous disabled={reportLocked||data.offset===0||loading} onClick={()=>setFilters(f=>({...f,offset:Math.max(0,f.offset-f.limit)}))}>{w.previous}</button><button type="button" data-read-next disabled={reportLocked||data.nextOffset===null||loading} onClick={()=>setFilters(f=>({...f,offset:data.nextOffset}))}>{w.next}</button></div></>}
 </div></div>}</section>;
}
