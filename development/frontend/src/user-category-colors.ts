import {ApiError,type RackClickApi} from './api.ts';
export const categoryNames=Object.freeze(['Patch Panel','Switch','Router','Firewall','Server','NAS/SAN','Other'] as const);
export const categorySwatches=Object.freeze(['#ffffff','#d1d5db','#fbbf24','#3b82f6','#10b981','#ef4444','#a855f7','#f97316','#06b6d4','#000000'] as const);
export const categoryPair=(a:string,b:string)=>[a,b].sort().join('↔');
export const categoryPairs=Object.freeze(categoryNames.flatMap((a,i)=>categoryNames.slice(i).map(b=>Object.freeze({a,b,key:categoryPair(a,b)}))));
export type CategoryColors=Partial<Record<string,string>>;
export type UserCategoryColors={kind:'userCategoryColors';ownerId:string;revision:number;colors:CategoryColors};
export type CategoryColorsDraft=Readonly<{actorId:string;colors:Readonly<CategoryColors>;revision:number;requestId:string}>;
const fields=(x:any,n:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===n.split(',').sort().join();
export const categoryColorsUuid=(x:any):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const revision=(x:any)=>Number.isSafeInteger(x)&&x>=0;
export const validCategoryColors=(x:any):x is CategoryColors=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length<=28&&Object.entries(x).every(([k,v])=>categoryPairs.some(p=>p.key===k)&&typeof v==='string'&&categorySwatches.some(c=>c===v));
export const sameCategoryColors=(a:CategoryColors,b:CategoryColors)=>Object.keys(a).length===Object.keys(b).length&&Object.entries(a).every(([k,v])=>Object.hasOwn(b,k)&&b[k]===v);
export const validUserCategoryColors=(x:any,actorId:string):x is UserCategoryColors=>fields(x,'kind,ownerId,revision,colors')&&x.kind==='userCategoryColors'&&categoryColorsUuid(actorId)&&x.ownerId===actorId&&revision(x.revision)&&validCategoryColors(x.colors)&&(x.revision!==0||Object.keys(x.colors).length===0);
export const validCategoryColorsDraft=(x:any):x is CategoryColorsDraft=>fields(x,'actorId,colors,revision,requestId')&&categoryColorsUuid(x.actorId)&&categoryColorsUuid(x.requestId)&&revision(x.revision)&&validCategoryColors(x.colors);
export function prepareCategoryColors(actorId:string,data:UserCategoryColors,colors:CategoryColors):CategoryColorsDraft{
 if(!validUserCategoryColors(data,actorId)||!validCategoryColors(colors))throw new ApiError(422,'category_colors_invalid');
 return Object.freeze({actorId,colors:Object.freeze({...colors}),revision:data.revision,requestId:crypto.randomUUID()});
}
function owner(api:RackClickApi,actorId:string){if(!categoryColorsUuid(actorId)||api.actorId!==actorId)throw new ApiError(409,'actor_changed')}
const etag=(n:number)=>'"category-colors-'+n+'"';
const invalid=(uncertain=false)=>new ApiError(200,'response_invalid',uncertain);
export async function readUserCategoryColors(api:RackClickApi,actorId=api.actorId,signal?:AbortSignal):Promise<UserCategoryColors>{
 owner(api,actorId);const {data,etag:tag}=await api.request('/me/category-colors',{signal});owner(api,actorId);
 if(!validUserCategoryColors(data,actorId)||tag!==etag(data.revision))throw invalid();return data;
}
export function confirmedCategoryColors(x:any,d:CategoryColorsDraft){
 if(!validCategoryColorsDraft(d)||!fields(x,'kind,ownerId,revision,requestId,operationId,result')||x.kind!=='userCategoryColors'||x.ownerId!==d.actorId||x.requestId!==d.requestId||!categoryColorsUuid(x.operationId)||!revision(x.revision)||!fields(x.result,'colors,changed')||!validCategoryColors(x.result.colors)||!sameCategoryColors(x.result.colors,d.colors)||typeof x.result.changed!=='boolean'||x.revision!==d.revision+(x.result.changed?1:0))throw invalid(true);
 return x;
}
export function categoryColorsOutcome(x:any,d:CategoryColorsDraft){
 if(!validCategoryColorsDraft(d)||!fields(x,'state,ownerId,revision,requestId,operation')||x.ownerId!==d.actorId||x.requestId!==d.requestId||!revision(x.revision)||!['committed','notRecorded','cancelled'].includes(x.state))throw invalid(true);
 if(x.state==='committed'){confirmedCategoryColors(x.operation,d);if(x.revision<x.operation.revision)throw invalid(true)}else if(x.operation!==null)throw invalid(true);
 return x;
}
function headers(api:RackClickApi,d:CategoryColorsDraft){
 if(!validCategoryColorsDraft(d))throw new ApiError(422,'category_colors_invalid');owner(api,d.actorId);if(!api.csrf)throw new ApiError(401,'authentication_required');
 return {'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':d.actorId,'If-Match':etag(d.revision),'Idempotency-Key':d.requestId};
}
export async function mutateCategoryColors(api:RackClickApi,d:CategoryColorsDraft){
 const {data,etag:tag}=await api.request('/me/category-colors',{method:'POST',headers:headers(api,d),body:JSON.stringify({colors:d.colors})});owner(api,d.actorId);const value=confirmedCategoryColors(data,d);if(tag!==etag(value.revision))throw invalid(true);return value;
}
export async function categoryColorsStatus(api:RackClickApi,d:CategoryColorsDraft){
 if(!validCategoryColorsDraft(d))throw new ApiError(422,'category_colors_invalid');owner(api,d.actorId);const {data,etag:tag}=await api.request('/me/category-colors/operations/'+encodeURIComponent(d.requestId));owner(api,d.actorId);const value=categoryColorsOutcome(data,d);if(tag!==etag(value.revision))throw invalid(true);return value;
}
export async function cancelCategoryColors(api:RackClickApi,d:CategoryColorsDraft){
 const {data,etag:tag}=await api.request('/me/category-colors/operations/'+encodeURIComponent(d.requestId)+'/cancel',{method:'POST',headers:headers(api,d),body:JSON.stringify({colors:d.colors})});owner(api,d.actorId);const value=categoryColorsOutcome(data,d);if(tag!==etag(value.revision)||value.state==='notRecorded')throw invalid(true);return value;
}
