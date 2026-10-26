import { ApiError, type RackClickApi } from './api.ts';
import { validEvent, timestamp, type AuditEvent } from './admin-audit.ts';

export type ContextObject = { kind: 'systemhaus'|'user'|'userGroup'|'customerGroup'|'customer'|'grant'|'session'; id: string; relation: 'target'|'intendedTarget'|'member'|'intendedMember'|'scope'|'intendedScope' };
export type AuditContext = { status: 'available'|'notRecorded'; captureVersion: number|null; actorId: string|null; scopeKind: 'systemhaus'|'customer'|null; scopeId: string|null; customerId: string|null; revisionScope: 'systemhaus'|null; revisionBefore: number|null; revisionAfter: number|null; outcome: 'committed'|'cancelled'|null; objects: ContextObject[]; customerRevisionBefore?: number|null; customerRevisionAfter?: number|null };
export type AuditContextSnapshot = { revision: number; event: AuditEvent; context: AuditContext };
const uuid = (x: unknown): x is string => typeof x === 'string' && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x) && x !== '00000000-0000-0000-0000-000000000000';
const same = (a: string,b: string) => a.toLowerCase() === b.toLowerCase();
const keys = (x: any, expected: string) => !!x && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).sort().join() === expected;
const positive = (x: any) => Number.isSafeInteger(x) && x > 0;
export async function readAuditContext(api: RackClickApi,event: AuditEvent,expected=api.actorId): Promise<AuditContextSnapshot> {
 const actor=()=>{if(!uuid(expected)||api.actorId!==expected)throw new ApiError(409,'actor_changed')};actor();
 if(!validEvent(event))throw new ApiError(422,'request_invalid');
 const selected={...event,actor:{...event.actor}};
 const {data,etag}=await api.request('/admin/audit/'+encodeURIComponent(selected.id)+'/context');actor();
 const invalid=():never=>{throw new ApiError(200,'response_invalid')};
 if(!keys(data,'context,event,revision')||!positive(data.revision)||etag!=='"'+data.revision+'"'||!validEvent(data.event))invalid();
 const e=data.event,c=data.context;
 for(const field of ['id','requestId','resourceId'] as const)if(!same(e[field],selected[field]))invalid();
 if(!same(e.actor.id,selected.actor.id)||e.action!==selected.action||timestamp(e.occurredAt)!==timestamp(selected.occurredAt))invalid();
 const base='actorId,captureVersion,customerId,objects,outcome,revisionAfter,revisionBefore,revisionScope,scopeId,scopeKind,status';
 const extended='actorId,captureVersion,customerId,customerRevisionAfter,customerRevisionBefore,objects,outcome,revisionAfter,revisionBefore,revisionScope,scopeId,scopeKind,status';
 if(!keys(c,base)&&!keys(c,extended))invalid();
 if(!Array.isArray(c.objects)||c.objects.length>3)invalid();
 if(c.status==='notRecorded'){
  if(c.objects.length||Object.entries(c).some(([key,value])=>key!=='status'&&key!=='objects'&&value!==null))invalid();
  return data;
 }
 if(c.status!=='available'||c.captureVersion!==1||!uuid(c.actorId)||!same(c.actorId,e.actor.id)||!uuid(c.scopeId)||c.revisionScope!=='systemhaus'||!positive(c.revisionBefore)||!positive(c.revisionAfter)||!c.objects.length)invalid();
 const cancel=e.action.endsWith('.cancel');
 if(cancel?c.outcome!=='cancelled'||c.revisionBefore!==c.revisionAfter:c.outcome!=='committed'||!Number.isSafeInteger(c.revisionBefore+1)||c.revisionAfter!==c.revisionBefore+1)invalid();
 const kinds=['systemhaus','user','userGroup','customerGroup','customer','grant','session'],relations=['target','intendedTarget','member','intendedMember','scope','intendedScope'];
 for(const o of c.objects)if(!keys(o,'id,kind,relation')||!uuid(o.id)||!kinds.includes(o.kind)||!relations.includes(o.relation))invalid();
 const action=cancel?e.action.slice(0,-7):e.action,target=cancel?'intendedTarget':'target';
 let expectedObjects: string[][],resourceIndex=0;
 if(['user.create','userGroup.create','customerGroup.create'].includes(action))expectedObjects=[[cancel?'systemhaus':action.split('.')[0],target]];
 else if(['user.state.set','user.password.reset'].includes(action))expectedObjects=[['user',target]];
 else if(action==='user.session.revoke'){expectedObjects=[['user',target],['session',target]];resourceIndex=1}
 else if(['userGroup.member.set','customerGroup.member.set'].includes(action))expectedObjects=[[action.split('.')[0],target],[action.startsWith('userGroup')?'user':'customer',cancel?'intendedMember':'member']];
 else if(action==='userGroup.grant.set')expectedObjects=[['userGroup',target],['grant',target],['*',cancel?'intendedScope':'scope']];
 else if(!cancel&&['systemhaus.rename','customer.create','customer.rename'].includes(action))expectedObjects=[[action.startsWith('customer')?'customer':'systemhaus','target']];
 else invalid();
 if(c.objects.length!==expectedObjects.length||!same(c.objects[resourceIndex].id,e.resourceId))invalid();
 expectedObjects.forEach(([kind,relation],i)=>{if((kind==='*'?!['systemhaus','customer','customerGroup'].includes(c.objects[i].kind):c.objects[i].kind!==kind)||c.objects[i].relation!==relation)invalid()});
 if(cancel&&action.endsWith('.create')&&!same(c.objects[0].id,c.scopeId))invalid();
 if(action==='systemhaus.rename'&&!same(e.resourceId,c.scopeId))invalid();
 if(action==='userGroup.grant.set'&&c.objects[2].kind==='systemhaus'&&!same(c.objects[2].id,c.scopeId))invalid();
 const customerAction=['customer.create','customer.rename'].includes(e.action);
 if(customerAction?c.scopeKind!=='customer':c.scopeKind!=='systemhaus')invalid();
 if(c.scopeKind==='systemhaus'){
  if(c.customerId!==null||(c.customerRevisionBefore??null)!==null||(c.customerRevisionAfter??null)!==null)invalid();
 }else if(c.scopeKind==='customer'){
  if(cancel||!uuid(c.customerId)||!same(c.scopeId,c.customerId)||!same(c.customerId,e.resourceId)||!positive(c.customerRevisionAfter))invalid();
  if(e.action==='customer.create'?c.customerRevisionBefore!==null||c.customerRevisionAfter!==1:e.action!=='customer.rename'||!positive(c.customerRevisionBefore)||!Number.isSafeInteger(c.customerRevisionBefore+1)||c.customerRevisionAfter!==c.customerRevisionBefore+1)invalid();
 }else invalid();
 return data;
}
