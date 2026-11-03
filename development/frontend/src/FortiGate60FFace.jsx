import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {specializedFaceMinimum} from './hardware-face-sizing.ts';
// Own flat drawing from the exact FG-60F reference; the front has no sockets.
// USB, serial console and DC require separate connector contracts, not Ethernet.
export function FortiGate60FFace({layout,renderPort,label,words}) {
 const rear=layout.face==='rear';
 const position=p=>p.rackclickHardwareGroupKey==='rear-wan'?{x:p.gn===2?274:339,name:'WAN'+p.gn}:
  p.rackclickHardwareGroupKey==='rear-dmz'?{x:404,name:'DMZ'}:
  p.rackclickHardwareGroupKey==='rear-fortilink'?{x:p.gn===2?469:534,name:p.gn===2?'B':'A'}:
  {x:599+(5-p.gn)*65,name:String(p.gn)};
 return <>
  <div key={layout.face} className="rc-shell-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering={rear?'fortigate60f-rear':'fortigate60f-front'}>
   <svg className="rc-fortinet-face" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 1000 182" aria-label={label}>
    <rect x="2" y="2" width="996" height="145" rx={rear?2:8} fill="#e6e7e7" stroke="#606368" strokeWidth="2"/>
    <rect x="12" y="10" width="976" height="128" rx={rear?0:8} fill="#f2f3f3" stroke="#93979a"/>
    {rear?<>
     <g aria-hidden="true" data-hardware-decoration>
      {Array.from({length:26},(_,i)=><g key={i}><rect x={124+i*31} y="19" width="19" height="5" rx="2" fill="#3f4449"/><rect x={124+i*31} y="30" width="19" height="5" rx="2" fill="#3f4449"/></g>)}
      <circle cx="32" cy="83" r="10" fill="#84898d" stroke="#4b5157"/><path d="m27 78 10 10m0-10-10 10" stroke="#353a40" strokeWidth="2"/>
      <circle cx="51" cy="119" r="3" fill="#32373c"/><text x="42" y="136" className="rc-fortinet-print">RESET</text>
      <path d="M78 54v-8h7v12h13V46h7v8M78 60h27v50H78Z" fill="#777d83" stroke="#3d444b"/>
      {[69,91].map(y=><rect key={y} x="85" y={y} width="13" height="11" fill="#23282e" stroke="#c0c6ca"/>)}
      <text x="91" y="135" textAnchor="middle" className="rc-fortinet-print">DC +12V</text>
      <rect x="126" y="58" width="24" height="54" rx="3" fill="#3d4248" stroke="#6c747b"/><rect x="132" y="65" width="11" height="40" fill="#1279a3"/>
      <text x="138" y="135" textAnchor="middle" className="rc-fortinet-print">USB</text>
      <rect x="169" y="58" width="70" height="54" fill="#bfc4c7" stroke="#5b636b"/>
      <path d="M179 100V70h10v-5h29v5h10v30Z" fill="#30363b"/>
      {Array.from({length:8},(_,i)=><path key={i} d={`M${187+i*4.2} 94v8`} stroke="#bfa976"/>)}
      <text x="204" y="135" textAnchor="middle" className="rc-fortinet-print">CONSOLE</text>
      <rect x="266" y="56" width="328" height="59" fill="#989ea3" stroke="#4e555d"/>
      <rect x="591" y="56" width="333" height="59" fill="#989ea3" stroke="#4e555d"/>
     </g>
     {layout.ports.map(p=>{const {x,name}=position(p);return <g key={p.id}>
      <foreignObject x={x} y="60" width="50" height="50"><div className="rc-fortinet-socket">{renderPort(p,'fortinet')}</div></foreignObject>
      <text x={x+25} y="134" textAnchor="middle" className="rc-fortinet-print">{name}</text>
      <text x={x+25} y="170" textAnchor="middle" textLength={p.label?.length>8?60:undefined} lengthAdjust="spacingAndGlyphs" className="rc-fortinet-label">{p.label||''}</text>
     </g>})}
    </>:<g aria-hidden="true" data-hardware-decoration>
     <text x="42" y="57" fill="#2c2e31" fontSize="27" fontWeight="700" fontFamily="Arial">F<tspan fill="#db3039">O</tspan>RTINET</text>
     <text x="78" y="85" fill="#5f6367" fontSize="15" fontFamily="Arial">FortiGate 60F</text>
     {[43,49,55].map(x=><rect key={x} x={x} y="71" width="3" height="17" rx="1" fill="#91be31"/>)}
     {['PWR','STATUS','HA'].map((name,i)=><g key={name}><text x={367+i*32} y="107" textAnchor="middle" className="rc-fortinet-led-label">{name}</text><rect x={362+i*32} y="114" width="10" height="10" fill="#78857b" stroke="#38483e"/></g>)}
     {['1','2','3','4','5','A','B','DMZ','WAN1','WAN2'].map((name,i)=><g key={name}><text x={606+i*29} y="83" textAnchor="middle" className="rc-fortinet-led-label">{name}</text>{[90,113].map(y=><rect key={y} x={601+i*29} y={y} width="9" height="9" fill="#78857b" stroke="#38483e"/>)}</g>)}
     <text x="904" y="98" className="rc-fortinet-led-label">LINK/ACT</text><text x="904" y="121" className="rc-fortinet-led-label">SPEED</text>
    </g>}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{rear?words.fortinetRear:words.fortinetFront}</HardwareFaceCaption>
 </>;
}

export function FortinetSocket() {
 return <svg viewBox="0 0 40 40" aria-hidden="true"><rect x="1" y="1" width="38" height="38" fill="#b8bdc2" stroke="#5e656d"/><path d="M3 5h34v24H27v7H13v-7H3Z" fill="#151a20"/>{Array.from({length:8},(_,i)=><path key={i} d={`M${7+i*3.7} 6v10`} stroke="#c9b783" strokeWidth="1"/>)}</svg>;
}
