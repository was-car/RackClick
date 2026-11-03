import {validConnectorDescriptor} from './hardware-connector-classification.mjs';
import {ApiError,allows,type RackClickApi,type Session} from './api.ts';
export type ReportFilter={reportKind:'ports'|'connections';query:string;status:string;family:string;rackId:string|null};
export type ReportRequest=Readonly<{actorId:string;customerId:string;revision:number;requestId:string;body:string}>;
export const reportUuid=(x:any)=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const invalid=():never=>{throw new ApiError(200,'response_invalid',true)};
export function reportAllowed(api:RackClickApi,session:Session,customerId:string){return api.actorId===session.user.id&&allows(session,'inventory.read',customerId)&&allows(session,'reports.export',customerId)}
export function prepareReport(api:RackClickApi,actorId:string,customerId:string,revision:number,filter:ReportFilter):ReportRequest{
 if(api.actorId!==actorId||!reportUuid(actorId))throw new ApiError(409,'actor_changed');
 if(!reportUuid(customerId)||!Number.isSafeInteger(revision)||revision<1||!keys(filter,'reportKind,query,status,family,rackId')||!['ports','connections'].includes(filter.reportKind)||typeof filter.query!=='string'||Array.from(filter.query).length>200||!['all','free','reserved','disabled','faulty'].includes(filter.status)||!['all','rj45','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c','sfp56','qsfpdd','idc','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc'].includes(filter.family)||filter.reportKind==='connections'&&(filter.status!=='all'||filter.family!=='all')||filter.rackId!==null&&!reportUuid(filter.rackId))throw new ApiError(422,'request_invalid');
 return Object.freeze({actorId,customerId,revision,requestId:crypto.randomUUID(),body:JSON.stringify(filter)});
}
export function parseReportCsv(text:string):string[][]{
 const rows:string[][]=[];let row:string[]=[],cell='',quoted=false,closed=false,start=true;
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=c;continue;}
  if(start){if(c!=='"')invalid();quoted=true;start=false;continue;}
  if(!closed)invalid();
  if(c===','){row.push(cell);cell='';closed=false;start=true;}
  else if(c==='\r'&&text[i+1]==='\n'){row.push(cell);rows.push(row);row=[];cell='';closed=false;start=true;i++;}
  else invalid();
 }
 if(quoted||closed||!start||row.length||!rows.length)invalid();
 return rows;
}
export const portReportColumns='customer_id,source_revision,port_id,device_id,device_name,device_kind,rack_id,rack_name,room_id,room_name,site_id,site_name,building_id,building_name,group_id,group_name,type,family,gn,label,status,face,poe,watts,color,power_role,connected,connection_ids,peer_port_ids'.split(',');
export const connectionReportColumns=['customer_id','source_revision','connection_id','note','color','patch','cross_rack',...portReportColumns.slice(2).map(k=>'from_'+k),...portReportColumns.slice(2).map(k=>'to_'+k)];
export function reportColumns(kind:string,physical=false){
 const ports=physical?[...portReportColumns,'physical_connector']:portReportColumns;
 return kind==='ports'?ports:['customer_id','source_revision','connection_id','note','color','patch','cross_rack',...ports.slice(2).map(k=>'from_'+k),...ports.slice(2).map(k=>'to_'+k)];
}
// Exactly two closed layouts. Legacy data keeps its original header and bytes.
export function validReportColumns(kind:string,rows:string[][]):boolean{
 if(!rows.length||!['ports','connections'].includes(kind))return false;
 const header=rows[0],same=(a:string[])=>JSON.stringify(a)===JSON.stringify(header);
 if(rows.some(row=>row.length!==header.length))return false;
 if(same(reportColumns(kind)))return true;
 if(!same(reportColumns(kind,true)))return false;
 const pairs=kind==='ports'?[['type','physical_connector']]:[['from_type','from_physical_connector'],['to_type','to_physical_connector']];
 let present=false;
 for(const row of rows.slice(1))for(const [type,key] of pairs){
  const value=row[header.indexOf(key)];if(value!==''){if(!validConnectorDescriptor(row[header.indexOf(type)],value))return false;present=true;}
 }
 return present;
}

export const encodeReportValue=(value:string)=>value.startsWith("'")||/^[\t\r\n]/.test(value)||/^\p{White_Space}*[=+@-]/u.test(value)?"'"+value:value;
export const decodeReportValue=(value:string)=>value.startsWith("'")?value.slice(1):value;
export async function validateReportResult(data:any,operation:ReportRequest){
 const f=JSON.parse(operation.body),r=data?.report;
 if(!keys(data,'kind,customerId,revision,requestId,operationId,report')||data.kind!=='report'||data.customerId!==operation.customerId||data.revision!==operation.revision||data.requestId!==operation.requestId||!reportUuid(data.operationId)||!keys(r,'reportKind,query,status,family,rackId,filename,contentType,encoding,csvValueEncoding,rowCount,byteLength,sha256,contentBase64')||!Object.keys(f).every(k=>r[k]===f[k])||r.filename!==`rackclick-${f.reportKind}-${operation.customerId}-r${operation.revision}.csv`||r.contentType!=='text/csv; charset=utf-8'||r.encoding!=='utf-8-bom'||r.csvValueEncoding!=='spreadsheet-safe-apostrophe-v1'||!Number.isSafeInteger(r.rowCount)||r.rowCount<0||r.rowCount>10000||!Number.isSafeInteger(r.byteLength)||r.byteLength<3||r.byteLength>4194304||typeof r.sha256!=='string'||!/^[0-9a-f]{64}$/.test(r.sha256)||typeof r.contentBase64!=='string'||r.contentBase64.length>5592408||r.contentBase64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(r.contentBase64))invalid();
 let bytes:Uint8Array;try{const decoded=atob(r.contentBase64);if(btoa(decoded)!==r.contentBase64)invalid();bytes=Uint8Array.from(decoded,c=>c.charCodeAt(0));}catch{invalid();}
 if(bytes!.length!==r.byteLength||bytes![0]!==239||bytes![1]!==187||bytes![2]!==191)invalid();
 const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');if(sha!==r.sha256)invalid();
 let text:string;try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes!);}catch{invalid();}
 const rows=parseReportCsv(text!);if(rows.length!==r.rowCount+1||!rows[0].length||rows.some((row,i)=>row.length!==rows[0].length||i>0&&row.some(cell=>encodeReportValue(decodeReportValue(cell))!==cell)))invalid();
 if(!validReportColumns(f.reportKind,rows.map((row,index)=>index?row.map(decodeReportValue):row)))invalid();
 const ids=new Set();for(const row of rows.slice(1)){const decoded=row.map(decodeReportValue),id=decoded[2];if(decoded[0]!==operation.customerId||decoded[1]!==String(operation.revision)||!reportUuid(id)||ids.has(id))invalid();ids.add(id);}
 return {result:data,bytes:bytes!,rows};
}
function current(api:RackClickApi,operation:ReportRequest,signal?:AbortSignal){if(signal?.aborted||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed');}
export async function sendReport(api:RackClickApi,operation:ReportRequest,signal?:AbortSignal){
 current(api,operation,signal);if(!api.csrf)throw new ApiError(401,'authentication_required');
 const {data}=await api.request('/customers/'+operation.customerId+'/reports/csv',{method:'POST',signal,headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':operation.actorId,'If-Match':'"'+operation.revision+'"','Idempotency-Key':operation.requestId},body:operation.body});
 current(api,operation,signal);const validated=await validateReportResult(data,operation);current(api,operation,signal);return validated;
}
export async function recoverReport(api:RackClickApi,operation:ReportRequest,signal?:AbortSignal){
 current(api,operation,signal);const {data}=await api.request('/customers/'+operation.customerId+'/reports/operations/'+operation.requestId,{signal});current(api,operation,signal);
 if(!keys(data,'state,customerId,requestId,operation')||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!['committed','notRecorded'].includes(data.state))invalid();
 if(data.state==='notRecorded'){if(data.operation!==null)invalid();return null;}
 const validated=await validateReportResult(data.operation,operation);current(api,operation,signal);return validated;
}
export function downloadReport(validated:Awaited<ReturnType<typeof validateReportResult>>,api:RackClickApi,session:Session,customerId:string){
 if(!reportAllowed(api,session,customerId)||validated.result.customerId!==customerId)throw new ApiError(403,'forbidden');
 const url=URL.createObjectURL(new Blob([validated.bytes],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');
 try{link.href=url;link.download=validated.result.report.filename;document.body.appendChild(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
}
