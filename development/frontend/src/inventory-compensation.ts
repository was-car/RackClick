import type { Project } from './inventory-model.ts';
import type { InventoryMutation } from './inventory-api.ts';
type CandidateIdentity = {actorId:string;customerId:string;operationId:string;revision:number;deviceId:string;portIds:string[]};
export type CompensationCandidate = CandidateIdentity & (
 {compensationKind?:never;groupId:string} |
 {compensationKind:'groupGrowth'|'groupReduction';groupIds:string[];connectionIds:string[]}
);
const fields = new Set(['status','label','color','face','poe','watts']);
export const compensationUuid=(x:unknown):x is string=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
export function candidateMatches(candidate:CompensationCandidate|null,project:Project|null,actorId:string,customerId:string):boolean {
 return !!candidate&&!!project&&candidate.actorId===actorId&&candidate.customerId===customerId&&project.customerId===customerId&&candidate.revision===project.revision;
}
export function compensationIdsEqual(left:string[],right:string[]):boolean {
 const sorted=[...right].sort();return left.length===right.length&&[...left].sort().every((id,index)=>id===sorted[index]);
}
export function compensationCandidate(operation:InventoryMutation|undefined,result:any,before:Project|null,actorId:string,customerId:string,after?:Project):CompensationCandidate|null {
 try {
  if(!operation||operation.actorId!==actorId||operation.customerId!==customerId||result?.customerId!==customerId||result?.requestId!==operation.requestId||!compensationUuid(result.operationId)||result.revision!==Number(operation.etag.slice(1,-1))+1)return null;
  const command=JSON.parse(operation.body),p=command.payload,changes=p?.changes;
  if(command.type==='device.editPortGroups')return groupCandidate(operation,result,before,after,actorId,customerId,p);
  if(command.type!=='ports.update'||!p||Object.keys(p).sort().join()!=='changes,deviceId,groupId,groupType,portIds'||!changes||typeof changes!=='object'||Array.isArray(changes)||!Object.keys(changes).length||!Object.keys(changes).every(k=>fields.has(k)))return null;
  if(!compensationUuid(p.deviceId)||!compensationUuid(p.groupId)||!Array.isArray(p.portIds)||!p.portIds.length||p.portIds.length>256||!p.portIds.every(compensationUuid)||new Set(p.portIds).size!==p.portIds.length||result.result?.resourceId!==p.deviceId||!Array.isArray(result.result?.changedIds)||JSON.stringify(result.result.changedIds)!==JSON.stringify(p.portIds))return null;
  // A matching pre-commit view can prove a no-op. Recovery after reload cannot.
  if(before?.customerId===customerId&&before.revision===result.revision-1){
   const ports=p.portIds.map((id:string)=>before.ports.find(port=>port.id===id));
   if(ports.some((port:any)=>!port||port.deviceId!==p.deviceId||port.groupId!==p.groupId))return null;
   // UpdatePorts also normalises the RJ45 variant when PoE is supplied, even if its boolean is unchanged.
   if(!ports.some((port:any)=>Object.entries(changes).some(([key,value])=>port[key]!==value)||Object.hasOwn(changes,'poe')&&['rj45','rj45_poe'].includes(port.type)&&port.type!==(changes.poe?'rj45_poe':'rj45')))return null;
  }
  return {actorId,customerId,operationId:result.operationId,revision:result.revision,deviceId:p.deviceId,groupId:p.groupId,portIds:[...p.portIds]};
 } catch {return null}
}

// A pair of adjacent server views describes a proposal only. The command sends
// the source operationId, never these views or previous values. The server's
// complete audit evidence, permissions and current state remain authoritative.
function groupCandidate(operation:InventoryMutation,result:any,before:Project|null,after:Project|undefined,actorId:string,customerId:string,p:any):CompensationCandidate|null {
 if(!before||!after||before.customerId!==customerId||after.customerId!==customerId||before.revision!==result.revision-1||after.revision!==result.revision||
    !compensationUuid(actorId)||!compensationUuid(customerId)||!compensationUuid(p?.deviceId)||result.result?.resourceId!==p.deviceId||
    Object.keys(p).some(k=>!['deviceId','groups','removedPortIds','confirmationToken'].includes(k))||!Array.isArray(p.groups))return null;
 const ids=(value:any,max=256)=>Array.isArray(value)&&value.length<=max&&value.every(compensationUuid)&&new Set(value.map((id:string)=>id.toLowerCase())).size===value.length;
 const r=result.result;
 if(Object.keys(r).sort().join()!=='createdIds,removedIds,resourceId'||!ids(r.createdIds)||!ids(r.removedIds)||!ids(p.removedPortIds))return null;
 function canonical(value:any):string {
  if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
  if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}';
  return JSON.stringify(value);
 }
 const scope=(project:Project)=>{
  const groups=project.portGroups.filter(g=>g.deviceId===p.deviceId),ports=project.ports.filter(port=>port.deviceId===p.deviceId),portIds=new Set(ports.map(port=>port.id));
  const connections=project.connections.filter(c=>portIds.has(c.fromPortId)||portIds.has(c.toPortId));
  if(groups.length>32||ports.length>3072||connections.length>3072||![groups,ports,connections].every(rows=>ids(rows.map(row=>row.id),3072)))throw Error('invalid_scope');
  return {groups,ports,connections};
 };
 const oldDevice=before.devices.find(d=>d.id===p.deviceId),newDevice=after.devices.find(d=>d.id===p.deviceId);
 if(!oldDevice||!newDevice||canonical(oldDevice)!==canonical(newDevice))return null;
 const old=scope(before),next=scope(after);
 const difference=(left:{id:string}[],right:{id:string}[])=>left.filter(row=>!right.some(other=>other.id===row.id)).map(row=>row.id).sort();
 const addedPorts=difference(next.ports,old.ports),removedPorts=difference(old.ports,next.ports),addedGroups=difference(next.groups,old.groups),removedGroups=difference(old.groups,next.groups);
 const unchanged=(left:{id:string}[],right:{id:string}[])=>left.every(row=>{const other=right.find(item=>item.id===row.id);return !other||canonical(row)===canonical(other)});
 if(!unchanged(old.groups,next.groups)||!unchanged(old.ports,next.ports)||!unchanged(old.connections,next.connections))return null;
 const removedConnections=difference(old.connections,next.connections),addedConnections=difference(next.connections,old.connections);
 if(addedPorts.length&&removedPorts.length===0&&removedGroups.length===0&&removedConnections.length===0&&addedConnections.length===0&&
    r.removedIds.length===0&&p.removedPortIds.length===0&&compensationIdsEqual(r.createdIds,[...addedPorts,...addedGroups])&&addedPorts.length+addedGroups.length<=256){
  return {actorId,customerId,operationId:result.operationId,revision:result.revision,deviceId:p.deviceId,compensationKind:'groupGrowth',portIds:addedPorts,groupIds:addedGroups,connectionIds:[]};
 }
 if(removedPorts.length&&addedPorts.length===0&&addedGroups.length===0&&addedConnections.length===0&&r.createdIds.length===0&&
    removedPorts.length+removedGroups.length<=256&&removedConnections.length<=removedPorts.length&&
    compensationIdsEqual(r.removedIds,removedPorts)&&compensationIdsEqual(p.removedPortIds,removedPorts)&&
    old.connections.filter(c=>removedConnections.includes(c.id)).every(c=>removedPorts.includes(c.fromPortId)||removedPorts.includes(c.toPortId))){
  return {actorId,customerId,operationId:result.operationId,revision:result.revision,deviceId:p.deviceId,compensationKind:'groupReduction',portIds:removedPorts,groupIds:removedGroups,connectionIds:removedConnections};
 }
 return null;
}
