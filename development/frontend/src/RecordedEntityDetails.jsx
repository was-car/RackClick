import {changeDetailWords,changeEntityRows,changeEntitySummary} from './client-change-detail-words.ts';

export function RecordedEntitySummary({details,lang}){
 const summary=changeEntitySummary(details),w=changeDetailWords[lang];
 if(!summary?.entities.length)return null;
 return <p data-change-entity-summary>{summary.entities.map((entity,index)=><React.Fragment key={entity.kind+':'+entity.id}>{index>0?' · ':''}<span data-change-summary-entity={entity.id}>{w.kinds[entity.kind]}: {entity.name||w.empty}</span></React.Fragment>)}{summary.more&&<> · {w.extra}</>}</p>;
}
export function RecordedEntityDetails({details,lang}){
 const w=changeDetailWords[lang];
 if(details.status==='notAvailable')return <p data-change-entities-unavailable>{w.missing}</p>;
 return <section data-change-entities><h4>{w.title}</h4><p>{w.help}</p>{[['before',details.beforeEntities],['after',details.afterEntities]].map(([side,items])=><section key={side} data-change-entity-side={side}><h5>{w[side]}</h5>{items.length?<ul>{items.map(entity=><li key={entity.kind+':'+entity.id+':'+entity.relation} data-change-entity-id={entity.id} data-change-entity-kind={entity.kind} data-change-entity-relation={entity.relation}><p><strong>{w.kinds[entity.kind]}</strong> · {w.relations[entity.relation]}</p><dl>{changeEntityRows(entity,lang).map(row=><React.Fragment key={row.field}><dt>{row.label}</dt><dd data-change-entity-field={row.field} style={{whiteSpace:'pre-wrap',marginInlineStart:12}}>{row.value}</dd></React.Fragment>)}</dl></li>)}</ul>:<p>{w.none}</p>}</section>)}</section>;
}
