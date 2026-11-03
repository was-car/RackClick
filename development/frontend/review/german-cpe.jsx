import {hardwareChoices} from '../src/hardware-mounting.ts';
import {HardwareProfilePicker} from '../src/HardwareProfilePicker.jsx';
import {hardwareShellLayout} from '../src/hardware-shells.ts';
import {HardwareShellFace} from '../src/HardwareShellFace.jsx';
import {BatchSocket} from '../src/BatchHardwareFace.jsx';
import {hardwareWords} from '../src/hardware-words.ts';
import {mountedDeviceWidthStyle} from '../src/hardware-face-sizing.ts';
import {MountedPhysicalRack} from '../src/MountedPhysicalRack.jsx';
const {useState}=React;
const models=hardwareChoices.filter(p=>p.revision==='german-cpe-20261103-v1');
function fixture(p){return {id:p.key,name:p.identity.model,u:p.sizeU,hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:p.identity,mountParentId:'review-shelf',mountSlotKey:'main',ports:p.groups.flatMap((g,j)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+(i+1),groupId:'g'+j,gn:i+1,type:g.type,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPhysicalConnector:g.physicalConnector||null,rackclickPowerSystem:g.powerSystem||null,rackclickPowerRole:g.powerRole||'unspecified',label:'',status:'free'})))}};
function App(){
 const [selected,setSelected]=useState(()=>hardwareChoices.find(p=>p.key===decodeURIComponent(location.hash.slice(1))&&p.visual)||models[0]),[face,setFace]=useState('front'),[port,setPort]=useState(null),[enlarged,setEnlarged]=useState(false),[width,setWidth]=useState(1000);
 if(!selected)return <p role="alert">No hay perfiles alemanes en esta compilación.</p>;
 const w=hardwareWords.es,d=fixture(selected),layout=hardwareShellLayout(d,face),style=enlarged?{width:'100%'}:mountedDeviceWidthStyle(selected.widthMm,440);
 const choose=p=>{setSelected(p);setPort(null);setEnlarged(false);location.hash=encodeURIComponent(p.key)};
 function renderPort(p){return <button className="rc-hardware-port rc-shell-port" type="button" data-vport={p.id} data-port-type={p.type} data-port-connected="false" data-port-status="free" aria-label={p.rackclickHardwareGroupKey+' '+p.gn+' '+p.type} aria-pressed={port?.id===p.id} title={p.id+' · '+p.type} onClick={()=>setPort(p)}><BatchSocket type={p.type} physicalConnector={p.rackclickPhysicalConnector}/></button>}
 return <main><h1>RackClick · routers de Alemania y proporciones</h1><p>Revisión local del renderer del producto. No instala, no usa la DB y no guarda conexiones. Las funciones completas de conexión se comprueban por separado en el laboratorio.</p>
  <section className="controls"><HardwareProfilePicker choices={hardwareChoices.filter(p=>p.visual)} selected={selected} onChoose={choose} onSearch={()=>{}} w={w}/><label>Ancho de la zona de rack: {width}px<input type="range" min="320" max="1400" step="20" value={width} onChange={e=>setWidth(Number(e.target.value))}/></label></section>
  <div className="face-controls"><button aria-pressed={face==='front'} onClick={()=>setFace('front')}>Frontal</button><button aria-pressed={face==='rear'} onClick={()=>setFace('rear')}>Trasera</button><button aria-pressed={enlarged} onClick={()=>setEnlarged(!enlarged)}>{enlarged?'Volver a proporciones':'Ampliar vista'}</button></div>
  <p data-model-title><strong>{selected.identity?.manufacturer} · {selected.identity?.model}</strong> · SKU {selected.identity?.sku} · {selected.widthMm} × {selected.heightMm} × {selected.depthMm} mm</p>
  <div className="review-rack" style={{width:'min(100%, '+width+'px)'}}><p>Bandeja de demostración · ancho útil de referencia:440mm</p><article className="rc-mount-device" style={style} data-review-model={selected.key}>{layout?<HardwareShellFace layout={layout} renderPort={renderPort} words={w} label={selected.identity?.model+' '+face}/>:<p>Sin geometría específica para esta revisión.</p>}</article></div>
  <p role="status" data-port-selection>{port?'Puerto seleccionado: '+port.rackclickHardwareGroupKey+' / '+port.gn+' · '+port.type:'Pulsa un puerto para comprobar su objetivo interactivo.'}</p>
  <details><summary>Datos, revisión y alcance</summary><p>Revisión:{selected.revision}. Los radios no añaden bocas de cable. Un esquema de conectores no certifica circuitos internos ni instalación eléctrica. Las tomas laterales se indican en los límites del modelo.</p>{selected.limitations?.map((s,i)=><p key={i}>{s}</p>)}<a href={selected.source} target="_blank" rel="noreferrer">Fuente del fabricante</a></details>
  <details><summary>Los seis modelos nuevos</summary><ul>{models.map(p=><li key={p.key}><button data-german-model={p.key} onClick={()=>choose(p)}>{p.identity.manufacturer} · {p.identity.model} · {p.identity.sku}</button></li>)}</ul></details>
  <section><h2>Ejemplos de soportes que señaló Wascar</h2><p>Selecciona uno y abre «Verlo en el rack» para revisar las etiquetas y los detalles plegables del componente real.</p>{['tplink-tl-sg108e-un6-0','zyxel-xgs1250-12','selected-nb-2ffc5d29f711ec36'].map(key=>{const p=hardwareChoices.find(p=>p.key===key&&p.visual);return p&&<button key={key} data-review-example={key} onClick={()=>choose(p)}>{p.identity.model}</button>})}</section>
  <details data-native-rack-review><summary>Verlo en el rack · componente real, datos locales</summary><NativeRackExample model={selected} face={face} onFace={setFace} onPort={setPort}/></details>
 </main>;
}
function NativeRackExample({model,face,onFace,onPort}){
 const d=fixture(model);d.id='native-'+d.id;d.physicalDimensionsMm={width:model.widthMm,height:model.heightMm,depth:model.depthMm};d.ports=d.ports.map(p=>({...p,id:'native-'+p.id,groupPrefix:p.rackclickHardwareGroupKey+' '}));
 d.mountParentId='native-review-shelf';d.name=model.identity.model;
 const shelf={id:'native-review-shelf',name:'Soporte QA c01.model-30b8f6d6a8d0b9560b4f · nombre completo conservado',u:5,hardwareProfileKey:'shelf-5u',hardwareProfileVersion:'mount-support-20261030-v1',ports:[],notes:{}};
 const rack={id:'native-rack',name:'Rack de revisión local',size:12,location:'Datos sintéticos del visor, sin conexión a la DB',devs:[shelf,d]},project={name:'Revisión',racks:[rack],crossConns:[]};
 const noop=()=>{};
 return <MountedPhysicalRack project={project} rack={rack} allConns={[]} colors={{}} selection={null} onPort={(_device,id)=>onPort(d.ports.find(p=>p.id===id)||null)} onContext={e=>e.preventDefault()} onLabel={noop} onEdit={noop} onDelete={noop} onDeviceContext={noop} face={face} zoom={100} lang="es" id="native-example-export" onMove={noop} onSelect={noop} selectedDevs={new Set()} collapsedDevs={new Set()} onCollapse={noop} onDrop={noop} onDragStart={noop} onDragEnter={noop} onDragEnd={noop} onTouchDragStart={noop} onTouchDragMove={noop} onTouchDragEnd={noop} search="" flashPorts={new Set()} wireFocus={null} onWireFocus={noop} ptColors={{}} onFaces={noop} onFace={onFace} hardwareCanEdit={false} hardwareCanDelete={false} hardwareBlocked={false}/>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
