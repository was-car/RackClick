import {inventoryJsonExportAllowed,prepareInventoryJsonExport,sendInventoryJsonExport,recoverInventoryJsonExport,downloadInventoryJsonExport} from './inventory-json-export.ts';
import {inventoryJsonExportWords} from './inventory-json-export-words.ts';
const {useState,useRef,useEffect}=React;
export function InventoryJsonExport({api,session,project,lang,onRefresh,blocked=false,authorityLost=false}){
 const w=inventoryJsonExportWords[lang]||inventoryJsonExportWords.en,actor=session.user.id;
 const allowed=!authorityLost&&inventoryJsonExportAllowed(api,session,project.customerId),scope=JSON.stringify([actor,api.actorId,project.customerId,allowed]);
 const [expanded,setExpanded]=useState(false),[ack,setAck]=useState(false),[pending,setPending]=useState(null),[confirmed,setConfirmed]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null),[status,setStatus]=useState(null);
 const epoch=useRef(0),control=useRef(null),live=useRef(null);live.current={scope,allowed,session};
 useEffect(()=>{epoch.current++;control.current?.abort();setPending(null);setConfirmed(null);setAck(false);setError(null);setStatus(null);setBusy(false);return()=>{epoch.current++;control.current?.abort()}},[scope]);
 useEffect(()=>{if(!pending){setConfirmed(null);setStatus(null)}},[project.revision]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 async function run(mode){
  if(busy||!allowed||blocked||(!pending&&!ack))return;
  let operation;try{operation=pending||prepareInventoryJsonExport(api,actor,project.customerId,project.revision)}catch(e){setError(e);return;}
  const seq=++epoch.current,originalScope=scope,controller=new AbortController();control.current=controller;setPending(operation);setBusy(true);setError(null);setStatus(null);setConfirmed(null);
  try{const value=mode==='check'?await recoverInventoryJsonExport(api,operation,controller.signal):await sendInventoryJsonExport(api,operation,controller.signal);if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope||!live.current.allowed)return;if(value){setConfirmed({...value,operation});setPending(null);setStatus('confirmed')}else setStatus('unknown')}
  catch(e){if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope)return;setError(e);if(!e.uncertain&&mode!=='check'&&!pending)setPending(null)}
  finally{if(seq===epoch.current){setBusy(false);control.current=null}}
 }
 async function download(){
  if(!confirmed||!allowed||busy||blocked)return;
  const seq=++epoch.current,originalScope=scope,controller=new AbortController();control.current=controller;setBusy(true);setError(null);
  try{const value=await recoverInventoryJsonExport(api,confirmed.operation,controller.signal);if(!value)throw{code:'response_invalid'};if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope||!live.current.allowed)return;downloadInventoryJsonExport(value,api,live.current.session,project.customerId);setStatus('started')}
  catch(e){if(seq===epoch.current&&!controller.signal.aborted){setError(e);setConfirmed(null);setStatus(null)}}finally{if(seq===epoch.current){setBusy(false);control.current=null}}
 }
 if(!allowed)return null;
 const locked=busy||!!pending;
 return <section className="ir-location" data-inventory-json-export><button type="button" data-json-export-toggle disabled={locked} aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}>{w.title}</button>{expanded&&<div>
  <p>{w.scope}</p><p data-json-export-warning>{w.warning}</p><p className="rc-muted">{w.limits}</p>
  {!pending&&<label><input data-json-export-ack type="checkbox" checked={ack} disabled={busy||blocked} onChange={e=>setAck(e.target.checked)}/>{w.ack}</label>}
  {!pending&&<button type="button" data-json-export-generate disabled={busy||blocked||!ack} onClick={()=>run('send')}>{busy?w.working:w.generate}</button>}
  {pending&&<><p role="status" data-json-export-pending>{w.pending}</p><button type="button" data-json-export-check disabled={busy||blocked} onClick={()=>run('check')}>{w.check}</button><button type="button" data-json-export-retry disabled={busy||blocked} onClick={()=>run('send')}>{w.retry}</button></>}
  {confirmed&&<><p>{w.rows}: {confirmed.result.archive.rowCount}</p><button type="button" data-json-export-download disabled={busy||blocked} onClick={download}>{w.download}</button></>}
  {status&&<p role="status" data-json-export-status={status}>{w[status]}</p>}
  {error&&<div role="alert" data-json-export-error><p>{error.status===412?w.stale:error.code==='report_too_large'?w.large:w.error}</p>{error.status===412&&!pending&&<button type="button" disabled={busy||blocked} onClick={()=>onRefresh()}>{w.refresh}</button>}</div>}
  <details><summary>{w.details}</summary><p>{w.revision}: {pending?.revision||confirmed?.result.revision||project.revision}</p>{pending&&<p>{w.request}: <span data-json-export-request>{pending.requestId}</span></p>}{confirmed&&<p>SHA256: {confirmed.result.archive.sha256}</p>}</details>
 </div>}</section>;
}
