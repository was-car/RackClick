import { cancelGroup, createGroup, groupJournal, groupStatus } from './admin-groups.ts';
import { completeGroupCreation } from './admin-group-receipt.ts';
const { useEffect, useRef, useState } = React;
export const creationWords = {
 en: { title:'Create group', kind:'Group type', userGroup:'User group', customerGroup:'Customer group', name:'Group name', create:'Create group', retry:'Retry original creation', check:'Check group result', cancel:'Cancel pending group creation', help:'New groups have no members, customers or permissions. Use the membership and Permissions of user groups panels to make explicit assignments, then wait for server confirmation. Opening group relationships does not grant access.', pending:'Group creation awaiting confirmation. The original name, type and request are retained.', unknown:'No result is recorded yet. This does not confirm cancellation; keep the original request.', saved:'Group creation confirmed by the server.', cancelled:'Cancellation confirmed by the server. This request did not create a group.', cancelHelp:'Cancel only the unconfirmed request. If the group was already created, its saved result will be recovered.', denied:'Administrator permission is required.', expired:'Session expired. Sign in again and reopen Groups to recover the request.', conflict:'The revision changed. Keep the original request; check or cancel it before creating another group.', storage:'The recovery journal is unavailable. Reopen Groups to recover any pending request.', invalid:'Use a name of 1–100 valid Unicode characters.', error:'Could not confirm the operation.' },
 de: { title:'Gruppe anlegen', kind:'Gruppentyp', userGroup:'Benutzergruppe', customerGroup:'Kundengruppe', name:'Gruppenname', create:'Gruppe anlegen', retry:'Ursprüngliche Anlage wiederholen', check:'Gruppenergebnis prüfen', cancel:'Ausstehende Gruppenanlage abbrechen', help:'Neue Gruppen haben keine Mitglieder, Kunden oder Berechtigungen. In den Bereichen für Mitgliedschaften und Berechtigungen von Benutzergruppen ausdrücklich zuweisen und die Serverbestätigung abwarten. Das Öffnen von Gruppenbeziehungen gewährt keinen Zugriff.', pending:'Gruppenanlage noch nicht bestätigt. Ursprünglicher Name, Typ und Auftrag bleiben erhalten.', unknown:'Noch kein Ergebnis gespeichert. Das bestätigt keinen Abbruch; ursprünglichen Auftrag beibehalten.', saved:'Gruppenanlage vom Server bestätigt.', cancelled:'Abbruch vom Server bestätigt. Dieser Auftrag hat keine Gruppe angelegt.', cancelHelp:'Nur den unbestätigten Auftrag abbrechen. Wurde die Gruppe bereits angelegt, wird das gespeicherte Ergebnis abgerufen.', denied:'Administratorberechtigung erforderlich.', expired:'Sitzung abgelaufen. Erneut anmelden und Gruppen zur Wiederherstellung öffnen.', conflict:'Revision geändert. Ursprünglichen Auftrag beibehalten; vor einer weiteren Anlage prüfen oder abbrechen.', storage:'Wiederherstellungsjournal nicht verfügbar. Gruppen erneut öffnen, um ausstehende Aufträge abzurufen.', invalid:'Name: 1–100 gültige Unicode-Zeichen.', error:'Vorgang konnte nicht bestätigt werden.' },
 es: { title:'Crear grupo', kind:'Tipo de grupo', userGroup:'Grupo de usuarios', customerGroup:'Grupo de clientes', name:'Nombre del grupo', create:'Crear grupo', retry:'Reintentar alta original', check:'Consultar resultado del grupo', cancel:'Cancelar alta de grupo pendiente', help:'Los grupos nuevos no tienen miembros, clientes ni permisos. Usa los paneles de membresías y Permisos de grupos de usuarios para asignar explícitamente y espera la confirmación del servidor. Abrir relaciones de grupos no concede acceso.', pending:'Alta de grupo pendiente de confirmación. Se conservan el nombre, tipo y solicitud originales.', unknown:'Todavía no hay resultado registrado. No confirma cancelación; conserva la solicitud original.', saved:'Alta de grupo confirmada por el servidor.', cancelled:'Cancelación confirmada por el servidor. Esta solicitud no creó ningún grupo.', cancelHelp:'Cancela solo la solicitud sin confirmar. Si el grupo ya fue creado, se recuperará su resultado guardado.', denied:'Se requiere permiso de administración.', expired:'Sesión caducada. Inicia sesión de nuevo y vuelve a Grupos para recuperar la solicitud.', conflict:'La revisión cambió. Conserva la solicitud original; consúltala o cancélala antes de crear otro grupo.', storage:'El registro de recuperación no está disponible. Reabre Grupos para recuperar cualquier solicitud pendiente.', invalid:'Usa un nombre de 1 a 100 caracteres Unicode válidos.', error:'No se pudo confirmar la operación.' }
};
export function AdminGroupCreation({ api, actor, lang, revision, onChanged, onReceipt, onCreationState, onInvalidated }) {
 const w=creationWords[lang], [pending,setPending]=useState(null), [ready,setReady]=useState(false), [busy,setBusy]=useState(false), [name,setName]=useState(''), [kind,setKind]=useState('userGroup'), [error,setError]=useState(null), [status,setStatus]=useState(null);
 const locked=useRef(false), live=useRef(false), context=useRef({actor,api,generation:0}), state=useRef({ready:false,busy:false,pending:false});
 if(context.current.actor!==actor||context.current.api!==api)context.current={actor,api,generation:context.current.generation+1};
 const generation=context.current.generation;
 const current=()=>live.current&&context.current.generation===generation&&api.actorId===actor;
 function report(patch){state.current={...state.current,...patch};onCreationState?.(state.current)}
 useEffect(()=>{
  live.current=true;locked.current=false;state.current={ready:false,busy:false,pending:false};setReady(false);setBusy(false);setPending(null);setError(null);setStatus(null);report({});
  groupJournal('read',actor).then(p=>{if(current()){setPending(p);setName(p?.name||'');setKind(p?.kind||'userGroup');setReady(true);report({ready:true,pending:!!p})}}).catch(e=>{if(current())setError(e)});
  return()=>{live.current=false};
 },[actor,api]);
 useEffect(()=>{if(!pending)return;const warn=e=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[pending]);
 async function run(action) {
  if(!current()||locked.current||!ready||(!pending&&(!revision||action!=='create')))return;
  locked.current=true;setBusy(true);report({busy:true});setError(null);setStatus(null);
  const draft=pending||{actorId:actor,requestId:crypto.randomUUID(),kind,name,revision};
  if(!pending)onInvalidated?.();
  let phase='operation';
  try {
   let result;
   if(action==='create') {
    phase='write';await groupJournal('write',actor,draft);if(!current())return;
    setPending(draft);report({pending:true});phase='operation';result=await createGroup(api,draft);
   } else {
    result=action==='check'?await groupStatus(api,draft):await cancelGroup(api,draft);
   }
   if(!current())return;
   await completeGroupCreation(result,draft,actor,{
    current,remember:receipt=>onReceipt?.(receipt),removeJournal:()=>{phase='cleanup';return groupJournal('remove',actor,draft)},
    clearPending:()=>{setPending(null);setName('');report({pending:false});setStatus(result.state==='cancelled'?'cancelled':'saved')},reload:onChanged
   });
   if(current()&&result===null)setStatus('unknown');
  } catch(e) {
   if(current()){
    setError(e);
    if(e.status===401||e.status===403)onInvalidated?.(e);
    if(e.code==='draft_storage_unavailable'&&phase!=='cleanup'){setReady(false);report({ready:false})}
   }
  } finally {if(context.current.generation===generation){locked.current=false;if(live.current){setBusy(false);report({busy:false})}}}
 }
 function newIntent(change){if(!current())return;onInvalidated?.();setStatus(null);setError(null);change()}
 const message=error&&(error.status===403?w.denied:error.status===401?w.expired:error.status===412?w.conflict:error.code==='draft_storage_unavailable'?w.storage:['name_required','name_invalid'].includes(error.code)?w.invalid:w.error);
 return <section className="rc-group-creation"><h3>{w.title}</h3><p>{w.help}</p>{status&&<p role="status" data-group-result>{w[status]}</p>}{message&&<p role="alert" className="rc-error">{message}</p>}{pending&&<div className="ir-warning" data-pending-group><p>{w.pending}</p><button data-check-group onClick={()=>run('check')} disabled={busy||!ready}>{w.check}</button><p>{w.cancelHelp}</p><button data-cancel-group onClick={()=>run('cancel')} disabled={busy||!ready}>{w.cancel}</button></div>}<form className="rc-form" data-create-group onSubmit={e=>{e.preventDefault();run('create')}}><label>{w.kind}<select name="groupKind" value={kind} disabled={busy||!!pending||!ready} onChange={e=>newIntent(()=>setKind(e.target.value))}><option value="userGroup">{w.userGroup}</option><option value="customerGroup">{w.customerGroup}</option></select></label><label>{w.name}<input name="groupName" required value={name} disabled={busy||!!pending||!ready} onChange={e=>newIntent(()=>setName(e.target.value))}/></label><button type="submit" disabled={busy||!ready||(!pending&&!revision)}>{pending?w.retry:w.create}</button></form></section>;
}
