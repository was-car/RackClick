import {readFile,writeFile,mkdir,copyFile,lstat,readdir} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const root=path.resolve(process.argv[2]||'.'),out=path.resolve(process.argv[3]||'.local/german-cpe-preview');
try{await lstat(out);throw Error('preview_output_exists')}catch(e){if(e.code!=='ENOENT')throw e}
const require=createRequire(path.join(root,'development/frontend/package.json')),{build}=require('esbuild');
const source=path.join(root,'development/frontend/review/german-cpe.jsx');
await mkdir(out,{recursive:true});
await build({entryPoints:[source],bundle:true,format:'iife',target:'es2020',outfile:path.join(out,'preview.js'),legalComments:'inline'});
const vendor=path.join(root,'development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/vendor');
for(const name of ['react.production.min.js','react-dom.production.min.js'])await copyFile(path.join(vendor,name),path.join(out,name));
const css=await readFile(path.join(root,'development/frontend/dist/app.css'),'utf8');
const extraFiles=[];
const fonts=path.join(root,'development/frontend/dist/assets/fonts');await mkdir(path.join(out,'assets/fonts'),{recursive:true});
for(const name of await readdir(fonts)){await copyFile(path.join(fonts,name),path.join(out,'assets/fonts',name));extraFiles.push('assets/fonts/'+name)}
await writeFile(path.join(out,'index.html'),'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RackClick · Alemania y racks</title><style>'+css+'\n:root{--ir-bg:#101820;--ir-panel:#1b2835;--ir-border:#506270;--ir-text:#edf3f6;--ir-muted:#aabbca;--ir-accent:#69c7db}*{box-sizing:border-box}body{margin:0;background:#101820;color:#edf3f6;font:15px system-ui}main{max-width:1440px;margin:auto;padding:24px}button,input{font:inherit}button{background:#233747;color:#edf3f6;border:1px solid #506270;border-radius:5px;padding:8px;cursor:pointer}button:focus-visible,input:focus-visible{outline:3px solid #facc15}button[aria-pressed=true]{border-color:#69c7db}.controls{display:grid;grid-template-columns:minmax(0,500px) minmax(0,1fr);gap:20px}.controls label{display:grid;gap:8px}.face-controls{display:flex;gap:8px;margin:20px 0;flex-wrap:wrap}.review-rack{max-width:100%;border:8px solid #536371;padding:12px;background:#17212b}.review-rack article{margin:auto;max-width:100%}details{margin:16px 0}summary{padding:10px;cursor:pointer}a{color:#69c7db}@media(max-width:700px){main{padding:12px}.controls{grid-template-columns:1fr}}</style><main id="root"></main><script src="react.production.min.js"></script><script src="react-dom.production.min.js"></script><script src="preview.js"></script></html>');
const names=['index.html','preview.js','react.production.min.js','react-dom.production.min.js',...extraFiles],files={};
for(const n of names)files[n]=createHash('sha256').update(await readFile(path.join(out,n))).digest('hex');
await writeFile(path.join(out,'PAQUETE.json'),JSON.stringify({format:'RackClickLocalVisualReview-v1',date:'2026-11-03',notInstaller:true,notServerPersistence:true,files},null,2)+'\n');
console.log(JSON.stringify({output:out,files:Object.keys(files).length}));
