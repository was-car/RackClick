import { useAdminSelectionGuard } from './AdminSectionNavigation.jsx';
import { changeMfaAccount, mfaAccountChangeStatus, mfaAccountJournal, mfaChangeRequiresReauthentication, readMfaAccount } from './mfa-account.ts';
import { mfaAccountError, mfaAccountNotice, mfaAccountWords } from './mfa-account-words.ts';
import { MfaRecoveryCodesPanel } from './MfaRecoveryCodesPanel.jsx';
const { useEffect, useRef, useState } = React;

function noticeText(status, w) {
 const key = mfaAccountNotice(status);
 return w[key].replace('{days}', String(status.daysRemaining ?? ''));
}
function statusText(status, w) {
 return status.enrollmentPending ? w.pending : w[status.factorState];
}
const emptyView = scope => ({ scope, status: null, pending: null, phase: 'loading', error: null, outcome: null, ready: false });

// Personal and selected-user security use the same server contract. Setup secrets stay exclusively in MfaChallengeForm.
export function MfaAccountPanel({ api, session, targetUserId, lang = 'en', onReauthenticate, onSelectionGuard, onChanged }) {
 const w = mfaAccountWords[lang] || mfaAccountWords.en, actor = session.user.id;
 const admin = targetUserId !== undefined;
 const identity = actor + ':' + (admin ? 'admin:' + targetUserId : 'self');
 const scopeRef = useRef(null);
 if (!scopeRef.current || scopeRef.current.identity !== identity || scopeRef.current.api !== api) scopeRef.current = { identity, actor, api, live: false };
 const scope = scopeRef.current, requestLock = useRef(null), readSequence = useRef(0);
 const [storedView, setView] = useState(() => emptyView(null));
 const view = storedView.scope === scope ? storedView : emptyView(scope);
 const [form, setForm] = useState({ scope: null, action: null, password: '', ack: false });
 const currentForm = form.scope === scope ? form : { scope, action: null, password: '', ack: false };
 const current = () => scopeRef.current === scope && scope.live && api.actorId === actor;
 const patch = values => { if (current()) setView(old => ({ ...(old.scope === scope ? old : emptyView(scope)), ...values, scope })); };
 const setFields = values => setForm(old => ({ ...(old.scope === scope ? old : { scope, action: null, password: '', ack: false }), ...values, scope }));
 const [recoveryDirty,setRecoveryDirty]=useState(false);
 const busy = view.phase === 'working' || view.phase === 'loading';
 const pending = view.pending, effectiveAdmin = pending ? pending.scope === 'admin' : admin;
 const selected = pending?.userId || (admin ? targetUserId : actor);
 const effectiveAction = pending?.action || currentForm.action;
 const formId = 'rc-mfa-account-' + actor + '-' + (admin ? targetUserId || 'choose' : 'self');
 useAdminSelectionGuard('mfa', onSelectionGuard, busy || recoveryDirty || !view.ready || !!pending || !!currentForm.action || !!currentForm.password || currentForm.ack, requestLock);

 async function loadStatus(draft = pending) {
  const sequence = ++readSequence.current;
  const useAdmin = draft ? draft.scope === 'admin' : admin;
  const target = draft?.userId || (admin ? targetUserId : actor);
  if (useAdmin && !target) { patch({ status: null, phase: 'ready' }); return; }
  patch({ phase: 'loading', error: null });
  try {
   const status = await readMfaAccount(api, useAdmin ? target : undefined);
   if (current() && readSequence.current === sequence) patch({ status, phase: 'ready' });
  } catch (error) {
   if (current() && readSequence.current === sequence) patch({ status: null, phase: 'ready', error: mfaAccountError(error) });
  }
 }
 async function initialize() {
  patch({ phase: 'loading', error: null });
  try {
   const recovered = await mfaAccountJournal('read', actor);
   if (!current()) return;
   patch({ pending: recovered, ready: true });
   await loadStatus(recovered);
  } catch (error) { patch({ ready: false, phase: 'ready', error: mfaAccountError(error) }); }
 }
 useEffect(() => {
  scope.live = true; requestLock.current = null;
  setView(emptyView(scope)); setForm({ scope, action: null, password: '', ack: false });
  initialize();
  return () => { scope.live = false; readSequence.current++; };
 }, [scope]);

 async function finish(receipt, draft, recovered) {
  await mfaAccountJournal('remove', actor, draft);
  if (!current()) return;
  patch({ pending: null, outcome: 'saved', error: null, phase: 'ready' });
  setFields({ action: null, password: '', ack: false });
  if (mfaChangeRequiresReauthentication(receipt, recovered)) {
   onReauthenticate?.({ reason: 'mfa_changed', action: draft.action, userId: draft.userId });
   return;
  }
  await loadStatus(null);
  try { await onChanged?.(receipt); }
  catch { patch({ error: 'error' }); } // A parent refresh failure cannot erase a confirmed commit.
 }
 async function run(kind) {
  if (!current() || requestLock.current || !view.ready) return;
  const checking = kind === 'check', previousUnconfirmed = !!pending;
  if (!checking && effectiveAdmin && selected === actor) { patch({ error: 'selfService' }); return; }
  if (!checking && (!effectiveAction || !currentForm.ack || (!effectiveAdmin && !currentForm.password))) return;
  if (!checking && !pending && (!view.status || !view.status.available || !view.status['can' + effectiveAction[0].toUpperCase() + effectiveAction.slice(1)])) return;
  if (checking && !pending) return;
  const draft = pending || Object.freeze({ actorId: actor, userId: selected, action: effectiveAction, revision: view.status.revision, requestId: crypto.randomUUID(), scope: effectiveAdmin ? 'admin' : 'self' });
  const password = currentForm.password;
  let journalReady = !!pending;
  requestLock.current = scope; readSequence.current++;
  patch({ phase: 'working', error: null, outcome: null });
  setFields({ password: '' });
  try {
   if (!pending) await mfaAccountJournal('write', actor, draft);
   journalReady = true;
   if (!current()) return;
   patch({ pending: draft });
   const receipt = checking ? await mfaAccountChangeStatus(api, draft) : await changeMfaAccount(api, draft, password);
   if (!current()) return;
   if (receipt) await finish(receipt, draft, checking || previousUnconfirmed);
   else patch({ phase: 'ready', outcome: 'notRecorded', pending: draft });
  } catch (error) {
   if (!current()) return;
   if (!journalReady) { patch({ pending: null, ready: false, error: 'storage', phase: 'ready' }); return; }
   const unconfirmed = previousUnconfirmed || error.uncertain === true || error.status === 0;
   if (!unconfirmed && !checking) {
    try { await mfaAccountJournal('remove', actor, draft); }
    catch { patch({ pending: draft, error: 'storage', phase: 'ready' }); return; }
    patch({ pending: null, status: null, error: mfaAccountError(error), phase: 'ready' });
   } else patch({ pending: draft, error: mfaAccountError(error), phase: 'ready' });
  } finally {
   if (requestLock.current === scope) requestLock.current = null;
   if (current()) setView(old => old.scope === scope && old.phase === 'working' ? { ...old, phase: 'ready' } : old);
  }
 }
 function choose(action) {
  if (busy || pending) return;
  setFields({ action, password: '', ack: false });
  patch({ error: null, outcome: null });
 }

 return <section className="rc-group-creation rc-mfa-account" data-mfa-account={admin ? 'admin' : 'self'} aria-labelledby={formId + '-title'}>
  <h2 id={formId + '-title'}>{effectiveAdmin ? w.adminTitle : w.selfTitle}</h2>
  <h3>{w.title}</h3>
  {view.status && <><p data-mfa-account-target={view.status.userId}>{w.user}: <strong>{view.status.userName}</strong></p><p data-mfa-factor-state={view.status.factorState}>{statusText(view.status, w)} · {view.status.required ? w.required : w.optional}</p><p role="status" data-mfa-grace-notice>{noticeText(view.status, w)}</p>{view.status.deadlineUtc && <p>{w.serverDate}: <time dateTime={view.status.deadlineUtc}>{new Date(view.status.deadlineUtc).toLocaleDateString(lang === 'de' ? 'de-DE' : lang === 'es' ? 'es-ES' : 'en-GB', { timeZone: 'UTC' })}</time></p>}{view.status.globalAdministratorExempt && mfaAccountNotice(view.status) !== 'exempt' && <p className="rc-muted">{w.exempt}</p>}</>}
  {!selected && !pending && <p>{w.choose}</p>}
  <p className="rc-muted">{effectiveAdmin ? w.adminHelp : w.selfHelp}</p>
  {effectiveAdmin && view.status && !view.status.sessionMfaVerified && <p className="ir-warning" data-mfa-admin-verification-required>{w.verifyAdmin}</p>}
  {effectiveAdmin && selected === actor && <p className="ir-warning" data-mfa-self-service-required>{w.selfService}</p>}
  {busy && <p role="status">{view.phase === 'working' ? w.working : w.loading}</p>}
  {view.error && <p className="rc-error" role="alert" data-mfa-account-error>{w[view.error] || w.error}</p>}
  {view.outcome && <p role="status" data-mfa-account-result={view.outcome}>{w[view.outcome]}</p>}
  {pending && <div className="ir-warning" data-mfa-account-pending><p>{w.pendingRequest}</p><p>{w.recoverTarget}: <strong>{pending.userId}</strong> · {w[pending.action]}</p><p>{w.requestId}: {pending.requestId}</p><button type="button" disabled={busy} data-mfa-account-check onClick={() => run('check')}>{w.check}</button></div>}
  <div className="rc-inline-buttons"><button type="button" disabled={busy || recoveryDirty || !!pending} data-mfa-account-refresh onClick={() => view.ready ? loadStatus(null) : initialize()}>{w.refresh}</button>{!pending && ['enable', 'disable', 'reset'].map(action => <button type="button" data-mfa-action={action} key={action} disabled={busy || recoveryDirty || !view.ready || !view.status?.available || (effectiveAdmin && selected === actor) || !view.status?.['can' + action[0].toUpperCase() + action.slice(1)]} onClick={() => choose(action)}>{w[action]}</button>)}</div>
  {effectiveAction && <form className="rc-form" data-mfa-account-confirm onSubmit={event => { event.preventDefault(); run('save'); }}>
   <p>{w[effectiveAction + 'Help']}</p>
   {!effectiveAdmin && <label htmlFor={formId + '-password'}>{w.password}<input id={formId + '-password'} name="mfaAccountPassword" data-mfa-password type="password" autoComplete="current-password" maxLength={1024} required disabled={busy} value={currentForm.password} onChange={event => setFields({ password: event.target.value })}/></label>}
   <label htmlFor={formId + '-ack'}><input id={formId + '-ack'} data-mfa-ack type="checkbox" checked={currentForm.ack} disabled={busy} onChange={event => setFields({ ack: event.target.checked })}/>{w.confirm}</label>
   <div className="rc-inline-buttons"><button type="submit" data-mfa-account-save disabled={busy || !currentForm.ack || (!pending && !view.status) || (effectiveAdmin && selected === actor) || (!effectiveAdmin && !currentForm.password)}>{pending ? w.retry : w.save}</button>{!pending && <button type="button" disabled={busy} onClick={() => setFields({ action: null, password: '', ack: false })}>{w.cancelForm}</button>}</div>
  </form>}
  {(pending || view.error === 'expired') && <p>{w.signInHelp} <button type="button" disabled={busy} data-mfa-account-reauthenticate onClick={() => onReauthenticate?.({ reason: 'mfa_recovery', userId: actor })}>{w.reauthenticate}</button></p>}
  {!admin && view.status && !pending && !currentForm.action && <MfaRecoveryCodesPanel api={api} session={session} lang={lang} onDirtyChange={setRecoveryDirty} onReauthenticate={onReauthenticate}/>}
 </section>;
}

// Compact server-derived reminder: no client-side deadline/security calculation and no secret material.
export function MfaReminder({ api, session, lang = 'en', onManage }) {
 const w = mfaAccountWords[lang] || mfaAccountWords.en, actor = session.user.id;
 const scopeRef = useRef(null), [view, setView] = useState(null);
 if (!scopeRef.current || scopeRef.current.api !== api || scopeRef.current.actor !== actor) scopeRef.current = { api, actor, live: false };
 const scope = scopeRef.current;
 useEffect(() => {
  scope.live = true; let busy = false, sequence = 0;
  async function load() {
   if (busy || !scope.live || api.actorId !== actor) return;
   busy = true; const current = ++sequence;
   try {
    const status = await readMfaAccount(api);
    if (scopeRef.current === scope && scope.live && sequence === current && api.actorId === actor) setView({ scope, status });
   } catch {
    if (scopeRef.current === scope && scope.live && sequence === current) setView(null);
   } finally { busy = false; }
  }
  load(); const timer = setInterval(load, 60000);
  const visible = () => { if (!document.hidden) load(); };
  window.addEventListener('focus', load); document.addEventListener('visibilitychange', visible);
  return () => { scope.live = false; sequence++; clearInterval(timer); window.removeEventListener('focus', load); document.removeEventListener('visibilitychange', visible); };
 }, [scope]);
 if (view?.scope !== scope || !view.status) return null;
 const status = view.status;
 const notice = mfaAccountNotice(status);
 return <aside className={notice === 'deadline' || notice === 'pending' ? 'ir-warning rc-mfa-reminder' : 'rc-muted rc-mfa-reminder'} data-mfa-reminder role="status"><span>{noticeText(status, w)}</span> <button type="button" data-mfa-open-security onClick={onManage}>{w.manage}</button></aside>;
}
