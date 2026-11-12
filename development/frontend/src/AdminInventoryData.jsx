import { inventoryDataWords } from './admin-inventory-data-words.ts';
import { inventoryDataAllowed, inventoryDataCountKeys, readInventoryData, readInventoryDataFile, previewInventoryData, prepareInventoryDataIntent, inventoryDataJournal, executeInventoryDataIntent, inventoryDataStatus, cancelInventoryData, completeInventoryDataIntent, verifyInventoryDataArchive } from './admin-inventory-data.ts';

const {useState,useRef,useEffect,useLayoutEffect} = React;
function InventoryDataCounts({counts,w,label}) {
 return <details data-inventory-data-counts><summary>{label}</summary><dl className="rc-session">{inventoryDataCountKeys.map(key=><React.Fragment key={key}><dt>{w.labels[key]}</dt><dd data-inventory-count={key}>{counts[key]}</dd></React.Fragment>)}</dl></details>;
}

export function AdminInventoryData({api,session,lang,blocked=false,onBlockedChange,onInventoryChanged}) {
 const w=inventoryDataWords[lang], actor=session.user.id, house=session.user.houseId, origin=window.location.origin;
 const allowed=inventoryDataAllowed(session), canImport=inventoryDataAllowed(session,'restore'), canExport=inventoryDataAllowed(session,'backup');
 const securityKey=JSON.stringify([actor,house,api.csrf,session.csrf,[...session.permissions.systemhausCapabilities].sort()]);
 const scopeRef=useRef(null),lock=useRef(false);
 if(!scopeRef.current||scopeRef.current.api!==api||scopeRef.current.securityKey!==securityKey||scopeRef.current.origin!==origin)scopeRef.current={api,securityKey,csrf:api.csrf,origin,live:false};
 const scope=scopeRef.current,context={actorId:actor,houseId:house,origin};
 const notifications=useRef(null);
 if(notifications.current?.scope!==scope)notifications.current={scope,operations:new Set()};
 const current=()=>scopeRef.current===scope&&scope.live&&api.actorId===actor&&api.csrf===scope.csrf&&allowed;
 const [snapshot,setSnapshot]=useState(null),[pending,setPending]=useState(null),[receipt,setReceipt]=useState(null),[download,setDownload]=useState(null);
 const [ready,setReady]=useState(false),[authorized,setAuthorized]=useState(false),[phase,setPhase]=useState('loading'),[error,setError]=useState(null),[unknown,setUnknown]=useState(false),[cancelled,setCancelled]=useState(false),[cancelAck,setCancelAck]=useState(false);
 const [selected,setSelected]=useState(null),[fileName,setFileName]=useState(''),[preview,setPreview]=useState(null),[demoAck,setDemoAck]=useState(false),[restoreAck,setRestoreAck]=useState(false);
 const fileRef=useRef(null),busy=phase!==null;
 useLayoutEffect(()=>{onBlockedChange?.(allowed&&(busy||!!pending))},[allowed,busy,pending,onBlockedChange]);
 useEffect(()=>()=>onBlockedChange?.(false),[onBlockedChange]);
 function report(e){setError(e);if(e.status===401||e.status===403||e.code==='actor_changed'){setAuthorized(false);setSnapshot(null);setDownload(null)}if(e.code==='inventory_data_storage')setReady(false)}
 async function load(){const value=await readInventoryData(api,context);if(current()){setSnapshot(value);setAuthorized(true)}}
 async function committed(value,intent){
  let inventoryRefresh=null;
  await completeInventoryDataIntent(value,intent,{
   current,knownResult:receipt,remember:result=>{setAuthorized(true);setReceipt(result);setCancelled(result===null);setUnknown(false);setSelected(null);setPreview(null);setRestoreAck(false);setDemoAck(false);setCancelAck(false);if(fileRef.current)fileRef.current.value='';setFileName('');
    if(result&&['demo50','restore'].includes(result.action)&&onInventoryChanged&&!notifications.current.operations.has(result.operationId)){
     notifications.current.operations.add(result.operationId);
     inventoryRefresh=Promise.resolve().then(()=>{if(current())return onInventoryChanged(result)}).catch(e=>{if(current())report(e)});
    }
   },
   remove:()=>inventoryDataJournal('remove',context,intent),
   clear:()=>setPending(null),reload:load
  });
  if(inventoryRefresh)await inventoryRefresh;
  // The server commit and local file integrity are separate facts. A corrupt
  // download cannot turn a confirmed backup back into a pending mutation.
  if(value.action==='backup'&&current()){
   setPhase('verifying');
   const verified=await verifyInventoryDataArchive(value.archive,value.operationId);
   if(current())setDownload(verified);
  }
 }
 useEffect(()=>{
  scope.live=true;lock.current=true;setReady(false);setAuthorized(false);setSnapshot(null);setPending(null);setReceipt(null);setDownload(null);setSelected(null);setPreview(null);setFileName('');setDemoAck(false);setRestoreAck(false);setCancelAck(false);setCancelled(false);setError(null);setUnknown(false);setPhase('loading');
  if(!allowed){lock.current=false;setPhase(null);return()=>{scope.live=false}}
  (async()=>{
   try{
    // Read the journal independently: a failed status read must never hide an intention.
    const intent=await inventoryDataJournal('read',context);if(!current())return;
    setPending(intent);setReady(true);
    if(intent){setPhase('checking');const result=await inventoryDataStatus(api,intent,context);if(!current())return;if(result)await committed(result,intent);else{setUnknown(true);await load()}}
    else await load();
   }catch(e){if(current())report(e)}finally{if(current()){lock.current=false;setPhase(null)}}
  })();
  return()=>{scope.live=false};
 },[scope]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 async function refresh(){if(lock.current||!current())return;lock.current=true;setPhase('loading');setError(null);try{await load();if(!ready){const intent=await inventoryDataJournal('read',context);if(current()){setPending(intent);setReady(true)}}}catch(e){if(current())report(e)}finally{if(current()){lock.current=false;setPhase(null)}}}
 async function check(){if(lock.current||!current()||!pending)return;lock.current=true;setPhase('checking');setError(null);try{const result=await inventoryDataStatus(api,pending,context);if(current()){if(result)await committed(result,pending);else setUnknown(true)}}catch(e){if(current())report(e)}finally{if(current()){lock.current=false;setPhase(null)}}}
 async function cancel(){if(lock.current||!current()||!pending||!cancelAck)return;lock.current=true;setPhase('cancelling');setError(null);try{const result=await cancelInventoryData(api,pending,context);if(current())await committed(result,pending)}catch(e){if(current())report(e)}finally{if(current()){lock.current=false;setPhase(null)}}}
 async function selectFile(e){
  if(lock.current||pending||!current())return;const file=e.target.files?.[0];setSelected(null);setPreview(null);setRestoreAck(false);setFileName(file?.name||'');setError(null);
  if(!file)return;lock.current=true;setPhase('reading');
  try{const value=await readInventoryDataFile(file,snapshot?.maxArchiveBytes);if(current())setSelected(value)}catch(err){if(current()){report(err);if(fileRef.current)fileRef.current.value=''}}finally{if(current()){lock.current=false;setPhase(null)}}
 }
 async function previewFile(){if(lock.current||pending||!selected||!current()||!canImport)return;lock.current=true;setPhase('previewing');setPreview(null);setRestoreAck(false);setError(null);try{const value=await previewInventoryData(api,context,selected);if(current())setPreview(value)}catch(e){if(current())report(e)}finally{if(current()){lock.current=false;setPhase(null)}}}
 async function run(action){
  if(lock.current||!current()||!ready||pending||blocked||!snapshot||(action==='backup'?!canExport:!canImport||!snapshot.empty)||(action==='demo50'&&(!demoAck||!snapshot.demo.available))||(action==='restore'&&(!restoreAck||!preview||!selected)))return;
  lock.current=true;setPhase('recording');setError(null);setReceipt(null);setDownload(null);setUnknown(false);setCancelled(false);setCancelAck(false);
  try{
   const intent=prepareInventoryDataIntent(session,action,snapshot.systemhausRevision,action==='restore'?preview:null,origin);
   const result=await executeInventoryDataIntent(api,intent,context,action==='restore'?selected:null,{
    current,write:()=>inventoryDataJournal('write',context,intent),pending:value=>{setPending(value);setSnapshot(null);setPhase(action)}
   });
   if(current())await committed(result,intent);
  }catch(e){if(current())report(e)}finally{if(current()){lock.current=false;setPhase(null)}}
 }
 function saveFile(){if(!download||!authorized||!current()||busy)return;const url=URL.createObjectURL(download.blob),anchor=document.createElement('a');anchor.href=url;anchor.download=download.filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 if(!allowed)return null;
 const disabled=!ready||busy||!!pending||blocked||!snapshot;
 const code=typeof error?.code==='string'?error.code:'',message=error&&(error.status===401||code==='actor_changed'?w.expired:error.status===403?w.denied:error.status===412?w.conflict:code==='inventory_data_storage'?w.storage:code==='inventory_archive_size'?w.size:code==='inventory_crypto_unavailable'?w.crypto:['inventory_archive_integrity','inventory_archive_changed','response_invalid'].includes(code)?w.integrity:code.includes('archive')?w.archiveInvalid:w.error);
 return <section id="rc-admin-inventory-data" className="rc-admin-section rc-group-creation" tabIndex={-1} aria-label={w.title} data-admin-inventory-data aria-busy={busy}>
  <h2>{w.title}</h2><p>{w.help}</p><p className="ir-warning" data-inventory-data-scope>{w.scope}</p>
  <button type="button" data-inventory-data-refresh onClick={refresh} disabled={busy}>{w.refresh}</button>
  {busy&&<p role="status" className="rc-status" data-inventory-data-phase><progress aria-label={w.phases[phase]}/> {w.phases[phase]}</p>}
  {message&&<p role="alert" className="rc-error" data-inventory-data-error>{message}</p>}
  {blocked&&!pending&&<p role="status">{w.blocked}</p>}
  {snapshot&&<div data-inventory-data-state><p>{w.revision}: <strong data-inventory-data-revision>{snapshot.systemhausRevision}</strong> · <span data-inventory-data-empty={snapshot.empty?'true':'false'}>{snapshot.empty?w.empty:w.populated}</span></p><InventoryDataCounts counts={snapshot.counts} w={w} label={w.current}/></div>}
  {pending&&<div className="ir-warning" data-inventory-data-pending><p>{w.pending}</p><p className="rc-session">{w.request}: <strong>{pending.requestId}</strong> · {w.action}: {w[pending.action==='backup'?'backupTitle':pending.action==='demo50'?'demoTitle':'restoreTitle']}</p><button type="button" data-inventory-data-check onClick={check} disabled={busy}>{w.check}</button>{unknown&&<p role="status" data-inventory-data-unknown>{w.unknown}</p>}<p>{w.cancelHelp}</p><label><input type="checkbox" name="inventoryCancelConfirm" checked={cancelAck} onChange={e=>setCancelAck(e.target.checked)} disabled={busy}/>{w.cancelConfirm}</label><button type="button" data-inventory-data-cancel onClick={cancel} disabled={busy||!cancelAck}>{w.cancel}</button></div>}
  {cancelled&&<p role="status" data-inventory-data-cancelled>{w.cancelled}</p>}
  {receipt&&authorized&&<article className="rc-detail" data-inventory-data-receipt><h3>{w.receipt}</h3><p role="status">{w.confirmed}</p><dl className="rc-session"><dt>{w.action}</dt><dd>{w[receipt.action==='backup'?'backupTitle':receipt.action==='demo50'?'demoTitle':'restoreTitle']}</dd><dt>{w.request}</dt><dd data-inventory-data-receipt-request>{receipt.requestId}</dd><dt>{w.operation}</dt><dd>{receipt.operationId}</dd><dt>{w.revision}</dt><dd>{receipt.systemhausRevision}</dd>{receipt.archive&&<><dt>{w.hash}</dt><dd>{receipt.archive.sha256}</dd><dt>{w.bytes}</dt><dd>{receipt.archive.byteLength}</dd></>}</dl><InventoryDataCounts counts={receipt.counts} w={w} label={w.counts}/>{download&&<><p>{w.downloadHelp}</p><button type="button" data-inventory-data-download onClick={saveFile} disabled={busy}>{w.download}</button></>}</article>}
  <div className="rc-hierarchy">
   <section data-inventory-data-card="demo50"><h3>{w.demoTitle}</h3><p>{w.demoHelp}</p>{snapshot?.demo&&<InventoryDataCounts counts={snapshot.demo.counts} w={w} label={w.example}/>}<form className="rc-form" onSubmit={e=>{e.preventDefault();run('demo50')}}><label><input type="checkbox" name="inventoryDemoConfirm" checked={demoAck} disabled={disabled||!canImport||!snapshot?.empty} onChange={e=>setDemoAck(e.target.checked)}/>{w.demoConfirm}</label><button type="submit" data-inventory-data-demo disabled={disabled||!canImport||!snapshot?.empty||!snapshot?.demo.available||!demoAck}>{w.demo}</button></form>{!canImport&&<p>{w.importDenied}</p>}</section>
   <section data-inventory-data-card="backup"><h3>{w.backupTitle}</h3><p>{w.backupHelp}</p><div className="rc-form"><button type="button" data-inventory-data-backup onClick={()=>run('backup')} disabled={disabled||!canExport}>{w.backup}</button></div>{!canExport&&<p>{w.exportDenied}</p>}</section>
   <section data-inventory-data-card="restore"><h3>{w.restoreTitle}</h3><p>{w.restoreHelp}</p><div className="rc-form"><label>{w.file}<input ref={fileRef} type="file" name="inventoryDataFile" accept=".json,application/json" disabled={!ready||busy||!!pending||!snapshot||!canImport} onChange={selectFile}/></label>{fileName&&<p>{fileName}</p>}{selected&&<p role="status">{w.fileSelected} · {w.bytes}: {selected.byteLength}</p>}<button type="button" data-inventory-data-preview onClick={previewFile} disabled={busy||!!pending||!selected||!canImport}>{w.preview}</button>{preview&&<div data-inventory-data-preview-result><h4>{w.previewTitle}</h4><p className="rc-session">{w.hash}: {preview.archiveSha256}</p><p>{w.bytes}: {preview.byteLength}</p><InventoryDataCounts counts={preview.counts} w={w} label={w.counts}/></div>}<label><input type="checkbox" name="inventoryRestoreConfirm" checked={restoreAck} disabled={disabled||!canImport||!snapshot?.empty||!preview} onChange={e=>setRestoreAck(e.target.checked)}/>{w.restoreConfirm}</label><button type="button" data-inventory-data-restore onClick={()=>run('restore')} disabled={disabled||!canImport||!snapshot?.empty||!preview||!restoreAck}>{w.restore}</button></div></section>
  </div>
 </section>;
}
