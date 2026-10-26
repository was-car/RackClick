import {ApiError,allows,type RackClickApi,type Session} from './api.ts';
export type PrintableFilter={reportKind:'rack'|'client'|'rackLabels';language:'en'|'de'|'es';rackIds:string[]};
export type PrintableRequest=Readonly<{actorId:string;customerId:string;revision:number;requestId:string;body:string}>;
export const printableTemplate='rackclick-print-v1';
export const printableCsp="default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'none'; font-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'";
const uuid=(x:any)=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const invalid=():never=>{throw new ApiError(200,'response_invalid',true)};
export function printableAllowed(api:RackClickApi,session:Session,customerId:string){return api.actorId===session.user.id&&allows(session,'inventory.read',customerId)&&allows(session,'reports.export',customerId)}
export function preparePrintable(api:RackClickApi,actorId:string,customerId:string,revision:number,filter:PrintableFilter):PrintableRequest{
 if(api.actorId!==actorId||!uuid(actorId))throw new ApiError(409,'actor_changed');
 if(!uuid(customerId)||!Number.isSafeInteger(revision)||revision<1||!keys(filter,'reportKind,language,rackIds')||!['rack','client','rackLabels'].includes(filter.reportKind)||!['en','de','es'].includes(filter.language)||!Array.isArray(filter.rackIds)||filter.rackIds.some(id=>!uuid(id)))throw new ApiError(422,'request_invalid');
 const rackIds=filter.rackIds.map(id=>id.toLowerCase()).sort();
 if(new Set(rackIds).size!==rackIds.length||filter.reportKind==='rack'&&rackIds.length!==1||filter.reportKind==='client'&&rackIds.length!==0||filter.reportKind==='rackLabels'&&(rackIds.length<1||rackIds.length>64))throw new ApiError(422,'request_invalid');
 return Object.freeze({actorId,customerId,revision,requestId:crypto.randomUUID(),body:JSON.stringify({reportKind:filter.reportKind,language:filter.language,rackIds})});
}
// Validate the fixed passive template without inserting server HTML into the application DOM.
function validateHtml(html:string,filter:PrintableFilter,rowCount:number){
 if(!/^<!doctype html>/i.test(html)||!html.endsWith('</html>'))invalid();
 const permitted=new Set('html head meta title style body main header footer section article h1 h2 h3 h4 p div span b strong small table thead tbody tfoot tr th td caption colgroup col br hr ul ol li dl dt dd'.split(' '));
 let rows=0,language=false,template=false,kind=false,csp=false;for(const match of html.matchAll(/<\/?([a-z][a-z0-9]*)\b([^<>]*)>/gi)){
  const tag=match[1].toLowerCase(),attributes=match[2];if(!permitted.has(tag))invalid();
  const attr=(name:string)=>{const found=attributes.match(new RegExp('(?:^|\\s)'+name+'\\s*=\\s*(?:"([^"]*)"|\'([^\']*)\')','i'));return (found?.[1]??found?.[2])?.replace(/&(?:amp|quot|apos|#39|#x27);/gi,entity=>({'&amp;':'&','&quot;':'"','&apos;':"'",'&#39;':"'",'&#x27;':"'"}[entity.toLowerCase()]!))};
  if(tag==='html'&&attr('lang')===filter.language)language=true;
  if(tag==='body'&&attr('data-report-kind')===filter.reportKind)kind=true;
  if(tag==='meta'&&attr('name')==='rackclick-template'&&attr('content')===printableTemplate)template=true;
  if(tag==='meta'&&attr('http-equiv')?.toLowerCase()==='content-security-policy'&&attr('content')===printableCsp)csp=true;
  // Attribute values remain quoted in the server template; inspect names, not note text.
  const names=attributes.replace(/"[^"]*"|'[^']*'/g,'');
  if(/(?:^|\s)(?:on[a-z]+|src|href|srcdoc|action|formaction)\s*=/i.test(names)||tag==='meta'&&/http-equiv\s*=\s*["']?refresh/i.test(attributes))invalid();
  if(/(?:^|\s)data-report-row(?:\s*=|\s|$)/.test(attributes)&&!match[0].startsWith('</'))rows++;
 }
 for(const style of html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi))if(/@import|url\s*\(|expression\s*\(/i.test(style[1]))invalid();
 if(!language||!template||!kind||!csp||rows!==rowCount)invalid();
}
export async function validatePrintableResult(data:any,operation:PrintableRequest){
 const f:PrintableFilter=JSON.parse(operation.body),r=data?.report;
 if(!keys(data,'kind,customerId,revision,requestId,operationId,report')||data.kind!=='report'||data.customerId!==operation.customerId||data.revision!==operation.revision||data.requestId!==operation.requestId||!uuid(data.operationId)||!keys(r,'reportKind,language,rackIds,filename,contentType,encoding,templateVersion,rowCount,byteLength,sha256,contentBase64')||r.reportKind!==f.reportKind||r.language!==f.language||JSON.stringify(r.rackIds)!==JSON.stringify(f.rackIds)||r.filename!==`rackclick-${f.reportKind}-${operation.customerId}-r${operation.revision}-${f.language}.html`||r.contentType!=='text/html; charset=utf-8'||r.encoding!=='utf-8'||r.templateVersion!==printableTemplate||!Number.isSafeInteger(r.rowCount)||r.rowCount<0||r.rowCount>10000||!Number.isSafeInteger(r.byteLength)||r.byteLength<1||r.byteLength>4194304||typeof r.sha256!=='string'||!/^[0-9a-f]{64}$/.test(r.sha256)||typeof r.contentBase64!=='string'||r.contentBase64.length>5592408||r.contentBase64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(r.contentBase64))invalid();
 let bytes:Uint8Array;try{const decoded=atob(r.contentBase64);if(btoa(decoded)!==r.contentBase64)invalid();bytes=Uint8Array.from(decoded,c=>c.charCodeAt(0));}catch{invalid();}
 if(bytes!.length!==r.byteLength||bytes![0]===239&&bytes![1]===187&&bytes![2]===191)invalid();
 const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');if(sha!==r.sha256)invalid();
 let html:string;try{html=new TextDecoder('utf-8',{fatal:true}).decode(bytes!);}catch{invalid();}
 validateHtml(html!,f,r.rowCount);return {result:data,bytes:bytes!};
}
function current(api:RackClickApi,operation:PrintableRequest,signal?:AbortSignal){if(signal?.aborted||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed');}
export async function sendPrintable(api:RackClickApi,operation:PrintableRequest,signal?:AbortSignal){
 current(api,operation,signal);if(!api.csrf)throw new ApiError(401,'authentication_required');
 const {data}=await api.request('/customers/'+operation.customerId+'/reports/printable',{method:'POST',signal,headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':operation.actorId,'If-Match':'"'+operation.revision+'"','Idempotency-Key':operation.requestId},body:operation.body});
 current(api,operation,signal);const validated=await validatePrintableResult(data,operation);current(api,operation,signal);return validated;
}
export async function recoverPrintable(api:RackClickApi,operation:PrintableRequest,signal?:AbortSignal){
 current(api,operation,signal);const {data}=await api.request('/customers/'+operation.customerId+'/reports/printable/operations/'+operation.requestId,{signal});current(api,operation,signal);
 if(!keys(data,'state,customerId,requestId,operation')||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!['committed','notRecorded'].includes(data.state))invalid();
 if(data.state==='notRecorded'){if(data.operation!==null)invalid();return null;}
 const validated=await validatePrintableResult(data.operation,operation);current(api,operation,signal);return validated;
}
export function downloadPrintable(validated:Awaited<ReturnType<typeof validatePrintableResult>>,api:RackClickApi,session:Session,customerId:string){
 if(!printableAllowed(api,session,customerId)||validated.result.customerId!==customerId)throw new ApiError(403,'forbidden');
 const url=URL.createObjectURL(new Blob([validated.bytes],{type:'text/html;charset=utf-8'})),link=document.createElement('a');
 try{link.href=url;link.download=validated.result.report.filename;document.body.appendChild(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
}
