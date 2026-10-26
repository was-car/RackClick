import { compensationUuid, compensationIdsEqual, type CompensationCandidate } from './inventory-compensation.ts';
import { ApiError, type Mutation, type RackClickApi } from './api.ts';
import { validProject, type Project } from './inventory-model.ts';
export type InventoryMutation = Mutation & { customerId: string };
// Ephemeral response expectations only. The journal and request body stay unchanged.
let expected:CompensationCandidate|null=null;
export function rememberCompensation(candidate:CompensationCandidate){expected=candidate}
function expectedCompensation(operation:InventoryMutation,sourceId:string){return expected?.actorId===operation.actorId&&expected.customerId===operation.customerId&&expected.operationId===sourceId?expected:null}
export async function loadProject(api: RackClickApi, customerId: string): Promise<Project> {
 const { data, etag } = await api.request('/customers/' + encodeURIComponent(customerId) + '/project');
 if (!validProject(data, customerId) || etag !== '"' + data.revision + '"') throw new ApiError(200, 'response_invalid');
 return data;
}
export function prepareCommand(api: RackClickApi, customerId: string, type: string, payload: object, revision: number, actorId = api.actorId): InventoryMutation {
 if (!customerId || !type || !Number.isSafeInteger(revision) || revision < 1) throw new ApiError(422, 'command_invalid');
 return Object.freeze({ customerId, path: '/customers/' + encodeURIComponent(customerId) + '/commands', method: 'POST', body: JSON.stringify({ type, payload }), etag: '"' + revision + '"', requestId: crypto.randomUUID(), actorId });
}
function validateCompensationResult(operation:InventoryMutation,data:any) {
 let command;try {command=JSON.parse(operation.body)} catch {throw new ApiError(200,'response_invalid',true)}
 if(command.type!=='operations.compensate')return;
 const r=data?.result,source=command.payload?.operationId,expected=expectedCompensation(operation,source);
 if(r?.compensationKind==='groupReduction'){
  const ports=r.restoredPortIds,groups=r.restoredGroupIds,connections=r.restoredConnectionIds;
  const validIds=(ids:any,max:number,min:number)=>Array.isArray(ids)&&ids.length>=min&&ids.length<=max&&ids.every(compensationUuid)&&new Set(ids.map((id:string)=>id.toLowerCase())).size===ids.length;
  if(expected&&expected.compensationKind!=='groupReduction'||data.customerId!==operation.customerId||data.requestId!==operation.requestId||data.revision!==Number(operation.etag.slice(1,-1))+1||!compensationUuid(data.operationId)||data.operationId===source||!compensationUuid(source)||r.compensatedOperationId!==source||!compensationUuid(r.resourceId)||Object.keys(r).sort().join()!=='compensatedOperationId,compensationKind,resourceId,restoredConnectionIds,restoredGroupIds,restoredPortIds'||!validIds(ports,256,1)||!validIds(groups,32,0)||!validIds(connections,256,0)||ports.length+groups.length>256||connections.length>ports.length||new Set([...ports,...groups,...connections,r.resourceId].map((id:string)=>id.toLowerCase())).size!==ports.length+groups.length+connections.length+1||expected?.compensationKind==='groupReduction'&&(r.resourceId!==expected.deviceId||!compensationIdsEqual(ports,expected.portIds)||!compensationIdsEqual(groups,expected.groupIds)||!compensationIdsEqual(connections,expected.connectionIds)))throw new ApiError(200,'response_invalid',true);
  return;
 }
 if(r?.compensationKind==='groupGrowth'){
  const ports=r.removedPortIds,groups=r.removedGroupIds;
  const validIds=(ids:any,max:number,min:number)=>Array.isArray(ids)&&ids.length>=min&&ids.length<=max&&ids.every(compensationUuid)&&new Set(ids.map((id:string)=>id.toLowerCase())).size===ids.length;
  if(expected&&expected.compensationKind!=='groupGrowth'||data.customerId!==operation.customerId||data.requestId!==operation.requestId||data.revision!==Number(operation.etag.slice(1,-1))+1||!compensationUuid(data.operationId)||data.operationId===source||!compensationUuid(source)||r.compensatedOperationId!==source||!compensationUuid(r.resourceId)||Object.keys(r).sort().join()!=='compensatedOperationId,compensationKind,removedGroupIds,removedPortIds,resourceId'||!validIds(ports,256,1)||!validIds(groups,32,0)||ports.length+groups.length>256||new Set([...ports,...groups,r.resourceId].map((id:string)=>id.toLowerCase())).size!==ports.length+groups.length+1||expected?.compensationKind==='groupGrowth'&&(r.resourceId!==expected.deviceId||!compensationIdsEqual(ports,expected.portIds)||!compensationIdsEqual(groups,expected.groupIds)))throw new ApiError(200,'response_invalid',true);
  return;
 }
 if(expected?.compensationKind||data?.customerId!==operation.customerId||data?.requestId!==operation.requestId||data?.revision!==Number(operation.etag.slice(1,-1))+1||!compensationUuid(data?.operationId)||data.operationId===source||!r||Object.keys(r).sort().join()!=='changedIds,compensatedOperationId,resourceId'||!compensationUuid(r.resourceId)||!compensationUuid(source)||r.compensatedOperationId!==source||!Array.isArray(r.changedIds)||!r.changedIds.length||r.changedIds.length>256||!r.changedIds.every(compensationUuid)||new Set(r.changedIds.map((id:string)=>id.toLowerCase())).size!==r.changedIds.length||expected&&(r.resourceId!==expected.deviceId||JSON.stringify(r.changedIds)!==JSON.stringify(expected.portIds)))throw new ApiError(200,'response_invalid',true);
}
function validateCatalogResult(operation:InventoryMutation,data:any){
 let command;try{command=JSON.parse(operation.body)}catch{throw new ApiError(200,'response_invalid',true)}
 if(!['device.createFromCatalog','device.createFromPrivateTemplate','device.createFromSharedTemplate'].includes(command.type))return;
 const r=data?.result,ids=r?.createdIds;
 if(Object.keys(data||{}).sort().join()!=='customerId,operationId,requestId,result,revision'||data.revision!==Number(operation.etag.slice(1,-1))+1||!compensationUuid(data.operationId)||!r||Object.keys(r).sort().join()!=='createdIds,resourceId'||!compensationUuid(r.resourceId)||!Array.isArray(ids)||ids.length<1||ids.length>3105||!ids.every(compensationUuid)||new Set(ids.map((id:string)=>id.toLowerCase())).size!==ids.length||ids[0]!==r.resourceId)throw new ApiError(200,'response_invalid',true);
}
function confirmedCommand(operation:InventoryMutation,data:any) {
 if (data?.customerId !== operation.customerId || data.requestId !== operation.requestId || !Number.isSafeInteger(data.revision) || data.revision < 1 || typeof data.operationId !== 'string' || !data.result || typeof data.result !== 'object') throw new ApiError(200, 'response_invalid', true);
 validateCompensationResult(operation,data);
 validateCatalogResult(operation,data);
 return data as { customerId: string; revision: number; requestId: string; operationId: string; result: { resourceId?: string; createdIds?: string[]; removedIds?: string[]; compensationKind?: 'groupGrowth' | 'groupReduction'; removedPortIds?: string[]; removedGroupIds?: string[]; restoredPortIds?: string[]; restoredGroupIds?: string[]; restoredConnectionIds?: string[] } };
}
export async function executeCommand(api: RackClickApi, operation: InventoryMutation) {
 return confirmedCommand(operation,await api.sendMutation(operation));
}
export async function readPendingCommand(api:RackClickApi,operation:InventoryMutation,signal?:AbortSignal) {
 const authority=(uncertain=false)=>{if(signal?.aborted||!api.actorId||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed',uncertain)};
 authority();
 if(!compensationUuid(operation.customerId)||!compensationUuid(operation.requestId))throw new ApiError(422,'request_invalid');
 const {data}=await api.request('/customers/'+encodeURIComponent(operation.customerId)+'/operations/'+encodeURIComponent(operation.requestId),{method:'GET',signal});
 authority(true);
 const keys=data&&typeof data==='object'?Object.keys(data).sort().join():'';
 const expectedKeys=data?.state==='cancelled'?'customerId,operation,operationId,requestId,revision,state':'customerId,operation,requestId,revision,state';
 if(keys!==expectedKeys||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!Number.isSafeInteger(data.revision)||data.revision<1||!['committed','notRecorded','cancelled'].includes(data.state))throw new ApiError(200,'response_invalid',true);
 if(data.state==='committed'){
  const result=confirmedCommand(operation,data.operation);
  if(data.revision<result.revision)throw new ApiError(200,'response_invalid',true);
 }else if(data.operation!==null||data.state==='cancelled'&&!compensationUuid(data.operationId))throw new ApiError(200,'response_invalid',true);
 return data as {state:'committed'|'notRecorded'|'cancelled';customerId:string;requestId:string;revision:number;operation:ReturnType<typeof confirmedCommand>|null};
}
export async function cancelPendingCommand(api: RackClickApi, operation: InventoryMutation) {
 const data = await api.sendMutation({ ...operation, path: '/customers/' + encodeURIComponent(operation.customerId) + '/operations/' + encodeURIComponent(operation.requestId) + '/cancel' });
 if (data?.customerId !== operation.customerId || data?.requestId !== operation.requestId) throw new ApiError(200, 'response_invalid', true);
 if (data.state === 'cancelled') return data as { state: 'cancelled'; customerId: string; requestId: string };
 if (data.state === 'committed' && data.operation?.customerId === operation.customerId && data.operation?.requestId === operation.requestId && Number.isSafeInteger(data.operation?.revision) && typeof data.operation?.operationId === 'string' && data.operation?.result) { validateCompensationResult(operation,data.operation); validateCatalogResult(operation,data.operation); return data; }
 throw new ApiError(200, 'response_invalid', true);
}
