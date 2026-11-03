import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {hardwareNumberColor} from './hardware-label-contrast.ts';
import {FamilyConnectorShape} from './FamilyConnectorShape.jsx';
import {validConnectorDescriptor} from './hardware-connector-classification.mjs';
import {OpticalConnectorShape} from './OpticalConnectorShape.jsx';
import {ExtendedConnectorShape} from './ExtendedConnectorShape.jsx';
import {extendedConnectorMetadata,isExtendedConnector} from './hardware-connector-family-l.mjs';
import {socketFaceMinimum} from './hardware-face-sizing.ts';
function Decoration({d,index}){
 const common={'aria-hidden':true,'data-batch-decoration':d.kind};
 if(d.kind==='rect')return <rect {...common} x={d.x} y={d.y} width={d.w} height={d.h} fill={d.fill} stroke={d.stroke} rx={d.radius||0}/>;
 if(d.kind==='circle')return <circle {...common} cx={d.cx} cy={d.cy} r={d.r} fill={d.fill} stroke={d.stroke}/>;
 if(d.kind==='text')return <text {...common} x={d.x} y={d.y} fill={d.fill} fontSize={d.size} textAnchor={d.anchor||'start'} fontFamily="Arial,sans-serif">{d.text}</text>;
 if(d.kind==='line')return <line {...common} x1={d.x1} y1={d.y1} x2={d.x2} y2={d.y2} stroke={d.stroke} strokeWidth={d.width||1}/>;
 if(d.kind==='fan')return <g {...common}><circle cx={d.cx} cy={d.cy} r={d.r} fill="#161d24"/>{[.25,.48,.7,.91].map(k=><circle key={k} cx={d.cx} cy={d.cy} r={d.r*k} fill="none" stroke="#919da6" strokeWidth={Math.max(1,d.r*.035)}/>)}{[0,60,120].map(a=><line key={a} x1={d.cx-d.r} x2={d.cx+d.r} y1={d.cy} y2={d.cy} stroke="#919da6" strokeWidth={Math.max(1,d.r*.035)} transform={`rotate(${a} ${d.cx} ${d.cy})`}/>)}</g>;
 if(d.kind==='tray')return <g {...common}><rect x={d.x} y={d.y} width={d.w} height={d.h} rx="2" fill="#30373d" stroke="#64717b"/><rect x={d.x+d.w*.1} y={d.y+d.h*.12} width={d.w*.8} height={d.h*.12} fill="#1a222b"/>{d.lock&&<circle cx={d.x+d.w/2} cy={d.y+d.h*.78} r={Math.min(d.w,d.h)*.09} fill="#17202a" stroke="#9ba7b0"/>}</g>;
 if(d.kind==='vent')return <g {...common}>{Array.from({length:d.count},(_,i)=><line key={i} x1={d.x+(i+.5)*d.w/d.count} x2={d.x+(i+.5)*d.w/d.count} y1={d.y} y2={d.y+d.h} stroke="#343f48" strokeWidth={Math.max(1,d.w/d.count*.3)}/>)}</g>;
 return null;
}
export function BatchHardwareFace({layout,renderPort,label,words}){
 const v=layout.visual,plate=v.plate;
 const minimum=socketFaceMinimum(v.width,layout.sockets);
 return <>
  <div key={layout.face} className="rc-shell-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering={'batch50-'+layout.face} data-batch-model={layout.sku}>
   <svg className="rc-batch50-face" viewBox={`0 0 ${v.width} ${v.height}`} style={{minWidth:minimum,maxWidth:Math.max(minimum,v.width<=500?460:1200)}} aria-label={label}>
    <rect x={plate.x} y={plate.y} width={plate.w} height={plate.h} fill={plate.fill} stroke={plate.stroke||'#667580'} rx={plate.radius||0}/>
    {v.decorations.map((d,i)=><Decoration key={i} d={d} index={i}/>)}
    {layout.sockets.map(s=><g key={s.port.id}>
     <text x={s.x+s.w/2} y={s.y-3} textAnchor="middle" className="rc-batch50-number" style={{fill:hardwareNumberColor(plate.fill),stroke:plate.fill,strokeWidth:1.5,paintOrder:'stroke'}} fontSize={Math.max(5,Math.min(11,s.h*.28))}>{s.label}</text>
     <foreignObject x={s.x} y={s.y} width={s.w} height={s.h}><div className="rc-batch50-socket">{renderPort(s.port,'batch50')}</div></foreignObject>
    </g>)}
   </svg>
  </div>
  {!!layout.ports.some(p=>p.label)&&<div className="rc-batch50-labels">{layout.sockets.filter(s=>s.port.label).map(s=><span key={s.port.id} data-batch-label={s.port.id}>{s.label}: {s.port.label}</span>)}</div>}
  <HardwareFaceCaption words={words}>{layout.model} · {layout.face==='front'?words.batch50Front:words.batch50Rear}</HardwareFaceCaption>
 </>;
}
export function BatchSocket({type,physicalConnector}){
 if(type==='usb_a'||type==='usb_c')return <svg data-hardware-connector={type} viewBox="0 0 40 40" aria-hidden="true"><rect x="3" y={type==='usb_c'?11:8} width="34" height={type==='usb_c'?18:24} rx={type==='usb_c'?9:2} fill="#bac2c8" stroke="#5d6972"/><rect x="7" y="14" width="26" height="12" rx={type==='usb_c'?6:1} fill="#111922"/><path d="M10 20h20" stroke="#4583ab" strokeWidth="3"/></svg>;
 if(extendedConnectorMetadata[type]||isExtendedConnector(type,physicalConnector))return <ExtendedConnectorShape type={type} physicalConnector={physicalConnector}/>;
 if(type==='console'||type==='idc'||validConnectorDescriptor(type,physicalConnector))return <FamilyConnectorShape type={type} physicalConnector={physicalConnector}/>;
 if(type==='sfp56'||type==='qsfpdd')return <OpticalConnectorShape type={type}/>;
 if(type==='power')return <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M7 5h26l4 6v25H3V11Z" fill="#17202a" stroke="#83939f"/><rect x="7" y="9" width="26" height="22" fill="#0b121a"/><text x="20" y="24" textAnchor="middle" fontSize="9" fill="#9caeba">AC</text></svg>;
 if(type==='qsfp')return <svg data-hardware-connector="qsfp" viewBox="0 0 64 40" aria-hidden="true"><rect x="1" y="7" width="62" height="28" rx="2" fill="#b7c1c9" stroke="#596b78"/><rect x="5" y="10" width="54" height="21" fill="#101923"/><path d="M8 30h48M18 32v5h28v-5" fill="none" stroke="#8d9da8"/><text x="32" y="24" textAnchor="middle" fontSize="8" fill="#cbd5e1">QSFP</text></svg>;
 if(type==='sfp28')return <svg data-hardware-connector="sfp28" viewBox="0 0 40 40" aria-hidden="true"><rect x="2" y="5" width="36" height="30" fill="#b7c1c9" stroke="#596b78"/><rect x="5" y="8" width="30" height="24" fill="#101923"/><path d="M8 31h24" stroke="#8d9da8"/><text x="20" y="23" textAnchor="middle" fontSize="9" fill="#bce5f6">28</text></svg>;
 if(type==='sfp')return <svg viewBox="0 0 40 40" aria-hidden="true"><rect x="2" y="5" width="36" height="30" fill="#b7c1c9" stroke="#596b78"/><rect x="5" y="8" width="30" height="24" fill="#101923"/><path d="M8 31h24" stroke="#8d9da8"/></svg>;
 return <svg viewBox="0 0 40 40" aria-hidden="true"><rect x="1" y="2" width="38" height="36" fill="#aebcc7" stroke="#516574"/><path d="M4 7h32v21h-8v7H12v-7H4Z" fill="#111c26"/>{Array.from({length:8},(_,i)=><path key={i} d={`M${7+i*3.7} 7v8`} stroke="#c8b67d"/>)}</svg>;
}
