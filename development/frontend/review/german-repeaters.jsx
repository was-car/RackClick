import {hardwareChoices} from '../src/hardware-mounting.ts';
import {HardwareProfilePicker} from '../src/HardwareProfilePicker.jsx';
import {HardwareRoomFace} from '../src/HardwareRoomFace.jsx';
import {hardwareWords} from '../src/hardware-words.ts';
const {useState}=React;
const revision='german-repeaters-20261103-v1';
const models=hardwareChoices.filter(p=>p.revision===revision);
function fixture(p){return {id:p.key,name:p.identity.model,kind:'endDevice',roomId:'review-room',rackId:null,u:null,hardwareProfileKey:p.key,hardwareProfileVersion:p.revision,hardwareIdentity:p.identity,physicalDimensionsMm:{width:p.widthMm,height:p.heightMm,depth:p.depthMm},mountParentId:null,mountSlotKey:null,ports:p.groups.flatMap((g,j)=>Array.from({length:g.count},(_,i)=>({id:p.key+'-'+g.key+'-'+(i+1),groupId:'group-'+j,gn:i+1,type:g.type,rackclickFace:g.face,rackclickHardwareGroupKey:g.key,rackclickPhysicalConnector:g.physicalConnector||null,rackclickPowerRole:g.powerRole||'unspecified',rackclickPowerSystem:g.powerSystem||null,label:'',status:'free'})))}};
function App(){
 const [selected,setSelected]=useState(()=>models.find(p=>p.key===decodeURIComponent(location.hash.slice(1)))||models[0]),[port,setPort]=useState(null),[lang,setLang]=useState('es');
 if(!selected)return <p role="alert">Esta compilación aún no contiene el lote de repetidores.</p>;
 const d=fixture(selected),project={serverEndpoints:Object.fromEntries(d.ports.map(p=>[p.id,selected.identity.model+' · '+p.rackclickHardwareGroupKey+' '+p.gn+' · '+p.type])),connections:[]};
 function choose(p){setSelected(p);setPort(null);location.hash=encodeURIComponent(p.key)}
 return <main><h1>RackClick · repetidores de Alemania</h1><p>Revisión local del catálogo y del componente de sala del producto. No instala, no se conecta a la DB y no simula cobertura o enlaces WiFi.</p>
  <div className="controls"><HardwareProfilePicker choices={models} selected={selected} onChoose={choose} onSearch={()=>{}} w={hardwareWords[lang]}/><label>Idioma de controles<select value={lang} onChange={e=>setLang(e.target.value)}><option value="es">Español</option><option value="de">Deutsch</option><option value="en">English</option></select></label></div>
  <h2 data-repeater-title>{selected.identity.manufacturer} · {selected.identity.model}</h2><p>SKU {selected.identity.sku} · {selected.kind==='wall'?'Enchufe / pared':'Sobremesa en sala'} · {selected.widthMm??'?'} × {selected.heightMm??'?'} × {selected.depthMm??'?'} mm</p>
  <section className="room-review"><HardwareRoomFace key={d.id} device={d} project={project} lang={lang} selection={port?{pid:port.id}:null} onPort={(_owner,id)=>setPort(d.ports.find(p=>p.id===id))} onContext={(_owner,id)=>setPort(d.ports.find(p=>p.id===id))}/></section>
  <p role="status" data-selected-repeater-port>{port?'Seleccionado: '+port.rackclickHardwareGroupKey+' '+port.gn+' · '+port.type:'Pulsa un conector para comprobar su selección.'}</p>
  <details><summary>Conectores, montaje y límites del modelo</summary><p>Ethernet: {d.ports.filter(p=>p.type==='rj45').length} · Energía: {d.ports.filter(p=>['power','power_dc'].includes(p.type)).length}. WiFi/Mesh no son conectores de cable. El equipo pertenece a una sala: no reserva U ni exige soporte de rack.</p>{selected.reviewLimits?.map((s,i)=><p key={i}>{s}</p>)}<p>Revisión: {selected.revision}. Las cotas desconocidas no acreditan encaje. Las clavijas y entradas son representaciones documentales, sin certificación eléctrica.</p><a href={selected.source} target="_blank" rel="noreferrer">Referencia del fabricante</a></details>
  <details><summary>Los modelos de esta tanda</summary><ul>{models.map(p=><li key={p.key}><button data-repeater-model={p.key} onClick={()=>choose(p)}>{p.identity.manufacturer} · {p.identity.model}</button></li>)}</ul></details>
 </main>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
