import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {specializedFaceMinimum} from './hardware-face-sizing.ts';
// Own flat DS423+ drawing from exact-model references. No disks/RAID telemetry.
// Front USB/power and rear USB/DC/reset/security slot remain decorative.
export function DiskStation423Face({layout,renderPort,label,words}) {
 const rear=layout.face==='rear';
 return <>
  <div key={layout.face} className="rc-shell-scroll rc-diskstation-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering={rear?'diskstation-ds423plus-rear':'diskstation-ds423plus-front'}>
   <svg className="rc-diskstation-face" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 320 290" aria-label={label}>
    <path d="M13 7H307l8 12v234l-8 10H13L5 253V19Z" fill="#272a2d" stroke="#60666c" strokeWidth="2"/>
    <path d="M13 18H307V250H13Z" fill="#25282b" stroke="#444b52"/>
    {[16,289].map(x=><rect key={x} x={x} y="263" width="18" height="5" fill="#10171e"/>)}
    {rear?<>
     <g aria-hidden="true" data-hardware-decoration>
      {[84,237].map(x=><g key={x} data-diskstation-fan><rect x={x-66} y="31" width="132" height="139" rx="6" fill="#11171d" stroke="#3a424a"/>
       <circle cx={x} cy="99" r="61" fill="#131a20"/>
       {[22,36,49,59].map(r=><circle key={r} cx={x} cy="99" r={r} fill="none" stroke="#565f66" strokeWidth="2.5"/>)}
       {[25,85,145].map(a=><path key={a} d={`M${x-59} 99h118`} stroke="#565f66" strokeWidth="3" transform={`rotate(${a} ${x} 99)`}/>)}
      </g>)}
      <text x="31" y="191" className="rc-diskstation-print">RESET</text><circle cx="40" cy="197" r="1.5" fill="#0a1016"/>
      <rect x="49" y="229" width="21" height="8" fill="#141c24" stroke="#6a757e"/><path d="M51 232h17" stroke="#2584b1" strokeWidth="2.5"/><text x="77" y="236" className="rc-diskstation-print">USB</text>
      <circle cx="59" cy="251" r="9" fill="#141a20" stroke="#6b767f"/>{[[-3,-3],[3,-3],[-3,3],[3,3]].map(([x,y])=><circle key={x+','+y} cx={59+x} cy={251+y} r="1.3" fill="#5d6973"/>)}
      <text x="32" y="254" className="rc-diskstation-print">DC IN</text><rect x="284" y="198" width="10" height="4" fill="#10171e"/>
     </g>
     {layout.ports.map(p=>{const x=p.gn===1?50:77;return <g key={p.id}>
      <text x={x+9} y="187" textAnchor="middle" className="rc-diskstation-print">LAN{p.gn}</text>
      <foreignObject x={x} y="193" width="18" height="23"><div className="rc-diskstation-socket">{renderPort(p,'diskstation')}</div></foreignObject>
      <text x={x+9} y={p.gn===1?279:288} textAnchor="middle" textLength={p.label?.length>6?47:undefined} lengthAdjust="spacingAndGlyphs" className="rc-diskstation-label">{p.label||''}</text>
     </g>})}
    </>:<g aria-hidden="true" data-hardware-decoration>
     <rect x="36" y="27" width="208" height="220" rx="6" fill="#10161b" stroke="#363d45"/>
     {Array.from({length:4},(_,i)=>{const x=43+i*49;return <g key={i} data-diskstation-tray={i+1}>
      <rect x={x} y="36" width="43" height="194" rx="3" fill="#363a3e" stroke="#484f55"/>
      <circle cx={x+21.5} cy="193" r="5.2" fill="#141c23" stroke="#747e87"/><path d={`M${x+21.5} 191v5`} stroke="#65717a"/>
      <path d={`M${x+21.5} 213v6`} stroke="#1c242b" strokeWidth="2"/>
      <text x={x+21.5} y="244" textAnchor="middle" className="rc-diskstation-print">{i+1}</text>
     </g>})}
     {['STATUS','DISK 1','DISK 2','DISK 3','DISK 4'].map((name,i)=><g key={name}><text x="298" y={53+i*16} textAnchor="end" className="rc-diskstation-print">{name}</text><rect x="304" y={49+i*16} width="3" height="4" fill="#6e8069"/></g>)}
     <rect x="280" y="186" width="10" height="23" fill="#101820" stroke="#66727c"/><path d="M285 189v17" stroke="#237da5" strokeWidth="3"/>
     <rect x="274" y="223" width="23" height="21" rx="3" fill="#10171e" stroke="#56626c"/><path d="M285.5 228v6m-4-3a6 6 0 1 0 8 0" fill="none" stroke="#6d9bac"/>
     <text x="285" y="254" textAnchor="middle" fill="#d0d7dc" fontSize="5" fontFamily="Arial">DS423+</text>
    </g>}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{rear?words.diskstationRear:words.diskstationFront}</HardwareFaceCaption>
 </>;
}
export function DiskStationSocket(){return <svg viewBox="0 0 32 40" aria-hidden="true"><rect x="1" y="1" width="30" height="38" fill="#9caab4" stroke="#52636f"/><path d="M3 5h26v25h-6v7H9v-7H3Z" fill="#0c151d"/>{Array.from({length:8},(_,i)=><path key={i} d={`M${5+i*3.1} 5v8`} stroke="#cbb788" strokeWidth=".8"/>)}</svg>}
