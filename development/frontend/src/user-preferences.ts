import {ApiError,type RackClickApi} from './api.ts';
export type PreferenceKey='language'|'theme';
export type PreferenceValue='en'|'de'|'es'|'dark'|'light';
export type UserPreferences={kind:'userPreferences';ownerId:string;revision:number;language:'en'|'de'|'es'|null;theme:'dark'|'light'|null};
export type PreferenceDraft=Readonly<{actorId:string;key:PreferenceKey;value:PreferenceValue;revision:number;requestId:string}>;
const fields=(x:any,n:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===n.split(',').sort().join();
export const preferenceUuid=(x:any):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const revision=(x:any)=>Number.isSafeInteger(x)&&x>=0;
export const validPreferenceValue=(key:any,value:any)=>key==='language'?['en','de','es'].includes(value):key==='theme'&&['dark','light'].includes(value);
export const validUserPreferences=(x:any,actorId:string):x is UserPreferences=>fields(x,'kind,ownerId,revision,language,theme')&&x.kind==='userPreferences'&&preferenceUuid(actorId)&&x.ownerId===actorId&&revision(x.revision)&&(x.language===null||validPreferenceValue('language',x.language))&&(x.theme===null||validPreferenceValue('theme',x.theme))&&(x.revision!==0||(x.language===null&&x.theme===null));
export const validPreferenceDraft=(x:any):x is PreferenceDraft=>fields(x,'actorId,key,value,revision,requestId')&&preferenceUuid(x.actorId)&&preferenceUuid(x.requestId)&&revision(x.revision)&&validPreferenceValue(x.key,x.value);
export function preparePreference(actorId:string,data:UserPreferences,key:PreferenceKey,value:PreferenceValue):PreferenceDraft{
 if(!validUserPreferences(data,actorId)||!validPreferenceValue(key,value))throw new ApiError(422,'preferences_invalid');
 return Object.freeze({actorId,key,value,revision:data.revision,requestId:crypto.randomUUID()});
}
function owner(api:RackClickApi,actorId:string){if(!preferenceUuid(actorId)||api.actorId!==actorId)throw new ApiError(409,'actor_changed')}
const etag=(n:number)=>'"preferences-'+n+'"';
const invalid=(uncertain=false)=>new ApiError(200,'response_invalid',uncertain);
export async function readUserPreferences(api:RackClickApi,actorId=api.actorId,signal?:AbortSignal):Promise<UserPreferences>{
 owner(api,actorId);const {data,etag:tag}=await api.request('/me/preferences',{signal});owner(api,actorId);
 if(!validUserPreferences(data,actorId)||tag!==etag(data.revision))throw invalid();return data;
}
export function confirmedPreference(x:any,d:PreferenceDraft){
 if(!validPreferenceDraft(d)||!fields(x,'kind,ownerId,revision,requestId,operationId,result')||x.kind!=='userPreferences'||x.ownerId!==d.actorId||x.requestId!==d.requestId||!preferenceUuid(x.operationId)||!revision(x.revision)||!fields(x.result,'key,value,changed')||x.result.key!==d.key||x.result.value!==d.value||typeof x.result.changed!=='boolean'||x.revision!==d.revision+(x.result.changed?1:0)||(x.revision===0&&!x.result.changed))throw invalid(true);
 return x;
}
export function preferenceOutcome(x:any,d:PreferenceDraft){
 if(!validPreferenceDraft(d)||!fields(x,'state,ownerId,revision,requestId,operation')||x.ownerId!==d.actorId||x.requestId!==d.requestId||!revision(x.revision)||!['committed','notRecorded','cancelled'].includes(x.state))throw invalid(true);
 if(x.state==='committed'){confirmedPreference(x.operation,d);if(x.revision<x.operation.revision)throw invalid(true)}else if(x.operation!==null)throw invalid(true);
 return x;
}
function headers(api:RackClickApi,d:PreferenceDraft){
 if(!validPreferenceDraft(d))throw new ApiError(422,'preferences_invalid');owner(api,d.actorId);if(!api.csrf)throw new ApiError(401,'authentication_required');
 return {'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':d.actorId,'If-Match':etag(d.revision),'Idempotency-Key':d.requestId};
}
export async function mutatePreference(api:RackClickApi,d:PreferenceDraft){
 const {data,etag:tag}=await api.request('/me/preferences',{method:'POST',headers:headers(api,d),body:JSON.stringify({key:d.key,value:d.value})});owner(api,d.actorId);const value=confirmedPreference(data,d);if(tag!==etag(value.revision))throw invalid(true);return value;
}
export async function preferenceStatus(api:RackClickApi,d:PreferenceDraft){
 if(!validPreferenceDraft(d))throw new ApiError(422,'preferences_invalid');owner(api,d.actorId);const {data,etag:tag}=await api.request('/me/preferences/operations/'+encodeURIComponent(d.requestId));owner(api,d.actorId);const value=preferenceOutcome(data,d);if(tag!==etag(value.revision))throw invalid(true);return value;
}
export async function cancelPreference(api:RackClickApi,d:PreferenceDraft){
 const {data,etag:tag}=await api.request('/me/preferences/operations/'+encodeURIComponent(d.requestId)+'/cancel',{method:'POST',headers:headers(api,d),body:JSON.stringify({key:d.key,value:d.value})});owner(api,d.actorId);const value=preferenceOutcome(data,d);if(tag!==etag(value.revision)||value.state==='notRecorded')throw invalid(true);return value;
}
