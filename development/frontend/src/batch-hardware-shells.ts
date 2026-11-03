import catalogues from './hardware-batch50.generated.json' with {type:'json'};
import cataloguesB from './hardware-batch50b.generated.json' with {type:'json'};
import catalogues100 from './hardware-batch100.generated.json' with {type:'json'};
import catalogues100B from './hardware-batch100b.generated.json' with {type:'json'};
import catalogues100C from './hardware-batch100c.generated.json' with {type:'json'};
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
function freezeVisualData(value: any): any {
 if(value&&typeof value==='object'){for(const child of Object.values(value))freezeVisualData(child);Object.freeze(value)}
 return value;
}
// A returned face cannot change the next device's geometry. Do not freeze the
// instance ports: these remain the original objects owned by the RC9 projection.
const snapshots=freezeVisualData(structuredClone([...catalogues,...cataloguesB,...catalogues100,...catalogues100B,...catalogues100C,...selected506a,...selected506b,...selected506c,...selected506d,...selected506e,...selected506f,...selected506g,...selected506h,...selected506i,...selected506j,...selected506k,...selected506l,...germanCpe,...germanRepeaters]));
const profiles = new Map(snapshots.flatMap(c=>c.profiles.filter(p=>p.visual).map(p=>[JSON.stringify([p.key,c.version]),p])));

// Physical labels never identify inventory endpoints. Every visible socket is
// bound through its exact template group and ordinal to the original UUID.
export function expandHardwareBanks(face: any) {
 return face.banks.flatMap(bank=>bank.rows.flatMap((row: number[],r: number)=>row.map((ordinal: number,col: number)=>({
  groupKey:bank.groupKey,ordinal,x:bank.x+col*bank.dx,y:bank.y+r*bank.dy,w:bank.w,h:bank.h,
  label:bank.labels?.[String(ordinal)]??String(ordinal)
 }))));
}
export function batchHardwareShellLayout(device: any, face: string) {
 if(!['front','rear'].includes(face))return null;
 const profile: any=profiles.get(JSON.stringify([device?.hardwareProfileKey,device?.hardwareProfileVersion]));
 if(!profile||!profile.visual||!['manufacturer','family','model','sku'].every(k=>device.hardwareIdentity?.[k]===profile.identity[k]))return null;
 const room=['wall','pole','din','floor','tabletop'].includes(profile.kind);
 if(room?device.u!==null:device.u!==profile.sizeU)return null;
 if(profile.kind==='desktop') {if(!device.mountParentId||device.mountSlotKey!=='main')return null;}
 else if(profile.kind==='sharedU'){if(!device.mountParentId||device.mountSlotKey!=='shared')return null;}
 else if(profile.kind==='vertical0U'){if(device.mountParentId||!['vertical-left','vertical-right'].includes(device.mountSlotKey))return null;}
 else if(device.mountParentId||device.mountSlotKey)return null;
 const ports=device.ports,total=profile.groups.reduce((n,g)=>n+g.count,0);
 if(!Array.isArray(ports)||ports.length!==total||ports.some(p=>typeof p?.id!=='string'||!p.id.trim()||typeof p.groupId!=='string'||!p.groupId.trim())||new Set(ports.map(p=>p.id)).size!==total)return null;
 const byTemplate=new Map(),groupIds=[];
 for(const g of profile.groups){
  const list=ports.filter(p=>p.rackclickHardwareGroupKey===g.key);
  if(list.length!==g.count||new Set(list.map(p=>p.groupId)).size!==1||new Set(list.map(p=>p.gn)).size!==g.count||list.some(p=>(p.type!==g.type&&!(g.type==='rj45'&&p.type==='rj45_poe'))||p.rackclickFace!==g.face||(p.rackclickPowerRole||'unspecified')!==(g.powerRole||'unspecified')||!Number.isInteger(p.gn)||p.gn<1||p.gn>g.count))return null;
  groupIds.push(list[0].groupId);
  for(const p of list)byTemplate.set(JSON.stringify([g.key,p.gn]),p);
 }
 if(new Set(groupIds).size!==groupIds.length)return null;
 const visual=profile.visual.faces[face],sockets=expandHardwareBanks(visual).map(s=>Object.freeze({...s,port:byTemplate.get(JSON.stringify([s.groupKey,s.ordinal]))}));
 if(sockets.some(s=>!s.port)||sockets.length!==ports.filter(p=>p.rackclickFace===face).length)return null;
 return Object.freeze({id:profile.key+'-'+face+'-v1',family:'batch50',face,visual,model:profile.identity.model,sku:profile.identity.sku,
  ports:Object.freeze(sockets.map(s=>s.port)),sockets:Object.freeze(sockets)});
}
