import {ApiError,allows,type RackClickApi,type Session} from './api.ts';
import {validProject} from './inventory-model.ts';
export type InventoryJsonExportRequest=Readonly<{actorId:string;customerId:string;revision:number;requestId:string;body:string}>;
export const inventoryJsonFormat='RackClickInventory-v1';
export const inventoryJsonCollections=['sites','buildings','rooms','racks','devices','portGroups','ports','connections'];
const uuid=(v:any)=>typeof v==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(v)&&v!=='00000000-0000-0000-0000-000000000000';
const keys=(v:any,wanted:string)=>!!v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join()===wanted.split(',').sort().join();
const invalid=():never=>{throw new ApiError(200,'response_invalid',true)};
export function inventoryJsonExportAllowed(api:RackClickApi,session:Session,customerId:string){return api.actorId===session.user.id&&allows(session,'inventory.read',customerId)&&allows(session,'reports.export',customerId)}
export function prepareInventoryJsonExport(api:RackClickApi,actorId:string,customerId:string,revision:number):InventoryJsonExportRequest{
 if(api.actorId!==actorId||!uuid(actorId))throw new ApiError(409,'actor_changed');
 if(!uuid(customerId)||!Number.isSafeInteger(revision)||revision<1)throw new ApiError(422,'request_invalid');
 return Object.freeze({actorId,customerId,revision,requestId:crypto.randomUUID(),body:JSON.stringify({formatVersion:1,scope:'customer'})});
}
const fields:Record<string,string>={sites:'id,name,properties',buildings:'id,name,properties,siteId',rooms:'id,name,properties,buildingId',racks:'id,roomId,name,location,sizeU,properties',devices:'id,kind,rackId,roomId,name,sizeU,sortOrder,poeBudget,hardwareProfileKey,mountParentId,mountSlotKey,properties',portGroups:'id,deviceId,type,name,prefix,sortOrder',ports:'id,deviceId,groupId,type,gn,sortOrder,label,status,poe,watts,color,face,powerRole,properties',connections:'id,fromPortId,toPortId,note,color,patch,createdAt,properties'};
export async function validateInventoryJsonExport(data:any,operation:InventoryJsonExportRequest){
 const a=data?.archive;
 if(!keys(data,'kind,customerId,revision,requestId,operationId,archive')||data.kind!=='inventoryExport'||data.customerId!==operation.customerId||data.revision!==operation.revision||data.requestId!==operation.requestId||!uuid(data.operationId)||!keys(a,'format,scope,filename,contentType,encoding,rowCount,byteLength,sha256,contentBase64')||a.format!==inventoryJsonFormat||a.scope!=='customer'||a.filename!==`rackclick-inventory-${operation.customerId}-r${operation.revision}.json`||a.contentType!=='application/json; charset=utf-8'||a.encoding!=='utf-8'||!Number.isSafeInteger(a.rowCount)||a.rowCount<0||a.rowCount>100000||!Number.isSafeInteger(a.byteLength)||a.byteLength<1||a.byteLength>4194304||typeof a.sha256!=='string'||!/^[a-f0-9]{64}$/.test(a.sha256)||typeof a.contentBase64!=='string'||a.contentBase64.length>5592408||a.contentBase64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(a.contentBase64))invalid();
 let bytes:Uint8Array;
 try{const text=atob(a.contentBase64);if(btoa(text)!==a.contentBase64)invalid();bytes=Uint8Array.from(text,c=>c.charCodeAt(0));}catch{invalid();}
 if(bytes!.length!==a.byteLength||bytes![0]===239&&bytes![1]===187&&bytes![2]===191)invalid();
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');if(digest!==a.sha256)invalid();
 let document:any;
 try{document=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes!));}catch{invalid();}
 if(!keys(document,'formatVersion,kind,scope,customerId,revision,inventory')||document.formatVersion!==1||document.kind!=='RackClickInventory'||document.scope!=='customer'||document.customerId!==operation.customerId||document.revision!==operation.revision||!keys(document.inventory,inventoryJsonCollections.join(',')))invalid();
 let rows=0;
 for(const name of inventoryJsonCollections){
  const items=document.inventory[name];if(!Array.isArray(items))invalid();rows+=items.length;
  for(const item of items){if(!item||typeof item!=='object'||Array.isArray(item))invalid();const allowed=name==='racks'&&Object.hasOwn(item,'hardwareProfileKey')?fields[name]+',hardwareProfileKey':fields[name];if(!keys(item,allowed)||!uuid(item.id))invalid();}
 }
 if(rows!==a.rowCount||!validProject({customerId:document.customerId,revision:document.revision,...document.inventory},operation.customerId))invalid();
 return {result:data,bytes:bytes!,document};
}
function current(api:RackClickApi,operation:InventoryJsonExportRequest,signal?:AbortSignal){if(signal?.aborted||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed')}
export async function sendInventoryJsonExport(api:RackClickApi,operation:InventoryJsonExportRequest,signal?:AbortSignal){
 current(api,operation,signal);if(!api.csrf)throw new ApiError(401,'authentication_required');
 const {data}=await api.request('/customers/'+operation.customerId+'/exports/inventory-json',{method:'POST',signal,headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':operation.actorId,'If-Match':'"'+operation.revision+'"','Idempotency-Key':operation.requestId},body:operation.body});
 current(api,operation,signal);const validated=await validateInventoryJsonExport(data,operation);current(api,operation,signal);return validated;
}
export async function recoverInventoryJsonExport(api:RackClickApi,operation:InventoryJsonExportRequest,signal?:AbortSignal){
 current(api,operation,signal);const {data}=await api.request('/customers/'+operation.customerId+'/exports/inventory-json/operations/'+operation.requestId,{signal});current(api,operation,signal);
 if(!keys(data,'state,customerId,requestId,operation')||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!['committed','notRecorded'].includes(data.state))invalid();
 if(data.state==='notRecorded'){if(data.operation!==null)invalid();return null;}
 const validated=await validateInventoryJsonExport(data.operation,operation);current(api,operation,signal);return validated;
}
export function downloadInventoryJsonExport(validated:Awaited<ReturnType<typeof validateInventoryJsonExport>>,api:RackClickApi,session:Session,customerId:string){
 if(!inventoryJsonExportAllowed(api,session,customerId)||validated.result.customerId!==customerId)throw new ApiError(403,'forbidden');
 const url=URL.createObjectURL(new Blob([validated.bytes],{type:'application/json;charset=utf-8'})),link=document.createElement('a');
 try{link.href=url;link.download=validated.result.archive.filename;document.body.appendChild(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
}
