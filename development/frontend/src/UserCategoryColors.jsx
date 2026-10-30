import {ApiError} from './api.ts';
import {readUserCategoryColors,prepareCategoryColors,mutateCategoryColors,categoryColorsStatus,cancelCategoryColors,categoryPairs,categorySwatches,validCategoryColors,sameCategoryColors} from './user-category-colors.ts';
import {categoryColorsJournal} from './user-category-colors-journal.ts';
import {userCategoryColorsWords} from './user-category-colors-words.ts';
import {UserPortColors} from './UserPortColors.jsx';
const {useState,useRef,useEffect}=React;
export function useUserCategoryColors({api,actorId,userName,generation=0,suspended=false,onAuthenticationInvalidated}){
 const [data,setData]=useState(null),[pending,setPending]=useState(null),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(null),[notice,setNotice]=useState(''),[view,setView]=useState(-1);
 const context=(actorId||'anonymous')+':'+generation+':'+suspended,scope=useRef({context,token:0}),mounted=useRef(false),inFlight=useRef(null);
 if(scope.current.context!==context)scope.current={context,token:scope.current.token+1};const token=scope.current.token;
 const sameScope=()=>mounted.current&&scope.current.context===context&&scope.current.token===token,current=()=>sameScope()&&!suspended&&api.actorId===actorId;
 const ensure=()=>{if(!current())throw new ApiError(409,'actor_changed')};
 async function read(signal){ensure();const value=await readUserCategoryColors(api,actorId,signal);ensure();setData(value);return value}
 async function load(signal){ensure();setReady(false);const d=await categoryColorsJournal('read',actorId);ensure();setPending(d);await read(signal);ensure();setReady(true)}
 useEffect(()=>{mounted.current=true;inFlight.current=null;setData(null);setPending(null);setReady(false);setBusy(false);setError(null);setNotice('');setView(token);const c=new AbortController();if(actorId&&!suspended)load(c.signal).catch(e=>{if(current()&&!c.signal.aborted)setError(e)});return()=>{mounted.current=false;c.abort()}},[api,context]);
 async function task(action,reauth=false){
  if(inFlight.current||!sameScope()||suspended||!actorId||(!reauth&&api.actorId!==actorId))return;
  const job={context,token};inFlight.current=job;setBusy(true);setError(null);setNotice('');
  try{return await action()}catch(e){if(sameScope()&&(api.actorId===actorId||(reauth&&!api.actorId)))setError(e)}finally{if(inFlight.current===job){inFlight.current=null;if(sameScope())setBusy(false)}}
 }
 async function finish(d,committed){
  ensure();try{await read()}catch(e){if(e.code==='actor_changed'||e.status===401)throw e;throw new ApiError(0,'category_colors_refresh_failed')}
  ensure();await categoryColorsJournal('remove',actorId,d);ensure();setPending(null);setNotice(committed?'saved':'cancelled');setReady(true);
 }
 async function save(colors){
  if(suspended||!actorId||!validCategoryColors(colors))return;
  return task(async()=>{ensure();if(view!==token||!ready||pending||!data)throw new ApiError(409,'category_colors_not_ready');const d=prepareCategoryColors(actorId,data,colors);await categoryColorsJournal('write',actorId,d);ensure();setPending(d);await mutateCategoryColors(api,d);ensure();await finish(d,true)});
 }
 async function recover(action){return task(async()=>{ensure();if(view!==token||!pending)return;const d=pending;if(action==='retry'){await mutateCategoryColors(api,d);ensure();await finish(d,true);return}if(!['query','cancel'].includes(action))throw new ApiError(422,'category_colors_invalid');const result=action==='cancel'?await cancelCategoryColors(api,d):await categoryColorsStatus(api,d);ensure();if(result.state==='notRecorded'){setNotice('notRecorded');return}await finish(d,result.state==='committed')})}
 async function authenticate(password){return task(async()=>{
  const identity=await api.login(userName,password);
  // Cookie and the shared API cache already changed when login resolves.
  if(!sameScope()||identity.user.id!==actorId){api.csrf='';api.actorId='';onAuthenticationInvalidated?.();if(sameScope())throw new ApiError(409,'actor_changed');return}
  ensure();await load();
 },true)}
 const visible=view===token&&api.actorId===actorId&&!suspended,confirmed=visible&&data?.ownerId===actorId?data:null;
 return{actorId,data:confirmed,colors:confirmed?.colors||{},pending:visible?pending:null,ready:visible&&ready,busy:visible&&busy,error:view===token?error:null,notice:visible?notice:'',disabled:suspended||!actorId||!visible||!ready||busy||!!pending,save,recover,authenticate,reload:()=>task(()=>load())};
}
export function PersonalPalette({portState,categoryState,lang,onClose}){
 const [tab,setTab]=useState('ports'),t=userCategoryColorsWords[lang];
 const navigation=<nav aria-label={t.open} className="rc-inline-buttons" style={{flexWrap:'wrap'}}><button type="button" data-palette-tab="ports" aria-pressed={tab==='ports'} onClick={()=>setTab('ports')}>{t.ports}</button><button type="button" data-palette-tab="categories" aria-pressed={tab==='categories'} onClick={()=>setTab('categories')}>{t.open}</button></nav>;
 return <><UserPortColors state={portState} lang={lang} onClose={onClose} active={tab==='ports'} paletteNavigation={navigation}/><UserCategoryColors state={categoryState} lang={lang} onClose={onClose} active={tab==='categories'} paletteNavigation={navigation}/></>;
}
export function UserCategoryColors({state,lang,onClose,active=true,paletteNavigation}){
 const t=userCategoryColorsWords[lang],dialog=useRef(null),[draft,setDraft]=useState(()=>({...((state.pending?.colors)||state.data?.colors||{})})),[password,setPassword]=useState('');
 useEffect(()=>{if(active)dialog.current.showModal();else dialog.current.close();return()=>dialog.current?.close()},[active]);
 useEffect(()=>{if(state.data&&!state.pending)setDraft({...state.data.colors})},[state.data,state.pending]);
 const error=state.error,message=!error?'':error.status===412?t.conflict:error.status===401?t.expired:error.code==='actor_changed'?t.actor:error.code==='category_colors_storage_unavailable'?t.storage:error.code==='category_colors_refresh_failed'?t.refresh:error.code==='category_colors_revision_exhausted'?t.exhausted:error.code==='response_invalid'?t.invalid:t.unavailable;
 const colors=state.pending?.colors||draft,reset=key=>setDraft(old=>{const next={...old};delete next[key];return next});
 const toggle=(key,color)=>setDraft(old=>{const next={...old};if(next[key]===color)delete next[key];else next[key]=color;return next});
 const editing=!state.pending&&state.data&&!sameCategoryColors(draft,state.data.colors),status=state.busy?'saving':state.notice==='saved'&&editing?'ready':state.notice||(!state.ready?'loading':'ready');
 return <dialog ref={dialog} className="ir-dialog" data-category-colors-panel aria-labelledby="category-colors-title" style={{width:'min(760px, calc(100vw - 24px))',maxWidth:'calc(100vw - 24px)',boxSizing:'border-box',maxHeight:'calc(100dvh - 24px)',overflowY:'auto',overflowWrap:'anywhere'}} onCancel={e=>{e.preventDefault();onClose()}}><form className="rc-form" onSubmit={e=>{e.preventDefault();state.save(draft)}}><div className="rc-dialog-title"><h2 id="category-colors-title">{t.scope}</h2></div>{paletteNavigation}<p>{t.help}</p><span data-category-colors-revision hidden>{state.data?.revision??'—'}</span><p role="status" aria-live="polite" data-category-colors-status={status}>{state.busy?t.saving:editing?t.preview:state.notice?t[state.notice]:!state.ready?t.loading:''}</p>{message&&<p role="alert" className="rc-error" data-category-colors-error>{message}</p>}<section aria-label={t.preview} style={{display:'grid',gap:6}}>{categoryPairs.map(({a,b,key})=>{const label=t.categories[a]+' ↔ '+t.categories[b];return <div key={key} data-category-colors-pair={key} style={{display:'flex',alignItems:'center',flexWrap:'wrap',gap:6,padding:'4px 8px',background:'var(--ir-raised)',border:'1px solid var(--ir-border)',borderRadius:4,minWidth:0}}><span style={{flex:'1 1 220px',minWidth:0}}>{label}</span><div role="group" aria-label={label} style={{display:'flex',alignItems:'center',flexWrap:'wrap',gap:4,minWidth:0}}>{categorySwatches.map(color=><button key={color} type="button" data-category-colors-swatch={color} data-category-colors-key={key} aria-label={label+' '+color} title={label+' '+color} aria-pressed={colors[key]===color} disabled={state.disabled} onClick={()=>toggle(key,color)} style={{width:24,height:24,minWidth:24,padding:0,background:color,border:colors[key]===color?'2px solid var(--ir-text)':'1px solid var(--ir-border)',outline:colors[key]===color?'1px solid var(--ir-text)':'',outlineOffset:2,borderRadius:4}}/>)}<button type="button" data-category-colors-reset={key} aria-label={t.reset+' '+label} title={t.reset+' '+label} disabled={state.disabled||!Object.hasOwn(colors,key)} onClick={()=>reset(key)} style={{padding:'2px 6px',minWidth:24}}>×</button></div></div>})}</section><button type="button" data-category-colors-reset-all disabled={state.disabled} onClick={()=>setDraft({})}>{t.resetAll}</button>{state.pending&&<div className="ir-warning" data-category-colors-pending><p>{t.pending}</p><div className="rc-inline-buttons"><button type="button" data-category-colors-query disabled={state.busy} onClick={()=>state.recover('query')}>{t.query}</button><button type="button" data-category-colors-retry disabled={state.busy} onClick={()=>state.recover('retry')}>{t.retry}</button><button type="button" data-category-colors-cancel disabled={state.busy} onClick={()=>{if(window.confirm(t.cancelConfirm))state.recover('cancel')}}>{t.cancel}</button></div></div>}{error?.status===401&&<div className="rc-form"><label>{t.password}<input type="password" data-category-colors-password autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button type="button" data-category-colors-authenticate disabled={state.busy||!password} onClick={()=>{const secret=password;setPassword('');state.authenticate(secret)}}>{t.signIn}</button></div>}{(message||!state.ready)&&<button type="button" data-category-colors-reload disabled={state.busy} onClick={state.reload}>{t.reload}</button>}<footer className="rc-inline-buttons"><button type="button" data-category-colors-close onClick={onClose}>{t.close}</button><button type="submit" data-category-colors-save disabled={state.disabled}>{t.save}</button></footer></form></dialog>;
}
