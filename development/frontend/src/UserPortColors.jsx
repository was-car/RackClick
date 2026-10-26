import {ApiError} from './api.ts';
import {readUserPortColors,preparePortColors,mutatePortColors,portColorsStatus,cancelPortColors,defaultPortColors,validPortColors,samePortColors} from './user-port-colors.ts';
import {portColorsJournal} from './user-port-colors-journal.ts';
import {userPortColorsWords} from './user-port-colors-words.ts';
import {PT,IRPortShape} from '../generated/rc9.jsx';
const {useState,useRef,useEffect}=React;
export function useUserPortColors({api,actorId,userName,generation=0,suspended=false,onAuthenticationInvalidated}){
 const [data,setData]=useState(null),[pending,setPending]=useState(null),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(null),[notice,setNotice]=useState(''),[view,setView]=useState(-1);
 const context=(actorId||'anonymous')+':'+generation+':'+suspended,scope=useRef({context,token:0}),mounted=useRef(false),inFlight=useRef(null);
 if(scope.current.context!==context)scope.current={context,token:scope.current.token+1};const token=scope.current.token;
 const sameScope=()=>mounted.current&&scope.current.context===context&&scope.current.token===token,current=()=>sameScope()&&!suspended&&api.actorId===actorId;
 const ensure=()=>{if(!current())throw new ApiError(409,'actor_changed')};
 async function read(signal){ensure();const value=await readUserPortColors(api,actorId,signal);ensure();setData(value);return value}
 async function load(signal){ensure();const d=await portColorsJournal('read',actorId);ensure();setPending(d);await read(signal);ensure();setReady(true)}
 useEffect(()=>{mounted.current=true;inFlight.current=null;setData(null);setPending(null);setReady(false);setBusy(false);setError(null);setNotice('');setView(token);const c=new AbortController();if(actorId&&!suspended)load(c.signal).catch(e=>{if(current()&&!c.signal.aborted)setError(e)});return()=>{mounted.current=false;c.abort()}},[api,context]);
 async function task(action,reauth=false){
  if(inFlight.current||!sameScope()||suspended||!actorId||(!reauth&&api.actorId!==actorId))return;
  const job={context,token};inFlight.current=job;setBusy(true);setError(null);setNotice('');
  try{return await action()}catch(e){if(sameScope()&&(api.actorId===actorId||(reauth&&!api.actorId)))setError(e)}finally{if(inFlight.current===job){inFlight.current=null;if(sameScope())setBusy(false)}}
 }
 async function finish(d,committed){
  ensure();try{await read()}catch(e){if(e.code==='actor_changed'||e.status===401)throw e;throw new ApiError(0,'port_colors_refresh_failed')}
  ensure();await portColorsJournal('remove',actorId,d);ensure();setPending(null);setNotice(committed?'saved':'cancelled');setReady(true);
 }
 async function save(colors){
  if(suspended||!actorId||!validPortColors(colors))return;
  return task(async()=>{ensure();if(view!==token||!ready||pending||!data)throw new ApiError(409,'port_colors_not_ready');const d=preparePortColors(actorId,data,colors);await portColorsJournal('write',actorId,d);ensure();setPending(d);await mutatePortColors(api,d);ensure();await finish(d,true)});
 }
 async function recover(action){return task(async()=>{ensure();if(view!==token||!pending)return;const d=pending;if(action==='retry'){await mutatePortColors(api,d);ensure();await finish(d,true);return}if(!['query','cancel'].includes(action))throw new ApiError(422,'port_colors_invalid');const result=action==='cancel'?await cancelPortColors(api,d):await portColorsStatus(api,d);ensure();if(result.state==='notRecorded'){setNotice('notRecorded');return}await finish(d,result.state==='committed')})}
 async function authenticate(password){return task(async()=>{
  const identity=await api.login(userName,password);
  // Cookie and the shared API cache already changed when login resolves.
  if(!sameScope()||identity.user.id!==actorId){api.csrf='';api.actorId='';onAuthenticationInvalidated?.();if(sameScope())throw new ApiError(409,'actor_changed');return}
  ensure();await load();
 },true)}
 const visible=view===token&&api.actorId===actorId&&!suspended,confirmed=visible&&data?.ownerId===actorId?data:null;
 return{actorId,data:confirmed,colors:confirmed?.colors||{},pending:visible?pending:null,ready:visible&&ready,busy:visible&&busy,error:view===token?error:null,notice:visible?notice:'',disabled:suspended||!actorId||!visible||!ready||busy||!!pending,save,recover,authenticate,reload:()=>task(()=>load())};
}
export function UserPortColors({state,lang,onClose,active=true,paletteNavigation}){
 const t=userPortColorsWords[lang],dialog=useRef(null),[draft,setDraft]=useState(()=>({...((state.pending?.colors)||state.data?.colors||{})})),[password,setPassword]=useState('');
 useEffect(()=>{if(active)dialog.current.showModal();else dialog.current.close();return()=>dialog.current?.close()},[active]);
 useEffect(()=>{if(state.data&&!state.pending)setDraft({...state.data.colors})},[state.data,state.pending]);
 const error=state.error,message=!error?'':error.status===412?t.conflict:error.status===401?t.expired:error.code==='actor_changed'?t.actor:error.code==='port_colors_storage_unavailable'?t.storage:error.code==='port_colors_refresh_failed'?t.refresh:error.code==='port_colors_revision_exhausted'?t.exhausted:error.code==='response_invalid'?t.invalid:t.unavailable;
 const colors=state.pending?.colors||draft,reset=key=>setDraft(old=>{const next={...old};delete next[key];return next});
 const editing=!state.pending&&state.data&&!samePortColors(draft,state.data.colors),status=state.busy?'saving':state.notice==='saved'&&editing?'ready':state.notice||(!state.ready?'loading':'ready');
 return <dialog ref={dialog} className="ir-dialog" data-port-colors-panel aria-labelledby="port-colors-title" style={{width:'min(620px, calc(100vw - 24px))',maxWidth:'calc(100vw - 24px)',boxSizing:'border-box',maxHeight:'calc(100dvh - 24px)',overflowY:'auto',overflowWrap:'anywhere'}} onCancel={e=>{e.preventDefault();onClose()}}><form className="rc-form" onSubmit={e=>{e.preventDefault();state.save(draft)}}><div className="rc-dialog-title"><h2 id="port-colors-title">{t.scope}</h2></div>{paletteNavigation}<p>{t.help}</p><span data-port-colors-revision hidden>{state.data?.revision??'—'}</span><p role="status" aria-live="polite" data-port-colors-status={status}>{state.busy?t.saving:editing?t.preview:state.notice?t[state.notice]:!state.ready?t.loading:''}</p>{message&&<p role="alert" className="rc-error" data-port-colors-error>{message}</p>}<section aria-label={t.preview} style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,220px),1fr))',gap:6}}>{Object.entries(PT).map(([key,pt])=><div key={key} style={{display:'flex',alignItems:'center',gap:6,padding:'4px 8px',background:'var(--ir-raised)',border:'1px solid var(--ir-border)',borderRadius:4,minWidth:0}}><label style={{display:'flex',alignItems:'center',gap:6,flex:1,minWidth:0}}><input type="color" data-port-colors-input={key} aria-label={pt.label} disabled={state.disabled} value={colors[key]||defaultPortColors[key]} onChange={e=>{const value=e.target.value.toLowerCase();setDraft(old=>({...old,[key]:value}))}} style={{width:24,height:24,minWidth:24,padding:0,border:0,background:'none',cursor:'pointer'}}/><span>{pt.label}</span></label><svg aria-hidden="true" data-port-colors-preview={key} viewBox="0 0 40 40" style={{width:24,height:24,fill:'none',stroke:colors[key]||defaultPortColors[key],strokeWidth:2,flexShrink:0}}><IRPortShape type={key}/></svg><button type="button" data-port-colors-reset={key} aria-label={t.reset+' '+pt.label} title={t.reset+' '+pt.label} disabled={state.disabled||!Object.hasOwn(colors,key)} onClick={()=>reset(key)} style={{padding:'4px 7px'}}>↺</button></div>)}</section><button type="button" data-port-colors-reset-all disabled={state.disabled} onClick={()=>setDraft({})}>{t.resetAll}</button>{state.pending&&<div className="ir-warning" data-port-colors-pending><p>{t.pending}</p><div className="rc-inline-buttons"><button type="button" data-port-colors-query disabled={state.busy} onClick={()=>state.recover('query')}>{t.query}</button><button type="button" data-port-colors-retry disabled={state.busy} onClick={()=>state.recover('retry')}>{t.retry}</button><button type="button" data-port-colors-cancel disabled={state.busy} onClick={()=>{if(window.confirm(t.cancelConfirm))state.recover('cancel')}}>{t.cancel}</button></div></div>}{error?.status===401&&<div className="rc-form"><label>{t.password}<input type="password" data-port-colors-password autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button type="button" data-port-colors-authenticate disabled={state.busy||!password} onClick={()=>{const secret=password;setPassword('');state.authenticate(secret)}}>{t.signIn}</button></div>}{(message||!state.ready)&&<button type="button" data-port-colors-reload disabled={state.busy} onClick={state.reload}>{t.reload}</button>}<footer className="rc-inline-buttons"><button type="button" data-port-colors-close onClick={onClose}>{t.close}</button><button type="submit" data-port-colors-save disabled={state.disabled}>{t.save}</button></footer></form></dialog>;
}
