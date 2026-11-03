import {ReportTechnicalDetails} from './ReportTechnicalDetails.jsx';
import {reportUiWords} from './report-ui-words.ts';
import {prepareRc9Excel,sendRc9Excel,recoverRc9Excel,downloadRc9Excel,rc9ExcelAllowed} from './inventory-rc9-excel-reports.ts';
import {rc9ExcelWords} from './inventory-rc9-excel-words.ts';
import {roomPath} from './inventory-model.ts';
const {useState,useEffect,useRef}=React;
export function InventoryRc9ExcelExport({api,session,project,lang,onRefresh,blocked=false,authorityLost=false,activeRackId=null}){
 const w=rc9ExcelWords[lang],actor=session.user.id,allowed=!authorityLost&&rc9ExcelAllowed(api,session,project.customerId);
 const [expanded,setExpanded]=useState(false),[rackId,setRackId]=useState(''),[pending,setPending]=useState(null),[confirmed,setConfirmed]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null),[status,setStatus]=useState(null);
 const key=JSON.stringify([actor,api.actorId,project.customerId,rackId,allowed]),context=useRef({key,generation:0}),live=useRef(null),inFlight=useRef(null);
 if(context.current.key!==key)context.current={key,generation:context.current.generation+1};
 const generation=context.current.generation;live.current={key,generation,allowed,blocked,session};
 const current=()=>context.current.key===key&&context.current.generation===generation&&live.current?.key===key&&live.current?.generation===generation&&live.current?.allowed&&api.actorId===actor;
 useEffect(()=>{setPending(null);setConfirmed(null);setError(null);setStatus(null);setBusy(false);inFlight.current=null;return()=>{inFlight.current?.controller.abort();if(context.current.key===key)context.current={key,generation:context.current.generation+1}}},[key]);
 useEffect(()=>{if(!pending){setConfirmed(null);setStatus(null)}},[project.revision]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 const locked=busy||!!pending,selectedRack=project.racks.find(r=>r.id===rackId),validScope=!!selectedRack;
 const rackText=r=>[roomPath(project,r.roomId).join(' / '),r.name,r.location].filter(Boolean).join(' / ')+' · '+r.id;
 const contextInitialized=useRef(false),contextRack=project.racks.find(r=>r.id===activeRackId),ui=reportUiWords[lang]||reportUiWords.en;
 function useOpenRack(){if(locked||!contextRack)return;setRackId(contextRack.id);}
 function togglePanel(){if(locked)return;if(!expanded&&!contextInitialized.current){contextInitialized.current=true;if(!rackId&&contextRack)useOpenRack()}setExpanded(value=>!value)}
 async function run(mode){
  if(inFlight.current||!current()||live.current.blocked||!pending&&!validScope)return;
  let operation;try{operation=pending||prepareRc9Excel(api,actor,project.customerId,project.revision,{rackId})}catch(e){setError(e);return}
  const job={controller:new AbortController()};inFlight.current=job;setPending(operation);setBusy(true);setError(null);setStatus(null);setConfirmed(null);
  try{const data=mode==='check'?await recoverRc9Excel(api,operation,job.controller.signal):await sendRc9Excel(api,operation,job.controller.signal);if(!current()||job.controller.signal.aborted||inFlight.current!==job)return;if(data){setConfirmed({...data,operation});setPending(null);setStatus('confirmed')}else setStatus('unknown')}
  catch(e){if(current()&&!job.controller.signal.aborted&&inFlight.current===job){setError(e);if(!e.uncertain&&mode!=='check'&&!pending)setPending(null)}}
  finally{if(inFlight.current===job){inFlight.current=null;if(current())setBusy(false)}}
 }
 async function download(){
  if(!confirmed||inFlight.current||!current()||live.current.blocked)return;
  const job={controller:new AbortController()};inFlight.current=job;setBusy(true);setError(null);
  try{const latest=await recoverRc9Excel(api,confirmed.operation,job.controller.signal);if(!latest)throw {code:'response_invalid'};if(!current()||live.current.blocked||job.controller.signal.aborted||inFlight.current!==job)return;downloadRc9Excel(latest,api,live.current.session,project.customerId,confirmed.operation);setStatus('started')}
  catch(e){if(current()&&!job.controller.signal.aborted&&inFlight.current===job){setError(e);setConfirmed(null);setStatus(null)}}finally{if(inFlight.current===job){inFlight.current=null;if(current())setBusy(false)}}
 }
 if(!allowed)return null;
 return <section className="ir-location" data-inventory-rc9-excel style={{minWidth:0,maxWidth:'100%',overflowWrap:'anywhere'}}><button type="button" data-rc9-excel-toggle disabled={locked} aria-expanded={expanded} onClick={togglePanel}>{w.title}</button>{expanded&&<div style={{minWidth:0}}>
 <p>{w.scope}</p><label style={{display:'block',minWidth:0}}>{w.rack}<select data-rc9-excel-rack disabled={locked} value={rackId} onChange={e=>setRackId(e.target.value)} style={{width:'100%',minWidth:0,maxWidth:'100%'}}><option value="">{w.choose}</option>{project.racks.map(r=><option key={r.id} value={r.id}>{rackText(r)}</option>)}</select></label>
 {contextRack&&rackId!==contextRack.id&&<button type="button" className="rc-report-context-use" data-use-open-rack="rc9-excel" disabled={locked} onClick={useOpenRack}>{ui.useRack}: {contextRack.name}</button>}
 {selectedRack&&<p data-rc9-excel-selected>{rackText(selectedRack)}</p>}
 {!project.racks.length&&<p>{w.empty}</p>}<p data-rc9-excel-format>{w.format}</p>
 {!pending&&<button type="button" data-rc9-excel-generate disabled={busy||blocked||!validScope} onClick={()=>run('send')}>{busy?w.generating:w.generate}</button>}
 {pending&&<><p role="status" data-rc9-excel-pending>{w.pending}</p><button type="button" data-rc9-excel-check disabled={busy||blocked} onClick={()=>run('check')}>{w.check}</button><button type="button" data-rc9-excel-retry disabled={busy||blocked} onClick={()=>run('send')}>{w.retry}</button></>}
 {confirmed&&<><p>{w.rows}: {confirmed.result.report.rowCount}</p><button type="button" data-rc9-excel-download disabled={busy||blocked} onClick={download}>{w.download}</button></>}
 {status&&<p role="status" aria-live="polite" data-rc9-excel-status={status}>{w[status]}</p>}{error&&<div role="alert" data-rc9-excel-error><p>{error.code==='report_mounting_unsupported'?reportUiWords[lang].mountingUnsupported:error.status===412?w.stale:error.status===401?w.expired:error.status===403?w.denied:error.code==='report_too_large'?w.large:['report_cell_invalid','report_source_invalid'].includes(error.code)?w.invalid:w.error}</p>{error.status===412&&!pending&&<button type="button" data-rc9-excel-refresh disabled={busy||blocked} onClick={()=>onRefresh()}>{w.refresh}</button>}</div>}
 <ReportTechnicalDetails kind="rc9-excel" lang={lang}><p>{w.revision}: {pending?.revision||confirmed?.result.revision||project.revision}</p>{pending&&<p>{w.request}: <span data-rc9-excel-request>{pending.requestId}</span></p>}{confirmed&&<p>SHA256: {confirmed.result.report.sha256}</p>}</ReportTechnicalDetails>
 <small>{w.limits} {w.memory}</small></div>}</section>;
}
