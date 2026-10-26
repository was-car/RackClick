import { ApiError, type RackClickApi } from './api.ts';
import type { Project } from './inventory-model.ts';
export const readKinds = ['all','site','building','room','rack','device','port','connection'];
export const readFamilies = ['all','rj45','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c'];
export const readStatuses = ['all','free','reserved','disabled','faulty'];
export type ReadView = 'search'|'ports'|'connections';
export type ReadFilter = {query:string;kind:string;status:string;family:string;offset:number;limit:number};
const uuid=(x:any)=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x);
const eq=(a:any,b:any)=>JSON.stringify(a)===JSON.stringify(b);
const keys=(x:any,names:string)=>!!x&&typeof x==='object'&&Object.keys(x).sort().join(',')===names.split(',').sort().join(',');
const invalid=()=>new ApiError(200,'response_invalid');
export function inventoryPath(p:Project,kind:string,id:string):any[]{
 const collection:any={site:p.sites,building:p.buildings,room:p.rooms,rack:p.racks,device:p.devices,port:p.ports};
 const x=collection[kind]?.find((x:any)=>x.id===id); if(!x)return [];
 let parent:any=null;
 if(kind==='building')parent=['site',x.siteId];
 if(kind==='room')parent=['building',x.buildingId];
 if(kind==='rack'&&x.roomId)parent=['room',x.roomId];
 if(kind==='device')parent=x.rackId?['rack',x.rackId]:['room',x.roomId];
 if(kind==='port')parent=['device',x.deviceId];
 return [...(parent?inventoryPath(p,...parent as [string,string]):[]),{kind,id:x.id,name:kind==='port'?(x.label||String(x.gn)):x.name}];
}
export function expectedReadPort(p:Project,id:string):any{
 const x=p.ports.find(x=>x.id===id);if(!x)return null;
 const d=p.devices.find(d=>d.id===x.deviceId)!,g=p.portGroups.find(g=>g.id===x.groupId)!,r=p.racks.find(r=>r.id===d.rackId);
 const cables=p.connections.filter(c=>c.fromPortId===id||c.toPortId===id);
 return {customerId:p.customerId,id:x.id,deviceId:d.id,deviceName:d.name,deviceKind:d.kind,rackId:d.rackId,roomId:d.roomId??r?.roomId??null,path:inventoryPath(p,'port',id),groupId:g.id,groupName:g.name,type:x.type,family:x.type==='rj45_poe'?'rj45':x.type,gn:x.gn,label:x.label,status:x.status,face:x.face,poe:x.poe,watts:x.watts,color:x.color,powerRole:x.powerRole,connected:cables.length>0,connectionIds:cables.map(c=>c.id).sort(),peerPortIds:cables.map(c=>c.fromPortId===id?c.toPortId:c.fromPortId).sort()};
}
export function validReadEnvelope(data:any,etag:string|null,p:Project,view:ReadView,f:ReadFilter):boolean{
 if(!keys(data,'customerId,revision,query,kind,status,family,offset,limit,total,nextOffset,items')||data.customerId!==p.customerId||data.revision!==p.revision||etag!=='"'+p.revision+'"'||data.query!==f.query||data.kind!==(view==='search'?f.kind:null)||data.status!==(view==='ports'?f.status:null)||data.family!==(view==='ports'?f.family:null)||data.offset!==f.offset||data.limit!==f.limit||!Number.isSafeInteger(data.total)||data.total<0||!Array.isArray(data.items)||data.items.length!==Math.min(f.limit,Math.max(0,data.total-f.offset))||data.nextOffset!==(f.offset+data.items.length<data.total?f.offset+data.items.length:null))return false;
 const seen=new Set();
 return data.items.every((x:any,index:number)=>{
  if(!uuid(x?.id)||x.customerId!==p.customerId||seen.has(x.id)||index>0&&data.items[index-1].id>=x.id)return false;seen.add(x.id);
  if(view==='ports')return portMatches(x)&&(f.status==='all'||x.status===f.status)&&(f.family==='all'||x.family===f.family);
  if(view==='connections'){
   const c=p.connections.find(c=>c.id===x.id);if(!c||!keys(x,'customerId,id,from,to,note,color,patch,crossRack'))return false;
   return x.from?.id===c.fromPortId&&x.to?.id===c.toPortId&&portMatches(x.from)&&portMatches(x.to)&&x.note===c.note&&x.color===c.color&&x.patch===c.patch&&x.crossRack===(x.from.rackId&&x.to.rackId?x.from.rackId!==x.to.rackId:null);
  }
  if(!keys(x,'customerId,id,kind,name,path,rackId,roomId,deviceId,groupId,type,gn,status')||!readKinds.slice(1).includes(x.kind)||f.kind!=='all'&&x.kind!==f.kind||!Array.isArray(x.path)||typeof x.name!=='string')return false;
  if(x.kind==='connection')return p.connections.some(c=>c.id===x.id&&c.note===x.name)&&eq(x.path,[])&&['rackId','roomId','deviceId','groupId','type','gn','status'].every(key=>x[key]===null);
  const path=inventoryPath(p,x.kind,x.id);if(!path.length||!eq(x.path,path)||x.name!==path.at(-1).name)return false;
  const leaf=x.kind==='port'?p.ports.find(v=>v.id===x.id):null;
  const d=x.kind==='device'?p.devices.find(v=>v.id===x.id):leaf?p.devices.find(v=>v.id===leaf.deviceId):null;
  const rackId=x.kind==='rack'?x.id:d?.rackId??null;
  const roomId=x.kind==='room'?x.id:d?.roomId??p.racks.find(v=>v.id===rackId)?.roomId??null;
  return x.rackId===rackId&&x.roomId===roomId&&x.deviceId===(d?.id??null)&&x.groupId===(leaf?.groupId??null)&&x.type===(leaf?.type??null)&&x.gn===(leaf?.gn??null)&&x.status===(leaf?.status??null);
 });
 function portMatches(x:any){const expected=expectedReadPort(p,x?.id);return !!expected&&keys(x,Object.keys(expected).join(','))&&Object.entries(expected).every(([key,value])=>eq(x[key],value));}
}
export async function loadInventoryRead(api:RackClickApi,actorId:string,p:Project,view:ReadView,f:ReadFilter,signal?:AbortSignal){
 if(api.actorId!==actorId||!actorId)throw new ApiError(409,'actor_changed');
 const params=new URLSearchParams({query:f.query,offset:String(f.offset),limit:String(f.limit)});
 if(view==='search')params.set('kind',f.kind);
 if(view==='ports'){params.set('status',f.status);params.set('family',f.family);}
 const {data,etag}=await api.request('/customers/'+encodeURIComponent(p.customerId)+'/inventory/'+view+'?'+params,{signal,headers:{'If-Match':'"'+p.revision+'"'}});
 if(signal?.aborted||api.actorId!==actorId)throw new ApiError(409,'actor_changed');
 if(!validReadEnvelope(data,etag,p,view,f))throw invalid();
 return data;
}
