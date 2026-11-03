import {BatchHardwareFace,BatchSocket} from './BatchHardwareFace.jsx';
import {batchHardwareShellLayout} from './batch-hardware-shells.ts';
import {hardwareWords} from './hardware-words.ts';
import {repeaterRoomWidth} from './hardware-room-sizing.ts';
import {socketFaceMinimum} from './hardware-face-sizing.ts';
const {useState}=React;
export function HardwareRoomFace({device,project,lang,selection,onPort,onContext}){
 const [face,setFace]=useState('front'),[expanded,setExpanded]=useState(false),viewId=React.useId(),w=hardwareWords[lang]||hardwareWords.en;
 const repeater=device.hardwareProfileVersion==='german-repeaters-20261103-v1';
 const zoom=lang==='de'?['Ansicht vergrößern','Kompakte Ansicht']:lang==='es'?['Ampliar vista','Vista compacta']:['Enlarge view','Compact view'];
 const layout=batchHardwareShellLayout(device,face);
 if(!layout)return null;
 const compactWidth=Math.max(repeaterRoomWidth(device.physicalDimensionsMm?.width),socketFaceMinimum(layout.visual.width,layout.sockets));
 function renderPort(p){const title=project.serverEndpoints[p.id],connected=project.connections.some(c=>c.fp===p.id||c.tp===p.id);return <button type="button" key={p.id} data-room-port={p.id} data-vport={p.id} data-ir-hit={p.id} data-port-owner={device.id} data-port-connected={connected?'true':'false'} data-port-status={p.status} className={'rc-hardware-port rc-shell-port '+(selection?.pid===p.id?'selected':'')} title={title} aria-label={title} aria-pressed={selection?.pid===p.id} onClick={()=>onPort(device.id,p.id)} onContextMenu={e=>{e.preventDefault();onContext(device.id,p.id)}}><BatchSocket type={p.type} physicalConnector={p.rackclickPhysicalConnector}/><span>{p.gn}</span><small>{p.label}</small></button>}
 return <section data-room-hardware={device.id} data-hardware-face={face}><div className="rc-inline-buttons"><button type="button" aria-pressed={face==='front'} onClick={()=>setFace('front')}>{w.front}</button><button type="button" aria-pressed={face==='rear'} onClick={()=>setFace('rear')}>{w.rear}</button>{repeater&&<button type="button" data-room-enlarge aria-expanded={expanded} aria-controls={viewId} onClick={()=>setExpanded(!expanded)}>{zoom[expanded?1:0]}</button>}</div><div id={viewId} style={repeater?{maxWidth:expanded?'100%':compactWidth+'px',minWidth:0}:undefined}><BatchHardwareFace layout={layout} renderPort={renderPort} label={device.name+' · '+w[face]} words={w}/></div></section>;
}
