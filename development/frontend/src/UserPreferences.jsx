import {ApiError} from './api.ts';
import {readUserPreferences,preparePreference,mutatePreference,preferenceStatus,cancelPreference,validPreferenceValue} from './user-preferences.ts';
import {preferenceJournal} from './user-preferences-journal.ts';
import {userPreferenceWords} from './user-preferences-words.ts';
const {useState,useRef,useEffect}=React;
const anonymousPreference=(key,fallback,kind)=>{try{const v=localStorage.getItem(key);return validPreferenceValue(kind,v)?v:fallback}catch{return fallback}};
export function useUserPreferences({api,actorId,userName,generation=0,suspended=false,onAuthenticationInvalidated}){
 const [anonymous,setAnonymous]=useState(()=>({language:anonymousPreference('rackclick_server_language','en','language'),theme:anonymousPreference('rackclick_server_theme','dark','theme')}));
 const [data,setData]=useState(null),[pending,setPending]=useState(null),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(null),[notice,setNotice]=useState(''),[view,setView]=useState(-1);
 const context=(actorId||'anonymous')+':'+generation+':'+suspended,scope=useRef({context,token:0}),mounted=useRef(false),inFlight=useRef(null);
 if(scope.current.context!==context)scope.current={context,token:scope.current.token+1};const token=scope.current.token;
 const sameScope=()=>mounted.current&&scope.current.context===context&&scope.current.token===token,current=()=>sameScope()&&!suspended&&api.actorId===actorId;
 const ensure=()=>{if(!current())throw new ApiError(409,'actor_changed')};
 useEffect(()=>{if(!actorId){try{localStorage.setItem('rackclick_server_language',anonymous.language);localStorage.setItem('rackclick_server_theme',anonymous.theme)}catch{}}},[actorId,anonymous]);
 async function read(signal){ensure();const value=await readUserPreferences(api,actorId,signal);ensure();setData(value);return value}
 async function load(signal){ensure();const d=await preferenceJournal('read',actorId);ensure();setPending(d);await read(signal);ensure();setReady(true)}
 useEffect(()=>{mounted.current=true;inFlight.current=null;setData(null);setPending(null);setReady(false);setBusy(false);setError(null);setNotice('');setView(token);const c=new AbortController();if(actorId&&!suspended)load(c.signal).catch(e=>{if(current()&&!c.signal.aborted)setError(e)});return()=>{mounted.current=false;c.abort()}},[api,context]);
 async function task(action,reauth=false){
  if(inFlight.current||!sameScope()||suspended||!actorId||(!reauth&&api.actorId!==actorId))return;
  const job={context,token};inFlight.current=job;setBusy(true);setError(null);setNotice('');
  try{return await action()}catch(e){if(sameScope()&&(api.actorId===actorId||(reauth&&!api.actorId)))setError(e)}finally{if(inFlight.current===job){inFlight.current=null;if(sameScope())setBusy(false)}}
 }
 async function finish(d,committed){
  ensure();try{await read()}catch(e){if(e.code==='actor_changed'||e.status===401)throw e;throw new ApiError(0,'preferences_refresh_failed')}
  ensure();await preferenceJournal('remove',actorId,d);ensure();setPending(null);setNotice(committed?'saved':'cancelled');setReady(true);
 }
 async function choose(key,value){
  if(suspended||!validPreferenceValue(key,value))return;
  if(!actorId){setAnonymous(old=>({...old,[key]:value}));return}
  return task(async()=>{ensure();if(view!==token||!ready||pending||!data)throw new ApiError(409,'preferences_not_ready');const d=preparePreference(actorId,data,key,value);await preferenceJournal('write',actorId,d);ensure();setPending(d);await mutatePreference(api,d);ensure();await finish(d,true)});
 }
 async function recover(action){return task(async()=>{ensure();if(view!==token||!pending)return;const d=pending;if(action==='retry'){await mutatePreference(api,d);ensure();await finish(d,true);return}if(!['query','cancel'].includes(action))throw new ApiError(422,'preferences_invalid');const result=action==='cancel'?await cancelPreference(api,d):await preferenceStatus(api,d);ensure();if(result.state==='notRecorded'){setNotice('notRecorded');return}await finish(d,result.state==='committed')})}
 async function authenticate(password){return task(async()=>{
  const identity=await api.login(userName,password);
  // Login changes the cookie and shared API cache before it resolves. A late login must
  // therefore close the visible authenticated session, even when its intention is ignored.
  if(!sameScope()||identity.user.id!==actorId){api.csrf='';api.actorId='';onAuthenticationInvalidated?.();if(sameScope())throw new ApiError(409,'actor_changed');return}
  ensure();await load();
 },true)}
 const visible=view===token&&api.actorId===actorId&&!suspended,confirmed=visible&&data?.ownerId===actorId?data:null;
 return{lang:confirmed?.language??anonymous.language,theme:confirmed?.theme??anonymous.theme,anonymous,actorId,data:confirmed,pending:visible?pending:null,ready:visible&&ready,busy:visible&&busy,error:view===token?error:null,notice:visible?notice:'',disabled:suspended||!!actorId&&(!visible||!ready||busy||!!pending),chooseLanguage:value=>choose('language',value),chooseTheme:value=>choose('theme',value),recover,authenticate,reload:()=>task(()=>load())};
}
export function UserPreferenceStatus({state,lang}){
 const t=userPreferenceWords[lang],[password,setPassword]=useState('');if(!state.actorId)return null;
 const error=state.error,message=!error?'':error.status===412?t.conflict:error.status===401?t.expired:error.code==='actor_changed'?t.actor:error.code==='preferences_storage_unavailable'?t.storage:error.code==='preferences_refresh_failed'?t.refresh:error.code==='preferences_revision_exhausted'?t.exhausted:error.code==='response_invalid'?t.invalid:t.unavailable;
 return <section data-user-preferences aria-label={t.scope} className="rc-form"><span data-preferences-revision hidden>{state.data?.revision??'—'}</span><p role="status" aria-live="polite" data-preferences-status={state.busy?'saving':state.notice||(!state.ready?'loading':'ready')}>{state.busy?t.saving:state.notice?t[state.notice]:!state.ready?t.loading:''}</p>{message&&<p role="alert" className="rc-error" data-preferences-error>{message}</p>}{state.pending&&<div className="ir-warning" data-preferences-pending><p>{t.pending}</p><p>{state.pending.key==='language'?t.pendingLanguage:t.pendingTheme}: {state.pending.value}</p><div className="rc-inline-buttons"><button type="button" data-preferences-query disabled={state.busy} onClick={()=>state.recover('query')}>{t.query}</button><button type="button" data-preferences-retry disabled={state.busy} onClick={()=>state.recover('retry')}>{t.retry}</button><button type="button" data-preferences-cancel disabled={state.busy} onClick={()=>{if(window.confirm(t.cancelConfirm))state.recover('cancel')}}>{t.cancel}</button></div></div>}{error?.status===401&&<div className="rc-form"><label>{t.password}<input type="password" data-preferences-password autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button type="button" data-preferences-authenticate disabled={state.busy||!password} onClick={()=>{const secret=password;setPassword('');state.authenticate(secret)}}>{t.signIn}</button></div>}{(message||!state.ready)&&<button type="button" data-preferences-reload disabled={state.busy} onClick={state.reload}>{t.reload}</button>}</section>;
}
