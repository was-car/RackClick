import type {ChangeEntity,ChangeDetails} from './client-change-details.ts';

export const changeDetailWords={
 en:{title:'Recorded inventory entities',help:'These names and immediate parent IDs were recorded with the change. They are independent of names in your loaded view. No complete historical location path is inferred.',missing:'No recorded inventory description is available for this event. Older events and changes exceeding the description limit are not reconstructed.',before:'Before',after:'After',none:'No entities on this side of the change.',name:'Recorded name',empty:'(empty name)',id:'ID',parent:'Immediate parent',unassigned:'Unassigned',deviceKind:'Device kind',rack:'Rack ID',room:'Room ID',sizeU:'Size (U)',sortOrder:'Stored order (starting at 0)',groupType:'Group connector family',prefix:'Recorded prefix',emptyPrefix:'(empty prefix)',portCount:'Port count',extra:'More entities in the recorded details',relations:{target:'Affected entity',source:'Duplication source',scope:'Operation scope'},kinds:{customer:'Client',site:'Site',building:'Building',room:'Room',rack:'Rack',device:'Device',portGroup:'Port group'},deviceKinds:{rackEquipment:'Rack equipment',dose:'Outlet (Dose)',endDevice:'End device'}},
 de:{title:'Protokollierte Inventarobjekte',help:'Diese Namen und unmittelbaren Eltern-IDs wurden beim Vorgang erfasst. Sie sind unabhängig von Namen der geladenen Ansicht. Ein vollständiger historischer Standortpfad wird nicht abgeleitet.',missing:'Für dieses Ereignis ist keine protokollierte Inventarbeschreibung verfügbar. Ältere Ereignisse und Änderungen oberhalb der Beschreibungsgrenze werden nicht rekonstruiert.',before:'Vorher',after:'Nachher',none:'Keine Objekte auf dieser Seite der Änderung.',name:'Protokollierter Name',empty:'(leerer Name)',id:'ID',parent:'Unmittelbares Elternobjekt',unassigned:'Nicht zugeordnet',deviceKind:'Geräteart',rack:'Rack-ID',room:'Raum-ID',sizeU:'Größe (HE)',sortOrder:'Gespeicherte Reihenfolge (ab 0)',groupType:'Anschlussfamilie der Gruppe',prefix:'Protokolliertes Präfix',emptyPrefix:'(leeres Präfix)',portCount:'Portanzahl',extra:'Weitere Objekte in den protokollierten Details',relations:{target:'Betroffenes Objekt',source:'Duplizierungsquelle',scope:'Vorgangsumfang'},kinds:{customer:'Kunde',site:'Standort',building:'Gebäude',room:'Raum',rack:'Rack',device:'Gerät',portGroup:'Portgruppe'},deviceKinds:{rackEquipment:'Rackgerät',dose:'Dose',endDevice:'Endgerät'}},
 es:{title:'Objetos de inventario registrados',help:'Estos nombres e IDs de padre inmediato se registraron con el cambio. Son independientes de los nombres de tu vista cargada. No se deduce una ruta histórica completa de ubicación.',missing:'No hay descripción de inventario registrada para este evento. No se reconstruyen eventos anteriores ni cambios que superan el límite de descripción.',before:'Antes',after:'Después',none:'Sin objetos en este lado del cambio.',name:'Nombre registrado',empty:'(nombre vacío)',id:'ID',parent:'Padre inmediato',unassigned:'Sin asignar',deviceKind:'Clase de equipo',rack:'ID de rack',room:'ID de sala',sizeU:'Tamaño (U)',sortOrder:'Orden guardado (desde 0)',groupType:'Familia de conectores del grupo',prefix:'Prefijo registrado',emptyPrefix:'(prefijo vacío)',portCount:'Cantidad de puertos',extra:'Más objetos en el detalle registrado',relations:{target:'Objeto afectado',source:'Origen de duplicación',scope:'Ámbito de la operación'},kinds:{customer:'Cliente',site:'Sede',building:'Edificio',room:'Sala',rack:'Rack',device:'Equipo',portGroup:'Grupo de puertos'},deviceKinds:{rackEquipment:'Equipo de rack',dose:'Toma (Dose)',endDevice:'Dispositivo final'}}
};
export type ChangeDetailLanguage=keyof typeof changeDetailWords;
// Values remain literal; only field names and fixed domain terms are translated.
export function changeEntityRows(entity:ChangeEntity,lang:ChangeDetailLanguage){
 const w=changeDetailWords[lang],rows=[{field:'name',label:w.name,value:entity.name||w.empty},{field:'id',label:w.id,value:entity.id},{field:'parent',label:w.parent,value:entity.parentId?w.kinds[entity.parentKind!]+': '+entity.parentId:w.unassigned}];
 if(entity.deviceKind!==null)rows.push({field:'deviceKind',label:w.deviceKind,value:w.deviceKinds[entity.deviceKind]});
 if(entity.rackId!==null)rows.push({field:'rackId',label:w.rack,value:entity.rackId});
 if(entity.roomId!==null)rows.push({field:'roomId',label:w.room,value:entity.roomId});
 if(entity.sizeU!==null)rows.push({field:'sizeU',label:w.sizeU,value:String(entity.sizeU)});
 if(entity.sortOrder!==null)rows.push({field:'sortOrder',label:w.sortOrder,value:String(entity.sortOrder)});
 if(entity.groupType!==null)rows.push({field:'groupType',label:w.groupType,value:entity.groupType});
 if(entity.prefix!==null)rows.push({field:'prefix',label:w.prefix,value:entity.prefix||w.emptyPrefix});
 if(entity.portCount!==null)rows.push({field:'portCount',label:w.portCount,value:String(entity.portCount)});
 return rows;
}
export function changeEntitySummary(details:ChangeDetails){
 if(details.status!=='captured')return null;
 const select=(items:ChangeEntity[])=>items.filter(e=>e.relation!=='scope'&&e.kind!=='portGroup'),after=select(details.afterEntities),items=after.length?after:select(details.beforeEntities);
 // A bounded visual summary only; the full server-provided description is kept below.
 return {entities:items.slice(0,3),more:items.length>3};
}
