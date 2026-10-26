import { useAdminSelectionGuard, AdminSelectionTarget } from './AdminSectionNavigation.jsx';

import { assignMember, cancelMember, memberJournal, memberStatus } from './admin-group-members.ts';

const { useEffect, useRef, useState } = React;

export const memberWords = {

 en:{title:'User group membership',group:'User group',user:'User',action:'Action',add:'Add',remove:'Remove',save:'Save assignment',retry:'Retry original assignment',check:'Check assignment result',cancel:'Cancel pending assignment',help:'Select the group and user. Adding a user applies this group’s permissions; removing revokes this group’s contribution. The server checks every operation.',pending:'Assignment awaiting confirmation. Original IDs, action and request are retained.',unknown:'No result is recorded yet. This does not confirm cancellation.',saved:'Assignment confirmed by the server.',cancelled:'Cancellation confirmed by the server. This request did not change membership.',cancelHelp:'Cancel only the unconfirmed request. A committed assignment is recovered, not reversed.',denied:'Administrator permission is required.',expired:'Session expired. Sign in again and reopen Groups to recover.',conflict:'The revision changed. Check or cancel the original request before another assignment.',storage:'The recovery journal is unavailable. Reopen Groups.',lastAdmin:'Cannot remove the last active administrator with permission to manage security.',error:'Could not confirm the assignment.',choose:'Choose…',inactive:'Inactive'},

 de:{title:'Mitgliedschaft in Benutzergruppen',group:'Benutzergruppe',user:'Benutzer',action:'Aktion',add:'Hinzufügen',remove:'Entfernen',save:'Zuweisung speichern',retry:'Ursprüngliche Zuweisung wiederholen',check:'Zuweisungsergebnis prüfen',cancel:'Ausstehende Zuweisung abbrechen',help:'Gruppe und Benutzer auswählen. Hinzufügen gewährt Gruppenrechte; Entfernen widerruft den Beitrag dieser Gruppe. Der Server prüft jeden Vorgang.',pending:'Zuweisung noch nicht bestätigt. Ursprüngliche IDs, Aktion und Auftrag bleiben erhalten.',unknown:'Noch kein Ergebnis gespeichert. Das bestätigt keinen Abbruch.',saved:'Zuweisung vom Server bestätigt.',cancelled:'Abbruch vom Server bestätigt. Dieser Auftrag änderte keine Mitgliedschaft.',cancelHelp:'Nur unbestätigten Auftrag abbrechen. Eine gespeicherte Zuweisung wird abgerufen, nicht rückgängig gemacht.',denied:'Administratorberechtigung erforderlich.',expired:'Sitzung abgelaufen. Erneut anmelden und Gruppen zur Wiederherstellung öffnen.',conflict:'Revision geändert. Ursprünglichen Auftrag vor einer weiteren Zuweisung prüfen oder abbrechen.',storage:'Wiederherstellungsjournal nicht verfügbar. Gruppen erneut öffnen.',lastAdmin:'Der letzte aktive Administrator mit Sicherheitsverwaltung darf nicht entfernt werden.',error:'Zuweisung konnte nicht bestätigt werden.',choose:'Auswählen…',inactive:'Inaktiv'},

 es:{title:'Membresía de grupos de usuarios',group:'Grupo de usuarios',user:'Usuario',action:'Acción',add:'Añadir',remove:'Retirar',save:'Guardar asignación',retry:'Reintentar asignación original',check:'Consultar resultado de asignación',cancel:'Cancelar asignación pendiente',help:'Selecciona el grupo y el usuario. Añadir aplica los permisos del grupo; retirar revoca la aportación de ese grupo. El servidor comprueba cada operación.',pending:'Asignación pendiente de confirmación. Se conservan IDs, acción y solicitud originales.',unknown:'Todavía no hay resultado registrado. No confirma cancelación.',saved:'Asignación confirmada por el servidor.',cancelled:'Cancelación confirmada por el servidor. Esta solicitud no cambió la membresía.',cancelHelp:'Cancela solo la solicitud sin confirmar. Una asignación guardada se recupera, no se deshace.',denied:'Se requiere permiso de administración.',expired:'Sesión caducada. Inicia sesión de nuevo y reabre Grupos para recuperar.',conflict:'La revisión cambió. Consulta o cancela la solicitud original antes de otra asignación.',storage:'El registro de recuperación no está disponible. Reabre Grupos.',lastAdmin:'No se puede retirar al último administrador activo con permiso para administrar seguridad.',error:'No se pudo confirmar la asignación.',choose:'Selecciona…',inactive:'Inactivo'}

};

export function AdminGroupMembers({api,actor,lang,data,onChanged,selectedUserId,onSelectionGuard}) {

 const w=memberWords[lang], [pending,setPending]=useState(null), [ready,setReady]=useState(false), [busy,setBusy]=useState(false), [groupId,setGroupId]=useState(''), [userId,setUserId]=useState(''), [assigned,setAssigned]=useState(true), [error,setError]=useState(null), [status,setStatus]=useState(null);

 const locked=useRef(false), live=useRef(false);

 const [actionDirty,setActionDirty]=useState(false);

 useAdminSelectionGuard('members',onSelectionGuard,busy||!ready||!data||!!pending||!!groupId||actionDirty,locked);

 React.useLayoutEffect(()=>{if(selectedUserId===undefined||pending||busy||groupId||actionDirty||userId===selectedUserId)return;setUserId(selectedUserId);setError(null);setStatus(null)},[selectedUserId,pending,busy,groupId,actionDirty,userId]);

 useEffect(()=>{live.current=true;setReady(false);memberJournal('read',actor).then(p=>{if(live.current){setPending(p);setGroupId(p?.groupId||'');setUserId(p?.userId||selectedUserId||'');setAssigned(p?.assigned??true);setReady(true)}}).catch(e=>{if(live.current)setError(e)});return()=>{live.current=false}},[actor]);

 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);

 const validTargets=data?.userGroups.some(g=>g.id===groupId)&&data?.users.some(u=>u.id===userId);

 async function confirmed(result,current) {

  await memberJournal('remove',actor,current);

  if(live.current){setPending(null);setGroupId('');setUserId(selectedUserId??'');setActionDirty(false);setAssigned(true);setStatus(result.state==='cancelled'?'cancelled':'saved');onChanged()}

 }

 async function run(action) {

  if(locked.current||!ready||(!pending&&(!validTargets||!data?.revision||action!=='save')))return;

  locked.current=true;setBusy(true);setError(null);setStatus(null);

  const current=pending||{actorId:actor,requestId:crypto.randomUUID(),groupId,userId,assigned,revision:data.revision};

  try {

   if(action==='save'){await memberJournal('write',actor,current);if(live.current)setPending(current);await confirmed(await assignMember(api,current),current)}

   else {const result=action==='check'?await memberStatus(api,current):await cancelMember(api,current);if(result)await confirmed(result,current);else if(live.current)setStatus('unknown')}

  } catch(e){if(live.current){setError(e);if(e.code==='draft_storage_unavailable')setReady(false)}}

  finally{locked.current=false;if(live.current)setBusy(false)}

 }

 const message=error&&(error.status===403?w.denied:error.status===401?w.expired:error.status===412?w.conflict:error.code==='draft_storage_unavailable'?w.storage:error.code==='last_admin_required'?w.lastAdmin:w.error);

 const disabled=busy||!!pending||!ready;

 return <section className="rc-group-members rc-group-creation"><h3>{w.title}</h3><p>{w.help}</p>{selectedUserId!==undefined&&<AdminSelectionTarget lang={lang} id={pending?.userId||userId} users={data?.users}/>}{status&&<p role="status" data-member-result>{w[status]}</p>}{message&&<p role="alert" className="rc-error">{message}</p>}{pending&&<div className="ir-warning" data-pending-member><p>{w.pending}</p><p>{pending.groupId} · {pending.userId} · {pending.assigned?w.add:w.remove}</p><button data-check-member onClick={()=>run('check')} disabled={busy||!ready}>{w.check}</button><p>{w.cancelHelp}</p><button data-cancel-member onClick={()=>run('cancel')} disabled={busy||!ready}>{w.cancel}</button></div>}{!pending&&(groupId||actionDirty)&&<button type="button" data-discard-member disabled={busy} onClick={()=>{setGroupId('');setAssigned(true);setActionDirty(false);setError(null)}}>{lang==='es'?'Descartar borrador de membresía':lang==='de'?'Zuordnungsentwurf verwerfen':'Discard membership draft'}</button>}<form className="rc-form" data-assign-member onSubmit={e=>{e.preventDefault();run('save')}}><label>{w.group}<select name="memberGroup" value={groupId} disabled={disabled||!data} onChange={e=>setGroupId(e.target.value)}><option value="">{w.choose}</option>{data?.userGroups.map(g=><option key={g.id} value={g.id}>{g.name} · {g.id.slice(0,8)}</option>)}{pending&&!data?.userGroups.some(g=>g.id===groupId)&&<option value={groupId}>{groupId}</option>}</select></label><label>{w.user}<select name="memberUser" value={userId} disabled={selectedUserId!==undefined||disabled||!data} onChange={e=>setUserId(e.target.value)}><option value="">{w.choose}</option>{data?.users.map(u=><option key={u.id} value={u.id}>{u.userName}{!u.active&&' ('+w.inactive+')'} · {u.id.slice(0,8)}</option>)}{pending&&!data?.users.some(u=>u.id===userId)&&<option value={userId}>{userId}</option>}</select></label><label>{w.action}<select name="memberAction" value={assigned?'add':'remove'} disabled={disabled} onChange={e=>{setAssigned(e.target.value==='add');setActionDirty(true)}}><option value="add">{w.add}</option><option value="remove">{w.remove}</option></select></label><button type="submit" disabled={busy||!ready||(!pending&&!validTargets)}>{pending?w.retry:w.save}</button></form></section>;
}
