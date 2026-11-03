import {isExtendedConnector,extendedConnectorLabel} from './hardware-connector-family-l.mjs';
// Physical description only. Cable ends, electrical ratings and pinouts are not inferred.
export const connectorDescriptors=Object.freeze({
 power:Object.freeze(['iec-c13','iec-c14','iec-c19','iec-c20','nema-5-15p','nema-5-15r','nema-5-20p','nema-5-20r','nema-l5-30p','nema-l5-30r','nema-l6-20p','nema-l6-20r','nema-l6-30p','nema-l6-30r','iec60309-16a-2p-e-plug','iec60309-16a-2p-e-connector','iec60309-32a-2p-e-plug']),
 console:Object.freeze(['serial-8p8c','serial-10p10c','serial-de9','serial-rj12']),
 idc:Object.freeze(['idc-110','idc-dual-110-krone'])
});
export function validConnectorDescriptor(type,value){return typeof value==='string'&&!!connectorDescriptors[type]?.includes(value)||isExtendedConnector(type,value);}
export function connectorDescriptorLabel(type,value){
 if(isExtendedConnector(type,value))return extendedConnectorLabel(type,value);
 if(!validConnectorDescriptor(type,value))return type==='idc'?'IDC':type==='console'?'SERIAL':type;
 return {'serial-8p8c':'SERIAL 8P8C','serial-10p10c':'SERIAL 10P10C','serial-de9':'SERIAL DE-9','serial-rj12':'SERIAL RJ12','idc-110':'IDC 110','idc-dual-110-krone':'IDC 110/Krone'}[value]||value.replace(/^iec60309-/,'IEC 60309 ').replace(/^iec-/,'IEC ').replace(/^nema-/,'NEMA ').toUpperCase();
}
// Do not promote arbitrary properties of legacy or manually created ports into
// authenticated catalogue classification. All three bindings must agree.
export function recordedConnectorDescriptor(device,port,findProfile){
 const version=device?.properties?.hardwareProfileVersion;
 if(typeof device?.hardwareProfileKey!=='string'||typeof version!=='string'||typeof findProfile!=='function')return null;
 const profile=findProfile(device.hardwareProfileKey,version);
 if(!profile||device.hardwareProfileKey!==profile.key)return null;
 const group=profile.groups?.find(g=>g.key===port.properties?.hardwareGroupKey);
 const value=port.properties?.hardwarePhysicalConnector;
 return group&&group.type===port.type&&group.face===port.face&&
   group.physicalConnector===value&&validConnectorDescriptor(port.type,value)?value:null;
}

const recordedGroupFields=Object.freeze({physicalFace:'hardwarePhysicalFace',interfaceRole:'hardwareInterfaceRole',signalRole:'hardwareSignalRole',powerSystem:'hardwarePowerSystem'});
export function recordedGroupClassification(device,port,findProfile,field){
 if(!Object.hasOwn(recordedGroupFields,field))return null;
 const version=device?.properties?.hardwareProfileVersion;
 if(typeof device?.hardwareProfileKey!=='string'||typeof version!=='string'||typeof findProfile!=='function')return null;
 const profile=findProfile(device.hardwareProfileKey,version),group=profile?.groups?.find(g=>g.key===port.properties?.hardwareGroupKey);
 const value=port.properties?.[recordedGroupFields[field]];
 return group&&profile.key===device.hardwareProfileKey&&(group.type===port.type||group.type==='rj45'&&port.type==='rj45_poe')&&group.face===port.face&&typeof group[field]==='string'&&group[field]===value?value:null;
}
