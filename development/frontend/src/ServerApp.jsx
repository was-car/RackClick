import { RackClickApi, ApiError, allows, mutationRemainsUnconfirmed } from './api.ts';
import MfaChallengeForm from './MfaChallengeForm.jsx';
import { words } from './words.ts';
import { IRIcon } from '../generated/rc9.jsx';
import { AdminUsers, adminWords } from './AdminUsers.jsx';
import { MfaAccountPanel, MfaReminder } from './MfaAccountPanel.jsx';
import { mfaAccountWords } from './mfa-account-words.ts';
import { AdminAudit, auditWords } from './AdminAudit.jsx';
import { InventoryPanel } from './InventoryPanel.jsx';
import { pendingJournal, pendingRecord } from './pending-journal.ts';
import { inventoryWords } from './inventory-words.ts';
import { useUserPreferences, UserPreferenceStatus } from './UserPreferences.jsx';
import { useUserPortColors } from './UserPortColors.jsx';
import { useUserCategoryColors, PersonalPalette } from './UserCategoryColors.jsx';
import { userPortColorsWords } from './user-port-colors-words.ts';
const { useState, useEffect, useRef } = React;
const api = new RackClickApi();
function MfaDialog({ pending, lang, onComplete, onCancel }) {
 const dialog = useRef(null);
 const [dialogLang, setDialogLang] = useState(lang);
 useEffect(() => { dialog.current?.showModal(); }, []);
 return <dialog ref={dialog} lang={dialogLang} className="ir-dialog rc-mfa-dialog" aria-labelledby={'rc-mfa-title-' + pending.challenge.generation} onCancel={event => event.preventDefault()}><div className="rc-settings"><Language lang={dialogLang} onLanguage={setDialogLang}/></div><MfaChallengeForm api={api} challenge={pending.challenge} lang={dialogLang} onComplete={onComplete} onCancel={onCancel}/></dialog>;
}
function Language({ lang, onLanguage, disabled }) {
 return <select aria-label={words[lang].language} disabled={disabled} value={lang} onChange={e => onLanguage(e.target.value)}><option value="en">English</option><option value="de">Deutsch</option><option value="es">Español</option></select>;
}
function Settings({ lang, setLang, theme, setTheme, disabled, onPalette }) {
 const w = words[lang];
 return <div className="rc-settings"><Language lang={lang} disabled={disabled} onLanguage={setLang}/><button type="button" aria-label={w.theme} disabled={disabled} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? w.light : w.dark}</button>{onPalette && <button type="button" data-port-colors-open onClick={onPalette}>{userPortColorsWords[lang].open}</button>}</div>;
}

// RC9 IRClientNavigation: original structure/classes/icons, server IDs and authorized commands.
function IRClientNavigation({ customers, customerId, onClient, onHome, systemhaus, onRename, canRename, onLogout, session, lang, inventoryNavigation, onAdmin, onAudit, canAdmin, onSecurity }) {
 const w = words[lang], [open, setOpen] = useState(false);
 return <><button className="ir-mobile-nav" onClick={() => setOpen(!open)} aria-label={w.infrastructure}><IRIcon name="menu"/>RackClick</button><aside className={'ir-nav ' + (open ? 'open' : '')}><a href="#" className="ir-brand" onClick={e => { e.preventDefault(); onHome(); setOpen(false); }}><IRIcon name="rack"/><b>Rack<span>Click</span></b></a><div className="ir-eyebrow">SYSTEMHAUS</div><button className="ir-org" aria-label={w.house} onClick={onRename} disabled={!canRename}><strong>{systemhaus}</strong>{canRename && <IRIcon name="edit"/>}</button><div className="ir-eyebrow">{w.infrastructure}</div><button className="ir-all-clients" onClick={() => { onHome(); setOpen(false); }}>{w.allClients}</button><div className="ir-client-tree">{customers.map(customer => <div key={customer.id}><button className={'ir-client-link ' + (customerId === customer.id ? 'active' : '')} onClick={() => { onClient(customer.id); setOpen(false); }}><IRIcon name="home"/>{customer.name}</button>{customerId === customer.id && inventoryNavigation?.customerId === customer.id && <div className="ir-racks">{inventoryNavigation.racks.map(r => <button key={r.id} className={inventoryNavigation.activeRackId === r.id ? "active" : ""} onClick={() => { inventoryNavigation.onRack(r.id); setOpen(false); }}><IRIcon name="rack"/><span>{r.name}<small>{r.path}</small></span></button>)}</div>}</div>)}</div>{canAdmin && <button className="ir-settings" data-admin-users onClick={() => { onAdmin(); setOpen(false); }}>{adminWords[lang].title}</button>}{canAdmin && <button className="ir-settings" data-audit-navigation onClick={() => { onAudit(); setOpen(false); }}>{auditWords[lang].title}</button>}<div className="rc-session"><small>{w.identity}</small><p>{session.user.userName}</p></div><button className="ir-settings" data-mfa-settings-open onClick={onSecurity}><IRIcon name="user"/>{mfaAccountWords[lang].selfTitle}</button><button className="ir-settings" onClick={onLogout}><IRIcon name="user"/>{w.signOut}</button><div className="ir-nav-foot">{w.version}</div></aside></>;
}
// RC9 IRClientsHome: same cards/header/action layout. No invented rack counts or offline writes.
function IRClientsHome({ customers, onClient, onCreate, canCreate, lang, setLang, theme, setTheme, onRefresh, busy, status, preferences, onPalette }) {
 const w = words[lang];
 return <main className="ir-clients-home"><header><div><div className="ir-eyebrow">SYSTEMHAUS / {w.infrastructure}</div><h1>{w.clients}</h1><p>{w.connected}</p></div><Settings lang={lang} setLang={setLang} theme={theme} setTheme={setTheme} disabled={preferences.disabled} onPalette={onPalette}/></header><UserPreferenceStatus state={preferences} lang={lang}/><div className="ir-home-actions">{canCreate && <button onClick={onCreate} disabled={busy}>{w.create}</button>}<button onClick={onRefresh} disabled={busy}>{w.refresh}</button><span role="status" className="rc-status">{busy ? w.loading : status}</span></div><div className="ir-client-cards">{customers.map(customer => <button className="ir-client-card" key={customer.id} data-customer-id={customer.id} onClick={() => onClient(customer.id)}><div className="ir-client-card-icon"><IRIcon name="home" size={26}/></div><h2>{customer.name}</h2><p>{w.client}</p><span>{w.detail} →</span></button>)}</div>{!customers.length && !busy && <p>{w.empty}</p>}</main>;
}
function errorText(error, w) {
 if (error.code === 'draft_storage_unavailable') return inventoryWords[document.documentElement.lang || 'en'].storageError;
 if (error.uncertain) return w.offline;
 if (error.code === 'actor_changed') return w.expired;
 if (error.status === 412) return w.conflict;
 if (error.status === 401) return error.code === 'credentials_invalid' || error.code === 'login_invalid' ? w.credentials : w.expired;
 if (error.status === 429) return w.limited;
 if (error.status === 403 || error.status === 404) return w.denied;
 if (error.status === 422) return w.invalid;
 if (error.status === 0 || error.status >= 500) return w.unavailable;
 return w.error;
}
function NameDialog({ draft, setDraft, onClose, onCommitted, reload, lang, onPendingChange }) {
 const w = words[lang], iw = inventoryWords[lang], [busy, setBusy] = useState(false), [error, setError] = useState(null), [operation, setOperation] = useState(draft.operation || null), [conflict, setConflict] = useState(false), [unconfirmed, setUnconfirmed] = useState(!!draft.operation), [reauthPassword, setReauthPassword] = useState('');
 const dialog = useRef(null), input = useRef(null);
 useEffect(() => { dialog.current.showModal(); input.current.focus(); return () => { dialog.current?.close(); }; }, []);
 useEffect(() => { const protect = e => { e.preventDefault(); e.returnValue = ''; }; window.addEventListener('beforeunload', protect); return () => window.removeEventListener('beforeunload', protect); }, []);
 async function submit(event) {
  event.preventDefault(); if (busy || conflict) return;
  if ((error?.status === 401 || error?.code === 'actor_changed') && reauthPassword) { await reauthenticate(); return; }
  setBusy(true); setError(null);
  const current = operation || api.prepare(draft.kind, draft.name, draft.revision, draft.id, draft.actorId);
  let confirmed = false;
  try {
   if (!operation) { await pendingJournal.put(pendingRecord(current, draft.kind, draft.name)); setOperation(current); await onPendingChange(); }
   const result = await api.execute(current); confirmed = true;
   try { await pendingJournal.remove(current.requestId, current.actorId); } catch {}
   await onPendingChange(); onCommitted(result, draft.kind);
  }
  catch (e) { if (confirmed) { onClose(); return; } setError(e); const pending = mutationRemainsUnconfirmed(unconfirmed, e); setUnconfirmed(pending); if (!pending) { try { await pendingJournal.remove(current.requestId, current.actorId); } catch {} setOperation(null); await onPendingChange(); } if (e.status === 412 && !pending) setConflict(true); }
  finally { setBusy(false); }
 }
 async function reauthenticate() {
  setBusy(true);
  try { const identity = await api.login(draft.userName, reauthPassword); setReauthPassword(''); if (identity.user.id !== draft.actorId) { try { await api.logout(); } catch {} finally { api.csrf = ''; api.actorId = ''; } throw { status: 409, code: 'actor_changed' }; } setError(null); }
  catch (e) { setError(e.status === 401 ? { ...e, code: 'credentials_invalid' } : e); }
  finally { setBusy(false); }
 }
 async function rebase() {
  setBusy(true);
  try { const snapshot = await reload(); const value = draft.kind === 'customer' ? snapshot.customers.find(c => c.id === draft.id) : snapshot.house; if (!value) throw { status: 403 }; setDraft({ ...draft, revision: value.revision, currentName: draft.kind === 'create' ? '' : value.name }); setConflict(false); setError(null); setOperation(null); }
  catch (e) { setError(e); }
  finally { setBusy(false); }
 }
 const locked = busy || !!operation;
 return <dialog ref={dialog} className="ir-dialog" aria-labelledby="name-title" onCancel={e => { e.preventDefault(); if (!busy) onClose(); }}><form className="rc-form" onSubmit={submit}><div className="rc-dialog-title"><h2 id="name-title">{draft.kind === 'house' ? w.house : draft.kind === 'create' ? w.create : w.rename}</h2></div>{draft.currentName && <p>{w.current}: {draft.currentName}</p>}<label>{w.name}<input ref={input} name="name" required autoComplete="off" value={draft.name} disabled={locked} onChange={e => { setDraft({ ...draft, name: e.target.value }); setError(null); }}/></label><small className="rc-muted">{operation ? iw.pendingHelp : w.draft}</small>{error && <div role="alert" className="rc-error">{errorText(error, w)}</div>}{unconfirmed && !error?.uncertain && <p>{w.offline}</p>}{(error?.status === 401 || error?.code === 'actor_changed') && <div className="rc-form"><p>{w.identity}: {draft.userName}</p><label>{w.password}<input type="password" autoComplete="current-password" value={reauthPassword} onChange={e => setReauthPassword(e.target.value)}/></label><button type="button" onClick={reauthenticate} disabled={busy || !reauthPassword}>{w.signIn}</button></div>}<footer>{conflict && <button type="button" onClick={rebase} disabled={busy}>{w.reload}</button>}<button type="button" onClick={onClose} disabled={busy}>{operation ? iw.close : w.cancel}</button><button type="submit" disabled={busy || conflict || !draft.name.trim()}>{busy ? w.saving : operation ? w.retry : w.save}</button></footer></form></dialog>;
}
function ServerApp() {
 const [session, setSession] = useState(null), [house, setHouse] = useState(null), [customers, setCustomers] = useState([]), [activeId, setActiveId] = useState(null);
 const [loading, setLoading] = useState(true), [status, setStatus] = useState('loaded'), [error, setError] = useState(null), [draft, setDraft] = useState(null);
 const [username, setUsername] = useState(''), [password, setPassword] = useState('');
 const [adminPage, setAdminPage] = useState(null), [paletteOpen,setPaletteOpen]=useState(false);
 const [authClosing,setAuthClosing]=useState(false);
 const [mfaPending,setMfaPending]=useState(null);
 const mfaPendingRef = useRef(null);
 const [inventoryNavigation, setInventoryNavigation] = useState(null);
 const [foundationPending, setFoundationPending] = useState([]), [journalReady, setJournalReady] = useState(false);
 const authEpoch = useRef(0);
 const preferences = useUserPreferences({ api, actorId: session?.user.id, userName: session?.user.userName, generation: authEpoch.current, suspended: authClosing, onAuthenticationInvalidated: forget });
 const portColors = useUserPortColors({ api, actorId: session?.user.id, userName: session?.user.userName, generation: authEpoch.current, suspended: authClosing, onAuthenticationInvalidated: forget });
 const categoryColors = useUserCategoryColors({ api, actorId: session?.user.id, userName: session?.user.userName, generation: authEpoch.current, suspended: authClosing, onAuthenticationInvalidated: forget });
 const { lang, theme, chooseLanguage: setLang, chooseTheme: setTheme } = preferences;
 const w = words[lang], active = customers.find(c => c.id === activeId);
 useEffect(() => { document.documentElement.lang = lang; document.documentElement.dataset.rcTheme = theme; }, [lang, theme]);
 useEffect(() => {
  api.onMfaRequired = challenge => new Promise((resolve, reject) => {
   mfaPendingRef.current?.reject(new ApiError(409, 'authentication_changed'));
   const pending = { challenge, resolve, reject };
   mfaPendingRef.current = pending; setMfaPending(pending);
  });
  return () => { api.onMfaRequired = null; api.cancelAuthentication(); mfaPendingRef.current?.reject(new ApiError(401, 'mfa_cancelled')); mfaPendingRef.current = null; };
 }, []);
 function completeMfa(identity) {
  const pending = mfaPendingRef.current;
  if (!pending || pending !== mfaPending) return;
  mfaPendingRef.current = null; setMfaPending(null); pending.resolve(identity);
 }
 function cancelMfa() {
  const pending = mfaPendingRef.current;
  mfaPendingRef.current = null; setMfaPending(null); api.cancelAuthentication();
  pending?.reject(new ApiError(401, 'mfa_cancelled')); forget(); setError(null);
 }
 function forget() { setPaletteOpen(false); setAdminPage(null); authEpoch.current++; setSession(null); setHouse(null); setCustomers([]); setActiveId(null); setDraft(null); setFoundationPending([]); setJournalReady(false); api.csrf = ''; api.actorId = ''; }
 async function refreshJournal(actorId = session?.user.id) {
  const epoch = authEpoch.current;
  try { const items = await pendingJournal.list(actorId); if (epoch === authEpoch.current) { setFoundationPending(items.filter(item => !item.customerId)); setJournalReady(true); } }
  catch (e) { if (epoch === authEpoch.current) { setJournalReady(false); setError(e); } }
 }
 async function reload() {
  const epoch = authEpoch.current;
  const identity = await api.me();
  const [nextHouse, nextCustomers] = await Promise.all([allows(identity, 'systemhaus.read') ? api.house() : Promise.resolve(null), api.customers()]);
  if (epoch === authEpoch.current) { setSession(identity); setHouse(nextHouse); setCustomers(nextCustomers); setActiveId(id => nextCustomers.some(c => c.id === id) ? id : null); await refreshJournal(identity.user.id); }
  return { house: nextHouse, customers: nextCustomers };
 }
 async function refresh() { setLoading(true); setError(null); try { await reload(); setStatus('loaded'); } catch (e) { setError(e); if (e.status === 401) forget(); } finally { setLoading(false); } }
 useEffect(() => { refresh(); }, []);
 async function login(e) {
  e.preventDefault(); setLoading(true); setError(null);
  const enteredPassword = password; setPassword('');
  try { await api.login(username, enteredPassword); await reload(); setStatus('loaded'); }
  catch (e) { if (e.code !== 'mfa_cancelled' && e.code !== 'authentication_changed') setError(e.status === 401 ? { ...e, code: 'credentials_invalid' } : e); }
  finally { setLoading(false); }
 }
 function reauthenticateMfa() { const name=session?.user.userName||''; api.cancelAuthentication(); forget(); setUsername(name); setPassword(''); setError(null); setLoading(false); }
 async function logout() { authEpoch.current++; setAuthClosing(true); setLoading(true); setError(null); try { await api.logout(); forget(); } catch (e) { if (e.status === 401) forget(); else setError(e); } finally { setAuthClosing(false); setLoading(false); } }
 const inventoryDataEpoch = authEpoch.current;
 async function inventoryChanged(result) {
  const expectedActor = session?.user.id;
  const current = () => inventoryDataEpoch === authEpoch.current && !!expectedActor && api.actorId === expectedActor;
  if (!current() || result?.kind !== 'inventoryData' || !['demo50','restore'].includes(result.action)) return;
  try {
   const identity = await api.me();
   if (!current() || identity.user.id !== expectedActor) return;
   const [nextHouse, nextCustomers] = await Promise.all([allows(identity, 'systemhaus.read') ? api.house() : Promise.resolve(null), api.customers()]);
   if (!current()) return;
   // Effective customer grants must include the imported customer IDs.
   setSession(identity); setHouse(nextHouse); setCustomers(nextCustomers); setActiveId(id => nextCustomers.some(c => c.id === id) ? id : null); setStatus('saved'); setError(null);
  } catch (e) { if (current()) { setError(e); if (e.status === 401) forget(); } }
 }
 function committed(result, kind) {
  // The response is produced after the API transaction commits. Only now replace visible shared data.
  if (kind === 'house') setHouse(result.resource);
  else { setCustomers(previous => kind === 'create' ? [...previous, result.resource] : previous.map(c => c.id === result.resource.id ? result.resource : c)); setHouse(previous => previous ? { ...previous, revision: result.systemhausRevision } : null); }
  setDraft(null); setStatus('saved'); setError(null);
  // Refresh effective permissions after creation; a later read failure cannot erase the confirmed result.
  const epoch = authEpoch.current;
  api.me().then(identity => { if (epoch === authEpoch.current) setSession(identity); }).catch(e => { if (epoch !== authEpoch.current) return; if (e.status === 401) forget(); else setError(e); });
 }
 const actor = { actorId: session?.user.id, userName: session?.user.userName };
 const openHouse = () => setDraft({ ...actor, kind: 'house', name: house.name, currentName: house.name, revision: house.revision });
 const openCreate = () => setDraft({ ...actor, kind: 'create', name: '', revision: house.revision });
 const openCustomer = () => setDraft({ ...actor, kind: 'customer', id: active.id, name: active.name, currentName: active.name, revision: active.revision });
 const recoverName = record => { const op = record.operation, kind = op.path === '/systemhaus' ? 'house' : op.method === 'POST' ? 'create' : 'customer'; setDraft({ ...actor, kind, id: kind === 'customer' ? op.path.split('/').pop() : undefined, name: JSON.parse(op.body).name, revision: Number(op.etag.slice(1,-1)), operation: op }); };
 const foundationBlocked = !journalReady || foundationPending.length > 0;
 const mfaDialog = mfaPending && <MfaDialog key={mfaPending.challenge.generation} pending={mfaPending} lang={lang} onComplete={completeMfa} onCancel={cancelMfa}/>;
 if (!session) return <><main className="rc-login ir-dialog"><div className="ir-brand"><IRIcon name="rack" size={26}/><b>Rack<span>Click</span></b></div><div className="ir-eyebrow">{w.version}</div><Settings lang={lang} setLang={setLang} theme={theme} setTheme={setTheme}/><h1>{w.signIn}</h1>{!mfaPending && <form className="rc-form" onSubmit={login}><label>{w.username}<input name="username" autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)}/></label><label>{w.password}<input name="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)}/></label>{error && error.code !== 'authentication_required' && <div role="alert" className="rc-error">{errorText(error, w)}</div>}<button type="submit" disabled={loading}>{loading ? w.loading : w.signIn}</button></form>}</main>{mfaDialog}</>;
 return <><div className="rc-app ir-app"><IRClientNavigation customers={customers} customerId={activeId} onClient={id => { setAdminPage(null); setActiveId(id); }} onHome={() => { setAdminPage(null); setActiveId(null); }} systemhaus={house?.name || 'Systemhaus'} onRename={openHouse} canRename={!foundationBlocked && !!house && allows(session, 'systemhaus.manage')} onLogout={logout} session={session} lang={lang} inventoryNavigation={inventoryNavigation} canAdmin={allows(session, 'security.manage')} onAdmin={() => { setActiveId(null); setAdminPage('users'); }} onAudit={() => { setActiveId(null); setAdminPage('audit'); }} onSecurity={() => { setActiveId(null); setAdminPage('security'); }}/><div className="ir-breadcrumb">{house?.name || 'Systemhaus'}<span>›</span><button className="ir-crumb-home" onClick={() => { setAdminPage(null); setActiveId(null); }}>{w.infrastructure}</button>{active && <><span>›</span>{active.name}</>}<small>Server · 0.1.0-alpha1</small></div>{error && <div role="alert" className="rc-error">{errorText(error, w)}</div>}{foundationPending.map(record => <div className="ir-warning rc-foundation-pending" key={record.requestId}><strong>{inventoryWords[lang].pending}</strong><p>{record.summary}</p><p>{inventoryWords[lang].pendingHelp}</p><button onClick={() => recoverName(record)}>{inventoryWords[lang].recover}</button></div>)}<MfaReminder key={session.user.id} api={api} session={session} lang={lang} onManage={() => { setActiveId(null); setAdminPage('security'); }}/>{adminPage === 'security' ? <main className="ir-clients-home rc-mfa-security-page"><header><h1>{mfaAccountWords[lang].selfTitle}</h1><Language lang={lang} disabled={preferences.disabled} onLanguage={setLang}/><button onClick={() => { setAdminPage(null); refresh(); }}>{adminWords[lang].home}</button></header><UserPreferenceStatus state={preferences} lang={lang}/><MfaAccountPanel key={session.user.id} api={api} session={session} lang={lang} onReauthenticate={reauthenticateMfa}/></main> : adminPage === 'audit' && allows(session, 'security.manage') ? <main className="ir-clients-home rc-admin-audit-page"><header><h1>{auditWords[lang].title}</h1><button onClick={() => { setAdminPage(null); refresh(); }}>{adminWords[lang].home}</button></header><AdminAudit key={session.user.id} api={api} actor={session.user.id} lang={lang}/></main> : adminPage === 'users' && allows(session, 'security.manage') ? <AdminUsers api={api} session={session} lang={lang} onInventoryChanged={inventoryChanged} onReauthenticate={reauthenticateMfa} onHome={() => { setAdminPage(null); refresh(); }}/> : !active ? <IRClientsHome customers={customers} onClient={id => { setAdminPage(null); setActiveId(id); }} onCreate={openCreate} canCreate={!foundationBlocked && !!house && allows(session, 'customer.create')} lang={lang} setLang={setLang} theme={theme} setTheme={setTheme} onRefresh={refresh} busy={loading} status={w[status]} preferences={preferences} onPalette={() => setPaletteOpen(true)}/> : <main className="rc-client-section"><div className="rc-detail rc-customer-header"><div className="ir-client-card-icon"><IRIcon name="home" size={26}/></div><h1>{active.name}</h1><dl><dt>{w.client}</dt><dd>{active.name}</dd></dl><div className="rc-inline-buttons">{allows(session, 'customer.manage', active.id) && <button disabled={foundationBlocked || inventoryNavigation?.blocked} onClick={openCustomer}>{w.rename}</button>}<button onClick={refresh} disabled={loading}>{w.refresh}</button><button onClick={() => setActiveId(null)}>{w.allClients}</button></div><p role="status">{loading ? w.loading : w[status]}</p></div><InventoryPanel ptColors={portColors.colors} pollSuspended={authClosing || !!mfaPending} key={session.user.id+':'+active.id} api={api} session={session} customer={active} lang={lang} onNavigation={setInventoryNavigation} onRevision={revision => setCustomers(previous => previous.map(c => c.id === active.id && c.revision !== revision ? { ...c, revision } : c))}/></main>}{paletteOpen && <PersonalPalette key={session.user.id} portState={portColors} categoryState={categoryColors} lang={lang} onClose={() => setPaletteOpen(false)}/>}{draft && <NameDialog draft={draft} setDraft={setDraft} onClose={() => setDraft(null)} onCommitted={committed} reload={reload} lang={lang} onPendingChange={refreshJournal}/>}</div>{mfaDialog}</>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<ServerApp/>);
