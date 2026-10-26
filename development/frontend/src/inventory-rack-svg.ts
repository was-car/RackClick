import {ApiError,allows,type RackClickApi,type Session} from './api.ts';
export type RackSvgFilter={rackId:string;face:'front'|'rear';language:'en'|'de'|'es'};
export type RackSvgRequest=Readonly<{actorId:string;customerId:string;revision:number;requestId:string;body:string}>;
export const rackSvgTemplate='rackclick-rack-svg-v1';
const uuid=(x:any)=>typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(x)&&x!=='00000000-0000-0000-0000-000000000000';
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const invalid=():never=>{throw new ApiError(200,'response_invalid',true)};
export function rackSvgAllowed(api:RackClickApi,session:Session,customerId:string){return api.actorId===session.user.id&&allows(session,'inventory.read',customerId)&&allows(session,'reports.export',customerId)}
export function prepareRackSvg(api:RackClickApi,actorId:string,customerId:string,revision:number,filter:RackSvgFilter):RackSvgRequest{
 if(api.actorId!==actorId||!uuid(actorId))throw new ApiError(409,'actor_changed');
 if(!uuid(customerId)||!Number.isSafeInteger(revision)||revision<1||!keys(filter,'rackId,face,language')||!uuid(filter.rackId)||!['front','rear'].includes(filter.face)||!['en','de','es'].includes(filter.language))throw new ApiError(422,'request_invalid');
 return Object.freeze({actorId,customerId,revision,requestId:crypto.randomUUID(),body:JSON.stringify({rackId:filter.rackId.toLowerCase(),face:filter.face,language:filter.language})});
}
const tags=new Set(['svg','title','desc','g','rect','circle','path','text']);
const rootNames='xmlns,lang,data-template,data-customer-id,data-rack-id,data-source-revision,data-face,viewBox,role,aria-label';
const attributes=new Set((rootNames+',x,y,x1,y1,x2,y2,cx,cy,r,rx,width,height,fill,stroke,stroke-width,stroke-dasharray,d,transform,font-family,font-size,font-weight,text-anchor,opacity,data-report-row,data-id,data-visible,data-device-id,data-group-id,data-from-port-id,data-to-port-id').split(','));
const numeric=new Set('x y x1 y1 x2 y2 cx cy r rx width height stroke-width font-size opacity'.split(' '));
const number='[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?';
const scalar=new RegExp('^'+number+'$');
const coordinates=new RegExp('^'+number+'(?:[ ,]+'+number+')*$');
const finiteCoordinate=(value:string)=>Number.isFinite(Number(value))&&Math.abs(Number(value))<=10000000;
function finiteTokens(value:string){for(const token of value.matchAll(new RegExp(number,'g')))if(!finiteCoordinate(token[0]))invalid()}
function xmlScalar(n:number){return n===9||n===10||n===13||n>=32&&n<=0xd7ff||n>=0xe000&&n<=0xfffd||n>=0x10000&&n<=0x10ffff}
function xmlText(text:string){
 if(text.includes(']]>'))invalid();for(const ch of text)if(!xmlScalar(ch.codePointAt(0)!))invalid();
 const decoded=text.replace(/&(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);/g,entity=>{
  if(entity[1]==='#'){const n=entity[2]==='x'?parseInt(entity.slice(3,-1),16):Number(entity.slice(2,-1));if(!xmlScalar(n))invalid();return String.fromCodePoint(n)}
  return ({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&apos;':"'"} as Record<string,string>)[entity];
 });
 if(text.replace(/&(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);/g,'').includes('&'))invalid();return decoded;
}
function validateAttribute(name:string,value:string){
 if(!attributes.has(name))invalid();
 if(numeric.has(name)&&(!scalar.test(value)||!finiteCoordinate(value)))invalid();
 if(['r','rx','width','height','stroke-width','font-size'].includes(name)&&Number(value)<0||name==='opacity'&&(Number(value)<0||Number(value)>1))invalid();
 if(['fill','stroke'].includes(name)&&!/^none$|^#[0-9a-fA-F]{6}$/.test(value))invalid();
 if(name==='stroke-dasharray'){if(!coordinates.test(value)||value.length>100)invalid();finiteTokens(value);if(value.split(/[ ,]+/).some(n=>Number(n)<0))invalid()}
 if(name==='d'){if(!/^[MmLlHhVvCcSsQqTtAaZz0-9eE+.,\s-]+$/.test(value)||value.length>10000)invalid();finiteTokens(value)}
 if(name==='transform'){
  let remainder=value;for(const m of value.matchAll(/(?:translate|scale)\(([^()]*)\)/g)){if(!coordinates.test(m[1])||m[1].split(/[ ,]+/).length>2)invalid();finiteTokens(m[1]);remainder=remainder.replace(m[0],'')}
  if(remainder.trim()||!value.trim())invalid();
 }
 if(name==='font-family'&&value!=='Arial,sans-serif')invalid();
 if(name==='font-weight'&&!/^(?:normal|bold|[1-9]00)$/.test(value))invalid();
 if(name==='text-anchor'&&!['start','middle','end'].includes(value))invalid();
 if(name==='data-report-row'&&!['rack','device','group','port','connection'].includes(value))invalid();
 if(['data-id','data-device-id','data-group-id','data-from-port-id','data-to-port-id'].includes(name)&&!uuid(value))invalid();
 if(name==='data-visible'&&!['true','false'].includes(value))invalid();
}
// This parses only the closed passive server grammar. It does not insert SVG in the app DOM.
export function validateRackSvgXml(xml:string,operation:RackSvgRequest,rowCount:number){
 const f:RackSvgFilter=JSON.parse(operation.body),stack:string[]=[],rows=new Set<string>();let offset=0,root=false,closed=false,rackRows=0;
 if(!xml.startsWith('<svg ')||!xml.endsWith('</svg>')||/<[!?]/.test(xml))invalid();
 const tokens=/<(\/?)([A-Za-z][A-Za-z0-9]*)([^<>]*)>/g;let match:RegExpExecArray|null;
 while((match=tokens.exec(xml))){
  const between=xml.slice(offset,match.index);if(between.includes('<')||!stack.length&&between.trim())invalid();xmlText(between);offset=tokens.lastIndex;
  const [,closing,tag,tail]=match;if(!tags.has(tag)||closed)invalid();
  if(closing){if(tail.trim()||stack.pop()!==tag)invalid();if(!stack.length)closed=true;continue}
  const self=tail.trimEnd().endsWith('/'),source=self?tail.trimEnd().slice(0,-1):tail,attrs:Record<string,string>={};let remaining=source;
  while(remaining.trim()){
   const a=remaining.match(/^\s+([a-zA-Z][a-zA-Z0-9:-]*)="([^"<>]*)"/);if(!a||Object.hasOwn(attrs,a[1]))invalid();const name=a![1],value=xmlText(a![2]);validateAttribute(name,value);attrs[name]=value;remaining=remaining.slice(a![0].length);
  }
  if(!root){
   if(tag!=='svg'||self||!keys(attrs,rootNames)||attrs.xmlns!=='http://www.w3.org/2000/svg'||attrs.lang!==f.language||attrs['data-template']!==rackSvgTemplate||attrs['data-customer-id']!==operation.customerId||attrs['data-rack-id']!==f.rackId||attrs['data-source-revision']!==String(operation.revision)||attrs['data-face']!==f.face||attrs.role!=='img')invalid();
   const box=attrs.viewBox.split(/\s+/);if(box.length!==4||box[0]!=='0'||box[1]!=='0'||box[2]!=='960'||!scalar.test(box[3])||Number(box[3])<250||Number(box[3])>999964)invalid();root=true;
  }else if(tag==='svg'||Object.keys(attrs).some(n=>rootNames.split(',').includes(n)))invalid();
  if(attrs['data-report-row']){const type=attrs['data-report-row'],id=attrs['data-id'],identity=type+':'+id;if(!uuid(id)||rows.has(identity))invalid();rows.add(identity);if(type==='rack'){if(id!==f.rackId)invalid();rackRows++}}
  if(!self)stack.push(tag);
 }
 if(offset!==xml.length||!root||!closed||stack.length||rows.size!==rowCount||rackRows!==1)invalid();
 if(typeof DOMParser!=='undefined'){const parsed=new DOMParser().parseFromString(xml,'image/svg+xml');if(parsed.documentElement.localName!=='svg'||parsed.documentElement.namespaceURI!=='http://www.w3.org/2000/svg'||parsed.getElementsByTagName('parsererror').length)invalid()}
 return {rowCount:rows.size};
}
export async function validateRackSvgResult(data:any,operation:RackSvgRequest){
 const f:RackSvgFilter=JSON.parse(operation.body),r=data?.report;
 if(!keys(data,'kind,customerId,revision,requestId,operationId,report')||data.kind!=='report'||data.customerId!==operation.customerId||data.revision!==operation.revision||data.requestId!==operation.requestId||!uuid(data.operationId)||!keys(r,'reportKind,rackId,face,language,filename,contentType,encoding,templateVersion,rowCount,byteLength,sha256,contentBase64')||r.reportKind!=='rackSvg'||r.rackId!==f.rackId||r.face!==f.face||r.language!==f.language||r.filename!==`rackclick-rackSvg-${operation.customerId}-${f.rackId}-r${operation.revision}-${f.face}-${f.language}.svg`||r.contentType!=='image/svg+xml; charset=utf-8'||r.encoding!=='utf-8'||r.templateVersion!==rackSvgTemplate||!Number.isSafeInteger(r.rowCount)||r.rowCount<1||r.rowCount>10000||!Number.isSafeInteger(r.byteLength)||r.byteLength<1||r.byteLength>4194304||typeof r.sha256!=='string'||!/^[0-9a-f]{64}$/.test(r.sha256)||typeof r.contentBase64!=='string'||r.contentBase64.length>5592408||r.contentBase64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(r.contentBase64))invalid();
 let bytes:Uint8Array;try{const decoded=atob(r.contentBase64);if(btoa(decoded)!==r.contentBase64)invalid();bytes=Uint8Array.from(decoded,c=>c.charCodeAt(0));}catch{invalid()}
 if(bytes!.length!==r.byteLength||bytes![0]===239&&bytes![1]===187&&bytes![2]===191)invalid();
 const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');if(sha!==r.sha256)invalid();
 let xml:string;try{xml=new TextDecoder('utf-8',{fatal:true}).decode(bytes!)}catch{invalid()}
 validateRackSvgXml(xml!,operation,r.rowCount);return {result:data,bytes:bytes!};
}
function current(api:RackClickApi,operation:RackSvgRequest,signal?:AbortSignal){if(signal?.aborted||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed')}
export async function sendRackSvg(api:RackClickApi,operation:RackSvgRequest,signal?:AbortSignal){
 current(api,operation,signal);if(!api.csrf)throw new ApiError(401,'authentication_required');
 const {data,etag}=await api.request('/customers/'+operation.customerId+'/reports/rack-svg',{method:'POST',signal,headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':operation.actorId,'If-Match':'"'+operation.revision+'"','Idempotency-Key':operation.requestId},body:operation.body});
 current(api,operation,signal);if(etag!=='"'+operation.revision+'"')invalid();const validated=await validateRackSvgResult(data,operation);current(api,operation,signal);return validated;
}
export async function recoverRackSvg(api:RackClickApi,operation:RackSvgRequest,signal?:AbortSignal){
 current(api,operation,signal);const {data}=await api.request('/customers/'+operation.customerId+'/reports/rack-svg/operations/'+operation.requestId,{signal});current(api,operation,signal);
 if(!keys(data,'state,customerId,requestId,operation')||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!['committed','notRecorded'].includes(data.state))invalid();
 if(data.state==='notRecorded'){if(data.operation!==null)invalid();return null}
 const validated=await validateRackSvgResult(data.operation,operation);current(api,operation,signal);return validated;
}
export function downloadRackSvg(validated:Awaited<ReturnType<typeof validateRackSvgResult>>,api:RackClickApi,session:Session,customerId:string){
 if(!rackSvgAllowed(api,session,customerId)||validated.result.customerId!==customerId)throw new ApiError(403,'forbidden');
 const url=URL.createObjectURL(new Blob([validated.bytes],{type:'image/svg+xml;charset=utf-8'})),link=document.createElement('a');
 try{link.href=url;link.download=validated.result.report.filename;document.body.appendChild(link);link.click()}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000)}
}
