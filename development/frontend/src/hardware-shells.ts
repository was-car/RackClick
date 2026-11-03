import {batchHardwareShellLayout} from './batch-hardware-shells.ts';
// Visual revisions are separate from the sealed hardware catalogue. They cannot
// add ports or change instances. Unknown geometry always keeps the generic view.
export function hardwareShellLayout(device: any, face: string) {
 if(['batch50-20261030-v1','batch50b-20261031-v1','batch100-20261031-v1','batch100b-20261031-v1','batch100c-20261031-v1','selected506a-20261101-v1','selected506b-20261101-v1','selected506c-20261101-v1','selected506d-20261101-v1','selected506e-20261101-v1','selected506f-20261101-v1','selected506g-20261101-v1','selected506h-20261101-v1','selected506i-20261101-v1','selected506j-20261101-v1','selected506k-20261101-v1','selected506l-20261101-v1','selected506l-support-20261101-v1','german-cpe-20261103-v1','german-repeaters-20261103-v1'].includes(device?.hardwareProfileVersion))return batchHardwareShellLayout(device,face);
 if(device?.hardwareProfileKey==='qnap-ts464-8g')return qnapShellLayout(device,face);
 if(device?.hardwareProfileKey==='synology-ds423plus')return diskstationShellLayout(device,face);
 if(device?.hardwareProfileKey==='synology-rs1221plus')return synologyShellLayout(device,face);
 if(device?.hardwareProfileKey==='fortinet-fg60f')return fortinetShellLayout(device,face);
 if(device?.hardwareProfileKey==='aruba-jl682a')return arubaShellLayout(device,face);
 if (!['front','rear'].includes(face) || device?.hardwareProfileKey !== 'startech-c6panelutp241uft' ||
     device.hardwareProfileVersion !== 'startech-20261030-v1' || device.u !== 1 ||
     device.hardwareIdentity?.manufacturer !== 'StarTech.com' ||
     device.hardwareIdentity?.model !== 'C6PANELUTP241UFT' || device.hardwareIdentity?.sku !== 'C6PANELUTP241UFT') return null;
 const ports = device.ports;
 if (!Array.isArray(ports) || ports.length !== 48 ||
     ports.some(p => typeof p?.id !== 'string' || !p.id.trim() || typeof p.groupId !== 'string' || !p.groupId.trim() ||
         p.type !== 'rj45' || !['front','rear'].includes(p.rackclickFace)) || new Set(ports.map(p => p.id)).size !== 48) return null;
 const faces = ['front','rear'].map(side => ports.filter(p => p.rackclickFace === side));
 if (faces.some(list => list.length !== 24 || new Set(list.map(p => p.groupId)).size !== 1 ||
     new Set(list.map(p => p.gn)).size !== 24 || list.some(p => !Number.isInteger(p.gn) || p.gn < 1 || p.gn > 24)) ||
     faces[0][0].groupId === faces[1][0].groupId) return null;
 const ordered = [...faces[face==='front'?0:1]].sort((a,b) => face==='front'?a.gn-b.gn:b.gn-a.gn);
 return Object.freeze({id:face==='front'?'startech-c6panelutp241uft-front-v1':'startech-c6panelutp241uft-rear-v1',face,
     blocks:Object.freeze(Array.from({length:4},(_,i) => Object.freeze(ordered.slice(i*6,i*6+6))))});
}

function qnapShellLayout(device: any,face: string) {
 if(!['front','rear'].includes(face)||device.hardwareProfileVersion!=='qnap-20261030-v1'||device.u!==0||!device.mountParentId||device.mountSlotKey!=='main'||device.hardwareIdentity?.manufacturer!=='QNAP'||device.hardwareIdentity?.model!=='TS-464'||device.hardwareIdentity?.sku!=='TS-464-8G')return null;
 const ports=device.ports;
 if(!Array.isArray(ports)||ports.length!==2||ports.some(p=>typeof p?.id!=='string'||!p.id.trim()||typeof p.groupId!=='string'||!p.groupId.trim()||p.type!=='rj45'||p.rackclickFace!=='rear'||p.rackclickHardwareGroupKey!=='rear-lan'||(p.rackclickPowerRole||'unspecified')!=='unspecified'||!Number.isInteger(p.gn)||p.gn<1||p.gn>2)||new Set(ports.map(p=>p.id)).size!==2||new Set(ports.map(p=>p.groupId)).size!==1||new Set(ports.map(p=>p.gn)).size!==2)return null;
 return Object.freeze({id:'qnap-ts464-'+face+'-v1',family:'qnap-ts464',face,ports:Object.freeze(face==='rear'?[...ports].sort((a,b)=>a.gn-b.gn):[])});
}

function diskstationShellLayout(device: any,face: string) {
 if(!['front','rear'].includes(face)||device.hardwareProfileVersion!=='synology-ds423plus-20261030-v1'||device.u!==0||!device.mountParentId||device.mountSlotKey!=='main'||device.hardwareIdentity?.manufacturer!=='Synology'||device.hardwareIdentity?.model!=='DS423+'||device.hardwareIdentity?.sku!=='DS423+')return null;
 const ports=device.ports;
 if(!Array.isArray(ports)||ports.length!==2||ports.some(p=>typeof p?.id!=='string'||!p.id.trim()||typeof p.groupId!=='string'||!p.groupId.trim()||p.type!=='rj45'||p.rackclickFace!=='rear'||p.rackclickHardwareGroupKey!=='rear-lan'||(p.rackclickPowerRole||'unspecified')!=='unspecified'||!Number.isInteger(p.gn)||p.gn<1||p.gn>2)||new Set(ports.map(p=>p.id)).size!==2||new Set(ports.map(p=>p.groupId)).size!==1||new Set(ports.map(p=>p.gn)).size!==2)return null;
 return Object.freeze({id:'synology-ds423plus-'+face+'-v1',family:'diskstation-ds423plus',face,ports:Object.freeze(face==='rear'?[...ports].sort((a,b)=>a.gn-b.gn):[])});
}

function synologyShellLayout(device: any,face: string) {
 if(!['front','rear'].includes(face)||device.hardwareProfileVersion!=='synology-20261030-v1'||device.u!==2||device.mountParentId||device.mountSlotKey||device.hardwareIdentity?.manufacturer!=='Synology'||device.hardwareIdentity?.model!=='RS1221+'||device.hardwareIdentity?.sku!=='RS1221+')return null;
 const ports=device.ports;
 if(!Array.isArray(ports)||ports.length!==5||ports.some(p=>typeof p?.id!=='string'||!p.id.trim()||typeof p.groupId!=='string'||!p.groupId.trim()||p.rackclickFace!=='rear')||new Set(ports.map(p=>p.id)).size!==5)return null;
 const groups=[['rear-lan','rj45',4,'unspecified'],['rear-power','power',1,'inlet']].map(([key,type,count,role])=>{
  const list=ports.filter(p=>p.rackclickHardwareGroupKey===key&&p.type===type);
  if(list.length!==count||new Set(list.map(p=>p.groupId)).size!==1||new Set(list.map(p=>p.gn)).size!==count||list.some(p=>!Number.isInteger(p.gn)||p.gn<1||p.gn>Number(count)||(p.rackclickPowerRole||'unspecified')!==role))return null;
  return [...list].sort((a,b)=>a.gn-b.gn);
 });
 if(groups.some(g=>!g)||groups[0]![0].groupId===groups[1]![0].groupId)return null;
 return Object.freeze({id:'synology-rs1221plus-'+face+'-v1',family:'synology-rs1221plus',face,ports:Object.freeze(face==='rear'?groups.flatMap(g=>g!):[])});
}

function fortinetShellLayout(device: any,face: string) {
 if(!['front','rear'].includes(face)||device.hardwareProfileVersion!=='fortinet-20261030-v1'||device.u!==0||!device.mountParentId||device.mountSlotKey!=='main'||device.hardwareIdentity?.manufacturer!=='Fortinet'||device.hardwareIdentity?.model!=='FortiGate 60F'||device.hardwareIdentity?.sku!=='FG-60F')return null;
 const ports=device.ports;
 if(!Array.isArray(ports)||ports.length!==10||ports.some(p=>typeof p?.id!=='string'||!p.id.trim()||typeof p.groupId!=='string'||!p.groupId.trim()||p.type!=='rj45'||p.rackclickFace!=='rear'||(p.rackclickPowerRole||'unspecified')!=='unspecified')||new Set(ports.map(p=>p.id)).size!==10)return null;
 const groups=[['rear-lan',5],['rear-fortilink',2],['rear-dmz',1],['rear-wan',2]].map(([key,count])=>{
  const list=ports.filter(p=>p.rackclickHardwareGroupKey===key);
  if(list.length!==count||new Set(list.map(p=>p.groupId)).size!==1||new Set(list.map(p=>p.gn)).size!==count||list.some(p=>!Number.isInteger(p.gn)||p.gn<1||p.gn>Number(count)))return null;
  return [...list].sort((a,b)=>a.gn-b.gn);
 });
 if(groups.some(g=>!g)||new Set(groups.map(g=>g![0].groupId)).size!==4)return null;
 return Object.freeze({id:'fortinet-fg60f-'+face+'-v1',family:'fortigate60f',face,ports:Object.freeze(face==='rear'?groups.flatMap(g=>g!):[])});
}

function arubaShellLayout(device: any,face: string) {
 if(!['front','rear'].includes(face)||device.hardwareProfileVersion!=='aruba-20261030-v1'||device.u!==1||device.hardwareIdentity?.manufacturer!=='HPE Aruba Networking'||device.hardwareIdentity?.model!=='JL682A'||device.hardwareIdentity?.sku!=='JL682A')return null;
 const ports=device.ports;
 if(!Array.isArray(ports)||ports.length!==29||ports.some(p=>typeof p?.id!=='string'||!p.id.trim()||typeof p.groupId!=='string'||!p.groupId.trim())||new Set(ports.map(p=>p.id)).size!==29)return null;
 const groups=[['rj45','front',24],['sfp','front',4],['power','rear',1]].map(([type,side,count])=>{
  const list=ports.filter(p=>p.type===type&&p.rackclickFace===side);
  if(list.length!==count||new Set(list.map(p=>p.groupId)).size!==1||new Set(list.map(p=>p.gn)).size!==count||list.some(p=>!Number.isInteger(p.gn)||p.gn<1||p.gn>Number(count)||(p.rackclickPowerRole||'unspecified')!==(type==='power'?'inlet':'unspecified')))return null;
  return [...list].sort((a,b)=>a.gn-b.gn);
 });
 if(groups.some(g=>!g)||new Set(groups.map(g=>g![0].groupId)).size!==3)return null;
 return Object.freeze({id:'aruba-jl682a-'+face+'-v1',family:'aruba1930',face,ports:Object.freeze((face==='front'?[...groups[0]!,...groups[1]!]:groups[2]!).slice())});
}
