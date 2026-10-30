const { useLayoutEffect, useRef, useState } = React;
export const relationWords = {
 en: { title:'Group relationships · read only', help:'Relationships may have several parents. These assignments are not inheritance or a calculation of effective permissions; the server authorizes every operation.', type:'Group type', user:'User groups', customer:'Customer groups', group:'Selected group', choose:'Choose a group', viewCustomer:'View customer group', viewUser:'View user group', members:'Members', grants:'Assigned permissions', customers:'Customers in this group', sources:'User groups with permissions on this customer group', empty:'No relationships.', unavailable:'Refresh groups to load current relationships.', revision:'Snapshot revision', inactive:'Inactive', scopes:{systemhaus:'Entire Systemhaus · global assignment',customer:'Customer · direct assignment',customerGroup:'Customer group · assignment'}, caps:['Read Systemhaus','Manage Systemhaus','Create customers','Manage customers','Read inventory','Edit inventory','Delete inventory','Manage security','Export reports','Publish shared templates'] },
 de: { title:'Gruppenbeziehungen · schreibgeschützt', help:'Beziehungen können mehrere Eltern haben. Diese Zuweisungen sind weder Vererbung noch eine Berechnung effektiver Berechtigungen; der Server autorisiert jeden Vorgang.', type:'Gruppentyp', user:'Benutzergruppen', customer:'Kundengruppen', group:'Ausgewählte Gruppe', choose:'Gruppe auswählen', viewCustomer:'Kundengruppe anzeigen', viewUser:'Benutzergruppe anzeigen', members:'Mitglieder', grants:'Zugewiesene Berechtigungen', customers:'Kunden dieser Gruppe', sources:'Benutzergruppen mit Berechtigungen für diese Kundengruppe', empty:'Keine Beziehungen.', unavailable:'Gruppen aktualisieren, um aktuelle Beziehungen zu laden.', revision:'Snapshot-Revision', inactive:'Inaktiv', scopes:{systemhaus:'Gesamtes Systemhaus · globale Zuweisung',customer:'Kunde · direkte Zuweisung',customerGroup:'Kundengruppe · Zuweisung'}, caps:['Systemhaus lesen','Systemhaus verwalten','Kunden anlegen','Kunden verwalten','Inventar lesen','Inventar bearbeiten','Inventar löschen','Sicherheit verwalten','Berichte exportieren','Geteilte Vorlagen veröffentlichen'] },
 es: { title:'Relaciones de grupos · solo lectura', help:'Las relaciones pueden tener varios padres. Estas asignaciones no son herencia ni un cálculo de permisos efectivos; el servidor autoriza cada operación.', type:'Tipo de grupo', user:'Grupos de usuarios', customer:'Grupos de clientes', group:'Grupo seleccionado', choose:'Elegir grupo', viewCustomer:'Ver grupo de clientes', viewUser:'Ver grupo de usuarios', members:'Miembros', grants:'Permisos asignados', customers:'Clientes de este grupo', sources:'Grupos de usuarios con permisos sobre este grupo de clientes', empty:'Sin relaciones.', unavailable:'Actualiza los grupos para cargar las relaciones vigentes.', revision:'Revisión del snapshot', inactive:'Inactivo', scopes:{systemhaus:'Todo el Systemhaus · asignación global',customer:'Cliente · asignación directa',customerGroup:'Grupo de clientes · asignación'}, caps:['Leer Systemhaus','Administrar Systemhaus','Crear clientes','Administrar clientes','Leer inventario','Editar inventario','Eliminar inventario','Administrar seguridad','Exportar informes','Publicar plantillas compartidas'] }
};
const capabilities=['systemhaus.read','systemhaus.manage','customer.create','customer.manage','inventory.read','inventory.edit','inventory.delete','security.manage','reports.export','templates.publish'];
// Receives the existing revision-checked snapshot. No independent requests, cache or permission decisions.
export function AdminGroupRelations({ data, lang, actor, generation, request, onRequestConsumed }) {
 const w=relationWords[lang], [kind,setKind]=useState('user'), [selected,setSelected]=useState('');
 const groupSelect=useRef(null), navigation=useRef(null), consumed=useRef(new Set());
 const groups=data?(kind==='user'?data.userGroups:data.customerGroups):[];
 const group=groups.find(g=>g.id===selected);
 useLayoutEffect(()=>{
  if(!data||!group){navigation.current=null;if(selected)setSelected('');return}
  const pending=navigation.current;
  navigation.current=null;
  if(pending?.data===data&&pending.kind===kind&&pending.id===group.id){if(pending.scroll)groupSelect.current?.scrollIntoView({block:'center',behavior:'auto'});groupSelect.current?.focus()}
 },[data,kind,selected]);
 useLayoutEffect(()=>{
  if(!request)return;
  const key=JSON.stringify([request.actorId,request.generation,request.token]);
  if(consumed.current.has(key))return;
  // Consume even an invalid/withdrawn request. A later refresh must never
  // resurrect a past navigation intent or choose a same-name replacement.
  consumed.current.add(key);onRequestConsumed?.(request.token);
  if(request.actorId!==actor||request.generation!==generation||request.snapshot!==data||!data||!Number.isSafeInteger(request.revision)||data.revision<request.revision||!['user','customer'].includes(request.kind))return;
  const target=(request.kind==='user'?data.userGroups:data.customerGroups).find(g=>g.id===request.id);
  if(!target)return;
  if(kind===request.kind&&selected===target.id){groupSelect.current?.scrollIntoView({block:'center',behavior:'auto'});groupSelect.current?.focus();return}
  navigation.current={data,kind:request.kind,id:target.id,scroll:true};setKind(request.kind);setSelected(target.id);
 },[request,data,actor,generation]);
 function showGroup(nextKind,id){
  const target=data&&(nextKind==='user'?data.userGroups:data.customerGroups).find(g=>g.id===id);
  if(!target)return;
  navigation.current={data,kind:nextKind,id:target.id};
  setKind(nextKind);setSelected(target.id);
 }
 const grants=(items)=><ul>{items.map(p=>{
  const target=kind==='user'&&p.scope==='customerGroup'&&data?.customerGroups.find(g=>g.id===p.target?.id);
  return <li key={p.id} data-relation-grant={p.id}>{w.caps[capabilities.indexOf(p.capability)]||p.capability} · {w.scopes[p.scope]}{p.target&&<> · {p.target.name} · {p.target.id}</>} · {p.id}{target&&<> <button type="button" data-relation-open-customer={target.id} aria-label={`${w.viewCustomer}: ${target.name} · ${target.id}`} onClick={()=>showGroup('customer',target.id)}>{w.viewCustomer}</button></>}</li>;
 })}</ul>;
 const list=(items,label)=><section aria-label={label}><h4>{label} · {items.length}</h4>{items.length?<ul>{items.map(x=><li key={x.id}>{x.name??x.userName} · {x.id}{x.active===false&&' · '+w.inactive}</li>)}</ul>:<p>{w.empty}</p>}</section>;
 return <section className="rc-detail" data-admin-group-relations aria-label={w.title} style={{minWidth:0,overflowWrap:'anywhere'}}>
  <h3>{w.title}</h3><p>{w.help}</p>
  <div className="rc-form"><label>{w.type}<select name="relationGroupType" value={kind} onChange={e=>{navigation.current=null;setKind(e.target.value);setSelected('')}}><option value="user">{w.user}</option><option value="customer">{w.customer}</option></select></label>
  <label>{w.group}<select ref={groupSelect} name="relationGroupId" value={group?selected:''} disabled={!data} onChange={e=>{navigation.current=null;setSelected(e.target.value)}} style={{minWidth:0,maxWidth:'100%'}}><option value="">{w.choose}</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name} · {g.id}</option>)}</select></label></div>
  <p role="status" aria-live="polite" aria-atomic="true" data-relation-selection-status style={{position:'absolute',width:1,height:1,padding:0,margin:-1,overflow:'hidden',clipPath:'inset(50%)',whiteSpace:'nowrap',border:0}}>{!data?w.unavailable:group?`${w.group}: ${group.name} · ${group.id}`:w.choose}</p>
  {!data?<p>{w.unavailable}</p>:<><p>{w.revision} · {data.revision}</p>{group&&<article data-relation-group={group.id}><h3>{group.name}</h3><p>{group.id}</p>{kind==='user'?<>{list(group.members,w.members)}<section aria-label={w.grants}><h4>{w.grants} · {group.grants.length}</h4>{group.grants.length?grants(group.grants):<p>{w.empty}</p>}</section></>:<>{list(group.customers,w.customers)}<section aria-label={w.sources}><h4>{w.sources}</h4>{data.userGroups.filter(g=>g.grants.some(p=>p.scope==='customerGroup'&&p.target?.id===group.id)).map(g=><article key={g.id} data-relation-source={g.id}><h5>{g.name} · {g.id}</h5><button type="button" data-relation-open-user={g.id} aria-label={`${w.viewUser}: ${g.name} · ${g.id}`} onClick={()=>showGroup('user',g.id)}>{w.viewUser}</button>{grants(g.grants.filter(p=>p.scope==='customerGroup'&&p.target?.id===group.id))}</article>)}{!data.userGroups.some(g=>g.grants.some(p=>p.scope==='customerGroup'&&p.target?.id===group.id))&&<p>{w.empty}</p>}</section></>}</article>}</>}
 </section>;
}
