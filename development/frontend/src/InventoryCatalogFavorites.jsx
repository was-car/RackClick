import {ApiError} from './api.ts';
import {readCatalogFavorites,prepareFavorite,setCatalogFavorite,catalogFavoriteStatus,cancelCatalogFavorite} from './catalog-favorites.ts';
import {favoriteJournal} from './catalog-favorites-journal.ts';
import {favoriteWords} from './catalog-favorites-words.ts';
import {inventoryWords} from './inventory-words.ts';
import {inventoryError} from './OperationDialog.jsx';
import {IRIcon} from '../generated/rc9.jsx';
const {useEffect,useState,useRef}=React;
export function useCatalogFavorites({api,actorId,customerId,userName,lang}){
 const [data,setData]=useState(null),[pending,setPending]=useState(null),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(null),[notice,setNotice]=useState('');
 const context=actorId+':'+customerId,scope=useRef({context,generation:0}),mounted=useRef(false),inFlight=useRef(null);
 if(scope.current.context!==context)scope.current={context,generation:scope.current.generation+1};
 const generation=scope.current.generation;
 const sameScope=()=>mounted.current&&scope.current.context===context&&scope.current.generation===generation;
 const current=()=>sameScope()&&api.actorId===actorId;
 async function read(){const next=await readCatalogFavorites(api,customerId,actorId);if(current())setData(next);return next}
 useEffect(()=>{mounted.current=true;inFlight.current=null;setBusy(false);setReady(false);setData(null);setPending(null);setError(null);setNotice('');let active=true;const controller=new AbortController();
  (async()=>{try{const draft=await favoriteJournal('read',actorId);const next=await readCatalogFavorites(api,customerId,actorId,controller.signal);if(active&&current()){setPending(draft);setData(next);setReady(true)}}catch(e){if(active&&sameScope())setError(e)}})();
  return()=>{active=false;mounted.current=false;controller.abort()};
 },[api,actorId,customerId]);
 async function task(action,reauthenticate=false){if(inFlight.current||!sameScope()||(!reauthenticate&&api.actorId!==actorId))return;const job={context,generation};inFlight.current=job;setBusy(true);setError(null);setNotice('');try{await action()}catch(e){if(sameScope())setError(e)}finally{if(inFlight.current===job){inFlight.current=null;if(sameScope())setBusy(false)}}}
 async function finish(d,committed){
  if(current())setNotice(committed?'saved':'cancelled');
  // The receipt is authoritative for the request; only a fresh GET supplies the complete set.
  try{await read()}catch{throw new ApiError(0,'favorites_refresh_failed')}
  await favoriteJournal('remove',actorId,d);if(current())setPending(null);
 }
 async function toggle(presetKey){await task(async()=>{
  if(!ready||pending||!data||data.ownerId!==actorId||data.customerId!==customerId)throw new ApiError(409,'favorites_not_ready');
  const d=prepareFavorite(actorId,data,presetKey,!data.presetKeys.includes(presetKey));await favoriteJournal('write',actorId,d);if(current())setPending(d);
  try{await setCatalogFavorite(api,customerId,d)}catch(e){
   if(e.status===412&&!e.uncertain){await favoriteJournal('remove',actorId,d);if(current())setPending(null);await read();if(current())setNotice('conflict');return}throw e;
  }
  await finish(d,true);
 })}
 async function recover(action){await task(async()=>{
  if(!pending)return;const d=pending;
  if(action==='retry'){await setCatalogFavorite(api,customerId,d);await finish(d,true);return}
  const result=action==='cancel'?await cancelCatalogFavorite(api,customerId,d):await catalogFavoriteStatus(api,customerId,d);
  if(result.state==='notRecorded'){if(current())setNotice('notRecorded');return}
  await finish(d,result.state==='committed');
 })}
 async function authenticate(password){await task(async()=>{const identity=await api.login(userName,password);if(identity.user.id!==actorId){try{await api.logout()}catch{}api.csrf='';api.actorId='';throw new ApiError(409,'actor_changed')}if(current()){setError(null);const d=await favoriteJournal('read',actorId);setPending(d);await read();if(current())setReady(true)}},true)}
 return {data:api.actorId===actorId&&data?.ownerId===actorId&&data.customerId===customerId?data:null,pending,ready:ready&&api.actorId===actorId,busy,error,notice,toggle,recover,authenticate,reload:()=>task(async()=>{const d=await favoriteJournal('read',actorId);if(current())setPending(d);await read();if(current())setReady(true)}),lang};
}
export function InventoryCatalogFavorites({state,selected,onlyFavorites,onOnlyFavorites,disabled,lang}){
 const f=favoriteWords[lang],w=inventoryWords[lang],[password,setPassword]=useState(''),marked=!!selected&&!!state.data?.presetKeys.includes(selected.key),locked=disabled||state.busy;
 return <section data-personal-favorites aria-label={f.title} style={{minWidth:0,overflowWrap:'anywhere'}}><h3>{f.title}</h3>
  {!state.ready&&<p role="status">{f.loading}</p>}
  <div className="ir-face-controls"><button type="button" className="rc8-favorite" data-favorite-toggle disabled={locked||!state.ready||!!state.pending||!selected} aria-pressed={marked} aria-label={selected?(marked?f.remove:f.add)+' '+selected.label:f.choose} onClick={()=>state.toggle(selected.key)}><IRIcon name="star" size={20}/>{selected?(marked?f.remove:f.add):f.choose}</button>
   <button type="button" data-only-favorites aria-pressed={onlyFavorites} disabled={disabled||!state.ready} onClick={()=>onOnlyFavorites(!onlyFavorites)}>{f.only}</button>
   <button type="button" data-favorites-refresh disabled={locked} onClick={state.reload}>{f.refresh}</button></div>
  {state.data&&<p data-favorites-revision>{f.scope}: {state.data.revision}</p>}
  {state.notice&&<p role="status" data-favorites-notice={state.notice}>{f[state.notice]}</p>}
  {state.error&&<p role="alert" className="rc-error" data-favorites-error>{state.error.code==='favorites_refresh_failed'?f.refreshFailed:inventoryError(state.error,w)}</p>}
  {state.pending&&<div className="ir-warning" data-favorites-pending><p>{f.pending}</p><p>{state.pending.favorite?f.add:f.remove}: {state.pending.presetKey} · {state.pending.requestId}</p><button type="button" data-favorites-query disabled={locked} onClick={()=>state.recover('query')}>{f.query}</button><button type="button" data-favorites-retry disabled={locked} onClick={()=>state.recover('retry')}>{f.retry}</button><button type="button" data-favorites-cancel disabled={locked} onClick={()=>{if(window.confirm(f.cancelConfirm))state.recover('cancel')}}>{f.cancel}</button></div>}
  {(state.error?.status===401||state.error?.code==='actor_changed')&&<div className="rc-form"><label>{f.password}<input data-favorites-password type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button type="button" disabled={locked||!password} onClick={()=>{const secret=password;setPassword('');state.authenticate(secret)}}>{f.signIn}</button></div>}
 </section>;
}
