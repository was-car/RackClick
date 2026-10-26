export const groupReceiptWords = {
 en:{title:'Group created',userGroup:'User group',customerGroup:'Customer group',saved:'Creation confirmed by the server. Opening relationships does not assign members or permissions.',open:'Open relationships',loading:'Wait for the current groups to finish loading.',pending:'The confirmed result is retained. Resolve the pending recovery request before continuing.',refresh:'Refresh groups to load a valid current snapshot before continuing.',missing:'This group is absent from the current snapshot. No other group with the same name will be selected.'},
 de:{title:'Gruppe angelegt',userGroup:'Benutzergruppe',customerGroup:'Kundengruppe',saved:'Anlage vom Server bestätigt. Das Öffnen der Beziehungen weist keine Mitglieder oder Berechtigungen zu.',open:'Beziehungen öffnen',loading:'Warten, bis die aktuellen Gruppen geladen sind.',pending:'Das bestätigte Ergebnis bleibt erhalten. Vor dem Fortfahren den ausstehenden Wiederherstellungsauftrag klären.',refresh:'Gruppen aktualisieren, um vor dem Fortfahren einen gültigen aktuellen Snapshot zu laden.',missing:'Diese Gruppe fehlt im aktuellen Snapshot. Keine andere Gruppe mit demselben Namen wird ausgewählt.'},
 es:{title:'Grupo creado',userGroup:'Grupo de usuarios',customerGroup:'Grupo de clientes',saved:'Alta confirmada por el servidor. Abrir relaciones no asigna miembros ni permisos.',open:'Abrir relaciones',loading:'Espera a que termine la lectura de los grupos vigentes.',pending:'El resultado confirmado se conserva. Resuelve la solicitud de recuperación pendiente antes de continuar.',refresh:'Actualiza los grupos para leer un snapshot vigente válido antes de continuar.',missing:'Este grupo no está en el snapshot vigente. No se elegirá otro grupo con el mismo nombre.'}
};

export function AdminGroupReceipt({receipt,actor,lang,blocked,onContinue}) {
 if(!receipt||receipt.actorId!==actor)return null;
 const w=groupReceiptWords[lang];
 return <section className="rc-detail rc-admin-section" data-group-receipt={receipt.groupId} aria-label={w.title} style={{minWidth:0,overflowWrap:'anywhere'}}>
  <h3>{w.title}</h3><p><strong>{receipt.name}</strong> · {w[receipt.kind]} · {receipt.groupId}</p><p>{w.saved}</p>
  <button type="button" data-group-receipt-open disabled={!!blocked} onClick={onContinue}>{w.open}</button>
  <p role="status" aria-live="polite" aria-atomic="true" data-group-receipt-blocked={blocked||''}>{blocked?w[blocked]:`${w.title}: ${receipt.name} · ${w[receipt.kind]} · ${receipt.groupId}`}</p>
 </section>;
}
