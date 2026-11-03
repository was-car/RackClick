import { readRecoveryStatus, generateRecoveryCodes, recoveryCodesReceipt, recoveryCodesJournal } from './mfa-recovery.ts';
import { mfaRecoveryWords } from './mfa-recovery-words.ts';
const {useState,useEffect,useRef}=React;

export function MfaRecoveryCodesPanel({api,session,lang='en',onDirtyChange,onReauthenticate}) {
 const w=mfaRecoveryWords[lang]||mfaRecoveryWords.en,id=session.user.id;
 const scopeRef=useRef(null);if(!scopeRef.current||scopeRef.current.id!==id||scopeRef.current.api!==api)scopeRef.current={id,api,live:false};
 const scope=scopeRef.current,flight=useRef(false),serial=useRef(0);
 const [view,setView]=useState({scope:null,status:null,pending:null,codes:null,ready:false,busy:true,error:null,notice:null});
 const [form,setForm]=useState({scope:null,password:'',ack:false});
 const v=view.scope===scope?view:{status:null,pending:null,codes:null,ready:false,busy:true,error:null,notice:null};
 const f=form.scope===scope?form:{password:'',ack:false};
 const current=()=>scopeRef.current===scope&&scope.live&&api.actorId===id;
 const patch=values=>{if(current())setView(old=>({...old,...values,scope}));};
 const fields=values=>setForm(old=>({...old,...values,scope}));
 const dirty=!!(v.pending||v.codes||f.password||f.ack||v.busy);
 useEffect(()=>{onDirtyChange?.(dirty);return()=>onDirtyChange?.(false);},[dirty,onDirtyChange]);
 function errorCode(error){return error?.code==='journal_unavailable'?'journal':error?.status===401?'expired':error?.status===429?'limited':'error';}
 async function load(){const mark=++serial.current;const status=await readRecoveryStatus(api);if(current()&&mark===serial.current)patch({status});}
 useEffect(()=>{
  scope.live=true;flight.current=false;setView({scope,status:null,pending:null,codes:null,ready:false,busy:true,error:null,notice:null});setForm({scope,password:'',ack:false});
  (async()=>{try{const pending=recoveryCodesJournal('read',id);patch({pending});await load();patch({ready:true,busy:false});}catch(e){patch({error:errorCode(e),busy:false});}})();
  return()=>{scope.live=false;serial.current++;};
 },[scope]);
 async function perform(check=false){
  if(!current()||flight.current||!v.ready||(!check&&(!f.password||!f.ack||!v.status?.canGenerate)))return;
  const draft=v.pending||Object.freeze({actorId:id,requestId:crypto.randomUUID(),revision:v.status.revision});
  if(check&&!v.pending)return;
  flight.current=true;const password=f.password;fields({password:''});patch({busy:true,error:null,notice:null});
  try{
   if(!v.pending)recoveryCodesJournal('write',id,draft);
   patch({pending:draft});
   const result=check?await recoveryCodesReceipt(api,draft):await generateRecoveryCodes(api,draft,password);
   if(!current())return;
   if(!result){patch({notice:'notRecorded'});return;}
   // A committed secret response remains displayable even if local journal cleanup fails.
   patch({codes:result.codesAvailable?result.codes:null,pending:null,notice:result.codesAvailable?'saved':'recorded'});fields({ack:false});
   try{recoveryCodesJournal('remove',id,draft);}catch{patch({error:'journal'});}
   await load();
  }catch(e){patch({error:errorCode(e),pending:draft});}
  finally{if(current()){flight.current=false;patch({busy:false});}}
 }
 function hide(){if(v.busy)return;patch({codes:null});fields({password:'',ack:false});}
 function download(){
  if(!current()||!v.codes)return;
  const blob=new Blob(['RackClick\n'+w.help+'\n\n'+v.codes.join('\n')+'\n'],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='RackClick-MFA-recovery-codes.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <details data-mfa-recovery-panel><summary>{w.title}</summary><p>{w.help}</p>
  {v.status&&<p data-mfa-recovery-remaining>{w.remaining.replace('{count}',String(v.status.remaining))}</p>}
  {v.error&&<p role="alert" className="rc-error" data-mfa-recovery-error>{w[v.error]||w.error}</p>}
  {v.notice&&<p role="status" data-mfa-recovery-outcome={v.notice}>{w[v.notice]}</p>}
  {v.busy&&<p role="status">{w.working}</p>}
  {v.codes?<div data-mfa-recovery-values><p>{w.once}</p><ol>{v.codes.map(code=><li key={code}><code>{code}</code></li>)}</ol><div className="rc-inline-buttons"><button type="button" data-mfa-recovery-download onClick={download}>{w.download}</button><button type="button" data-mfa-recovery-hide onClick={hide}>{w.hide}</button></div></div>:<>
   {v.pending&&<div className="ir-warning" data-mfa-recovery-pending><p>{w.pending}</p><code>{v.pending.requestId}</code><button type="button" disabled={v.busy} data-mfa-recovery-check onClick={()=>perform(true)}>{w.check}</button></div>}
   {v.status?.canGenerate?<form className="rc-form" onSubmit={e=>{e.preventDefault();perform(false);}}>
    <label>{w.password}<input data-mfa-recovery-password type="password" autoComplete="current-password" maxLength={1024} value={f.password} disabled={v.busy} required onChange={e=>fields({password:e.target.value})}/></label>
    <label><input data-mfa-recovery-ack type="checkbox" checked={f.ack} disabled={v.busy} onChange={e=>fields({ack:e.target.checked})}/>{w.ack}</label>
    <button data-mfa-recovery-generate type="submit" disabled={!v.ready||v.busy||!f.password||!f.ack}>{v.pending?w.retry:w.generate}</button>
   </form>:!v.busy&&<p>{w.required}</p>}
  </>}
  {v.error==='expired'&&<button type="button" disabled={v.busy} onClick={()=>onReauthenticate?.({reason:'mfa_recovery_codes',userId:id})}>{w.reauth}</button>}
 </details>;
}
