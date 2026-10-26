import { onboardingWords } from './admin-user-onboarding-words.ts';

export function AdminUserOnboarding({ receipt, actor, lang, blocked, onContinue }) {
 if (!receipt || receipt.actorId !== actor) return null;
 const w=onboardingWords[lang];
 return <section className="rc-group-creation rc-admin-section" data-user-onboarding={receipt.userId} aria-label={w.title}>
  <h3>{w.title}</h3><p><strong>{receipt.userName}</strong> · {receipt.userId}</p><p>{w.saved}</p>
  <ol><li><strong>{w.account}</strong></li><li><strong>{w.memberships}</strong><p>{w.membershipHelp}</p><button type="button" data-onboarding-memberships disabled={!!blocked} onClick={()=>onContinue('user-memberships')}>{w.openMemberships}</button></li><li><strong>{w.effective}</strong><p>{w.effectiveHelp}</p><button type="button" data-onboarding-effective disabled={!!blocked} onClick={()=>onContinue('effective-permissions')}>{w.openEffective}</button></li></ol>
  {blocked&&<p role="status" data-onboarding-blocked={blocked}>{w[blocked]}</p>}
 </section>;
}
