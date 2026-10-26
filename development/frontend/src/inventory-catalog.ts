import {ApiError,type RackClickApi} from './api.ts';
import type {Project} from './inventory-model.ts';
export const rc9CatalogVersion='rc9-base-v1';
export const rc9CatalogSha256='764aa2d016057bc8232f86d4b82a5ef7c156667e906460d1b6bdef51ffcfcd92';
export type CatalogPort={gn:number;sortOrder:number;type:string;label:string;status:'free';poe:boolean;watts:null;color:string|null;face:'auto'|'front'|'rear';powerRole:'unspecified'|'inlet'|'outlet';properties:Record<string,never>};
export type CatalogGroup={key:string;type:string;name:string;prefix:string;sortOrder:number;ports:CatalogPort[]};
export type CatalogPreset={key:string;categoryKey:string;label:string;icon:string;color:string;sizeU:number;poeBudget:null;portGroups:CatalogGroup[]};
export type InventoryCatalog={customerId:string;revision:number;language:'en'|'de'|'es';catalogVersion:string;catalogSha256:string;categories:{key:string;label:string;presetKeys:string[]}[];presets:CatalogPreset[]};
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const uuid=(x:any)=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const text=(x:any,max=100)=>typeof x==='string'&&Array.from(x).length<=max&&!/\p{Cc}/u.test(x);
const color=(x:any)=>typeof x==='string'&&/^#[0-9a-f]{6}$/i.test(x);
const types=new Set(['rj45','rj45_poe','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c']);
const family=(type:string)=>type==='rj45_poe'?'rj45':type;
const unique=(items:string[])=>new Set(items).size===items.length;
export const catalogPresetKeys=Object.freeze('pp24 pp48 ppf24 sw24 sw24p sw48 sw48p swsfp srv1u srv2u srv4u nas2u nas4u san rtr fw pdu ups mc bl1u bl2u sp1u sp2u cbl1u shelf sw8 sw16 sw8p rtr8 fw4 nas1u srv1u4 ap'.split(' '));
const presetKeys=catalogPresetKeys;
const categoryKeys=['Patch Panels','Switches','Servers','Storage','Network','Power','Spacers'];
export function validCatalog(data:any,customerId:string,revision:number,language:string):data is InventoryCatalog{
 if(!keys(data,'customerId,revision,language,catalogVersion,catalogSha256,categories,presets')||data.customerId!==customerId||data.revision!==revision||data.language!==language||data.catalogVersion!==rc9CatalogVersion||data.catalogSha256!==rc9CatalogSha256||!Array.isArray(data.categories)||data.categories.length!==7||!Array.isArray(data.presets)||data.presets.length!==33)return false;
 if(!data.categories.every((c:any,i:number)=>keys(c,'key,label,presetKeys')&&c.key===categoryKeys[i]&&text(c.label)&&c.label.length&&Array.isArray(c.presetKeys)&&c.presetKeys.length&&c.presetKeys.every((k:any)=>typeof k==='string'&&presetKeys.includes(k))))return false;
 const all=data.categories.flatMap((c:any)=>c.presetKeys);
 if(all.length!==33||!unique(all)||!data.presets.every((p:any,i:number)=>keys(p,'key,categoryKey,label,icon,color,sizeU,poeBudget,portGroups')&&p.key===presetKeys[i]&&text(p.label)&&p.label.length&&text(p.icon,8)&&p.icon.length&&color(p.color)&&Number.isInteger(p.sizeU)&&p.sizeU>0&&p.sizeU<=1000&&p.poeBudget===null&&data.categories.some((c:any)=>c.key===p.categoryKey&&c.presetKeys.includes(p.key))&&Array.isArray(p.portGroups)&&p.portGroups.length<=32&&p.portGroups.every((g:any,j:number)=>
  keys(g,'key,type,name,prefix,sortOrder,ports')&&g.key==='g'+(j+1)&&g.sortOrder===j&&types.has(g.type)&&g.type!=='rj45_poe'&&g.name===''&&g.prefix===''&&Array.isArray(g.ports)&&g.ports.length>0&&g.ports.length<=96&&g.ports.every((port:any,k:number)=>
   keys(port,'gn,sortOrder,type,label,status,poe,watts,color,face,powerRole,properties')&&port.gn===k+1&&port.sortOrder===k&&types.has(port.type)&&family(port.type)===g.type&&text(port.label)&&port.status==='free'&&port.poe===(port.type==='rj45_poe')&&port.watts===null&&(port.color===null||color(port.color))&&['auto','front','rear'].includes(port.face)&&['unspecified','inlet','outlet'].includes(port.powerRole)&&(port.type==='power'||port.powerRole==='unspecified')&&keys(port.properties,'')))))return false;
 return true;
}
export async function readInventoryCatalog(api:RackClickApi,customerId:string,revision:number,language:string,actorId=api.actorId,signal?:AbortSignal){
 const authority=()=>{if(signal?.aborted||api.actorId!==actorId||!uuid(actorId))throw new ApiError(409,'actor_changed')};authority();
 if(!uuid(customerId)||!Number.isSafeInteger(revision)||revision<1||!['en','de','es'].includes(language))throw new ApiError(422,'catalog_request_invalid');
 const {data,etag}=await api.request('/customers/'+customerId+'/catalog?language='+language,{signal,headers:{'If-Match':'"'+revision+'"'}});authority();
 if(etag!=='"'+revision+'"'||!validCatalog(data,customerId,revision,language))throw new ApiError(200,'response_invalid');
 return data;
}
export function catalogMatches(catalog:InventoryCatalog|null,actor:string,api:RackClickApi,project:Project,language:string,loadedActor:string){return !!catalog&&actor===loadedActor&&api.actorId===actor&&catalog.customerId===project.customerId&&catalog.revision===project.revision&&catalog.language===language;}
export function filterCatalog(catalog:InventoryCatalog,category:string,query:string){const needle=query.trim().toLocaleLowerCase(catalog.language);return catalog.presets.filter(p=>(!category||p.categoryKey===category)&&(!needle||[p.key,p.label,p.categoryKey,catalog.categories.find(c=>c.key===p.categoryKey)?.label,...p.portGroups.map(g=>g.type)].join(' ').toLocaleLowerCase(catalog.language).includes(needle)));}
export function catalogCreateCommand(api:RackClickApi,actorId:string,project:Project,language:string,form:any){
 const catalog=form.catalogue as InventoryCatalog|null;
 if(!catalogMatches(catalog,actorId,api,project,language,form.catalogueActor)||!validCatalog(catalog,project.customerId,project.revision,language))throw new ApiError(412,'catalog_stale');
 const preset=catalog!.presets.find(p=>p.key===form.catalogKey);if(!preset)throw new ApiError(422,'catalog_preset_required');
 const kind=preset.key==='ap'?'endDevice':form.catalogKind;
 if(!['rackEquipment','dose','endDevice'].includes(kind))throw new ApiError(422,'device_kind_invalid');
 const rackId=kind==='rackEquipment'?form.rackId:null,roomId=kind==='rackEquipment'?null:form.roomId;
 if(kind==='rackEquipment'?!project.racks.some(r=>r.id===rackId):!project.rooms.some(r=>r.id===roomId))throw new ApiError(422,'placement_invalid');
 const name=String(form.name||'').trim()||preset.label,selectedColor=form.color||preset.color;
 if(!text(name)||!name.length||!color(selectedColor))throw new ApiError(422,'request_invalid');
 const poeBudget=form.poeBudget===''||form.poeBudget==null?null:Number(form.poeBudget);
 if(poeBudget!==null&&(!Number.isFinite(poeBudget)||poeBudget<0||poeBudget>9999))throw new ApiError(422,'request_invalid');
 return {type:'device.createFromCatalog',payload:{presetKey:preset.key,catalogVersion:catalog!.catalogVersion,catalogSha256:catalog!.catalogSha256,language,kind,rackId,roomId,name,color:selectedColor,poeBudget,notes:{sn:form.sn,model:form.model,ip:form.ip,firmware:form.firmware,text:form.notes}}};
}
