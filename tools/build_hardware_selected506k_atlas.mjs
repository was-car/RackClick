// Adapt the reviewed Atlas UI; no new renderer, CDN, image, API or dependency.
import {readFile,writeFile,mkdir,copyFile,lstat} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const root=path.resolve(process.argv[2]||'.'),out=path.resolve(process.argv[3]||'.local/selected506k-atlas');
const sha=b=>createHash('sha256').update(b).digest('hex');
try{await lstat(out);throw Error('atlas_output_exists')}catch(e){if(e.code!=='ENOENT')throw e}
const require=createRequire(path.join(root,'development/frontend/package.json')),{build}=require('esbuild');
const raw=await readFile(path.join(root,'development/frontend/src/hardware-selected506k.generated.json'));
const catalogues=JSON.parse(raw),models=catalogues.flatMap(c=>c.profiles.filter(p=>p.visual));
if(models.length!==52||new Set(models.map(p=>p.key)).size!==52||catalogues.length!==2||
 catalogues.find(c=>c.version==='selected506k-20261101-v1')?.profiles.length!==52||
 !catalogues.some(c=>c.version==='mount-support7u-20261101-v1'&&c.profiles.length===1&&c.profiles[0].key==='shelf-7u-deep'&&!c.profiles[0].visual&&c.profiles[0].kind==='shelf'))throw Error('atlas_52_selected_models_required');
const inputEntry=await readFile(path.join(root,'development/frontend/review/hardware-batch50.jsx'));
if(sha(inputEntry)!=='feeada147a3b264c5196b722adedcae5988a47e6d64dc15b4d6d605642b4253e')throw Error('atlas_reference_entry_changed');
let entry=inputEntry.toString('utf8').replaceAll('hardware-batch50.generated.json','hardware-selected506k.generated.json')
 .replaceAll('batch50-20261030-v1','selected506k-20261101-v1').replaceAll('batch50-20261030','selected506k-20261101')
 .replaceAll('rackclick-visual-batch50-20261030-v1','rackclick-visual-selected506k-20261101-v1')
 .replaceAll('RackClick-Revision-Visual-50.json','RackClick-Revision-Visual-506K.json')
 .replaceAll('revisión visual de 50 modelos','revisión visual · selección 506 · grupo K · 52 modelos')
 .replaceAll('+49)%50','+models.length-1)%models.length').replaceAll('+1)%50','+1)%models.length')
 // 100 permitted notes can serialize to six bytes per UTF-16 unit. Eight MiB
 // includes their worst-case JSON escaping and the normal export metadata.
 .replaceAll('f.size>2*1024*1024','f.size>8*1024*1024')
 .replaceAll('La forma de una cara usa una imagen cuya identidad exacta aún no está confirmada.','La forma de una cara usa una referencia cuya identidad exacta aún no está confirmada.')
 .replaceAll("['rj45','sfp','power'].map(type","['rj45','sfp','sfp28','qsfp','sfp56','qsfpdd','power','console','idc'].map(type");
// Extend only this new review entry, never the adopted/historical source.
entry=entry.replace("rackclickPowerRole:g.powerRole||'unspecified'", "rackclickPhysicalConnector:g.physicalConnector||null,rackclickPowerRole:g.powerRole||'unspecified'")
 .replace('<BatchSocket type={p.type}/>', '<BatchSocket type={p.type} physicalConnector={p.rackclickPhysicalConnector}/>')
 .replace('<svg className="demo-wires"', '<button type="button" data-probe-inlet data-vport="probe-power-inlet" onClick={()=>portClick({id:"probe-power-inlet",type:"power",rackclickHardwareGroupKey:"prueba",gn:1,rackclickPowerRole:"inlet"})}>Entrada AC de prueba</button><svg className="demo-wires"');
if(!entry.includes('rackclickPhysicalConnector:g.physicalConnector')||!entry.includes('data-probe-inlet'))throw Error('atlas_family_mapping_missing');
if(!entry.includes("['rj45','sfp','sfp28','qsfp','sfp56','qsfpdd','power','console','idc'].map(type"))throw Error('atlas_connector_probes_missing');
if(entry.includes('batch50-20261030')||entry.includes('hardware-batch50.generated')||entry.includes('%50')||entry.includes('+49)')||entry.includes('f.size>2*1024*1024'))throw Error('atlas_old_batch_reference');
await mkdir(path.join(out,'modelos'),{recursive:true});
const vendor=path.join(root,'development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/vendor');
for(const f of ['react.production.min.js','react-dom.production.min.js'])await copyFile(path.join(vendor,f),path.join(out,f));
await copyFile(path.join(root,'development/frontend/review/hardware-batch50.css'),path.join(out,'atlas.css'));
await build({stdin:{contents:entry,resolveDir:path.join(root,'development/frontend/review'),sourcefile:'hardware-selected506k-review.jsx',loader:'jsx'},bundle:true,format:'iife',target:'es2020',outfile:path.join(out,'atlas.js'),minify:false,legalComments:'inline'});
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function html(model,base){return '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(model?model.identity.manufacturer+' '+model.identity.model:'RackClick · selección 506 · grupo K · 52 modelos')+'</title><link rel="stylesheet" href="'+base+'atlas.css"><body data-base="'+base+'" data-model="'+escape(model?.key||'')+'"><div id="root"></div><script src="'+base+'react.production.min.js"></script><script src="'+base+'react-dom.production.min.js"></script><script src="'+base+'atlas.js"></script></body></html>\n'}
await writeFile(path.join(out,'INDICE.html'),html(null,''));
for(const m of models){if(!/^[a-z0-9-]+$/.test(m.key))throw Error('atlas_model_key_invalid');await writeFile(path.join(out,'modelos',m.key+'.html'),html(m,'../'))}
const files=['INDICE.html','atlas.js','atlas.css','react.production.min.js','react-dom.production.min.js',...models.map(m=>'modelos/'+m.key+'.html')],hashes={};
for(const f of files)hashes[f]=sha(await readFile(path.join(out,f)));
await writeFile(path.join(out,'PAQUETE.json'),JSON.stringify({schemaVersion:1,kind:'local_visual_review_not_installer',selectionGroup:'K',revision:'selected506k-20261101-v1',models:52,catalogSha256:sha(raw),reviewSourceSha256:sha(inputEntry),files:hashes},null,2)+'\n');
console.log(JSON.stringify({result:'built',selectionGroup:'K',output:out,models:52,individualHtml:52,photosEmbedded:false,apiConnected:false}));
