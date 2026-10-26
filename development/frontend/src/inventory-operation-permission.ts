const deleteTypes = new Set(['site.delete', 'building.delete', 'room.delete', 'rack.delete', 'device.delete', 'devices.delete']);

// A recovery keeps the original command's permission, regardless of its UI label.
// This only selects GUI controls; the server checks current authorization again.
export function inventoryWriteCapability(draft, recovery) {
 if (recovery) {
  try {
   const type = JSON.parse(recovery.operation.body)?.type;
   if (typeof type !== 'string' || !type) return null;
   return deleteTypes.has(type) ? 'inventory.delete' : type.endsWith('.delete') ? null : 'inventory.edit';
  } catch { return null; }
 }
 if (!draft) return null;
 const capability = draft.requiredCapability ?? 'inventory.edit';
 return capability === 'inventory.edit' || capability === 'inventory.delete' ? capability : null;
}
