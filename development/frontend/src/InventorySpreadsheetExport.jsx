import {prepareReport,reportAllowed} from './inventory-reports.ts';
import {sendSpreadsheet,recoverSpreadsheet,downloadSpreadsheet} from './inventory-spreadsheet-reports.ts';
import {spreadsheetWords} from './inventory-spreadsheet-words.ts';
const {useState,useRef,useEffect}=React;
export function InventorySpreadsheetExport({api,session,project,filter,lang,onRefresh,onLock,blocked,authorityLost=false}){
 const w=spreadsheetWords[lang],actor=session.user.id,allowed=!authorityLost&&reportAllowed(api,session,project.customerId);
 const [pending,setPending]=useState(null),[confirmed,setConfirmed]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null),[status,setStatus]=useState(null);
 const control=useRef(null),epoch=useRef(0),live=useRef(null);
 const scope=JSON.stringify([actor,api.actorId,project.customerId,filter,allowed]);live.current={scope,allowed,session};
 useEffect(()=>{epoch.current++;control.current?.abort();setPending(null);setConfirmed(null);setError(null);setStatus(null);setBusy(false);onLock(false);return()=>{epoch.current++;control.current?.abort();onLock(false)}},[scope]);
 useEffect(()=>{if(!pending){setConfirmed(null);setStatus(null)}},[project.revision]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 async function run(mode){
  if(busy||!allowed||blocked)return;
  let operation;try{operation=pending||prepareReport(api,actor,project.customerId,project.revision,filter);}catch(e){setError(e);return;}
  const seq=++epoch.current,originalScope=scope,controller=new AbortController();control.current=controller;
  setPending(operation);onLock(true);setBusy(true);setError(null);setStatus(null);setConfirmed(null);
  try{
   const data=mode==='check'?await recoverSpreadsheet(api,operation,controller.signal):await sendSpreadsheet(api,operation,controller.signal);
   if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope||!live.current.allowed)return;
   if(data){setConfirmed({...data,operation});setPending(null);onLock(false);setStatus('confirmed');}else setStatus('unknown');
  }catch(e){if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope)return;setError(e);if(!e.uncertain&&mode!=='check'&&!pending){setPending(null);onLock(false);}}
  finally{if(seq===epoch.current){setBusy(false);control.current=null;}}
 }
 async function download(){
  if(!confirmed||!allowed||busy||blocked)return;
  const seq=++epoch.current,originalScope=scope,controller=new AbortController();control.current=controller;setBusy(true);setError(null);
  try{const latest=await recoverSpreadsheet(api,confirmed.operation,controller.signal);if(!latest)throw {code:'response_invalid'};if(seq!==epoch.current||controller.signal.aborted||live.current.scope!==originalScope||!live.current.allowed)return;downloadSpreadsheet(latest,api,live.current.session,project.customerId);setStatus('started');}catch(e){if(seq===epoch.current&&!controller.signal.aborted){setError(e);setConfirmed(null);setStatus(null);}}finally{if(seq===epoch.current){setBusy(false);control.current=null;}}
 }

 if(!allowed)return null;
 return <section data-inventory-spreadsheet style={{minWidth:0,overflowWrap:'anywhere'}}><h3>{w.title}</h3><p>{w.filter}: {w[filter.reportKind]} · {filter.query||'—'} · {filter.status} · {filter.family} · {filter.rackId||w.all} · {w.revision}: {pending?.revision||confirmed?.result.revision||project.revision}</p>
 {!pending&&<button type="button" data-spreadsheet-generate disabled={busy||blocked} onClick={()=>run('send')}>{busy?w.generating:w.generate}</button>}
 {pending&&<><p role="status" data-spreadsheet-pending>{w.pending}</p><p>{w.request}: <span data-spreadsheet-request>{pending.requestId}</span></p><button type="button" data-spreadsheet-check disabled={busy||blocked} onClick={()=>run('check')}>{w.check}</button><button type="button" data-spreadsheet-retry disabled={busy||blocked} onClick={()=>run('send')}>{w.retry}</button></>}
 {confirmed&&<><p>{w.rows}: {confirmed.result.report.rowCount} · SHA256: {confirmed.result.report.sha256}</p><button type="button" data-spreadsheet-download disabled={busy||blocked} onClick={download}>{w.download}</button></>}
 {status&&<p role="status" data-spreadsheet-status={status}>{w[status]}</p>}{error&&<div role="alert" data-spreadsheet-error><p>{error.status===412?w.stale:error.code==='report_too_large'?w.large:error.code==='report_cell_invalid'?w.cellInvalid:w.error}</p>{error.status===412&&!pending&&<button type="button" data-spreadsheet-refresh disabled={busy||blocked} onClick={()=>onRefresh()}>{w.refresh}</button>}</div>}<small>{w.memory} {w.scope}</small></section>;
}
