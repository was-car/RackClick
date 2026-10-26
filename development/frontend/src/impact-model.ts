import { roomPath, type Project } from './inventory-model.ts';

// IDs from the server remain authoritative; labels only explain the confirmed impact.
export function impactSections(impact: Record<string, string[]>, project: Project, words: Record<string, string>) {
 const rack = (id: string) => project.racks.find(r => r.id === id);
 const device = (id: string) => project.devices.find(d => d.id === id);
 const group = (id: string) => project.portGroups.find(g => g.id === id);
 const rackName = (id: string) => { const r = rack(id); return r ? [...roomPath(project, r.roomId), r.name].join(' / ') : id; };
 const deviceName = (id: string) => {
  const d = device(id); if (!d) return id;
  return [...(d.rackId ? [rackName(d.rackId)] : roomPath(project, d.roomId)), d.name].join(' / ');
 };
 const groupName = (id: string) => { const g = group(id); return g ? g.name || `${g.type.toUpperCase()} · ${g.sortOrder + 1}` : id; };
 const portName = (id: string) => {
  const p = project.ports.find(p => p.id === id); if (!p) return id;
  return `${deviceName(p.deviceId)} / ${groupName(p.groupId)} / #${group(p.groupId)?.prefix || ''}${p.gn}${p.label ? ' · ' + p.label : ''}`;
 };
 const definitions: Record<string, { label: string; name: (id: string) => string }> = {
  rackIds: { label: words.rack, name: rackName },
  deviceIds: { label: words.device, name: deviceName },
  groupIds: { label: words.groups, name: id => { const g = group(id); return g ? `${deviceName(g.deviceId)} / ${groupName(id)}` : id; } },
  portIds: { label: words.ports, name: portName },
  connectionIds: { label: words.connections, name: id => {
   const c = project.connections.find(c => c.id === id);
   return c ? `${portName(c.fromPortId)} → ${portName(c.toPortId)}${c.note ? ' · ' + c.note : ''}` : id;
  } }
 };
 return Object.entries(impact).filter(([, ids]) => Array.isArray(ids) && ids.length).map(([kind, ids]) => ({
  kind, label: definitions[kind]?.label || words.affected,
  entries: ids.map(id => ({ id, label: definitions[kind]?.name(id) || id }))
 }));
}
