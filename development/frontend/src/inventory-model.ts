import {knownDesktopHardwareKey,knownShelfHardwareKey,recordedMountFits,hardwareProfile} from './hardware-mounting.ts';
import {recordedConnectorDescriptor,recordedGroupClassification} from './hardware-connector-classification.mjs';
import {extendedRecordedMountValid} from './hardware-mounting-l.ts';
export type Site = { id: string; name: string; properties: Record<string, any> };
export type Building = Site & { siteId: string };
export type Room = Site & { buildingId: string };
export type Rack = Site & { roomId: string | null; location: string; sizeU: number; hardwareProfileKey?:string|null; hardwareProfileVersion?:string|null };
export type Device = Site & { kind: 'rackEquipment' | 'dose' | 'endDevice'; rackId: string | null; roomId: string | null; sizeU: number | null; sortOrder: number; poeBudget: number | null; hardwareProfileKey?: string | null; mountParentId?: string | null; mountSlotKey?: string | null };
export type PortGroup = { id: string; deviceId: string; type: string; name: string; prefix: string; sortOrder: number };
export type Port = { id: string; deviceId: string; groupId: string; type: string; gn: number; sortOrder: number; label: string; status: string; poe: boolean; watts: number | null; color: string | null; face: string; powerRole: string; properties: Record<string, any> };
export type Connection = { id: string; fromPortId: string; toPortId: string; note: string; color: string | null; patch: string; properties: Record<string, any> };
export type Project = { customerId: string; revision: number; sites: Site[]; buildings: Building[]; rooms: Room[]; racks: Rack[]; devices: Device[]; portGroups: PortGroup[]; ports: Port[]; connections: Connection[] };
const collections = ['sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections'];
export function validProject(value: any, customerId: string): value is Project {
 if (!(value?.customerId === customerId && Number.isSafeInteger(value.revision) && value.revision > 0 && collections.every(key => Array.isArray(value[key]) && value[key].every((x: any) => typeof x?.id === 'string' && x.id.length) && new Set(value[key].map((x: any) => x.id)).size === value[key].length))) return false;
 const has = (key: string, id: string) => value[key].some((x: any) => x.id === id);
 const named = (x: any) => typeof x.name === 'string' && x.properties && typeof x.properties === 'object';
 if (!['sites','buildings','rooms','racks','devices'].every(key => value[key].every(named))) return false;
 if (!value.buildings.every((x: any) => has('sites',x.siteId)) || !value.rooms.every((x: any) => has('buildings',x.buildingId))) return false;
 if (!value.racks.every((x: any) => (x.roomId === null || has('rooms',x.roomId)) && Number.isInteger(x.sizeU) && x.sizeU > 0)) return false;
 if (!value.devices.every((x: any) => x.kind === 'rackEquipment' ? has('racks',x.rackId) && x.roomId === null && Number.isInteger(x.sizeU) && (x.mountParentId || hardwareProfile(x.hardwareProfileKey,x.properties?.hardwareProfileVersion)?.kind==='vertical0U' ? x.sizeU === 0 : x.sizeU > 0) : ['dose','endDevice'].includes(x.kind) && has('rooms',x.roomId) && x.rackId === null && x.sizeU === null)) return false;
 const mountSlots = new Set();
 if (!value.devices.every((d: any) => {
  const extended=extendedRecordedMountValid(d,value.devices,hardwareProfile);
  if(extended!==null){if(!extended)return false;const key=d.rackId+':'+(d.mountParentId||'')+':'+d.mountSlotKey;if(d.kind==='rackEquipment'&&mountSlots.has(key))return false;if(d.kind==='rackEquipment')mountSlots.add(key);return true;}
  if (!d.mountParentId) return !d.mountSlotKey;
  const parent = value.devices.find((p: any) => p.id === d.mountParentId), key=d.mountParentId+':'+d.mountSlotKey;
  if (d.kind !== 'rackEquipment' || !parent || parent.mountParentId || parent.rackId !== d.rackId || !knownShelfHardwareKey(parent.hardwareProfileKey) || !knownDesktopHardwareKey(d.hardwareProfileKey) || d.mountSlotKey !== 'main' || mountSlots.has(key) || !recordedMountFits(d,parent)) return false;
  mountSlots.add(key); return true;
 })) return false;
 if (!value.portGroups.every((x: any) => has('devices',x.deviceId) && typeof x.type === 'string')) return false;
 if (!value.ports.every((x: any) => has('devices',x.deviceId) && value.portGroups.some((g: any) => g.id === x.groupId && g.deviceId === x.deviceId) && Number.isInteger(x.gn) && x.gn > 0 && typeof x.type === 'string')) return false;
 const occupied = new Set();
 return value.connections.every((x: any) => { if (!has('ports',x.fromPortId) || !has('ports',x.toPortId) || x.fromPortId === x.toPortId || occupied.has(x.fromPortId) || occupied.has(x.toPortId)) return false; occupied.add(x.fromPortId); occupied.add(x.toPortId); return true; });
}
const ordered = <T extends { id: string; sortOrder: number }>(items: T[]) => [...items].sort((a, b) => a.sortOrder - b.sortOrder || a.id.localeCompare(b.id));
export function roomPath(project: Project, roomId: string | null): string[] {
 const room = project.rooms.find(x => x.id === roomId), building = project.buildings.find(x => x.id === room?.buildingId), site = project.sites.find(x => x.id === building?.siteId);
 return [site?.name, building?.name, room?.name].filter((x): x is string => !!x);
}
function recordedDimensions(properties: any) {
 const value=properties?.physicalDimensionsMm;
 return value && ['width','height','depth'].every(key=>typeof value[key]==='number'&&Number.isFinite(value[key])&&value[key]>0)
  ? {width:value.width,height:value.height,depth:value.depth} : null;
}
// Projection only. DTO identities and relationships are never inferred from names or gn.
export function projectToRc9(snapshot: Project, customerName: string) {
 const groups = new Map(snapshot.portGroups.map(x => [x.id, x]));
 const devices = new Map(snapshot.devices.map(d => [d.id, {
  id: d.id, name: d.name, kind: d.kind, rackId: d.rackId, roomId: d.roomId, u: d.sizeU,
   hardwareProfileVersion: typeof d.properties?.hardwareProfileVersion==='string'?d.properties.hardwareProfileVersion:null, physicalDimensionsMm:recordedDimensions(d.properties),
   hardwareIdentity:d.properties?.hardwareIdentity&&['manufacturer','family','model','sku'].every(k=>typeof d.properties.hardwareIdentity[k]==='string')?{...d.properties.hardwareIdentity}:null,
  hardwareProfileKey: d.hardwareProfileKey ?? null, mountParentId: d.mountParentId ?? null, mountSlotKey: d.mountSlotKey ?? null,
  preset: d.properties?.preset || '', icon: d.properties?.icon || '▥', color: d.properties?.color || '#457b9d', notes: { ...(d.properties?.notes || {}) }, poeBudget: d.poeBudget,
  ports: ordered(snapshot.ports.filter(p => p.deviceId === d.id)).map(p => ({ id: p.id, groupId: p.groupId, type: p.type, gn: p.gn, label: p.label, status: p.status, poe: p.poe, watts: p.watts === null ? undefined : p.watts, portColor: p.color, rackclickFace: p.face === 'auto' ? undefined : p.face, rackclickPowerRole: p.powerRole, rackclickPhysicalConnector:recordedConnectorDescriptor(d,p,hardwareProfile),rackclickPhysicalFace:recordedGroupClassification(d,p,hardwareProfile,'physicalFace'),rackclickInterfaceRole:recordedGroupClassification(d,p,hardwareProfile,'interfaceRole'),rackclickSignalRole:recordedGroupClassification(d,p,hardwareProfile,'signalRole'),rackclickPowerSystem:recordedGroupClassification(d,p,hardwareProfile,'powerSystem'), rackclickHardwareGroupKey:typeof p.properties?.hardwareGroupKey==='string'?p.properties.hardwareGroupKey:null, groupName: groups.get(p.groupId)?.name, groupPrefix: groups.get(p.groupId)?.prefix || '' }))
 }]));
 const ports = new Map(snapshot.ports.map(p => [p.id, p])), rackNames = new Map(snapshot.racks.map(r => [r.id, r.name]));
 const serverEndpoints: Record<string, string> = {};
 for (const p of snapshot.ports) {
  const d = devices.get(p.deviceId); if (!d) throw Error('Snapshot port owner is missing');
  const location = d.rackId ? rackNames.get(d.rackId) : roomPath(snapshot, d.roomId).join(' / ');
  const group = groups.get(p.groupId); if (!group || group.deviceId !== d.id) throw Error('Snapshot port group owner mismatch');
  serverEndpoints[p.id] = `${location || ''} / ${d.name} · ${group.name ? group.name + ' · ' : ''}#${group.prefix || ''}${p.gn}${p.label ? ' · ' + p.label : ''}`;
 }
 const connections = snapshot.connections.map(c => {
  const fp = ports.get(c.fromPortId), tp = ports.get(c.toPortId);
  if (!fp || !tp) throw Error('Snapshot connection endpoint missing');
  const fd = devices.get(fp.deviceId)!, td = devices.get(tp.deviceId)!;
  return { id: c.id, fd: fd.id, td: td.id, fp: fp.id, tp: tp.id, fn: fd.name, tn: td.name, fpn: fp.gn, tpn: tp.gn, fpt2: fp.type, tpt2: tp.type, rackFrom: fd.rackId, rackTo: td.rackId, note: c.note, color: c.color, patchStatus: c.patch };
 });
 return { name: customerName, customerId: snapshot.customerId, revision: snapshot.revision, serverEndpoints, devices, connections,
  racks: snapshot.racks.map(r => ({ id: r.id, name: r.name, ...(r.hardwareProfileKey?{hardwareProfileKey:r.hardwareProfileKey,hardwareProfileVersion:r.properties?.hardwareProfileVersion}:{}), size: r.sizeU, location: r.location, roomId: r.roomId, rackclickLocation: { client: customerName, site: roomPath(snapshot, r.roomId)[0] || '', building: roomPath(snapshot, r.roomId)[1] || '', room: roomPath(snapshot, r.roomId)[2] || '' }, devs: ordered(snapshot.devices.filter(d => d.rackId === r.id && d.kind === 'rackEquipment')).map(d => devices.get(d.id)!), conns: connections.filter(c => c.rackFrom === r.id && c.rackTo === r.id) })),
  crossConns: connections.filter(c => !c.rackFrom || c.rackFrom !== c.rackTo)
 };
}
export function batchPortIds(snapshot: Project, deviceId: string, groupId: string, ids: string[]) {
 const group = snapshot.portGroups.find(g => g.id === groupId && g.deviceId === deviceId);
 if (!group || !ids.length || new Set(ids).size !== ids.length || ids.some(id => !snapshot.ports.some(p => p.id === id && p.deviceId === deviceId && p.groupId === groupId))) throw Error('Invalid explicit port selection');
 return { deviceId, groupId, expectedType: group.type, portIds: [...ids] };
}
export function reservedPortIds(snapshot: Project, ids: string[]) {
 return [...new Set(ids)].filter(id => snapshot.ports.find(p => p.id === id)?.status === 'reserved');
}
export function internalCablePortIds(snapshot: Project, rackId: string) {
 const deviceIds = new Set(snapshot.devices.filter(d => d.rackId === rackId).map(d => d.id));
 const ports = new Set(snapshot.ports.filter(p => deviceIds.has(p.deviceId)).map(p => p.id));
 return snapshot.connections.filter(c => ports.has(c.fromPortId) && ports.has(c.toPortId)).flatMap(c => [c.fromPortId,c.toPortId]);
}
