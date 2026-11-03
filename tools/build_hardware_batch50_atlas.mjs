import {readFile,writeFile,mkdir,copyFile,lstat} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const root=path.resolve(process.argv[2]||'.'),out=path.resolve(process.argv[3]||'.local/batch50-atlas');
try{await lstat(out);throw Error('atlas_output_exists')}catch(e){if(e.code!=='ENOENT')throw e}
const require=createRequire(path.join(root,'development/frontend/package.json')),{build}=require('esbuild');
const raw=await readFile(path.join(root,'development/frontend/src/hardware-batch50.generated.json')),catalogues=JSON.parse(raw),models=catalogues.flatMap(c=>c.profiles.filter(p=>p.visual));
if(models.length!==50||new Set(models.map(p=>p.key)).size!==50)throw Error('atlas_50_models_required');
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
await mkdir(path.join(out,'modelos'),{recursive:true});
const ref=path.join(root,'development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/vendor');
for(const f of ['react.production.min.js','react-dom.production.min.js'])await copyFile(path.join(ref,f),path.join(out,f));
await copyFile(path.join(root,'development/frontend/review/hardware-batch50.css'),path.join(out,'atlas.css'));
await build({entryPoints:[path.join(root,'development/frontend/review/hardware-batch50.jsx')],bundle:true,format:'iife',target:'es2020',outfile:path.join(out,'atlas.js'),minify:false,legalComments:'inline'});
function html(model,base){return '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(model?model.identity.manufacturer+' '+model.identity.model:'RackClick · 50 modelos')+'</title><link rel="stylesheet" href="'+base+'atlas.css"><body data-base="'+base+'" data-model="'+escape(model?.key||'')+'"><div id="root"></div><script src="'+base+'react.production.min.js"></script><script src="'+base+'react-dom.production.min.js"></script><script src="'+base+'atlas.js"></script></body></html>\n'}
await writeFile(path.join(out,'INDICE.html'),html(null,''));
for(const m of models){if(!/^[a-z0-9-]+$/.test(m.key))throw Error('atlas_model_key_invalid');await writeFile(path.join(out,'modelos',m.key+'.html'),html(m,'../'))}
const files=['INDICE.html','atlas.js','atlas.css','react.production.min.js','react-dom.production.min.js',...models.map(m=>'modelos/'+m.key+'.html')],hashes={};
for(const f of files)hashes[f]=createHash('sha256').update(await readFile(path.join(out,f))).digest('hex');
await writeFile(path.join(out,'PAQUETE.json'),JSON.stringify({schemaVersion:1,kind:'local_visual_review_not_installer',models:50,catalogSha256:createHash('sha256').update(raw).digest('hex'),files:hashes},null,2)+'\n');
console.log(JSON.stringify({result:'built',output:out,models:50,individualHtml:50,photosEmbedded:false,apiConnected:false}));
