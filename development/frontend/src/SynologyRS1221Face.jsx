import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {specializedFaceMinimum} from './hardware-face-sizing.ts';
// Own flat RS1221+ enclosure. Bays/fans/buttons are visual, not disk telemetry.
// The optional NIC slot is closed; only the five recorded UUIDs are interactive.
export function SynologyRS1221Face({layout,renderPort,label,words}) {
 const rear=layout.face==='rear';
 return <>
  <div key={layout.face} className="rc-shell-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering={rear?'synology-rs1221plus-rear':'synology-rs1221plus-front'}>
   <svg className="rc-synology-face" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 1280 290" aria-label={label}>
    {rear?<Rear layout={layout} renderPort={renderPort}/>:<Front/>}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{rear?words.synologyRear:words.synologyFront}</HardwareFaceCaption>
 </>;
}
function Front(){return <g aria-hidden="true" data-hardware-decoration>
 <rect x="3" y="2" width="1274" height="250" rx="5" fill="#27292b" stroke="#74777a"/>
 <rect x="66" y="6" width="1148" height="242" fill="#17191b" stroke="#45484b"/>
 {[5,1216].map(x=><g key={x}><rect x={x} y="8" width="59" height="235" rx="7" fill="#33373a" stroke="#111519"/>{[12,221].map(y=><rect key={y} x={x+15} y={y} width="25" height="12" rx="6" fill="#10151b" stroke="#858a8f"/>)}<path d={`M${x+12} 58h23l14 17v104l-14 18h-23l-6-18V76Z`} fill="#41474b" stroke="#1b2025"/></g>)}
 <text x="81" y="29" fill="#e5e6e7" fontSize="16" fontFamily="Arial">Synology</text><text x="1193" y="25" textAnchor="end" fill="#e0e2e3" fontSize="9" fontFamily="Arial">RS1221+</text>
 {['STATUS','ALERT'].map((name,i)=><g key={name}><text x={188+i*39} y="46" textAnchor="middle" className="rc-synology-print-front">{name}</text><circle cx={188+i*39} cy="55" r="3" fill="#6a7969"/></g>)}
 <circle cx="106" cy="51" r="5" fill="#303a40" stroke="#8c959b"/><path d="M106 43v7" stroke="#ced4d8"/>
 <circle cx="154" cy="53" r="5" fill="#363d43" stroke="#8c959b"/>
 {Array.from({length:8},(_,i)=><g key={i}><text x={258+i*18} y="47" textAnchor="middle" className="rc-synology-print-front">{i+1}</text><circle cx={258+i*18} cy="57" r="3" fill="#6a7969"/></g>)}
 {[36,51].map(y=><g key={y}><rect x="442" y={y} width="752" height="7" rx="2" fill="#06090c"/>{[640,900].map(x=><path key={x} d={`M${x} ${y-1}v9`} stroke="#4a4e52" strokeWidth="4"/>)}</g>)}
 {Array.from({length:8},(_,i)=>{const x=81+(i%4)*281,y=76+Math.floor(i/4)*83;return <g key={i} data-synology-tray={i+1}>
  <rect x={x-5} y={y-3} width="279" height="80" rx="2" fill="#090c10" stroke="#565b61"/>
  <rect x={x} y={y} width="268" height="73" rx="3" fill="#282c2f" stroke="#4b5156"/>
  {[16,31].map(offset=><path key={offset} d={`M${x+9} ${y+offset}h38`} stroke="#080c11" strokeWidth="6"/>)}
  <rect x={x+59} y={y+10} width="197" height="55" rx="3" fill="#33373a" stroke="#1b2025"/>
  <circle cx={x+143} cy={y+35} r="9" fill="#13191f" stroke="#61676d"/><path d={`M${x+143} ${y+31}v9`} stroke="#555d65" strokeWidth="2"/>
 </g>})}
 </g>}
function Rear({layout,renderPort}){return <>
 <rect x="3" y="2" width="1274" height="250" fill="#afb4b7" stroke="#5e666b"/>
 <rect x="13" y="9" width="1254" height="234" fill="#bfc3c6" stroke="#7c858b"/>
 <g aria-hidden="true" data-hardware-decoration>
  {[150,1133].map(x=><g key={x} data-synology-fan>
   <rect x={x-112} y="16" width="224" height="224" rx="4" fill="#3b4247" stroke="#7b848a"/>
   <circle cx={x} cy="129" r="99" fill="#141a20"/>
   {[36,63,89].map(r=><circle key={r} cx={x} cy="129" r={r} fill="none" stroke="#a0a8ad" strokeWidth="5"/>)}
   {[0,45,90,135].map(a=><path key={a} d={`M${x-100} 129h200`} stroke="#a0a8ad" strokeWidth="5" transform={`rotate(${a} ${x} 129)`}/>)}
   {[x-101,x+101].flatMap(cx=>[25,231].map(cy=><circle key={cx+'-'+cy} cx={cx} cy={cy} r="4" fill="#767f86" stroke="#434c54"/>))}
  </g>)}
  <rect x="302" y="22" width="235" height="51" fill="#90989d" stroke="#707a80"/>
  {Array.from({length:22},(_,i)=><path key={i} d={`M${313+i*9} 28v38`} stroke="#353d44" strokeWidth="5"/>)}
  <rect x="282" y="14" width="23" height="61" fill="#ccd0d3" stroke="#939ca3"/>
  <rect x="558" y="30" width="10" height="43" rx="1" fill="#3b434a" stroke="#929aa1"/>
  <circle cx="597" cy="64" r="2.5" fill="#333b44"/>
  {[27,52].map(y=><g key={y}><rect x="625" y={y} width="37" height="17" fill="#1f292f" stroke="#89939a"/><path d={`M629 ${y+5}h29`} stroke="#2184b4" strokeWidth="5"/></g>)}
  <text x="902" y="36" textAnchor="middle" className="rc-synology-print-rear">eSATA</text><rect x="876" y="46" width="58" height="20" fill="#d5d9dc" stroke="#6c7780"/><path d="M883 51h43v10h-43Z" fill="#141c24"/>
  <path d="M505 92h46l10 6v26l-10 6h-46l-9-8v-22Z" fill="#868f97" stroke="#3f4b55"/><path d="M509 100h39v21h-39Z" fill="#1b5374"/>
  {Array.from({length:9},(_,i)=><circle key={i} cx={515+(i%5)*6} cy={106+Math.floor(i/5)*8} r="1.5" fill="#c3ccd3"/>)}
  <text x="951" y="225" textAnchor="end" className="rc-synology-print-rear">RS1221+</text>
 </g>
 {layout.ports.map(p=>{const power=p.type==='power',x=power?302:680+(4-p.gn)*43,y=power?143:39,w=power?176:39;return <g key={p.id}>
  <foreignObject x={x} y={y} width={w} height={power?99:39}><div className="rc-synology-socket">{renderPort(p,'synology')}</div></foreignObject>
  <text x={power?490:x+w/2} y={power?225:29} textAnchor={power?'start':'middle'} className="rc-synology-print-rear">{power?'AC IN':'LAN'+p.gn}</text>
  <text x={x+w/2} y={power?282:269} textAnchor="middle" textLength={p.label?.length>12?116:undefined} lengthAdjust="spacingAndGlyphs" className="rc-synology-label">{p.label||''}</text>
 </g>})}
 </>}

export function SynologySocket({type}){
 // The source exposes the recessed power area, not its internal contact geometry.
 if(type==='power')return <svg viewBox="0 0 80 45" aria-hidden="true"><rect x="1" y="1" width="78" height="43" fill="#191f25" stroke="#717e88"/><rect x="3" y="3" width="74" height="39" fill="#262d34"/><path d="M4 42V4h72" fill="none" stroke="#10171e" strokeWidth="3"/></svg>;
 return <svg viewBox="0 0 40 40" aria-hidden="true"><rect x="1" y="1" width="38" height="38" fill="#a8b3b8" stroke="#78858e"/><path d="M3 6h34v24h-9v6H12v-6H3Z" fill="#10191f"/>{Array.from({length:8},(_,i)=><path key={i} d={`M${7+i*3.7} 6v9`} stroke="#cbb581"/>)}<rect x="3" y="3" width="5" height="3" fill="#74836d"/><rect x="32" y="3" width="5" height="3" fill="#74836d"/></svg>;
}
