// Definitions are deployment data, not customer data. Snapshot before freezing so
// neither a caller nor an exported nested array can modify an accepted revision.
function freezeData(value: any): any {
 if (value && typeof value === 'object') { for (const item of Object.values(value)) freezeData(item);Object.freeze(value); }
 return value;
}
export function createHardwareRegistry(catalogues: any[]) {
 const entries = new Map<string, any>(), snapshots = [];
 for (const input of catalogues) {
  const catalogue = structuredClone(input);
  if (typeof catalogue?.version !== 'string' || !catalogue.version.trim() || catalogue.version.length > 128 || !Array.isArray(catalogue.profiles)) throw Error('hardware_catalog_invalid');
  for (const profile of catalogue.profiles) {
   if (typeof profile?.key !== 'string' || !profile.key.trim() || profile.key.length > 128 || !Array.isArray(profile.groups)) throw Error('hardware_catalog_invalid');
   const identity = JSON.stringify([profile.key,catalogue.version]);
   if (entries.has(identity)) throw Error('hardware_catalog_duplicate_revision');
   entries.set(identity,freezeData(profile));
  }
  snapshots.push(freezeData(catalogue));
 }
 return Object.freeze({catalogues:Object.freeze(snapshots),find:(key: unknown,version: unknown)=>typeof key==='string'&&typeof version==='string'?entries.get(JSON.stringify([key,version])):undefined});
}
