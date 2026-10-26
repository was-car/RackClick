import { readGrantTargets } from './admin-grants.ts';
import { AdminGrants } from './AdminGrants.jsx';
import { AdminGroupRelations } from './AdminGroupRelations.jsx';
import { AdminCustomerGroupMembers } from './AdminCustomerGroupMembers.jsx';
import { AdminGroupMembers } from './AdminGroupMembers.jsx';
import { AdminGroupCreation } from './AdminGroupCreation.jsx';
import { AdminGroupReceipt } from './AdminGroupReceipt.jsx';
import { groupReceiptBlock } from './admin-group-receipt.ts';
import { adminNavigationWords } from './AdminSectionNavigation.jsx';
const { useEffect, useRef, useState } = React;
export const groupWords = {
 en: { title:'Groups and permissions', userGroups:'User groups', customerGroups:'Customer groups', members:'Members', grants:'Group permissions', customers:'Customers', empty:'No groups.', noMembers:'No members.', noGrants:'No permissions assigned.', noCustomers:'No customers.', refresh:'Refresh groups', loading:'Loading groups…', info:'These are the permissions assigned to each group. A user may belong to several groups; the server checks their combined permissions for every operation. User and customer memberships can be changed below. Permissions can be changed below.', denied:'Administrator permission is required.', error:'Could not load groups. Refresh to try again.', changed:'The data changed while loading. Refresh the groups.', inactive:'Inactive', scopes:{systemhaus:'Entire Systemhaus',customer:'Customer',customerGroup:'Customer group'}, caps:['Read Systemhaus','Manage Systemhaus','Create customers','Manage customers','Read inventory','Edit inventory','Delete inventory','Manage security','Export reports','Publish shared templates'] },
 de: { title:'Gruppen und Berechtigungen', userGroups:'Benutzergruppen', customerGroups:'Kundengruppen', members:'Mitglieder', grants:'Gruppenberechtigungen', customers:'Kunden', empty:'Keine Gruppen.', noMembers:'Keine Mitglieder.', noGrants:'Keine Berechtigungen zugewiesen.', noCustomers:'Keine Kunden.', refresh:'Gruppen aktualisieren', loading:'Gruppen werden geladen…', info:'Hier stehen die zugewiesenen Berechtigungen jeder Gruppe. Ein Benutzer kann mehreren Gruppen angehören; der Server prüft die kombinierten Berechtigungen bei jedem Vorgang. Benutzer- und Kundenmitglieder können unten geändert werden. Berechtigungen können unten geändert werden.', denied:'Administratorberechtigung erforderlich.', error:'Gruppen konnten nicht geladen werden. Erneut aktualisieren.', changed:'Daten während des Ladens geändert. Gruppen aktualisieren.', inactive:'Inaktiv', scopes:{systemhaus:'Gesamtes Systemhaus',customer:'Kunde',customerGroup:'Kundengruppe'}, caps:['Systemhaus lesen','Systemhaus verwalten','Kunden anlegen','Kunden verwalten','Inventar lesen','Inventar bearbeiten','Inventar löschen','Sicherheit verwalten','Berichte exportieren','Geteilte Vorlagen veröffentlichen'] },
 es: { title:'Grupos y permisos', userGroups:'Grupos de usuarios', customerGroups:'Grupos de clientes', members:'Miembros', grants:'Permisos del grupo', customers:'Clientes', empty:'No hay grupos.', noMembers:'Sin miembros.', noGrants:'Sin permisos asignados.', noCustomers:'Sin clientes.', refresh:'Actualizar grupos', loading:'Cargando grupos…', info:'Estos son los permisos asignados a cada grupo. Un usuario puede pertenecer a varios grupos; el servidor comprueba sus permisos combinados en cada operación. Las membresías de usuarios y clientes se cambian debajo. Los permisos se pueden cambiar debajo.', denied:'Se requiere permiso de administración.', error:'No se pudieron leer los grupos. Actualiza para reintentar.', changed:'Los datos cambiaron durante la lectura. Actualiza los grupos.', inactive:'Inactivo', scopes:{systemhaus:'Todo el Systemhaus',customer:'Cliente',customerGroup:'Grupo de clientes'}, caps:['Leer Systemhaus','Administrar Systemhaus','Crear clientes','Administrar clientes','Leer inventario','Editar inventario','Eliminar inventario','Administrar seguridad','Exportar informes','Publicar plantillas compartidas'] }
};
const capabilities=['systemhaus.read','systemhaus.manage','customer.create','customer.manage','inventory.read','inventory.edit','inventory.delete','security.manage','reports.export','templates.publish'];
export function AdminGroups({ api, actor, lang, selectedUserId, onSelectionGuard }) {
 const w=groupWords[lang], [snapshot,setSnapshot]=useState(null), [error,setError]=useState(null), [busy,setBusy]=useState(true), [reload,setReload]=useState(0);
 const [confirmation,setConfirmation]=useState(null), [creation,setCreation]=useState(null), [request,setRequest]=useState(null);
 const context=useRef({actor,api,generation:0}), sequence=useRef(0), navigationSequence=useRef(0), loading=useRef(true);
 if(context.current.actor!==actor||context.current.api!==api){context.current={actor,api,generation:context.current.generation+1};sequence.current++;loading.current=true}
 const generation=context.current.generation;
 const current=()=>context.current.generation===generation&&api.actorId===actor;
 const data=current()&&snapshot?.generation===generation?snapshot.data:null;
 const receipt=current()&&confirmation?.generation===generation?confirmation.receipt:null;
 const creationState=creation?.generation===generation?creation.state:null;
 const nw=adminNavigationWords[lang];
 function invalidate(reason){
  if(!current())return;
  setConfirmation(null);setRequest(null);
  if(reason?.status===401||reason?.status===403){context.current={...context.current,generation:generation+1};sequence.current++;loading.current=true;setSnapshot(null);setError(reason);setBusy(false)}
 }
 function refresh(){if(!current())return;loading.current=true;setSnapshot(null);setBusy(true);setRequest(null);setReload(x=>x+1)}
 useEffect(()=>{
  let live=true;const operation=++sequence.current;loading.current=true;setSnapshot(null);setError(null);setBusy(true);
  const valid=()=>live&&current()&&sequence.current===operation;
  readGrantTargets(api).then(x=>{if(valid())setSnapshot({generation,data:x})}).catch(e=>{if(valid()){if(e.status===401||e.status===403)invalidate(e);else setError(e)}}).finally(()=>{if(valid()){loading.current=false;setBusy(false)}});
  return()=>{live=false};
 },[actor,api,reload]);
 function block(){return groupReceiptBlock({receipt,actor,apiActor:api.actorId,snapshot:busy||error||loading.current?null:data,ready:!!creationState?.ready,busy:!!creationState?.busy||busy||loading.current,pending:!!creationState?.pending,current:current()})}
 const blocked=block();
 function openReceipt(){
  if(block())return;
  setRequest({token:++navigationSequence.current,actorId:actor,generation,kind:receipt.kind==='userGroup'?'user':'customer',id:receipt.groupId,revision:receipt.revision,snapshot:data});
 }
 const message=error&&(error.status===403?w.denied:error.code==='groups_changed'?w.changed:w.error);
 return <section className="rc-admin-groups rc-client-section" aria-label={w.title}>
  <h2>{w.title}</h2><p>{w.info}</p>{selectedUserId&&data&&<section className="rc-detail" data-selected-user-groups={selectedUserId}><h3>{data.users.find(u=>u.id===selectedUserId)?.userName||selectedUserId}</h3><h4>{w.userGroups}</h4>{data.userGroups.some(g=>g.members.some(m=>m.id===selectedUserId))?<ul>{data.userGroups.filter(g=>g.members.some(m=>m.id===selectedUserId)).map(g=><li key={g.id}>{g.name}</li>)}</ul>:<p>{w.noMembers}</p>}</section>}<button onClick={refresh} disabled={busy}>{w.refresh}</button>
  {busy&&<p role="status">{w.loading}</p>}{message&&<p role="alert" className="rc-error">{message}</p>}
  <AdminGroupRelations key={actor} actor={actor} generation={generation} lang={lang} data={busy||error||loading.current?null:data} request={current()&&request?.generation===generation?request:null} onRequestConsumed={token=>{if(current())setRequest(previous=>previous?.token===token?null:previous)}}/>
  <section id="rc-admin-group-create" className="rc-admin-section" tabIndex={-1} aria-label={nw.groupCreate}><AdminGroupCreation key={"create:"+actor+":"+generation} api={api} actor={actor} lang={lang} revision={busy||error||loading.current?null:data?.revision} onChanged={refresh} onReceipt={value=>{if(current())setConfirmation(value?{generation,receipt:value}:null)}} onCreationState={state=>{if(current())setCreation({generation,state})}} onInvalidated={invalidate}/></section>
  <AdminGroupReceipt receipt={receipt} actor={actor} lang={lang} blocked={blocked} onContinue={openReceipt}/>
  <section id="rc-admin-user-memberships" className="rc-admin-section" tabIndex={-1} aria-label={nw.userMembers}><AdminGroupMembers selectedUserId={selectedUserId} onSelectionGuard={onSelectionGuard} key={"members:"+actor} api={api} actor={actor} lang={lang} data={busy?null:data} onChanged={refresh}/></section>
  <section id="rc-admin-customer-memberships" className="rc-admin-section" tabIndex={-1} aria-label={nw.customerMembers}><AdminCustomerGroupMembers key={"customer-members:"+actor} api={api} actor={actor} lang={lang} data={busy?null:data} onChanged={refresh}/></section>
  <section id="rc-admin-group-grants" className="rc-admin-section" tabIndex={-1} aria-label={nw.grants}><AdminGrants key={"grants:"+actor} api={api} actor={actor} lang={lang} data={busy?null:data} onChanged={refresh}/></section>
  <section id="rc-admin-user-group-list" className="rc-admin-section" tabIndex={-1} aria-label={nw.userGroups}>{data&&<><h3>{w.userGroups}</h3>{!data.userGroups.length&&<p>{w.empty}</p>}<div className="ir-client-cards">{data.userGroups.map(g=><article className="ir-client-card" key={g.id} data-user-group-id={g.id}><h4>{g.name}</h4><h5>{w.members}</h5>{g.members.length?<ul>{g.members.map(m=><li key={m.id}>{m.userName}{!m.active&&' ('+w.inactive+')'}</li>)}</ul>:<p>{w.noMembers}</p>}<h5>{w.grants}</h5>{g.grants.length?<ul>{g.grants.map(p=><li key={p.id} data-grant-id={p.id}>{w.caps[capabilities.indexOf(p.capability)]||p.capability} · {w.scopes[p.scope]}{p.target&&': '+p.target.name}</li>)}</ul>:<p>{w.noGrants}</p>}</article>)}</div></>}</section>
  <section id="rc-admin-customer-group-list" className="rc-admin-section" tabIndex={-1} aria-label={nw.customerGroups}>{data&&<><h3>{w.customerGroups}</h3>{!data.customerGroups.length&&<p>{w.empty}</p>}<div className="ir-client-cards">{data.customerGroups.map(g=><article className="ir-client-card" key={g.id} data-customer-group-id={g.id}><h4>{g.name}</h4><h5>{w.customers}</h5>{g.customers.length?<ul>{g.customers.map(c=><li key={c.id}>{c.name}</li>)}</ul>:<p>{w.noCustomers}</p>}</article>)}</div></>}</section>
 </section>;
}
