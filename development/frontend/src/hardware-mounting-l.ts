// Additional mounting contracts; legacy shelf behaviour remains in its module.
export const roomHardwareKinds=Object.freeze(['wall','pole','din','floor','tabletop']);
export const isRoomHardware=(p:any)=>roomHardwareKinds.includes(p?.kind);
export const isZeroURackHardware=(p:any)=>p?.kind==='vertical0U';
export const hardwareMountTarget=(p:any)=>p?.mounting?.target||(p?.kind==='desktop'?'parent':'rack');
export const parentAcceptsShared=(p:any,parent:any,parentProfile:any)=>p?.kind==='sharedU'&&!!parent&&
 !parent.mountParentId&&parent.kind==='rackEquipment'&&parent.sizeU>0&&
 (!parent.hardwareProfileKey||['rack','shelf'].includes(parentProfile?.kind))&&
 (!p.mounting?.parentProfileKeys||p.mounting.parentProfileKeys.includes(parent.hardwareProfileKey));

export function extendedHardwareCreateCommand(form:any,project:any,profile:any,version:string,findProfile:any){
 const payload:any={profileKey:profile.key,profileVersion:version,name:form.name};
 if(profile.kind==='rackContainer'||isRoomHardware(profile)){
  if(!project.rooms?.some((r:any)=>r.id===form.roomId))throw {status:422,code:'room_invalid'};
  payload.roomId=form.roomId;
  return {type:profile.kind==='rackContainer'?'rack.createHardware':'device.createHardware',payload};
 }
 if(!['sharedU','vertical0U'].includes(profile.kind))return null;
 const rack=project.racks?.find((r:any)=>r.id===form.rackId);
 if(!rack)throw {status:422,code:'rack_invalid'};
 payload.rackId=rack.id;
 if(profile.kind==='vertical0U'){
  if(!['vertical-left','vertical-right'].includes(form.mountSlotKey))throw {status:422,code:'mount_slot_invalid'};
  if(!Number.isFinite(profile.heightMm)||profile.heightMm>rack.sizeU*44.45)throw {status:422,code:'mount_dimensions_invalid'};
  if(project.devices.some((d:any)=>d.rackId===rack.id&&!d.mountParentId&&d.mountSlotKey===form.mountSlotKey))throw {status:409,code:'mount_slot_occupied'};
  payload.mountSlotKey=form.mountSlotKey;
 }else{
  const parent=project.devices.find((d:any)=>d.id===form.mountParentId&&d.rackId===rack.id);
  if(!parentAcceptsShared(profile,parent,findProfile(parent?.hardwareProfileKey,parent?.properties?.hardwareProfileVersion)))throw {status:422,code:'mount_parent_invalid'};
  if(project.devices.some((d:any)=>d.mountParentId===parent.id&&d.mountSlotKey==='shared'))throw {status:409,code:'mount_slot_occupied'};
  payload.mountParentId=parent.id;payload.mountSlotKey='shared';
 }
 return {type:'device.createHardware',payload};
}

export function extendedRecordedMountValid(device:any,devices:any[],findProfile:any){
 const p=findProfile(device.hardwareProfileKey,device.properties?.hardwareProfileVersion);
 if(p?.kind==='vertical0U')return device.kind==='rackEquipment'&&device.sizeU===0&&!device.mountParentId&&['vertical-left','vertical-right'].includes(device.mountSlotKey);
 if(p?.kind==='sharedU'){
  const parent=devices.find(d=>d.id===device.mountParentId);
  return device.kind==='rackEquipment'&&device.sizeU===0&&device.mountSlotKey==='shared'&&parent?.rackId===device.rackId&&parentAcceptsShared(p,parent,findProfile(parent?.hardwareProfileKey,parent?.properties?.hardwareProfileVersion));
 }
 if(isRoomHardware(p))return device.kind==='endDevice'&&device.sizeU===null&&!device.rackId&&!device.mountParentId&&!device.mountSlotKey;
 return null;
}
