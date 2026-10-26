import {ApiError,allows,type RackClickApi,type Session} from './api.ts';
export type Rc9ExcelFilter={rackId:string};
export type Rc9ExcelRequest=Readonly<{actorId:string;customerId:string;revision:number;requestId:string;body:string}>;
export const rc9ExcelFormat='xls-html-rc9-v1';
export const rc9ExcelPrefix='<!DOCTYPE html><html xmlns="http://www.w3.org/TR/REC-html40" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel"><head><meta charset="utf-8"><style>td,th{mso-number-format:"\\@";white-space:pre-wrap}</style><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>Devices</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet><x:ExcelWorksheet><x:Name>Connections</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet><x:ExcelWorksheet><x:Name>Summary</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head>';
export const rc9ExcelHeaders={Devices:['Name','Preset','Size (U)','Ports','Connected','Icon','Color'],Connections:['From Device','From Port#','From Type','From Label','To Device','To Port#','To Type','To Label','Cable/Note','Cross-Rack','Color','Created'],Summary:['Property','Value']};
export const rc9ExcelSummaryKeys=['Rack Name','Location','Size','Used','Free','Devices','Connections','Project','Technician','Exported'];
const groupTypes=new Set(['rj45','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c']);
const uuid=(x:any)=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const canonicalUuid=(x:any)=>uuid(x)&&x===x.toLowerCase();
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const invalid=():never=>{throw new ApiError(200,'response_invalid',true)};
const escapeText=(s:string)=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
function cellText(raw:string){
 const text=raw.replace(/&(?:amp|lt|gt|quot|#39);/g,e=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'"}[e]!));
 if(text.length>32767||escapeText(text)!==raw)invalid();
 for(const char of text){const p=char.codePointAt(0)!;if(p<32&&![9,10,13].includes(p)||p>=127&&p<=159||p>=0xd800&&p<=0xdfff||(p&0xffff)>=0xfffe)invalid();}
 return text;
}
function cellAttribute(raw:string){
 const text=raw.replace(/&(?:amp|lt|gt|quot|#39|#9|#13|#10);/g,e=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'",'&#9;':'\t','&#13;':'\r','&#10;':'\n'}[e]!));
 const canonical=escapeText(text).replace(/\t/g,'&#9;').replace(/\r/g,'&#13;').replace(/\n/g,'&#10;');
 if(canonical!==raw)invalid();cellText(escapeText(text));return text;
}
export function rc9ExcelAllowed(api:RackClickApi,session:Session,customerId:string){return api.actorId===session.user.id&&allows(session,'inventory.read',customerId)&&allows(session,'reports.export',customerId)}
export function prepareRc9Excel(api:RackClickApi,actorId:string,customerId:string,revision:number,filter:Rc9ExcelFilter):Rc9ExcelRequest{
 if(api.actorId!==actorId||!uuid(actorId))throw new ApiError(409,'actor_changed');
 if(!uuid(customerId)||!Number.isSafeInteger(revision)||revision<1||!keys(filter,'rackId')||!uuid(filter.rackId))throw new ApiError(422,'request_invalid');
 return Object.freeze({actorId,customerId,revision,requestId:crypto.randomUUID(),body:JSON.stringify({rackId:filter.rackId.toLowerCase()})});
}
// A cursor consumes the entire versioned grammar. No browser HTML parser, DOM insertion,
// permissive tag allowlist, dynamic CSS or recursive entity decoding is involved.
export function parseRc9ExcelHtml(html:string,operation:Rc9ExcelRequest,report:any){
 let cursor=0;
 const take=(literal:string)=>{if(!html.startsWith(literal,cursor))invalid();cursor+=literal.length;};
 const attr=(name:string)=>{take(' '+name+'="');const end=html.indexOf('"',cursor);if(end<cursor)invalid();const value=html.slice(cursor,end);cursor=end+1;return value;};
 const idAttr=(name:string)=>{const value=attr(name);if(!canonicalUuid(value))invalid();return value;};
 const cell=(tag:'td'|'th')=>{let attribute:string|undefined;if(tag==='th')take('<th x:str>');else{take('<td x:str="');const close=html.indexOf('"',cursor);if(close<cursor)invalid();attribute=cellAttribute(html.slice(cursor,close));cursor=close;take('">');}const end=html.indexOf('</'+tag+'>',cursor);if(end<cursor)invalid();const value=cellText(html.slice(cursor,end));if(tag==='td'&&attribute!==value)invalid();cursor=end;take('</'+tag+'>');return value;};
 const table=(name:keyof typeof rc9ExcelHeaders)=>{take('<table x:str="" border="1" data-table="'+name+'"><thead><tr>');for(const h of rc9ExcelHeaders[name])if(cell('th')!==h)invalid();take('</tr></thead><tbody>');};
 take(rc9ExcelPrefix);take('<body data-format="xls-html-rc9-v1" data-customer-id="'+operation.customerId+'" data-rack-id="'+report.rackId+'" data-revision="'+operation.revision+'">');
 const devices:{id:string;cells:string[]}[]=[],connections:{id:string;from:{deviceId:string;portId:string;groupId:string;groupType:string};to:{deviceId:string;portId:string;groupId:string;groupType:string};cells:string[]}[]=[],summary:string[][]=[];
 const deviceIds=new Set<string>(),connectionIds=new Set<string>(),portIds=new Set<string>(),groups=new Map<string,string>();
 table('Devices');for(let i=0;i<report.deviceCount;i++){take('<tr');const id=idAttr('data-device-id');take('>');if(deviceIds.has(id))invalid();deviceIds.add(id);const cells=rc9ExcelHeaders.Devices.map(()=>cell('td'));take('</tr>');devices.push({id,cells});}take('</tbody></table>');
 table('Connections');for(let i=0;i<report.connectionCount;i++){
  take('<tr');const id=idAttr('data-connection-id');if(connectionIds.has(id))invalid();connectionIds.add(id);
  const endpoint=(side:'from'|'to')=>{const prefix='data-'+side+'-',deviceId=idAttr(prefix+'device-id'),portId=idAttr(prefix+'port-id'),groupId=idAttr(prefix+'group-id'),groupType=attr(prefix+'group-type');if(!groupTypes.has(groupType)||portIds.has(portId))invalid();portIds.add(portId);const owner=deviceId+':'+groupType;if(groups.has(groupId)&&groups.get(groupId)!==owner)invalid();groups.set(groupId,owner);return {deviceId,portId,groupId,groupType};};
  const from=endpoint('from'),to=endpoint('to');take('>');if(!deviceIds.has(from.deviceId)&&!deviceIds.has(to.deviceId))invalid();const cells=rc9ExcelHeaders.Connections.map(()=>cell('td'));take('</tr>');connections.push({id,from,to,cells});
 }take('</tbody></table>');
 table('Summary');for(const property of rc9ExcelSummaryKeys){take('<tr>');const row=[cell('td'),cell('td')];if(row[0]!==property)invalid();take('</tr>');summary.push(row);}take('</tbody></table></body></html>');
 if(cursor!==html.length||summary[5][1]!==String(report.deviceCount)||summary[6][1]!==String(report.connectionCount)||summary[8][1]!==''||summary[9][1]!==report.generatedAt)invalid();
 return {devices,connections,summary};
}
export async function validateRc9ExcelResult(data:any,operation:Rc9ExcelRequest){
 const f=JSON.parse(operation.body),r=data?.report;
 if(!keys(data,'kind,customerId,revision,requestId,operationId,report')||data.kind!=='rc9ExcelReport'||data.customerId!==operation.customerId||data.revision!==operation.revision||data.requestId!==operation.requestId||!canonicalUuid(data.operationId)||!keys(r,'format,cellEncoding,rackId,generatedAt,filename,contentType,deviceCount,connectionCount,summaryCount,rowCount,byteLength,sha256,contentBase64')||r.format!==rc9ExcelFormat||r.cellEncoding!=='html-text-v1'||r.rackId!==f.rackId||r.filename!==`rackclick-rack-${f.rackId}-r${operation.revision}.xls`||r.contentType!=='application/vnd.ms-excel;charset=utf-8'||typeof r.generatedAt!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(r.generatedAt)||!Number.isFinite(Date.parse(r.generatedAt))||new Date(r.generatedAt).toISOString()!==r.generatedAt||!Number.isSafeInteger(r.deviceCount)||r.deviceCount<0||!Number.isSafeInteger(r.connectionCount)||r.connectionCount<0||r.summaryCount!==10||!Number.isSafeInteger(r.rowCount)||r.rowCount!==r.deviceCount+r.connectionCount+10||r.rowCount>10000||!Number.isSafeInteger(r.byteLength)||r.byteLength<1||r.byteLength>4194304||typeof r.sha256!=='string'||!/^[0-9a-f]{64}$/.test(r.sha256)||typeof r.contentBase64!=='string'||r.contentBase64.length>5592408||r.contentBase64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(r.contentBase64))invalid();
 let bytes:Uint8Array;try{const decoded=atob(r.contentBase64);if(btoa(decoded)!==r.contentBase64)invalid();bytes=Uint8Array.from(decoded,c=>c.charCodeAt(0));}catch{invalid();}
 if(bytes!.length!==r.byteLength||bytes![0]===239&&bytes![1]===187&&bytes![2]===191)invalid();
 const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');if(sha!==r.sha256)invalid();
 let html:string;try{html=new TextDecoder('utf-8',{fatal:true}).decode(bytes!);}catch{invalid();}
 const parsed=parseRc9ExcelHtml(html!,operation,r);return {result:data,bytes:bytes!,parsed};
}
function current(api:RackClickApi,operation:Rc9ExcelRequest,signal?:AbortSignal){if(signal?.aborted||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed');}
export async function sendRc9Excel(api:RackClickApi,operation:Rc9ExcelRequest,signal?:AbortSignal){
 current(api,operation,signal);if(!api.csrf)throw new ApiError(401,'authentication_required');
 const {data}=await api.request('/customers/'+operation.customerId+'/reports/xls-html',{method:'POST',signal,headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':operation.actorId,'If-Match':'"'+operation.revision+'"','Idempotency-Key':operation.requestId},body:operation.body});
 current(api,operation,signal);const validated=await validateRc9ExcelResult(data,operation);current(api,operation,signal);return validated;
}
export async function recoverRc9Excel(api:RackClickApi,operation:Rc9ExcelRequest,signal?:AbortSignal){
 current(api,operation,signal);const {data}=await api.request('/customers/'+operation.customerId+'/reports/xls-html/operations/'+operation.requestId,{signal});current(api,operation,signal);
 if(!keys(data,'state,customerId,requestId,operation')||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!['committed','notRecorded'].includes(data.state))invalid();
 if(data.state==='notRecorded'){if(data.operation!==null)invalid();return null;}const validated=await validateRc9ExcelResult(data.operation,operation);current(api,operation,signal);return validated;
}
export function downloadRc9Excel(validated:Awaited<ReturnType<typeof validateRc9ExcelResult>>,api:RackClickApi,session:Session,customerId:string,operation:Rc9ExcelRequest){
 current(api,operation);if(!rc9ExcelAllowed(api,session,customerId)||validated.result.customerId!==customerId||operation.customerId!==customerId||validated.result.requestId!==operation.requestId||validated.result.revision!==operation.revision||validated.result.report.rackId!==JSON.parse(operation.body).rackId)throw new ApiError(403,'forbidden');
 const url=URL.createObjectURL(new Blob([validated.bytes],{type:'application/vnd.ms-excel;charset=utf-8'})),link=document.createElement('a');
 try{link.href=url;link.download=validated.result.report.filename;document.body.appendChild(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
}
