import {ApiError,type RackClickApi} from './api.ts';
export const defaultPortColors=Object.freeze({rj45:'#3b82f6',rj45_poe:'#3b82f6',sfp:'#a855f7',sfp28:'#ef4444',qsfp:'#10b981',mgmt:'#f59e0b',console:'#6b7280',power:'#ef4444',usb_a:'#9ca3af',usb_c:'#9ca3af',sfp56:'#06b6d4',qsfpdd:'#f97316',idc:'#a3b86c',ipc:'#b39d6b',fiber:'#62b6ad',sfpdd:'#57a4d2',cfp2:'#9673c4',sas:'#c39c70',dsl:'#d5ad69',telephony:'#bd8fb5',isdn:'#a9a0d5',expansion:'#b89287',power_dc:'#e49f66'});
export type PortColorKey=keyof typeof defaultPortColors;
export type PortColors=Partial<Record<PortColorKey,string>>;
export type UserPortColors={kind:'userPortColors';ownerId:string;revision:number;colors:PortColors};
export type PortColorsDraft=Readonly<{actorId:string;colors:Readonly<PortColors>;revision:number;requestId:string}>;
const fields=(x:any,n:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===n.split(',').sort().join();
export const portColorsUuid=(x:any):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const revision=(x:any)=>Number.isSafeInteger(x)&&x>=0;
export const validPortColors=(x:any):x is PortColors=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length<=Object.keys(defaultPortColors).length&&Object.entries(x).every(([k,v])=>Object.hasOwn(defaultPortColors,k)&&typeof v==='string'&&/^#[0-9a-f]{6}$/.test(v));
export const samePortColors=(a:PortColors,b:PortColors)=>Object.keys(a).length===Object.keys(b).length&&Object.entries(a).every(([k,v])=>Object.hasOwn(b,k)&&b[k as PortColorKey]===v);
export const validUserPortColors=(x:any,actorId:string):x is UserPortColors=>fields(x,'kind,ownerId,revision,colors')&&x.kind==='userPortColors'&&portColorsUuid(actorId)&&x.ownerId===actorId&&revision(x.revision)&&validPortColors(x.colors)&&(x.revision!==0||Object.keys(x.colors).length===0);
export const validPortColorsDraft=(x:any):x is PortColorsDraft=>fields(x,'actorId,colors,revision,requestId')&&portColorsUuid(x.actorId)&&portColorsUuid(x.requestId)&&revision(x.revision)&&validPortColors(x.colors);
export function preparePortColors(actorId:string,data:UserPortColors,colors:PortColors):PortColorsDraft{
 if(!validUserPortColors(data,actorId)||!validPortColors(colors))throw new ApiError(422,'port_colors_invalid');
 return Object.freeze({actorId,colors:Object.freeze({...colors}),revision:data.revision,requestId:crypto.randomUUID()});
}
function owner(api:RackClickApi,actorId:string){if(!portColorsUuid(actorId)||api.actorId!==actorId)throw new ApiError(409,'actor_changed')}
const etag=(n:number)=>'"port-colors-'+n+'"';
const invalid=(uncertain=false)=>new ApiError(200,'response_invalid',uncertain);
export async function readUserPortColors(api:RackClickApi,actorId=api.actorId,signal?:AbortSignal):Promise<UserPortColors>{
 owner(api,actorId);const {data,etag:tag}=await api.request('/me/port-colors',{signal});owner(api,actorId);
 if(!validUserPortColors(data,actorId)||tag!==etag(data.revision))throw invalid();return data;
}
export function confirmedPortColors(x:any,d:PortColorsDraft){
 if(!validPortColorsDraft(d)||!fields(x,'kind,ownerId,revision,requestId,operationId,result')||x.kind!=='userPortColors'||x.ownerId!==d.actorId||x.requestId!==d.requestId||!portColorsUuid(x.operationId)||!revision(x.revision)||!fields(x.result,'colors,changed')||!validPortColors(x.result.colors)||!samePortColors(x.result.colors,d.colors)||typeof x.result.changed!=='boolean'||x.revision!==d.revision+(x.result.changed?1:0))throw invalid(true);
 return x;
}
export function portColorsOutcome(x:any,d:PortColorsDraft){
 if(!validPortColorsDraft(d)||!fields(x,'state,ownerId,revision,requestId,operation')||x.ownerId!==d.actorId||x.requestId!==d.requestId||!revision(x.revision)||!['committed','notRecorded','cancelled'].includes(x.state))throw invalid(true);
 if(x.state==='committed'){confirmedPortColors(x.operation,d);if(x.revision<x.operation.revision)throw invalid(true)}else if(x.operation!==null)throw invalid(true);
 return x;
}
function headers(api:RackClickApi,d:PortColorsDraft){
 if(!validPortColorsDraft(d))throw new ApiError(422,'port_colors_invalid');owner(api,d.actorId);if(!api.csrf)throw new ApiError(401,'authentication_required');
 return {'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':d.actorId,'If-Match':etag(d.revision),'Idempotency-Key':d.requestId};
}
export async function mutatePortColors(api:RackClickApi,d:PortColorsDraft){
 const {data,etag:tag}=await api.request('/me/port-colors',{method:'POST',headers:headers(api,d),body:JSON.stringify({colors:d.colors})});owner(api,d.actorId);const value=confirmedPortColors(data,d);if(tag!==etag(value.revision))throw invalid(true);return value;
}
export async function portColorsStatus(api:RackClickApi,d:PortColorsDraft){
 if(!validPortColorsDraft(d))throw new ApiError(422,'port_colors_invalid');owner(api,d.actorId);const {data,etag:tag}=await api.request('/me/port-colors/operations/'+encodeURIComponent(d.requestId));owner(api,d.actorId);const value=portColorsOutcome(data,d);if(tag!==etag(value.revision))throw invalid(true);return value;
}
export async function cancelPortColors(api:RackClickApi,d:PortColorsDraft){
 const {data,etag:tag}=await api.request('/me/port-colors/operations/'+encodeURIComponent(d.requestId)+'/cancel',{method:'POST',headers:headers(api,d),body:JSON.stringify({colors:d.colors})});owner(api,d.actorId);const value=portColorsOutcome(data,d);if(tag!==etag(value.revision)||value.state==='notRecorded')throw invalid(true);return value;
}
