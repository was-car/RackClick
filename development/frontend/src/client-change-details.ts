import {ApiError,type RackClickApi} from './api.ts';
import {validateChangePage,type ClientChange,type ChangePage} from './client-changes.ts';

export type ChangeEntity={relation:'target'|'source'|'scope';kind:'site'|'building'|'room'|'rack'|'device'|'portGroup';id:string;name:string;parentKind:'customer'|'site'|'building'|'room'|'rack'|'device'|null;parentId:string|null;deviceKind:'rackEquipment'|'dose'|'endDevice'|null;rackId:string|null;roomId:string|null;sizeU:number|null;positionU:null;sortOrder:number|null;groupType:string|null;prefix:string|null;portCount:number|null};
export type ChangeDetails={status:'captured'|'notAvailable';beforeEntities:ChangeEntity[];afterEntities:ChangeEntity[]};
export type DescriptiveChange=ClientChange&{details:ChangeDetails};
export type DescriptiveChangePage=Omit<ChangePage,'events'>&{events:DescriptiveChange[]};
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const uuid=(x:unknown):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const same=(a:string|null,b:string|null)=>a===null||b===null?a===b:a.toLowerCase()===b.toLowerCase();
const integer=(x:unknown,min:number,max=2147483647)=>Number.isInteger(x)&&Number(x)>=min&&Number(x)<=max;
// Names.Validate and InventoryJson.Text count Unicode scalar values, including supplementary characters.
const text=(x:unknown,empty=false):x is string=>typeof x==='string'&&(empty&&x.length===0||x.length>0&&x===x.replace(/^\p{White_Space}+|\p{White_Space}+$/gu,''))&&x.length<=200&&Array.from(x).length<=100&&!/[\p{Cc}\uD800-\uDFFF]/u.test(x);
const families=new Set(['rj45','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c']);
const entityKeys='relation,kind,id,name,parentKind,parentId,deviceKind,rackId,roomId,sizeU,positionU,sortOrder,groupType,prefix,portCount';
const invalid=():never=>{throw new ApiError(200,'response_invalid')};
const idFields=new Set(['id','parentId','rackId','roomId']);
function equalEntity(a:ChangeEntity,b:ChangeEntity,except:string[]=[]){
 return entityKeys.split(',').every(key=>except.includes(key)||(idFields.has(key)?same(a[key],b[key]):a[key]===b[key]));
}

function entityValid(e:ChangeEntity,customer:string){
 if(!keys(e,entityKeys)||!['target','source','scope'].includes(e.relation)||!uuid(e.id)||!text(e.name,e.kind==='portGroup')||e.positionU!==null)return false;
 if(e.parentId!==null&&(!uuid(e.parentId)||same(e.parentId,e.id)))return false;
 if(e.rackId!==null&&!uuid(e.rackId)||e.roomId!==null&&!uuid(e.roomId))return false;
 if(e.kind!=='device'&&e.deviceKind!==null||e.kind!=='portGroup'&&(e.groupType!==null||e.prefix!==null||e.portCount!==null))return false;
 if(['site','building','room'].includes(e.kind))return e.parentKind===({site:'customer',building:'site',room:'building'} as const)[e.kind as 'site'|'building'|'room']&&uuid(e.parentId)&&(e.kind!=='site'||same(e.parentId,customer))&&e.rackId===null&&e.roomId===null&&e.sizeU===null&&e.sortOrder===null;
 if(e.kind==='rack')return (e.parentKind===null&&e.parentId===null||e.parentKind==='room'&&uuid(e.parentId))&&same(e.roomId,e.parentId)&&e.rackId===null&&integer(e.sizeU,1,1000)&&e.sortOrder===null;
 if(e.kind==='device')return integer(e.sortOrder,0)&&(e.deviceKind==='rackEquipment'?e.parentKind==='rack'&&uuid(e.parentId)&&same(e.rackId,e.parentId)&&e.roomId===null&&integer(e.sizeU,1,1000):['dose','endDevice'].includes(e.deviceKind as string)&&e.parentKind==='room'&&uuid(e.parentId)&&same(e.roomId,e.parentId)&&e.rackId===null&&e.sizeU===null);
 return e.kind==='portGroup'&&e.parentKind==='device'&&uuid(e.parentId)&&e.rackId===null&&e.roomId===null&&e.sizeU===null&&integer(e.sortOrder,0)&&families.has(e.groupType as string)&&text(e.prefix,true)&&integer(e.portCount,1,96);
}
const one=(items:ChangeEntity[],kind:string,relation:string,id:string|null)=>items.length===1&&items[0].kind===kind&&items[0].relation===relation&&same(items[0].id,id);
function deviceSet(items:ChangeEntity[],relation:'target'|'source',deviceId?:string|null){
 const devices=items.filter(e=>e.kind==='device'),groups=items.filter(e=>e.kind==='portGroup');
 return devices.length>0&&devices.length+groups.length===items.length&&items.every(e=>e.relation===relation)&&(!deviceId||devices.length===1&&same(devices[0].id,deviceId))&&groups.every(g=>devices.some(d=>same(d.id,g.parentId)));
}
function rackSet(items:ChangeEntity[],relation:'target'|'source',rackId?:string|null){
 const racks=items.filter(e=>e.kind==='rack'),rest=items.filter(e=>e.kind!=='rack');
 return racks.length===1&&racks[0].relation===relation&&(!rackId||same(racks[0].id,rackId))&&(!rest.length||deviceSet(rest,relation))&&rest.filter(e=>e.kind==='device').every(d=>d.deviceKind==='rackEquipment'&&same(d.rackId,racks[0].id));
}
function policyValid(event:ClientChange,before:ChangeEntity[],after:ChangeEntity[]){
 const [_,kind,action]=event.action.split('.'),id=event.resourceId;
 if(!uuid(id))return false;
 if(['site','building','room'].includes(kind))return action==='create'?!before.length&&one(after,kind,'target',id):action==='delete'?one(before,kind,'target',id)&&!after.length:action==='update'&&one(before,kind,'target',id)&&one(after,kind,'target',id);
 if(kind==='rack'){
  if(action==='delete')return rackSet(before,'target',id)&&!after.length;
  if(action==='duplicate')return rackSet(before,'source')&&rackSet(after,'target',id)&&!same(before.find(e=>e.kind==='rack')!.id,id);
  return action==='create'?!before.length&&one(after,'rack','target',id):['update','assignRoom'].includes(action)&&one(before,'rack','target',id)&&one(after,'rack','target',id);
 }
 if(kind==='devices')return action==='delete'&&deviceSet(before,'target')&&!after.length;
 if(kind!=='device')return false;
 if(action==='reorder'){
  const valid=(items:ChangeEntity[])=>one(items.filter(e=>e.kind==='rack'),'rack','scope',id)&&items.every(e=>e.kind==='rack'||e.kind==='device'&&e.relation==='target'&&e.deviceKind==='rackEquipment'&&same(e.rackId,id));
  return valid(before)&&valid(after)&&before.length===after.length&&before.every(b=>after.some(a=>a.kind===b.kind&&same(a.id,b.id)));
 }
 if(action==='editPortGroups'){
  const valid=(items:ChangeEntity[])=>one(items.filter(e=>e.kind==='device'),'device','scope',id)&&items.every(e=>e.kind==='device'||e.kind==='portGroup'&&e.relation==='target'&&same(e.parentId,id));
  return valid(before)&&valid(after);
 }
 if(['create','createFromCatalog','createFromPrivateTemplate','createFromSharedTemplate'].includes(action))return !before.length&&deviceSet(after,'target',id);
 if(action==='delete')return deviceSet(before,'target',id)&&!after.length;
 return ['update','move'].includes(action)&&deviceSet(before,'target',id)&&deviceSet(after,'target',id);
}
export function validChangeDetails(details:ChangeDetails,event:ClientChange,customer:string){
 if(!keys(details,'status,beforeEntities,afterEntities'))return false;
 for(const entities of [details.beforeEntities,details.afterEntities]){
  if(!Array.isArray(entities)||entities.length>512||!entities.every(e=>entityValid(e,customer)))return false;
  const identities=entities.map(e=>e.kind+':'+e.id.toLowerCase()+':'+e.relation);
  if(new Set(identities).size!==identities.length)return false;
 }
 if(details.status==='notAvailable')return !details.beforeEntities.length&&!details.afterEntities.length;
 if(details.status!=='captured'||!policyValid(event,details.beforeEntities,details.afterEntities))return false;
 const before=details.beforeEntities,after=details.afterEntities,action=event.action.split('.')[2];
 if(!['create','createFromCatalog','createFromPrivateTemplate','createFromSharedTemplate','delete','duplicate','editPortGroups'].includes(action)&&
  (before.length!==after.length||!before.every(b=>after.some(a=>a.kind===b.kind&&a.relation===b.relation&&same(a.id,b.id)))))return false;
 // Enforce only command invariants provable from these finite recorded fields.
 if(before.some(b=>b.kind==='device'&&after.some(a=>a.kind==='device'&&same(a.id,b.id)&&a.deviceKind!==b.deviceKind)))return false;
 if(event.action==='inventory.rack.duplicate')return before.every(b=>after.every(a=>!same(a.id,b.id)));
 if(event.action==='inventory.device.update'){
  const b=before.find(e=>e.kind==='device')!,a=after.find(e=>e.kind==='device')!;
  if(!['parentKind','parentId','rackId','roomId','sortOrder'].every(key=>idFields.has(key)?same(a[key],b[key]):a[key]===b[key]))return false;
 }
 if(['inventory.device.update','inventory.device.move'].includes(event.action)&&before.filter(e=>e.kind==='portGroup').some(b=>!equalEntity(b,after.find(a=>a.kind==='portGroup'&&same(a.id,b.id))!)))return false;
 if(event.action==='inventory.device.reorder'&&before.some(b=>!equalEntity(b,after.find(a=>a.kind===b.kind&&same(a.id,b.id))!,b.kind==='device'?['sortOrder']:[])))return false;
 if(event.action==='inventory.device.editPortGroups'&&!equalEntity(before.find(e=>e.kind==='device')!,after.find(e=>e.kind==='device')!))return false;
 return true;
}

export async function readClientChangeDetails(api:RackClickApi,customerId:string,afterRevision:number|null,expected=api.actorId,signal?:AbortSignal):Promise<DescriptiveChangePage>{
 const authority=()=>{if(!uuid(expected)||api.actorId!==expected)throw new ApiError(409,'actor_changed')};authority();
 if(!uuid(customerId)||afterRevision!==null&&(!Number.isSafeInteger(afterRevision)||afterRevision<=0))throw new ApiError(422,'changes_cursor_invalid');
 const {data,etag}=await api.request('/customers/'+encodeURIComponent(customerId)+'/changes/details?'+(afterRevision===null?'':'afterRevision='+afterRevision+'&')+'limit=50',{signal});authority();
 if(!keys(data,'customerId,currentRevision,nextRevision,hasMore,refreshRequired,events')||!Array.isArray(data.events)||data.events.length>50)invalid();
 const baseEvents=data.events.map((event:any)=>{
  if(!keys(event,'id,actor,action,resourceId,revisionBefore,revisionAfter,occurredAt,context,details'))invalid();
  const {details,...base}=event;return base;
 });
 validateChangePage({...data,events:baseEvents},etag,customerId,afterRevision);
 for(const event of data.events)if(!validChangeDetails(event.details,event,customerId))invalid();
 return data;
}
