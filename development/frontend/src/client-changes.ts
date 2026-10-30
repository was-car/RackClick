import {ApiError,type RackClickApi} from './api.ts';

export const changeActions=new Set([
 ...['site','building','room'].flatMap(entity=>['create','update','delete'].map(action=>'inventory.'+entity+'.'+action)),
 ...['create','update','assignRoom','delete','duplicate'].map(action=>'inventory.rack.'+action),
 ...['create','createFromCatalog','createFromPrivateTemplate','createFromSharedTemplate','update','move','reorder','delete','editPortGroups'].map(action=>'inventory.device.'+action),
 'inventory.devices.delete','inventory.operations.compensate','inventory.ports.update',...['create','createBatch','update','disconnect','reconnect'].map(action=>'inventory.connections.'+action)
]);
const portTypes=new Set(['rj45','rj45_poe','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c']);
export type ChangePort={id:string;deviceId:string;groupId:string;type:string;gn:number};
export type ChangeConnection={id:string;fromPortId:string;toPortId:string};
export type ClientChange={id:string;actor:{id:string;userNameCurrent:string|null};action:string;resourceId:string|null;revisionBefore:number;revisionAfter:number;occurredAt:string;context:{status:'captured'|'notAvailable';beforePorts:ChangePort[];afterPorts:ChangePort[];beforeConnections:ChangeConnection[];afterConnections:ChangeConnection[]}};
export type ChangePage={customerId:string;currentRevision:number;nextRevision:number;hasMore:boolean;refreshRequired:boolean;events:ClientChange[]};
const keys=(x:any,expected:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===expected;
const uuid=(x:unknown):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const positive=(x:any)=>Number.isSafeInteger(x)&&x>0;
const same=(a:string,b:string)=>a.toLowerCase()===b.toLowerCase();
const unique=(items:{id:string}[])=>items.every(x=>!!x&&uuid(x.id))&&new Set(items.map(x=>x.id.toLowerCase())).size===items.length;
const actorName=(x:any)=>x===null||typeof x==='string'&&Array.from(x).length>0&&Array.from(x).length<=100&&!/\p{Cc}/u.test(x);
function contextValid(event:ClientChange):boolean{
 const c=event.context;
 if(!keys(c,'afterConnections,afterPorts,beforeConnections,beforePorts,status'))return false;
 if(![c.beforePorts,c.afterPorts].every(x=>Array.isArray(x)&&x.length<=256&&unique(x)&&x.every(p=>keys(p,'deviceId,gn,groupId,id,type')&&uuid(p.id)&&uuid(p.deviceId)&&uuid(p.groupId)&&portTypes.has(p.type)&&Number.isInteger(p.gn)&&p.gn>0&&p.gn<=2147483647)))return false;
 if(![c.beforeConnections,c.afterConnections].every(x=>Array.isArray(x)&&x.length<=128&&unique(x)&&x.every(p=>keys(p,'fromPortId,id,toPortId')&&uuid(p.id)&&uuid(p.fromPortId)&&uuid(p.toPortId)&&!same(p.fromPortId,p.toPortId))&&new Set(x.flatMap(p=>[p.fromPortId.toLowerCase(),p.toPortId.toLowerCase()])).size===x.length*2))return false;
 if(event.action==='inventory.devices.delete'&&(c.status!=='notAvailable'||!uuid(event.resourceId)||!same(event.resourceId,event.id)))return false;
 if(c.status==='notAvailable')return !c.beforePorts.length&&!c.afterPorts.length&&!c.beforeConnections.length&&!c.afterConnections.length;
 if(c.status!=='captured'||!uuid(event.resourceId))return false;
 if(event.action==='inventory.ports.update'||event.action==='inventory.operations.compensate'){
  if(c.beforeConnections.length||c.afterConnections.length||!c.beforePorts.length||c.beforePorts.length!==c.afterPorts.length)return false;
  const first=c.beforePorts[0],family=(type:string)=>type==='rj45_poe'?'rj45':type;
  return same(first.deviceId,event.resourceId)&&c.beforePorts.every((p,i)=>{const a=c.afterPorts[i];return same(p.id,a.id)&&same(p.deviceId,first.deviceId)&&same(a.deviceId,first.deviceId)&&same(p.groupId,first.groupId)&&same(a.groupId,first.groupId)&&p.gn===a.gn&&family(p.type)===family(first.type)&&family(p.type)===family(a.type)});
 }
 if(c.beforePorts.length||c.afterPorts.length)return false;
 const before=c.beforeConnections,after=c.afterConnections,action=event.action;
 if(action==='inventory.connections.create'||action==='inventory.connections.createBatch')return !before.length&&after.length>0&&(action.endsWith('createBatch')||after.length===1)&&same(after[0].id,event.resourceId);
 if(action==='inventory.connections.disconnect')return before.length===1&&!after.length&&same(before[0].id,event.resourceId);
 if(!['inventory.connections.update','inventory.connections.reconnect'].includes(action)||before.length!==1||after.length!==1||!same(before[0].id,after[0].id)||!same(before[0].id,event.resourceId))return false;
 const from=same(before[0].fromPortId,after[0].fromPortId),to=same(before[0].toPortId,after[0].toPortId);
 return action.endsWith('update')?from&&to:from||to;
}
export async function readClientChanges(api:RackClickApi,customerId:string,afterRevision:number|null,expected=api.actorId,signal?:AbortSignal):Promise<ChangePage>{
 const authority=()=>{if(!uuid(expected)||api.actorId!==expected)throw new ApiError(409,'actor_changed')};authority();
 if(!uuid(customerId)||afterRevision!==null&&!positive(afterRevision))throw new ApiError(422,'changes_cursor_invalid');
 const {data,etag}=await api.request('/customers/'+encodeURIComponent(customerId)+'/changes?'+(afterRevision===null?'':'afterRevision='+afterRevision+'&')+'limit=50',{signal});authority();
 return validateChangePage(data,etag,customerId,afterRevision);
}
// Shared closed v1 validator; opting into descriptive notices does not expand the legacy DTO.
export function validateChangePage(data:any,etag:string|null,customerId:string,afterRevision:number|null):ChangePage{
 const invalid=():never=>{throw new ApiError(200,'response_invalid')};
 if(!keys(data,'currentRevision,customerId,events,hasMore,nextRevision,refreshRequired')||!uuid(data.customerId)||!same(data.customerId,customerId)||!positive(data.currentRevision)||!positive(data.nextRevision)||data.nextRevision>data.currentRevision||etag!=='"'+data.currentRevision+'"'||typeof data.hasMore!=='boolean'||typeof data.refreshRequired!=='boolean'||!Array.isArray(data.events)||data.events.length>50)invalid();
 if(afterRevision===null){if(data.events.length||data.hasMore||data.refreshRequired||data.nextRevision!==data.currentRevision)invalid();return data}
 if(data.refreshRequired){if(data.events.length||data.hasMore||data.nextRevision!==data.currentRevision)invalid();return data}
 if(afterRevision>data.currentRevision)invalid();
 let revision=afterRevision;const ids=new Set<string>();
 for(const event of data.events){
  if(!keys(event,'action,actor,context,id,occurredAt,resourceId,revisionAfter,revisionBefore')||!uuid(event.id)||ids.has(event.id.toLowerCase())||!keys(event.actor,'id,userNameCurrent')||!uuid(event.actor.id)||!actorName(event.actor.userNameCurrent)||!changeActions.has(event.action)||(event.resourceId!==null&&!uuid(event.resourceId))||!positive(event.revisionBefore)||event.revisionBefore!==revision||!positive(event.revisionAfter)||event.revisionAfter!==revision+1||typeof event.occurredAt!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?Z$/.test(event.occurredAt)||!Number.isFinite(Date.parse(event.occurredAt))||!contextValid(event))invalid();
  ids.add(event.id.toLowerCase());revision=event.revisionAfter;
 }
 if(data.nextRevision!==revision||data.hasMore!==(revision<data.currentRevision)||!data.events.length&&revision!==data.currentRevision)invalid();
 return data;
}

// Ephemeral notification metadata only: never a shared inventory cache or write revision.
export class ChangeInbox{
 cursor:number;currentRevision:number;events:ClientChange[]=[];more=false;refreshRequired=false;
 constructor(applied:number){if(!positive(applied))throw new ApiError(422,'changes_cursor_invalid');this.cursor=this.currentRevision=applied}
 apply(applied:number){if(!positive(applied))return;this.events=this.events.filter(e=>e.revisionAfter>applied);this.cursor=Math.max(this.cursor,applied);if(applied>=this.currentRevision){this.more=false;this.refreshRequired=false;this.currentRevision=applied}}
 accept(page:ChangePage,requestedAfter:number,actor:string){
  if(requestedAfter!==this.cursor||page.nextRevision<this.cursor&&!page.refreshRequired)return false;
  if(page.refreshRequired){if(page.currentRevision<requestedAfter)this.events=[];this.currentRevision=page.currentRevision;this.cursor=page.nextRevision;this.refreshRequired=true;this.more=true;return true}
  this.currentRevision=Math.max(this.currentRevision,page.currentRevision);this.cursor=Math.max(this.cursor,page.nextRevision);
  const known=new Set(this.events.map(e=>e.id.toLowerCase()+':'+e.revisionAfter));
  for(const event of page.events){const key=event.id.toLowerCase()+':'+event.revisionAfter;if(!same(event.actor.id,actor)&&!known.has(key)){known.add(key);this.events.push(event)}}
  this.more=this.more||page.hasMore||this.events.length>50;this.events=this.events.slice(-50);return true;
 }
 clear(){this.events=[];this.more=false;this.refreshRequired=false}
}
