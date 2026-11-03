import reference from './hardware-catalog.generated.json' with {type:'json'};
import commercial from './hardware-commercial.generated.json' with {type:'json'};
import aruba from './hardware-aruba.generated.json' with {type:'json'};
import fortinet from './hardware-fortinet.generated.json' with {type:'json'};
import synology from './hardware-synology.generated.json' with {type:'json'};
import diskstation from './hardware-diskstation.generated.json' with {type:'json'};
import qnap from './hardware-qnap.generated.json' with {type:'json'};
import batch50 from './hardware-batch50.generated.json' with {type:'json'};
import batch50b from './hardware-batch50b.generated.json' with {type:'json'};
import batch100 from './hardware-batch100.generated.json' with {type:'json'};
import batch100b from './hardware-batch100b.generated.json' with {type:'json'};
import batch100c from './hardware-batch100c.generated.json' with {type:'json'};
import selected506a from './hardware-selected506a.generated.json' with {type:'json'};
import selected506b from './hardware-selected506b.generated.json' with {type:'json'};
import selected506c from './hardware-selected506c.generated.json' with {type:'json'};
import selected506d from './hardware-selected506d.generated.json' with {type:'json'};
import selected506e from './hardware-selected506e.generated.json' with {type:'json'};
import selected506f from './hardware-selected506f.generated.json' with {type:'json'};
import selected506g from './hardware-selected506g.generated.json' with {type:'json'};
import selected506h from './hardware-selected506h.generated.json' with {type:'json'};
import selected506i from './hardware-selected506i.generated.json' with {type:'json'};
import selected506j from './hardware-selected506j.generated.json' with {type:'json'};
import selected506k from './hardware-selected506k.generated.json' with {type:'json'};
import selected506l from './hardware-selected506l.generated.json' with {type:'json'};
import germanCpe from './hardware-german-cpe.generated.json' with {type:'json'};
import germanRepeaters from './hardware-german-repeaters.generated.json' with {type:'json'};
import {createHardwareRegistry} from './hardware-registry.ts';
import {extendedHardwareCreateCommand,extendedRecordedMountValid} from './hardware-mounting-l.ts';
export const hardwareRegistry = createHardwareRegistry([reference,commercial,aruba,fortinet,synology,...diskstation,qnap,...batch50,...batch50b,...batch100,...batch100b,...batch100c,...selected506a,...selected506b,...selected506c,...selected506d,...selected506e,...selected506f,...selected506g,...selected506h,...selected506i,...selected506j,...selected506k,...selected506l,...germanCpe,...germanRepeaters]);
export const hardwareReference = hardwareRegistry.catalogues[0];
export const hardwareChoices = Object.freeze(hardwareRegistry.catalogues.flatMap(c=>c.profiles.map(p=>Object.freeze({...p,revision:c.version}))));
// Snapshot shape validation does not substitute a revision or grant permissions.
// Known keys may retain an unavailable recorded revision and use the generic face.
export const knownDesktopHardwareKey = (key: unknown) => hardwareChoices.some(p=>p.key===key&&p.kind==='desktop');
export const knownShelfHardwareKey = (key: unknown) => hardwareChoices.some(p=>p.key===key&&p.kind==='shelf');
export function hardwareShelfProfile(device: any) {
 if(!device||device.mountParentId)return undefined;
 const profile=hardwareProfile(device.hardwareProfileKey,device.properties?.hardwareProfileVersion);
 return profile?.kind==='shelf'&&profile.slot?profile:undefined;
}
export const hardwareFitsShelf = (profile: any, shelf: any) => profile?.kind==='desktop'&&shelf?.kind==='shelf'&&!!shelf.slot&&
 ['width','height','depth'].every(d=>Number.isFinite(profile[d+'Mm'])&&Number.isFinite(shelf.slot[d+'Mm'])&&profile[d+'Mm']>0&&profile[d+'Mm']<=shelf.slot[d+'Mm']);
// An unavailable recorded revision remains displayable without borrowing another
// revision's dimensions. Known revisions must fit their known support.
export function recordedMountFits(device: any,parent: any) {
 const child=hardwareProfile(device.hardwareProfileKey,device.properties?.hardwareProfileVersion),shelf=hardwareShelfProfile(parent);
 return !child||!shelf||hardwareFitsShelf(child,shelf);
}
export const hardwareChoiceValue = (p: any) => JSON.stringify([p.key,p.revision]);
export const hardwareProfile = (key: string | null | undefined, version: string | null | undefined) => hardwareRegistry.find(key,version);
export const hardwareRequestedVersion = (form: any) => Object.prototype.hasOwnProperty.call(form,'profileVersion') ? form.profileVersion : hardwareReference.version;
export function hardwareCreateCommand(form: any, project: any) {
 const version=hardwareRequestedVersion(form);
 const profile = hardwareProfile(form.profileKey,version);
 if (!profile) throw {status:422,code:'hardware_profile_invalid'};
 const extended=extendedHardwareCreateCommand(form,project,profile,version,hardwareProfile);
 if(extended)return extended;
 if(!project.racks.some((r: any) => r.id === form.rackId))throw {status:422,code:'hardware_profile_invalid'};
 const payload: any = {profileKey:profile.key, profileVersion:version, rackId:form.rackId, name:form.name};
 if (profile.kind === 'desktop') {
  const parent = project.devices.find((d: any) => d.id === form.mountParentId && d.rackId === form.rackId && !d.mountParentId);
  const shelf=hardwareShelfProfile(parent);
  if (!parent || !shelf) throw {status:422,code:'mount_parent_invalid'};
  if (!hardwareFitsShelf(profile,shelf)) throw {status:422,code:'mount_dimensions_invalid'};
  payload.mountParentId = parent.id; payload.mountSlotKey = 'main';
 }
 return {type:'device.createHardware',payload};
}
export function mountOccupancy(devices: any[]) {
 return devices.filter(d => !d.mountParentId).reduce((sum, d) => sum + (d.sizeU ?? d.u ?? 0), 0);
}
export function validMounts(devices: any[]) {
 const occupied = new Set();
 return devices.every(d => {
  const extended=extendedRecordedMountValid(d,devices,hardwareProfile);
  if(extended!==null){if(!extended)return false;if(d.kind!=='rackEquipment')return true;const key=d.rackId+':'+(d.mountParentId||'')+':'+d.mountSlotKey;if(occupied.has(key))return false;occupied.add(key);return true;}
  if (!d.mountParentId) return !d.mountSlotKey && d.sizeU > 0;
  const parent = devices.find(p => p.id === d.mountParentId);
  const key = d.mountParentId + ':' + d.mountSlotKey;
  if (!parent || parent.mountParentId || parent.rackId !== d.rackId || !knownShelfHardwareKey(parent.hardwareProfileKey) || !knownDesktopHardwareKey(d.hardwareProfileKey) || d.mountSlotKey !== 'main' || d.sizeU !== 0 || occupied.has(key) || !recordedMountFits(d,parent)) return false;
  occupied.add(key); return true;
 });
}

// Stable root order with each child kept immediately after its owning support.
export function expandMountOrder(devices: any[], roots: string[]) {
 return roots.flatMap(id => [id,...devices.filter(d=>d.mountParentId===id).map(d=>d.id)]);
}
