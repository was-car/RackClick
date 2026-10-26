import {prepareRackSvg,sendRackSvg,recoverRackSvg,downloadRackSvg,rackSvgAllowed} from './inventory-rack-svg.ts';
import {rackSvgWords} from './inventory-rack-svg-words.ts';
import {roomPath} from './inventory-model.ts';
const {useState,useEffect,useRef}=React;
export function InventoryRackSvgExport({api,session,project,lang,onRefresh,blocked=false,authorityLost=false}){
 const w=rackSvgWords[lang],actor=session.user.id,allowed=!authorityLost&&rackSvgAllowed(api,session,project.customerId);
 const [expanded,setExpanded]=useState(false),[rackId,setRackId]=useState(''),[face,setFace]=useState('front'),[language,setLanguage]=useState(lang);
 const [pending,setPending]=useState(null),[confirmed,setConfirmed]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null),[status,setStatus]=useState(null);
 const key=JSON.stringify([actor,api.actorId,project.customerId,rackId,face,language,allowed]),context=useRef({key,generation:0}),live=useRef(null),inFlight=useRef(null);
 if(context.current.key!==key)context.current={key,generation:context.current.generation+1};
 const generation=context.current.generation;live.current={key,generation,allowed,session};
 const current=()=>live.current?.key===key&&live.current?.generation===generation&&live.current?.allowed&&api.actorId===actor;
 useEffect(()=>{setPending(null);setConfirmed(null);setError(null);setStatus(null);setBusy(false);inFlight.current=null;return()=>{inFlight.current?.controller.abort();if(context.current.key===key)context.current={key,generation:context.current.generation+1}}},[key]);
 useEffect(()=>{if(!pending){setConfirmed(null);setStatus(null)}},[project.revision]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 const locked=busy||!!pending,validScope=project.racks.some(r=>r.id===rackId);
 async function run(mode){
  if(inFlight.current||!current()||blocked||!pending&&!validScope)return;
  let operation;try{operation=pending||prepareRackSvg(api,actor,project.customerId,project.revision,{rackId,face,language})}catch(e){setError(e);return}
  const job={controller:new AbortController()};inFlight.current=job;setPending(operation);setBusy(true);setError(null);setStatus(null);setConfirmed(null);
  try{const data=mode==='check'?await recoverRackSvg(api,operation,job.controller.signal):await sendRackSvg(api,operation,job.controller.signal);if(!current()||job.controller.signal.aborted||inFlight.current!==job)return;if(data){setConfirmed({...data,operation});setPending(null);setStatus('confirmed')}else setStatus('unknown')}
  catch(e){if(current()&&!job.controller.signal.aborted&&inFlight.current===job){setError(e);if(!e.uncertain&&mode!=='check'&&!pending)setPending(null)}}
  finally{if(inFlight.current===job){inFlight.current=null;if(current())setBusy(false)}}
 }
 async function download(){
  if(!confirmed||inFlight.current||!current()||blocked)return;
  const job={controller:new AbortController()};inFlight.current=job;setBusy(true);setError(null);
  try{const latest=await recoverRackSvg(api,confirmed.operation,job.controller.signal);if(!latest)throw {code:'response_invalid'};if(!current()||job.controller.signal.aborted||inFlight.current!==job)return;downloadRackSvg(latest,api,live.current.session,project.customerId);setStatus('started')}
  catch(e){if(current()&&!job.controller.signal.aborted&&inFlight.current===job){setError(e);setConfirmed(null);setStatus(null)}}finally{if(inFlight.current===job){inFlight.current=null;if(current())setBusy(false)}}
 }
 if(!allowed)return null;
 return <section className="ir-location" data-inventory-rack-svg style={{minWidth:0,maxWidth:'100%',overflowWrap:'anywhere'}}><button type="button" data-rack-svg-toggle disabled={locked} aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{w.title}</button>{expanded&&<div style={{minWidth:0}}>
 <p>{w.scope}</p><label style={{display:'block',minWidth:0}}>{w.rack}<select data-rack-svg-rack disabled={locked} value={rackId} onChange={e=>setRackId(e.target.value)} style={{width:'100%',minWidth:0,maxWidth:'100%'}}><option value="">{w.choose}</option>{project.racks.map(r=><option key={r.id} value={r.id}>{[roomPath(project,r.roomId).join(' / '),r.name,r.location].filter(Boolean).join(' / ')} · {r.id}</option>)}</select></label>
 <div className="rc-inline-buttons" style={{minWidth:0}}><label style={{minWidth:0,maxWidth:'100%'}}>{w.face}<select data-rack-svg-face disabled={locked} value={face} onChange={e=>setFace(e.target.value)} style={{maxWidth:'100%'}}>{['front','rear'].map(f=><option key={f} value={f}>{w[f]}</option>)}</select></label><label style={{minWidth:0,maxWidth:'100%'}}>{w.language}<select data-rack-svg-language disabled={locked} value={language} onChange={e=>setLanguage(e.target.value)} style={{maxWidth:'100%'}}><option value="en">English</option><option value="de">Deutsch</option><option value="es">Español</option></select></label></div>
 {!project.racks.length&&<p>{w.empty}</p>}<p>{w.revision}: {pending?.revision||confirmed?.result.revision||project.revision}</p>
 {!pending&&<button type="button" data-rack-svg-generate disabled={busy||blocked||!validScope} onClick={()=>run('send')}>{busy?w.generating:w.generate}</button>}
 {pending&&<><p role="status" data-rack-svg-pending>{w.pending}</p><p>{w.request}: <span data-rack-svg-request>{pending.requestId}</span></p><button type="button" data-rack-svg-check disabled={busy||blocked} onClick={()=>run('check')}>{w.check}</button><button type="button" data-rack-svg-retry disabled={busy||blocked} onClick={()=>run('send')}>{w.retry}</button></>}
 {confirmed&&<><p>{w.rows}: {confirmed.result.report.rowCount} · SHA256: {confirmed.result.report.sha256}</p><button type="button" data-rack-svg-download disabled={busy||blocked} onClick={download}>{w.download}</button></>}
 {status&&<p role="status" data-rack-svg-status={status}>{w[status]}</p>}{error&&<div role="alert" data-rack-svg-error><p>{error.status===412?w.stale:error.code==='report_too_large'?w.large:error.code==='report_text_invalid'?w.invalidXml:w.error}</p>{error.status===412&&!pending&&<button type="button" data-rack-svg-refresh disabled={busy||blocked} onClick={()=>onRefresh()}>{w.refresh}</button>}</div>}
 <small>{w.limits} {w.memory}</small></div>}</section>;
}
