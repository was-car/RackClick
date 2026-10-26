import {ApiError,type RackClickApi} from './api.ts';
import {catalogPresetKeys,rc9CatalogVersion,rc9CatalogSha256} from './inventory-catalog.ts';
export type FavoriteDraft={actorId:string;requestId:string;revision:number;presetKey:string;favorite:boolean;catalogVersion:string;catalogSha256:string};
export type CatalogFavorites={kind:'catalogFavorites';customerId:string;ownerId:string;revision:number;catalogVersion:string;catalogSha256:string;presetKeys:string[]};
const keys=(x:any,names:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===names.split(',').sort().join();
export const favoriteUuid=(x:any):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const revision=(x:any)=>Number.isSafeInteger(x)&&x>=0;
const canonical=(x:any)=>x.catalogVersion===rc9CatalogVersion&&x.catalogSha256===rc9CatalogSha256;
// Old public intentions remain recoverable/cancellable after a future catalogue update.
export function validFavoriteDraft(x:any):x is FavoriteDraft{return keys(x,'actorId,requestId,revision,presetKey,favorite,catalogVersion,catalogSha256')&&favoriteUuid(x.actorId)&&favoriteUuid(x.requestId)&&revision(x.revision)&&typeof x.presetKey==='string'&&/^[a-z0-9_-]{1,64}$/.test(x.presetKey)&&typeof x.favorite==='boolean'&&typeof x.catalogVersion==='string'&&/^[a-z0-9][a-z0-9._-]{0,63}$/.test(x.catalogVersion)&&typeof x.catalogSha256==='string'&&/^[0-9a-f]{64}$/.test(x.catalogSha256)}
export function validFavorites(x:any,customerId:string,actorId:string):x is CatalogFavorites{return keys(x,'kind,customerId,ownerId,revision,catalogVersion,catalogSha256,presetKeys')&&x.kind==='catalogFavorites'&&x.customerId===customerId&&x.ownerId===actorId&&revision(x.revision)&&canonical(x)&&Array.isArray(x.presetKeys)&&x.presetKeys.length<=catalogPresetKeys.length&&x.presetKeys.every((key:any,i:number)=>catalogPresetKeys.includes(key)&&(i===0||x.presetKeys[i-1]<key))}
function authority(api:RackClickApi,actorId:string,signal?:AbortSignal,uncertain=false){if(signal?.aborted||!favoriteUuid(actorId)||api.actorId!==actorId)throw new ApiError(409,'actor_changed',uncertain)}
function path(customerId:string){if(!favoriteUuid(customerId))throw new ApiError(422,'request_invalid');return '/customers/'+customerId+'/catalog/favorites'}
function requireDraft(api:RackClickApi,d:FavoriteDraft,uncertain=false){if(!validFavoriteDraft(d))throw new ApiError(422,'request_invalid');authority(api,d.actorId,undefined,uncertain)}
export async function readCatalogFavorites(api:RackClickApi,customerId:string,actorId=api.actorId,signal?:AbortSignal){authority(api,actorId,signal);const {data,etag}=await api.request(path(customerId),{signal});authority(api,actorId,signal);if(!validFavorites(data,customerId,actorId)||etag!=='"favorites-'+data.revision+'"')throw new ApiError(200,'response_invalid');return data}
export function prepareFavorite(actorId:string,current:CatalogFavorites,presetKey:string,favorite:boolean):FavoriteDraft{const d={actorId,requestId:crypto.randomUUID(),revision:current.revision,presetKey,favorite,catalogVersion:current.catalogVersion,catalogSha256:current.catalogSha256};if(current.ownerId!==actorId||!validFavorites(current,current.customerId,actorId)||!catalogPresetKeys.includes(presetKey)||!validFavoriteDraft(d))throw new ApiError(422,'request_invalid');return Object.freeze(d)}
export function confirmedFavorite(data:any,d:FavoriteDraft){
 const r=data?.result;
 if(!validFavoriteDraft(d)||!keys(data,'kind,ownerId,revision,requestId,operationId,result')||data.kind!=='catalogFavorites'||data.ownerId!==d.actorId||data.requestId!==d.requestId||!favoriteUuid(data.operationId)||!keys(r,'presetKey,favorite,changed,catalogVersion,catalogSha256')||r.presetKey!==d.presetKey||r.favorite!==d.favorite||typeof r.changed!=='boolean'||r.catalogVersion!==d.catalogVersion||r.catalogSha256!==d.catalogSha256||!revision(data.revision)||data.revision!==d.revision+(r.changed?1:0))throw new ApiError(200,'response_invalid',true);
 return data;
}
export function favoriteOutcome(data:any,d:FavoriteDraft){
 if(!validFavoriteDraft(d)||!keys(data,'state,ownerId,revision,requestId,operation')||data.ownerId!==d.actorId||data.requestId!==d.requestId||!revision(data.revision)||!['committed','notRecorded','cancelled'].includes(data.state))throw new ApiError(200,'response_invalid',true);
 if(data.state==='committed'){confirmedFavorite(data.operation,d);if(data.revision<data.operation.revision)throw new ApiError(200,'response_invalid',true)}else if(data.operation!==null)throw new ApiError(200,'response_invalid',true);
 return data;
}
const body=(d:FavoriteDraft)=>JSON.stringify({presetKey:d.presetKey,catalogVersion:d.catalogVersion,catalogSha256:d.catalogSha256,favorite:d.favorite});
async function send(api:RackClickApi,target:string,d:FavoriteDraft){requireDraft(api,d);if(!api.csrf)throw new ApiError(401,'authentication_required');const response=await api.request(target,{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':d.actorId,'If-Match':'"favorites-'+d.revision+'"','Idempotency-Key':d.requestId},body:body(d)});requireDraft(api,d,true);return response}
function etagMatches(etag:string|null,revision:number){if(etag!=='"favorites-'+revision+'"')throw new ApiError(200,'response_invalid',true)}
export async function setCatalogFavorite(api:RackClickApi,customerId:string,d:FavoriteDraft){const {data,etag}=await send(api,path(customerId),d);const result=confirmedFavorite(data,d);etagMatches(etag,result.revision);return result}
export async function catalogFavoriteStatus(api:RackClickApi,customerId:string,d:FavoriteDraft){requireDraft(api,d);const {data,etag}=await api.request(path(customerId)+'/operations/'+d.requestId);requireDraft(api,d,true);const result=favoriteOutcome(data,d);etagMatches(etag,result.revision);return result}
export async function cancelCatalogFavorite(api:RackClickApi,customerId:string,d:FavoriteDraft){const {data,etag}=await send(api,path(customerId)+'/operations/'+d.requestId+'/cancel',d);const result=favoriteOutcome(data,d);etagMatches(etag,result.revision);if(result.state==='notRecorded')throw new ApiError(200,'response_invalid',true);return result}
