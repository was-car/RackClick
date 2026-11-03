import { mfaWords, mfaErrorState } from './mfa-words.ts';
import { makeQrModules } from './mfa-qr.ts';
import { recoveryCodeFormat } from './mfa-recovery.ts';
import { mfaRecoveryWords } from './mfa-recovery-words.ts';
const { useState, useRef, useEffect, useMemo } = React;

// Research 27.10.2026: MDN autocomplete (one-time-code) and Microsoft MFA/TOTP guidance.
// https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/autocomplete
// https://learn.microsoft.com/en-us/aspnet/core/security/authentication/mfa?view=aspnetcore-10.0
// Reuse the RC9 login classes and existing server challenge flow. No external QR request, storage or automatic enrollment.
function AuthenticatorQr({ otpauth, label, unavailable }) {
 const modules = useMemo(() => {
  try {
   const next = makeQrModules(otpauth);
   return Array.isArray(next) && next.length > 0 && next.length <= 177 && next.every(row => Array.isArray(row) && row.length === next.length && row.every(value => typeof value === 'boolean')) ? next : null;
  } catch { return null; }
 }, [otpauth]);
 if (!modules) return <p className="rc-muted" role="status">{unavailable}</p>;
 const size = modules.length + 8;
 return <svg data-mfa-qr className="rc-mfa-qr" role="img" aria-label={label} viewBox={`0 0 ${size} ${size}`} width="224" height="224" shapeRendering="crispEdges" focusable="false"><rect width={size} height={size} fill="#fff"/>{modules.flatMap((row, y) => row.map((dark, x) => dark ? <rect key={`${x}:${y}`} x={x + 4} y={y + 4} width="1" height="1" fill="#000"/> : null))}</svg>;
}

export default function MfaChallengeForm({ api, challenge, lang, onComplete, onCancel }) {
 const w = mfaWords[lang] || mfaWords.en;
 const rw = mfaRecoveryWords[lang] || mfaRecoveryWords.en;
 const enroll = challenge.purpose === 'enroll';
 const [enrollment, setEnrollment] = useState(null), [code, setCode] = useState('');
 const [busy, setBusy] = useState(false), [started, setStarted] = useState(false), [problem, setProblem] = useState(null);
 const [restart, setRestart] = useState(false);
 const [recoveryMode,setRecoveryMode]=useState(false),[replacement,setReplacement]=useState(null);
 const [boundChallenge, setBoundChallenge] = useState(challenge);
 const live = useRef(false), epoch = useRef(0), inFlight = useRef(false), startAttempted = useRef(false);
 const currentChallenge = useRef(challenge), latestChallenge = useRef(challenge), codeInput = useRef(null), startButton = useRef(null);
 latestChallenge.current = challenge;
 const titleId = 'rc-mfa-title-' + challenge.generation, helpId = 'rc-mfa-help-' + challenge.generation;
 const sameChallenge = boundChallenge === challenge;

 useEffect(() => {
  currentChallenge.current = challenge; latestChallenge.current = challenge; live.current = true; epoch.current++;
  setBoundChallenge(challenge);
  inFlight.current = false; startAttempted.current = false;
  setEnrollment(null); setCode(''); setBusy(false); setStarted(false); setProblem(null); setRestart(false);setRecoveryMode(false);setReplacement(null);
  (challenge.purpose === 'enroll' ? startButton.current : codeInput.current)?.focus();
  return () => { live.current = false; epoch.current++; currentChallenge.current = null; latestChallenge.current = null; };
 }, [challenge]);
 useEffect(() => { if (enrollment && sameChallenge) codeInput.current?.focus(); }, [enrollment, sameChallenge]);

 function stillCurrent(attempt) { return live.current && epoch.current === attempt && currentChallenge.current === challenge && latestChallenge.current === challenge; }
 function clear() { setEnrollment(null); setCode(''); setProblem(null); }
 function fail(error, starting) {
  const next = mfaErrorState(error, starting);
  setProblem(next.key); setRestart(next.restart); setCode('');
  if (next.restart) setEnrollment(null);
 }
 async function beginEnrollment() {
  if (inFlight.current || startAttempted.current || !sameChallenge || restart) return;
  startAttempted.current = true; inFlight.current = true;
  setStarted(true); setBusy(true); setProblem(null);
  const attempt = epoch.current;
  try {
   const value = await api.startMfaEnrollment(challenge);
   if (!stillCurrent(attempt)) return;
   if (typeof value?.secret !== 'string' || !value.secret || typeof value?.otpauth !== 'string' || !value.otpauth) throw { code: 'response_invalid' };
   setEnrollment({ secret: value.secret, otpauth: value.otpauth });
  } catch (error) { if (stillCurrent(attempt)) fail(error, true); }
  finally { if (stillCurrent(attempt)) { inFlight.current = false; setBusy(false); } }
 }
 async function submit(event) {
  event.preventDefault();
  if (inFlight.current || !sameChallenge || restart || (enroll && !enrollment)) return;
  if (recoveryMode ? !recoveryCodeFormat(code) : !/^[0-9]{6}$/.test(code)) { setProblem(recoveryMode?'recoveryFormat':'codeFormat'); codeInput.current?.focus(); return; }
  inFlight.current = true; setBusy(true); setProblem(null);
  const attempt = epoch.current;
  let session;
  try {
   if (recoveryMode) {
    const next=await api.recoverMfa(challenge,code);
    if(stillCurrent(attempt)){clear();setReplacement(next);}
    return;
   }
   session = await (enroll ? api.confirmMfaEnrollment(challenge, code) : api.verifyMfa(challenge, code));
  } catch (error) {
   if (stillCurrent(attempt)) fail(error, false);
   return;
  } finally { if (stillCurrent(attempt)) { inFlight.current = false; setBusy(false); } }
  if (!stillCurrent(attempt)) return;
  clear();
  onComplete(session);
 }
 function cancel() {
  if (inFlight.current) return;
  epoch.current++; clear(); setRestart(true);
  onCancel();
 }

 const visibleEnrollment = sameChallenge && !restart ? enrollment : null;
 const ready = sameChallenge && !restart && (!enroll || !!visibleEnrollment);
 if(replacement&&sameChallenge)return <MfaChallengeForm api={api} challenge={replacement} lang={lang} onComplete={onComplete} onCancel={onCancel}/>;
 return <section data-mfa-challenge data-mfa-purpose={challenge.purpose} className="rc-mfa-challenge" aria-labelledby={titleId}>
  <h2 id={titleId}>{enroll ? w.enrollTitle : w.verifyTitle}</h2>
  <p className="rc-muted">{enroll ? w.enrollHelp : w.verifyHelp}</p>
  {enroll && !started && !restart && <button data-mfa-start ref={startButton} className="rc-mfa-start" type="button" disabled={busy || !sameChallenge} onClick={beginEnrollment}>{w.start}</button>}
  {visibleEnrollment && <div className="rc-mfa-setup"><p>{w.setupHelp}</p><AuthenticatorQr otpauth={visibleEnrollment.otpauth} label={w.qr} unavailable={w.qrUnavailable}/><details className="rc-mfa-manual"><summary>{w.manual}</summary><code data-mfa-secret>{visibleEnrollment.secret}</code><p className="rc-muted">{w.manualHelp}</p></details><p className="rc-muted rc-mfa-memory">{w.memoryHelp}</p></div>}
  <form className="rc-form" onSubmit={submit}>
   {ready && <><label>{recoveryMode?rw.code:w.code}<input data-mfa-code data-mfa-recovery-code={recoveryMode?'true':undefined} ref={codeInput} name="mfa-code" type="text" inputMode={recoveryMode?'text':'numeric'} autoComplete={recoveryMode?'off':'one-time-code'} pattern={recoveryMode?undefined:'[0-9]{6}'} maxLength={recoveryMode?39:6} aria-describedby={helpId} required value={code} disabled={busy} onChange={event => setCode(event.target.value)}/></label><p id={helpId} className="rc-muted rc-mfa-code-help">{recoveryMode?rw.codeHelp:w.codeHelp}</p></>}
   {problem && sameChallenge && <div role="alert" className="rc-error" data-mfa-error>{problem==='recoveryFormat'?rw.format:recoveryMode&&problem==='codeInvalid'?rw.codeInvalid:w[problem] || w.error}</div>}
   {busy && <p role="status" className="rc-muted">{enroll && !visibleEnrollment ? w.starting : w.working}</p>}
   {ready && <button data-mfa-submit type="submit" disabled={busy || (recoveryMode?!recoveryCodeFormat(code):!/^[0-9]{6}$/.test(code))}>{recoveryMode?rw.submit:enroll ? w.confirm : w.verify}</button>}
   {!enroll&&ready&&<button type="button" data-mfa-use-recovery disabled={busy} onClick={()=>{clear();setRecoveryMode(!recoveryMode);codeInput.current?.focus();}}>{recoveryMode?rw.back:rw.recover}</button>}
   <button data-mfa-cancel type="button" disabled={busy} onClick={cancel}>{w.cancel}</button>
  </form>
  <p className="rc-muted rc-mfa-cancel-help">{w.cancelHelp}</p>
 </section>;
}
