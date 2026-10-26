import { inventoryWords } from './inventory-words.ts';
import { groupCompensationWords } from './inventory-group-compensation-words.ts';

export function InventoryGroupCompensationScope({ candidate, project, lang, confirmed, onConfirm, disabled }) {
 const w=inventoryWords[lang], words=groupCompensationWords[lang];
 const lists=[[w.groups,candidate.groupIds,'group'],[w.ports,candidate.portIds,'port'],[w.connections,candidate.connectionIds,'connection']];
 return <section data-compensation-scope data-group-compensation={candidate.compensationKind} style={{overflowWrap:'anywhere'}}>
  <p>{words[candidate.compensationKind]}</p>
  <p>{w.device}: {project.devices.find(device=>device.id===candidate.deviceId)?.name} · {candidate.deviceId}</p>
  {lists.map(([label,ids,kind])=><details key={kind} open><summary>{label}: {ids.length}</summary><ul>{ids.map(id=><li key={id} {...{['data-undo-'+kind]:id}}>{id}</li>)}</ul></details>)}
  <p>{words.limits}</p><p className="rc-muted">{words.context}</p>
  <div className="rc-port-selection"><label><input data-confirm-group-undo type="checkbox" required checked={confirmed} disabled={disabled} onChange={event=>onConfirm(event.target.checked)}/>{words.confirm}</label></div>
 </section>;
}
