import {validConnectorDescriptor,connectorDescriptorLabel} from './hardware-connector-classification.mjs';
// Own schematic glyphs. A matching drawing does not certify cable pinout or power.
export function FamilyConnectorShape({type,physicalConnector,inline=false}){
 if(!['console','idc'].includes(type)&&!validConnectorDescriptor(type,physicalConnector))return null;
 const known=validConnectorDescriptor(type,physicalConnector),pc=known?physicalConnector:null;
 let drawing;
 if(type==='idc')drawing=<><rect x="2" y="8" width="36" height="25" rx="2" fill="#b6b9b0" stroke="#626b63"/>{[0,1].map(row=>Array.from({length:4},(_,i)=><g key={row+':'+i}><rect x={5+i*8} y={11+row*10} width="6" height="8" fill={row?'#66855c':'#d1b972'}/><path d={`M${8+i*8} ${11+row*10}v6`} stroke="#26382d" strokeWidth="2"/></g>))}<text x="20" y="7" textAnchor="middle" fontSize="5" fill="#d7e1d8">{pc==='idc-dual-110-krone'?'110/K':'IDC'}</text></>;
 else if(type==='console'){
  if(pc==='serial-de9')drawing=<><path d="M3 8h34l-4 25H7Z" fill="#a3aeb8" stroke="#586773"/><path d="M7 12h26l-3 17H10Z" fill="#213245"/>{[0,1].map(row=>Array.from({length:row?4:5},(_,i)=><circle key={row+':'+i} cx={10+row*2.5+i*5} cy={17+row*7} r="1.4" fill="#d7c27e"/>))}</>;
  else if(pc)drawing=<><rect x="2" y="3" width="36" height="34" rx="2" fill="#b5bcc2" stroke="#61707b"/><path d="M5 8h30v18h-9v8H14v-8H5Z" fill="#101820"/>{Array.from({length:pc==='serial-10p10c'?10:pc==='serial-rj12'?6:8},(_,i)=><path key={i} d={`M${7+i*26/((pc==='serial-10p10c'?10:pc==='serial-rj12'?6:8)-1)} 8v7`} stroke="#d9c47e"/>)}<text x="20" y="24" textAnchor="middle" fontSize="5" fill="#afd9eb">SER</text></>;
  else drawing=<><rect x="3" y="8" width="34" height="26" rx="4" fill="#153349" stroke="#6e9ab3"/><text x="20" y="23" textAnchor="middle" fontSize="6" fill="#d4edf7">SERIAL</text></>;
 }else{
  const male=pc.endsWith('p')||pc.endsWith('-plug')||['iec-c14','iec-c20'].includes(pc);
  if(pc.startsWith('iec-c')){
   const wide=['iec-c19','iec-c20'].includes(pc);
   drawing=<><path d={wide?'M3 9h34v25H3Z':'M9 5h22l6 7v23H3V12Z'} fill="#20272e" stroke="#a2a7ab"/><path d={wide?'M6 12h28v19H6Z':'M11 9h18l4 5v17H7V14Z'} fill="#070d12"/>{[[20,15],[12,25],[28,25]].map(([x,y],i)=><rect key={i} x={x-1.5} y={y-3} width={wide&&i>0?6:3} height={wide&&i>0?3:6} fill={male?'#d5bd77':'#57636a'} stroke={male?'#f0dca7':'#111820'}/>)}</>;
  }else if(pc.startsWith('nema-l')||pc.startsWith('iec60309')){
   const industrial=pc.startsWith('iec60309');
   drawing=<><circle cx="20" cy="20" r="18" fill={industrial?'#4362a5':'#232d34'} stroke="#9aabb6"/><circle cx="20" cy="20" r="13" fill="#10171e"/>{[0,120,240].map((a,i)=><path key={i} d="M19 8h4v7h-3" fill={male?'#dbc582':'none'} stroke={male?'#dbc582':'#8c9ba6'} strokeWidth="2" transform={`rotate(${a} 20 20)`}/>)}{industrial&&<text x="20" y="23" textAnchor="middle" fontSize="5" fill="#c7dcff">2P+E</text>}</>;
  }else drawing=<><circle cx="20" cy="20" r="18" fill="#252e35" stroke="#97a6b1"/>{!(male&&pc.includes('5-20'))&&<rect x="10" y="10" width="3" height="11" fill={male?'#d7c581':'#090f15'}/>}<rect x="27" y="10" width="3" height="11" fill={male?'#d7c581':'#090f15'}/>{pc.includes('5-20')&&<rect x="6" y="13" width="11" height="3" fill={male?'#d7c581':'#090f15'}/>}<path d="M17 29a3 3 0 0 1 6 0v4h-6Z" fill={male?'#d7c581':'#090f15'}/></>;
 }
 const props={'data-physical-media':type,'data-hardware-connector':pc||type,'data-connector-known':known?'true':'false','aria-hidden':true};
 return inline?<g {...props}>{drawing}</g>:<svg {...props} viewBox="0 0 40 40"><title>{connectorDescriptorLabel(type,pc)}</title>{drawing}</svg>;
}
