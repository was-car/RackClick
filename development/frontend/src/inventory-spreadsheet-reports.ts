import {ApiError,type RackClickApi,type Session} from './api.ts';
import {reportAllowed,reportUuid,portReportColumns,connectionReportColumns,reportColumns,validReportColumns,type ReportRequest} from './inventory-reports.ts';

export const spreadsheetMime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const maximum=4194304;
const parts=['[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels','xl/worksheets/sheet1.xml'];
const spreadsheetNs='http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const packageRelNs='http://schemas.openxmlformats.org/package/2006/relationships';
const officeRelNs='http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const contentNs='http://schemas.openxmlformats.org/package/2006/content-types';
const xmlNs='http://www.w3.org/XML/1998/namespace';
const keys=(x:any,k:string)=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===k.split(',').sort().join();
const invalid=():never=>{throw new ApiError(200,'response_invalid',true)};

const crcTable=Array.from({length:256},(_,i)=>{for(let bit=0;bit<8;bit++)i=(i&1)?0xedb88320^(i>>>1):i>>>1;return i>>>0;});
function crc32(bytes:Uint8Array){let crc=0xffffffff;for(const b of bytes)crc=crcTable[(crc^b)&255]^(crc>>>8);return (crc^0xffffffff)>>>0;}

/** Only the fixed, uncompressed, five-part package emitted by this API is accepted. */
function unpack(bytes:Uint8Array){
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),end=bytes.length-22;
 const u16=(p:number)=>p>=0&&p+2<=bytes.length?view.getUint16(p,true):invalid();
 const u32=(p:number)=>p>=0&&p+4<=bytes.length?view.getUint32(p,true):invalid();
 if(end<0||u32(end)!==0x06054b50||u16(end+4)!==0||u16(end+6)!==0||u16(end+8)!==5||u16(end+10)!==5||u16(end+20)!==0)invalid();
 const start=u32(end+16),size=u32(end+12);if(start+size!==end)invalid();
 let central=start,local=0,total=0;const output:string[]=[];
 const decoder=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true});
 for(const name of parts){
  if(central+46>end||u32(central)!==0x02014b50)invalid();
  const needed=u16(central+6),flags=u16(central+8),method=u16(central+10),crc=u32(central+16),length=u32(central+24),nameLength=u16(central+28);
  if(![10,20].includes(needed)||(flags!==0&&flags!==0x800)||method!==0||u16(central+12)!==0||u16(central+14)!==0x21||u32(central+20)!==length||u16(central+30)!==0||u16(central+32)!==0||u16(central+34)!==0||u32(central+42)!==local||central+46+nameLength>end)invalid();
  const expected=new TextEncoder().encode(name),actual=bytes.subarray(central+46,central+46+nameLength);
  if(nameLength!==expected.length||actual.some((v,i)=>v!==expected[i]))invalid();
  if(local+30+nameLength>start||u32(local)!==0x04034b50||u16(local+4)!==needed||u16(local+6)!==flags||u16(local+8)!==0||u16(local+10)!==0||u16(local+12)!==0x21||u32(local+14)!==crc||u32(local+18)!==length||u32(local+22)!==length||u16(local+26)!==nameLength||u16(local+28)!==0)invalid();
  if(bytes.subarray(local+30,local+30+nameLength).some((v,i)=>v!==expected[i]))invalid();
  const dataStart=local+30+nameLength,dataEnd=dataStart+length;total+=length;
  if(dataEnd>start||total>maximum)invalid();
  const content=bytes.subarray(dataStart,dataEnd);if(crc32(content)!==crc)invalid();
  try{output.push(decoder.decode(content));}catch{invalid();}
  local=dataEnd;central+=46+nameLength;
 }
 if(local!==start||central!==end)invalid();return output;
}

type Element={name:string;ns:string;attrs:Record<string,string>;children:(Element|string)[]};
function entityText(text:string){
 let out='',start=0;
 for(let i=0;i<text.length;i++){
  const n=text.charCodeAt(i);if(n===0x26){out+=text.slice(start,i);const end=text.indexOf(';',i+1);if(end<0||end-i>12)invalid();const token=text.slice(i+1,end),known:{[k:string]:string}={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'"};let value=known[token];
   if(value===undefined){if(!/^#(?:[0-9]+|x[0-9a-fA-F]+)$/.test(token))invalid();const cp=token[1]==='x'?parseInt(token.slice(2),16):parseInt(token.slice(1),10);if(!xmlChar(cp))invalid();value=String.fromCodePoint(cp);}
   out+=value;i=end;start=end+1;
  }else if(n>=0xd800&&n<=0xdbff){const low=text.charCodeAt(++i);if(!(low>=0xdc00&&low<=0xdfff))invalid();}else if(n===0x3c||!xmlChar(n))invalid();
 }
 return out+text.slice(start);
}
function xmlChar(cp:number){return cp===9||cp===10||cp===13||cp>=0x20&&cp<=0xd7ff||cp>=0xe000&&cp<=0xfffd||cp>=0x10000&&cp<=0x10ffff;}

/** Small namespace-aware XML subset; declarations/entities/DTD cannot fetch resources. */
function parseXml(source:string):Element{
 if(source.charCodeAt(0)===0xfeff)source=source.slice(1);
 if(source.startsWith('<?xml')){const decl=/^<\?xml version="1\.0" encoding="(?:utf-8|UTF-8)"(?: standalone="yes")?\?>/.exec(source);if(!decl)invalid();source=source.slice(decl[0].length);}
 // XML line-end normalization must precede entity processing. CR values use numeric references or SpreadsheetML escapes.
 source=source.replace(/\r\n?/g,'\n');
 let offset=0,root:Element|null=null;const stack:{element:Element;namespaces:Record<string,string>;qname:string}[]=[];
 const namePattern=/^[A-Za-z_][A-Za-z0-9_.:-]*/;
 const white=()=>{while(/[ \t\n]/.test(source[offset]||'\0'))offset++;};
 while(offset<source.length){
  if(source[offset]!=='<'){const end=source.indexOf('<',offset),raw=source.slice(offset,end<0?source.length:end);if(raw.includes(']]>'))invalid();const text=entityText(raw);if(stack.length)stack.at(-1)!.element.children.push(text);else if(/[^ \t\n\r]/.test(raw))invalid();offset=end<0?source.length:end;continue;}
  offset++;
  if(source[offset]==='/'){
   offset++;const match=namePattern.exec(source.slice(offset));if(!match)invalid();offset+=match![0].length;white();if(source[offset++]!=='>'||!stack.length||stack.at(-1)!.qname!==match![0])invalid();stack.pop();continue;
  }
  const match=namePattern.exec(source.slice(offset));if(!match)invalid();const qname=match![0];offset+=qname.length;const attrs:Record<string,string>=Object.create(null);
  let closed=false;
  while(offset<source.length){const before=offset;white();if(source.startsWith('/>',offset)){offset+=2;closed=true;break;}if(source[offset]==='>'){offset++;break;}if(before===offset)invalid();const attr=namePattern.exec(source.slice(offset));if(!attr||Object.hasOwn(attrs,attr![0]))invalid();offset+=attr![0].length;white();if(source[offset++]!=='=')invalid();white();const quote=source[offset++];if(quote!=='"'&&quote!=="'")invalid();const end=source.indexOf(quote,offset);if(end<0)invalid();attrs[attr![0]]=entityText(source.slice(offset,end).replace(/[\t\n]/g,' '));offset=end+1;}
  if(offset>source.length||source[offset-1]!=='>')invalid();
  const namespaces={...(stack.at(-1)?.namespaces||{xml:xmlNs})};
  for(const [key,value] of Object.entries(attrs))if(key==='xmlns'||key.startsWith('xmlns:')){const prefix=key==='xmlns'?'':key.slice(6);if(!['', 'r', 'xml'].includes(prefix)||![spreadsheetNs,packageRelNs,officeRelNs,contentNs,xmlNs].includes(value)||prefix==='xml'&&value!==xmlNs)invalid();namespaces[prefix]=value;}
  function expanded(q:string,attribute=false){const bits=q.split(':');if(bits.length>2||bits.some(b=>!b))invalid();const prefix=bits.length===2?bits[0]:'';const ns=prefix?namespaces[prefix]:attribute?'':namespaces[''];if(ns===undefined)invalid();return {name:bits.at(-1)!,ns};}
  const name=expanded(qname),element:Element={...name,attrs:Object.create(null),children:[]};
  for(const [key,value] of Object.entries(attrs)){if(key==='xmlns'||key.startsWith('xmlns:'))continue;const resolved=expanded(key,true),canonical=resolved.ns?`{${resolved.ns}}${resolved.name}`:resolved.name;if(Object.hasOwn(element.attrs,canonical))invalid();element.attrs[canonical]=value;}
  if(stack.length)stack.at(-1)!.element.children.push(element);else if(root)invalid();else root=element;
  if(!closed){if(stack.length>=8)invalid();stack.push({element,namespaces,qname});}
 }
 if(stack.length||!root)invalid();return root!;
}
function expectElement(element:Element,name:string,ns:string,attrs:Record<string,string>={}){
 if(!element||element.name!==name||element.ns!==ns||JSON.stringify(Object.keys(element.attrs).sort())!==JSON.stringify(Object.keys(attrs).sort())||Object.keys(attrs).some(k=>element.attrs[k]!==attrs[k]))invalid();
 return element;
}
function children(element:Element){const result:Element[]=[];for(const child of element.children){if(typeof child==='string'){if(/[^ \t\n\r]/.test(child))invalid();}else result.push(child);}return result;}
function empty(element:Element){if(children(element).length)invalid();}
function columnName(index:number){let result='';for(index++;index>0;index=Math.floor((index-1)/26))result=String.fromCharCode(65+(index-1)%26)+result;return result;}
function decodeCell(text:string){return text.replace(/_x([0-9a-fA-F]{4})_/g,(_,code)=>String.fromCharCode(parseInt(code,16)));}

function parseWorkbook(partsXml:string[],kind:string,rowCount:number){
 const roots=partsXml.map(parseXml),types=expectElement(roots[0],'Types',contentNs),typeEntries=children(types);
 const expectedTypes=[['Default',{Extension:'rels',ContentType:'application/vnd.openxmlformats-package.relationships+xml'}],['Default',{Extension:'xml',ContentType:'application/xml'}],['Override',{PartName:'/xl/workbook.xml',ContentType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'}],['Override',{PartName:'/xl/worksheets/sheet1.xml',ContentType:'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'}]] as const;
 if(typeEntries.length!==expectedTypes.length)invalid();for(let i=0;i<expectedTypes.length;i++){expectElement(typeEntries[i],expectedTypes[i][0],contentNs,expectedTypes[i][1]);empty(typeEntries[i]);}
 function relationship(root:Element,type:string,target:string){expectElement(root,'Relationships',packageRelNs);const entries=children(root);if(entries.length!==1)invalid();expectElement(entries[0],'Relationship',packageRelNs,{Id:'rId1',Type:officeRelNs+'/'+type,Target:target});empty(entries[0]);}
 relationship(roots[1],'officeDocument','xl/workbook.xml');relationship(roots[3],'worksheet','worksheets/sheet1.xml');
 const workbook=expectElement(roots[2],'workbook',spreadsheetNs),sheets=children(workbook);if(sheets.length!==1)invalid();expectElement(sheets[0],'sheets',spreadsheetNs);const sheet=children(sheets[0]);if(sheet.length!==1)invalid();expectElement(sheet[0],'sheet',spreadsheetNs,{name:kind==='ports'?'Ports':'Connections',sheetId:'1',[`{${officeRelNs}}id`]:'rId1'});empty(sheet[0]);
 const worksheet=expectElement(roots[4],'worksheet',spreadsheetNs),sheetData=children(worksheet);if(sheetData.length!==1)invalid();expectElement(sheetData[0],'sheetData',spreadsheetNs);
 const rowElements=children(sheetData[0]);if(rowElements.length!==rowCount+1)invalid();
 const legacy=reportColumns(kind),expanded=reportColumns(kind,true),firstCount=children(rowElements[0]).length;
 const columns=firstCount===legacy.length?legacy:firstCount===expanded.length?expanded:invalid();
 const rows:string[][]=[];
 for(let ri=0;ri<rowElements.length;ri++){
  const row=rowElements[ri];expectElement(row,'row',spreadsheetNs,{r:String(ri+1)});const cells=children(row);if(cells.length!==columns.length)invalid();const values:string[]=[];
  for(let ci=0;ci<cells.length;ci++){
   const cell=expectElement(cells[ci],'c',spreadsheetNs,{r:columnName(ci)+(ri+1),t:'inlineStr'}),inline=children(cell);if(inline.length!==1)invalid();expectElement(inline[0],'is',spreadsheetNs);const text=children(inline[0]);if(text.length!==1)invalid();expectElement(text[0],'t',spreadsheetNs,{[`{${xmlNs}}space`]:'preserve'});if(text[0].children.some(c=>typeof c!=='string'))invalid();const value=decodeCell(text[0].children.join(''));if(value.length>32767)invalid();
   // SpreadsheetML escapes must not manufacture unpaired UTF-16 surrogates.
   for(let i=0;i<value.length;i++){const unit=value.charCodeAt(i);if(unit>=0xd800&&unit<=0xdbff){const low=value.charCodeAt(++i);if(!(low>=0xdc00&&low<=0xdfff))invalid();}else if(unit>=0xdc00&&unit<=0xdfff)invalid();}
   values.push(value);
  }
  rows.push(values);
 }
 if(!validReportColumns(kind,rows))invalid();return rows;
}

export async function validateSpreadsheetResult(data:any,operation:ReportRequest){
 const f=JSON.parse(operation.body),r=data?.report;
 if(!keys(data,'kind,customerId,revision,requestId,operationId,report')||data.kind!=='spreadsheetReport'||data.customerId!==operation.customerId||data.revision!==operation.revision||data.requestId!==operation.requestId||!reportUuid(data.operationId)||!keys(r,'reportKind,query,status,family,rackId,filename,contentType,format,cellEncoding,rowCount,byteLength,sha256,contentBase64')||!Object.keys(f).every(k=>r[k]===f[k])||r.filename!==`rackclick-${f.reportKind}-${operation.customerId}-r${operation.revision}.xlsx`||r.contentType!==spreadsheetMime||r.format!=='xlsx'||r.cellEncoding!=='inline-string-v1'||!Number.isSafeInteger(r.rowCount)||r.rowCount<0||r.rowCount>10000||!Number.isSafeInteger(r.byteLength)||r.byteLength<22||r.byteLength>maximum||typeof r.sha256!=='string'||!/^[0-9a-f]{64}$/.test(r.sha256)||typeof r.contentBase64!=='string'||r.contentBase64.length>5592408||r.contentBase64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(r.contentBase64))invalid();
 let bytes:Uint8Array;try{const decoded=atob(r.contentBase64);if(btoa(decoded)!==r.contentBase64)invalid();bytes=Uint8Array.from(decoded,c=>c.charCodeAt(0));}catch{invalid();}
 if(bytes!.length!==r.byteLength)invalid();const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes!)),n=>n.toString(16).padStart(2,'0')).join('');if(sha!==r.sha256)invalid();
 const rows=parseWorkbook(unpack(bytes!),f.reportKind,r.rowCount),ids=new Set();
 for(const row of rows.slice(1)){if(row[0]!==operation.customerId||row[1]!==String(operation.revision)||!reportUuid(row[2])||ids.has(row[2]))invalid();ids.add(row[2]);}
 return {result:data,bytes:bytes!,rows};
}
function current(api:RackClickApi,operation:ReportRequest,signal?:AbortSignal){if(signal?.aborted||api.actorId!==operation.actorId)throw new ApiError(409,'actor_changed');}
export async function sendSpreadsheet(api:RackClickApi,operation:ReportRequest,signal?:AbortSignal){
 current(api,operation,signal);if(!api.csrf)throw new ApiError(401,'authentication_required');
 const {data}=await api.request('/customers/'+operation.customerId+'/reports/xlsx',{method:'POST',signal,headers:{'Content-Type':'application/json','X-RackClick-CSRF':api.csrf,'X-RackClick-Actor':operation.actorId,'If-Match':'"'+operation.revision+'"','Idempotency-Key':operation.requestId},body:operation.body});
 current(api,operation,signal);const validated=await validateSpreadsheetResult(data,operation);current(api,operation,signal);return validated;
}
export async function recoverSpreadsheet(api:RackClickApi,operation:ReportRequest,signal?:AbortSignal){
 current(api,operation,signal);const {data}=await api.request('/customers/'+operation.customerId+'/reports/xlsx/operations/'+operation.requestId,{signal});current(api,operation,signal);
 if(!keys(data,'state,customerId,requestId,operation')||data.customerId!==operation.customerId||data.requestId!==operation.requestId||!['committed','notRecorded'].includes(data.state))invalid();
 if(data.state==='notRecorded'){if(data.operation!==null)invalid();return null;}
 const validated=await validateSpreadsheetResult(data.operation,operation);current(api,operation,signal);return validated;
}
export function downloadSpreadsheet(validated:Awaited<ReturnType<typeof validateSpreadsheetResult>>,api:RackClickApi,session:Session,customerId:string){
 if(!reportAllowed(api,session,customerId)||validated.result.customerId!==customerId)throw new ApiError(403,'forbidden');
 const url=URL.createObjectURL(new Blob([validated.bytes],{type:spreadsheetMime})),link=document.createElement('a');
 try{link.href=url;link.download=validated.result.report.filename;document.body.appendChild(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
}
