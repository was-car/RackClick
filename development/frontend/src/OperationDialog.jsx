import { hardwareWords } from './hardware-words.ts';
import { mutationRemainsUnconfirmed } from './api.ts';
import { prepareCommand, executeCommand, cancelPendingCommand, readPendingCommand } from './inventory-api.ts';
import { pendingJournal, pendingRecord } from './pending-journal.ts';
import { inventoryWords } from './inventory-words.ts';
import { impactSections } from './impact-model.ts';
import { operationStatusWords } from './inventory-operation-status-words.ts';
import { inventoryOptionLabel } from './inventory-choice-labels.ts';
const { useState, useEffect, useRef } = React;
export function inventoryError(error, w) {
 const hw=w===inventoryWords.de?hardwareWords.de:w===inventoryWords.es?hardwareWords.es:hardwareWords.en;
 if (error.code === 'mount_support_revision_unavailable') return hw.supportUnavailable;
 if (error.code === 'mount_children_present') return hw.children;
 if (error.code === 'mount_slot_occupied') return hw.mountOccupied;
 if (error.code === 'rack_capacity_exceeded') return hw.capacity;
 if (['hardware_operation_unsupported','hardware_duplicate_unsupported','hardware_metadata_immutable'].includes(error.code)) return hw.unsupported;
 if (error.code === 'draft_storage_unavailable') return w.storageError;
 if (error.uncertain) return w.uncertain;
 if (error.status === 401 || error.code === 'actor_changed') return w.expired;
 if (error.status === 403 || error.status === 404) return w.denied;
 if (error.status === 412) return w.conflict;
 if (error.code === 'compensation_not_latest' || error.code === 'compensation_state_conflict') return w.undoStale;
 if (error.code === 'inventory_conflict') return w.integrityConflict;
 if (error.code === 'port_occupied') return w.occupied;
 if (error.code === 'reserved_confirmation_required') return w.reservedRequired;
 if (error.status === 422) return w.invalid;
 return w.error;
}
export function Fields({ fields, form, setForm, disabled, w }) {
 return fields.filter(field => !field.show || field.show(form)).map(field => {
  const options = field.type === 'select' ? (typeof field.options === 'function' ? field.options(form) : field.options) : [];
  const selected = options.find(option => String(option.value) === String(form[field.key] ?? ''));
  return <label key={field.key}>{w[field.label || field.key] || field.label || field.key}{field.type === 'select' ? <select name={field.key} value={form[field.key] ?? ''} title={selected?.title} disabled={disabled || field.disabled} required={field.required} onChange={e => setForm(field.change ? field.change(form, e.target.value) : { ...form, [field.key]: e.target.value })}>{options.map(option => <option key={option.value} value={option.value} title={option.title}>{inventoryOptionLabel(option,w)}</option>)}</select> : field.type === 'textarea' ? <textarea name={field.key} value={form[field.key] ?? ''} disabled={disabled} rows={3} onChange={e => setForm({ ...form, [field.key]: e.target.value })}/> : <input name={field.key} type={field.type || 'text'} min={field.min} max={field.max} step={field.step} required={field.required} disabled={disabled || field.disabled} value={form[field.key] ?? ''} onChange={e => setForm({ ...form, [field.key]: e.target.value })}/>}</label>;
 });
}
export function OperationDialog({ api, session, project, draft, recovery, lang, onClose, onCommit, onRefresh, onPendingChange, knownRevision=project.revision, writeAllowed=true, authorityLost=false }) {
 const w = inventoryWords[lang], ref = useRef(null), [form, setForm] = useState(draft?.initial || {}), [snapshot, setSnapshot] = useState(project), [operation, setOperation] = useState(recovery?.operation || null), [unconfirmed, setUnconfirmed] = useState(!!recovery), [busy, setBusy] = useState(false), [error, setError] = useState(null), [preview, setPreview] = useState(null), [password, setPassword] = useState('');
 const origin=useRef({api,actorId:recovery?.actorId||session.user.id,customerId:project.customerId});
 const actorId = origin.current.actorId;
 const [completed, setCompleted] = useState(false);
 const [queryNotice,setQueryNotice]=useState(null),queryAlive=useRef(true),queryController=useRef(null),qw=operationStatusWords[lang];
 const queryContext=useRef(null);queryContext.current={api,actorId:session.user.id,customerId:project.customerId,knownRevision:Math.max(project.revision,knownRevision),writeAllowed:writeAllowed&&!authorityLost,invalidated:!!queryContext.current?.invalidated||api!==origin.current.api||session.user.id!==actorId||project.customerId!==origin.current.customerId};
 function inContext(){const context=queryContext.current;if(api.actorId&&api.actorId!==actorId)context.invalidated=true;return queryAlive.current&&!context.invalidated&&context.api===api&&context.actorId===actorId&&context.customerId===origin.current.customerId&&api.actorId===actorId;}
 function requireCurrent(){if(!queryAlive.current)return false;if(!inContext())throw {status:409,code:'actor_changed'};return true;}
 function requireWrite(current,checkRevision){if(!requireCurrent())return false;const context=queryContext.current;if(!context.writeAllowed)throw {status:403,code:'permission_changed',uncertain:!!current};if(checkRevision&&context.knownRevision>snapshot.revision)throw {status:412,code:'revision_conflict',uncertain:!!current};return true;}
 useEffect(() => { queryAlive.current=true;ref.current.showModal(); const warn = e => { if (!operation) { e.preventDefault(); e.returnValue = ''; } }; window.addEventListener('beforeunload', warn); return () => {queryAlive.current=false;queryController.current?.abort();window.removeEventListener('beforeunload', warn);}; }, []);
 async function queryPending() {
  if(!operation||busy||completed)return;
  const controller=new AbortController();queryController.current=controller;setBusy(true);setError(null);setQueryNotice(null);
  const current=()=>{if(!queryAlive.current)return false;const context=queryContext.current;if(api.actorId&&api.actorId!==actorId)context.invalidated=true;if(context.invalidated||controller.signal.aborted||context.api!==api||context.actorId!==actorId||context.customerId!==operation.customerId||api.actorId!==actorId)throw {status:409,code:'actor_changed'};return true;};
  try{
   if(!current())return;
   const outcome=await readPendingCommand(api,operation,controller.signal);
   if(!current())return;
   if(outcome.state==='notRecorded'){setQueryNotice('notRecorded');return;}
   setCompleted(true);
   try{await pendingJournal.remove(operation.requestId,actorId);}catch{}
   if(!current())return;
   await onPendingChange();
   if(!current())return;
   if(outcome.state==='committed'){await onCommit?.(outcome.operation,operation);if(current())onClose();}
   else {await onRefresh();if(current())setQueryNotice('cancelled');}
  }catch(e){if(queryAlive.current){setError(e);setUnconfirmed(true);}}
  finally{if(queryAlive.current)setBusy(false);if(queryController.current===controller)queryController.current=null;}
 }
 async function authenticate() {
  setBusy(true); try { const identity = await api.login(session.user.userName, password); setPassword(''); if (identity.user.id !== actorId) { try { await api.logout(); } catch {} api.csrf = ''; api.actorId = ''; throw { code: 'actor_changed', status: 409 }; } setError(null); } catch (e) { setError(e); } finally { setBusy(false); }
 }
 async function submit(e) {
  e.preventDefault(); if (busy || completed) return;
  if ((error?.status === 401 || error?.code === 'actor_changed') && password) { if(!queryContext.current.invalidated)await authenticate(); return; }
  setBusy(true); setError(null); let current = operation, confirmed = false;const firstDispatch=!operation;
  try {
   if(!requireWrite(current,firstDispatch))return;
   if (!current) {
    const command = draft.build(form, snapshot);
    if ((typeof draft.destructive === 'function' ? draft.destructive(command) : draft.destructive) && !preview) {
     const { data } = await api.request('/customers/' + project.customerId + '/commands/preview', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-RackClick-CSRF': api.csrf, 'X-RackClick-Actor': actorId, 'If-Match': '"' + snapshot.revision + '"' }, body: JSON.stringify(command) });
     if(!requireWrite(null,true))return;
     if (data.customerId !== project.customerId || data.revision !== snapshot.revision || typeof data.confirmationToken !== 'string' || !data.impact) throw { code: 'response_invalid' };
     setPreview(data); return;
    }
    current = prepareCommand(api, project.customerId, command.type, { ...command.payload, ...(preview ? { confirmationToken: preview.confirmationToken } : {}) }, snapshot.revision, actorId);
    await pendingJournal.put(pendingRecord(current, draft.label, String(form.name || draft.summary || '')));
    if(!requireCurrent())return;
    setOperation(current);if(!requireWrite(current,true))return;await onPendingChange();
   }
   if(!requireWrite(current,firstDispatch))return;
   const result = await executeCommand(api, current);
   if(!requireCurrent())return;
   confirmed = true; setCompleted(true);
   try { await pendingJournal.remove(current.requestId, actorId); } catch {}
   if(!requireCurrent())return;
   await onPendingChange();if(!requireCurrent())return;
   await onCommit?.(result, current);if(requireCurrent())onClose();
  } catch (err) {
   if(!queryAlive.current)return;
   if (confirmed) { setError(err); return; }
   const pending = mutationRemainsUnconfirmed(unconfirmed, err)||!!current&&err.code==='actor_changed'; setUnconfirmed(pending); setError(err);
   if (!pending&&inContext()) {
    try { if (current) { try { await pendingJournal.remove(current.requestId, actorId); } catch {} } if(!inContext()){if(queryAlive.current)setError({status:409,code:'actor_changed'});return;}setOperation(null);await onPendingChange(); }
    catch(cleanupError){if(queryAlive.current)setError(cleanupError);}
   }
  } finally { if(queryAlive.current)setBusy(false); }
 }
 async function refreshRevision() { setBusy(true); try { if(!requireCurrent())return;const next=await onRefresh();if(!requireCurrent())return;setSnapshot(next); if(draft?.resetOnRefresh)setForm(draft.resetOnRefresh); setPreview(null); setError(null); } catch (e) { if(queryAlive.current)setError(e); } finally { if(queryAlive.current)setBusy(false); } }
 async function cancelPending() {
  if (!operation || busy || completed) return;
  setBusy(true); setError(null);
  let confirmed = false;
  try { if(!requireCurrent()||!window.confirm(w.cancelPendingConfirm)||!requireCurrent())return;const result = await cancelPendingCommand(api, operation);if(!requireCurrent())return;confirmed = true; setCompleted(true); await pendingJournal.remove(operation.requestId, actorId);if(!requireCurrent())return;await onPendingChange();if(!requireCurrent())return;if (result.state === 'committed') await onCommit?.(result.operation, operation); else await onRefresh();if(requireCurrent())onClose(); }
  catch (e) { if(queryAlive.current){if (!confirmed) setUnconfirmed(true); setError(e);} }
  finally { if(queryAlive.current)setBusy(false); }
 }
 const contextLost=queryContext.current.invalidated;
 const writeBlocked=!queryContext.current.writeAllowed,staleDraft=!operation&&!completed&&queryContext.current.knownRevision>snapshot.revision;
 const locked = busy || completed || contextLost || writeBlocked || staleDraft || !!operation || !!preview;
 const destructive = draft && (typeof draft.destructive === 'function' ? draft.destructive(draft.build(form, snapshot)) : draft.destructive);
 return <dialog ref={ref} className="ir-dialog rc-operation-dialog" onCancel={e => { if (busy) e.preventDefault(); else onClose(); }} aria-labelledby="operation-title"><form className="rc-form" onSubmit={submit}><header><h2 id="operation-title">{w[draft?.label || recovery?.label] || draft?.label || recovery?.label || w.pending}</h2></header>{recovery && <p>{recovery.summary}</p>}{draft && <><Fields fields={draft.fields || []} form={form} setForm={value => { setForm(value); setPreview(null); setError(null); }} disabled={locked} w={w}/>{draft.render && draft.render(form, setForm, locked, w, snapshot, refreshRevision)}</>}{preview && <section><h3>{w.affected}</h3><p>{w.deleteImpact}</p><ul>{impactSections(preview.impact, snapshot, w).map(section => <li key={section.kind} data-impact-kind={section.kind}>{section.label}: {section.entries.length}<details open><summary>{w.preview}</summary>{section.entries.map(entry => <div key={entry.id} data-impact-id={entry.id} title={entry.id}>{entry.label}</div>)}</details></li>)}</ul></section>}{error && <div role="alert" className="rc-error">{inventoryError(error, w)}</div>}{!error&&(writeBlocked||staleDraft)&&<div role="alert" className="rc-error">{writeBlocked?w.denied:w.conflict}</div>}{operation && <p className="rc-muted">{w.pendingHelp}</p>}{queryNotice&&<p role="status" data-operation-query-status={queryNotice}>{qw[queryNotice]}</p>}{(error?.status === 401 || error?.code === 'actor_changed') && <div className="rc-form"><label>{w.password}<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)}/></label><button type="button" onClick={authenticate} disabled={busy || contextLost || !password}>{w.signIn}</button></div>}<footer>{completed && <button type="button" disabled={busy} onClick={refreshRevision}>{w.refresh}</button>}{operation && !completed && <button type="button" data-query-pending onClick={queryPending} disabled={busy||contextLost}>{qw.query}</button>}{operation && !completed && <button type="button" onClick={cancelPending} disabled={busy||contextLost}>{w.cancelPending}</button>}{!contextLost&&!writeBlocked&&(staleDraft||error?.status === 412 && !unconfirmed) && <button type="button" onClick={refreshRevision} disabled={busy}>{w.reload}</button>}<button type="button" onClick={onClose} disabled={busy}>{operation ? w.close : w.cancel}</button><button type="submit" disabled={busy || completed || contextLost || writeBlocked || staleDraft || (error?.status === 412 && !unconfirmed)}>{busy ? w.saving : operation ? w.retry : preview ? w.confirmDelete : destructive ? w.preview : w.save}</button></footer></form></dialog>;
}
