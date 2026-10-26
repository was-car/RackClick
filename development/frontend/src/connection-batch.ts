import {ApiError} from './api.ts';
import {type Project} from './inventory-model.ts';
export type BatchEndpoint={groupId:string;groupType:string;portId:string};
export type BatchPair={from:BatchEndpoint;to:BatchEndpoint};
export function prepareConnectionBatch(project:Project,pairs:BatchPair[],confirmReserved=false,color:string|null=null){
 if(!Array.isArray(pairs)||!pairs.length||pairs.length>128)throw new ApiError(422,'pairs_required');
 const used=new Set<string>(),reserved:string[]=[];
 const endpoint=(x:BatchEndpoint)=>{
  const group=project.portGroups.find(g=>g.id===x.groupId),port=project.ports.find(p=>p.id===x.portId);
  if(!group||!port||group.type!==x.groupType||port.groupId!==group.id||port.deviceId!==group.deviceId||!(port.type===group.type||group.type==='rj45'&&port.type==='rj45_poe'||group.type==='rj45_poe'&&port.type==='rj45'))throw new ApiError(422,'port_scope_invalid');
  if(used.has(port.id))throw new ApiError(422,'duplicate_ids');used.add(port.id);
  if(['disabled','faulty'].includes(port.status))throw new ApiError(422,'blocked_port');
  if(project.connections.some(c=>c.fromPortId===port.id||c.toPortId===port.id))throw new ApiError(409,'port_occupied');
  if(port.status==='reserved')reserved.push(port.id);
  return port.id;
 };
 const selected=pairs.map(pair=>({fromPortId:endpoint(pair.from),toPortId:endpoint(pair.to),color}));
 if(reserved.length&&!confirmReserved)throw new ApiError(422,'reserved_confirmation_required');
 return {type:'connections.createBatch',payload:{pairs:selected,confirmedReservedPortIds:reserved}};
}
