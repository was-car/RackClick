// Local preview of the production picker. No API, inventory save or remote assets.
import {readFile,writeFile,mkdir,copyFile,lstat} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import path from 'node:path';
const root=path.resolve(process.argv[2]||'.'),out=path.resolve(process.argv[3]||'.local/selected506i-picker-preview');
try{await lstat(out);throw Error('preview_output_exists')}catch(e){if(e.code!=='ENOENT')throw e}
const require=createRequire(path.join(root,'development/frontend/package.json')),{build}=require('esbuild');
const entry=`import {HardwareCreationFields} from './HardwareCreationFields.jsx';
import {hardwareCreateCommand,hardwareReference,hardwareChoices} from './hardware-mounting.ts';
const {useState}=React;
if(hardwareChoices.length!==739)throw Error('preview_catalogue_count_invalid');
function Preview(){const [lang,setLang]=useState('es'),[form,setForm]=useState({profileKey:'shelf-2u',profileVersion:hardwareReference.version,name:'Ejemplo sintético',rackId:'demo-rack',mountParentId:''}),[result,setResult]=useState(null);
const project={racks:[{id:'demo-rack',name:'Rack sintético de demostración'}],devices:[{id:'demo-shelf',name:'Bandeja sintética 5U',rackId:'demo-rack',hardwareProfileKey:'shelf-5u',properties:{hardwareProfileVersion:'mount-support-20261030-v1'}}]};
return <main><h1>RackClick · selector compacto</h1><p>Demostración local de 739 perfiles, 734 comerciales. No conecta al servidor ni guarda inventario.</p><label>Idioma / Language / Sprache <select value={lang} onChange={e=>setLang(e.target.value)}><option value="es">Español</option><option value="en">English</option><option value="de">Deutsch</option></select></label><form onSubmit={e=>{e.preventDefault();try{setResult(hardwareCreateCommand(form,project))}catch(error){setResult({error:error.code})}}}><HardwareCreationFields form={form} setForm={value=>{setForm(value);setResult(null)}} project={project} lang={lang} disabled={false}/><button type="submit">Revisar selección / Review selection</button></form>{result&&<pre data-picker-preview-result>{JSON.stringify(result,null,2)}</pre>}<p>Prueba «sofos», Fortinet, Aruba o un SKU. Flechas y Enter eligen; Escape cierra la lista.</p></main>}
ReactDOM.createRoot(document.getElementById('root')).render(<Preview/>);`;
await mkdir(out,{recursive:true});
await build({stdin:{contents:entry,resolveDir:path.join(root,'development/frontend/src'),sourcefile:'hardware-picker-preview.jsx',loader:'jsx'},bundle:true,format:'iife',target:'es2020',outfile:path.join(out,'picker.js'),legalComments:'inline'});
const vendor=path.join(root,'development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/vendor');
for(const name of ['react.production.min.js','react-dom.production.min.js'])await copyFile(path.join(vendor,name),path.join(out,name));
await copyFile(path.join(root,'development/frontend/src/server.css'),path.join(out,'picker.css'));
await writeFile(path.join(out,'INDICE.html'),'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RackClick · selector compacto</title><link rel="stylesheet" href="picker.css"><style>body{margin:20px;background:#f0f4f8;color:#18212b;font:16px system-ui}main{max-width:760px;margin:auto;background:white;padding:20px;border-radius:8px}.rc-form label{display:flex;flex-direction:column;gap:5px;margin:10px 0}input,select,button{font:inherit;padding:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><div id="root"></div><script src="react.production.min.js"></script><script src="react-dom.production.min.js"></script><script src="picker.js"></script></html>\n');
const files={};
for(const name of ['INDICE.html','picker.js','picker.css','react.production.min.js','react-dom.production.min.js'])files[name]=createHash('sha256').update(await readFile(path.join(out,name))).digest('hex');
await writeFile(path.join(out,'PAQUETE.json'),JSON.stringify({schemaVersion:1,kind:'local_picker_preview_not_installer',totalProfiles:739,files},null,2)+'\n');
console.log(JSON.stringify({result:'built',output:out,profiles:739,apiConnected:false}));
