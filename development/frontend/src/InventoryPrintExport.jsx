import {preparePrintable,sendPrintable,recoverPrintable,downloadPrintable,printableAllowed} from './inventory-print-reports.ts';
import {printWords} from './inventory-print-words.ts';
import {roomPath} from './inventory-model.ts';
const {useState,useRef,useEffect}=React;
export function InventoryPrintExport({api,session,project,lang,onRefresh,blocked=false,authorityLost=false}){
 const w=printWords[lang],actor=session.user.id,allowed=!authorityLost&&printableAllowed(api,session,project.customerId);
 const [expanded,setExpanded]=useState(false),[kind,setKind]=useState('rack'),[language,setLanguage]=useState(lang),[rackId,setRackId]=useState(''),[labelIds,setLabelIds]=useState([]);
 const [pending,setPending]=useState(null),[confirmed,setConfirmed]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null),[status,setStatus]=useState(null);
 const control=useRef(null),epoch=useRef(0),live=useRef(null),rackIds=kind==='client'?[]:kind==='rack'?(rackId?[rackId]:[]):[...labelIds].sort();
 const filter={reportKind:kind,language,rackIds},scope=JSON.stringify([actor,api.actorId,project.customerId,filter,allowed]);live.current={scope,allowed,session};
 useEffect(()=>{epoch.current++;control.current?.abort();setPending(null);setConfirmed(null);setError(null);setStatus(null);setBusy(false);return()=>{epoch.current++;control.current?.abort()}},[scope]);
 useEffect(()=>{if(!pending){setConfirmed(null);setStatus(null)}},[project.revision]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 const locked=busy||!!pending,validScope=kind==='client'?project.racks.length<=20:kind==='rack'?rackIds.length===1&&project.racks.some(r=>r.id===rackId):rackIds.length>0&&rackIds.length<=64&&rackIds.every(id=>project.racks.some(r=>r.id===id));
 function rackText(r){return [roomPath(project,r.roomId).join(' / '),r.name,r.location].filter(Boolean).join(' / ')+' · '+r.id;}
 async function run(mode){
  if(busy||!allowed||blocked||!pending&&!validScope)return;
  let operation;try{operation=pending||preparePrintable(api,actor,project.customerId,project.revision,filter)}catch(e){setError(e);return;}
  const seq=++epoch.current,originalScope=scope,controller=new AbortController();control.current=controller;setPending(operation);setBusy(true);setError(null);setStatus(null);setConfirmed(null);
  try{const data=mode==='check'?await recoverPrintable(api,operation,controller.signal):await sendPrintable(api,operation,controller.signal);if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope||!live.current.allowed)return;if(data){setConfirmed({...data,operation});setPending(null);setStatus('confirmed')}else setStatus('unknown')}
  catch(e){if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope)return;setError(e);if(!e.uncertain&&mode!=='check'&&!pending)setPending(null)}
  finally{if(seq===epoch.current){setBusy(false);control.current=null}}
 }
 async function download(){
  if(!confirmed||!allowed||busy||blocked)return;
  const seq=++epoch.current,originalScope=scope,controller=new AbortController();control.current=controller;setBusy(true);setError(null);
  try{const latest=await recoverPrintable(api,confirmed.operation,controller.signal);if(!latest)throw {code:'response_invalid'};if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope||!live.current.allowed)return;downloadPrintable(latest,api,live.current.session,project.customerId);setStatus('started')}
  catch(e){if(seq===epoch.current&&!controller.signal.aborted){setError(e);setConfirmed(null);setStatus(null)}}finally{if(seq===epoch.current){setBusy(false);control.current=null}}
 }
 if(!allowed)return null;
 return <section className="ir-location" data-inventory-print style={{minWidth:0,maxWidth:'100%',overflowWrap:'anywhere'}}><button type="button" data-print-toggle disabled={locked} aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{w.title}</button>{expanded&&<div>
 <p>{w.scope}</p><div className="rc-inline-buttons"><label>{w.kind}<select data-print-kind disabled={locked} value={kind} onChange={e=>setKind(e.target.value)} style={{maxWidth:'100%'}}>{['rack','client','rackLabels'].map(k=><option key={k} value={k}>{w[k]}</option>)}</select></label><label>{w.language}<select data-print-language disabled={locked} value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">English</option><option value="de">Deutsch</option><option value="es">Español</option></select></label></div>
 {kind==='rack'&&<label style={{display:'block',minWidth:0}}>{w.rack}<select data-print-rack disabled={locked} value={rackId} onChange={e=>setRackId(e.target.value)} style={{maxWidth:'100%',width:'100%'}}><option value="">{w.choose}</option>{project.racks.map(r=><option key={r.id} value={r.id}>{rackText(r)}</option>)}</select></label>}
 {kind==='client'&&<><p data-print-client-scope>{w.clientScope}</p>{project.racks.length>20&&<p role="alert" data-print-client-limit>{w.clientLimit}</p>}</>}
 {kind==='rackLabels'&&<><p>{w.labelScope}</p><p data-print-selection>{w.selected}: {labelIds.length}/64</p><div style={{maxHeight:280,overflowY:'auto'}}>{project.racks.map(r=><label key={r.id} style={{display:'flex',gap:8,alignItems:'start',marginBottom:8}}><input type="checkbox" data-print-label-rack={r.id} disabled={locked||labelIds.length>=64&&!labelIds.includes(r.id)} checked={labelIds.includes(r.id)} onChange={e=>setLabelIds(previous=>e.target.checked?[...previous,r.id]:previous.filter(id=>id!==r.id))}/><span>{rackText(r)}</span></label>)}</div></>}
 {kind!=='client'&&!project.racks.length&&<p>{w.empty}</p>}<p>{w.revision}: {pending?.revision||confirmed?.result.revision||project.revision}</p>
 {!pending&&<button type="button" data-print-generate disabled={busy||blocked||!validScope} onClick={()=>run('send')}>{busy?w.generating:w.generate}</button>}
 {pending&&<><p role="status" data-print-pending>{w.pending}</p><p>{w.request}: <span data-print-request>{pending.requestId}</span></p><button type="button" data-print-check disabled={busy||blocked} onClick={()=>run('check')}>{w.check}</button><button type="button" data-print-retry disabled={busy||blocked} onClick={()=>run('send')}>{w.retry}</button></>}
 {confirmed&&<><p>{w.rows}: {confirmed.result.report.rowCount} · SHA256: {confirmed.result.report.sha256}</p><button type="button" data-print-download disabled={busy||blocked} onClick={download}>{w.download}</button></>}
 {status&&<p role="status" data-print-status={status}>{w[status]}</p>}{error&&<div role="alert" data-print-error><p>{error.status===412?w.stale:error.code==='report_too_large'?w.large:w.error}</p>{error.status===412&&!pending&&<button type="button" data-print-refresh disabled={busy||blocked} onClick={()=>onRefresh()}>{w.refresh}</button>}</div>}
 <p>{w.printHelp}</p><small>{w.limits} {w.memory}</small></div>}</section>;
}
