import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {specializedFaceMinimum} from './hardware-face-sizing.ts';
// Own flat drawing from QNAP TS-464 references: closed black front/gold strip.
// The photograph establishes the chassis, not installed memory or disks.
export function QnapTS464Face({layout,renderPort,label,words}) {
 const rear=layout.face==='rear';
 return <>
  <div key={layout.face} className="rc-shell-scroll rc-qnap-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering={rear?'qnap-ts464-rear':'qnap-ts464-front'}>
   <svg className="rc-qnap-face" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 320 330" aria-label={label}>
    <rect x="6" y="8" width="308" height="299" rx="19" fill="#292a2d" stroke="#6b6d70" strokeWidth="2"/>
    {rear?<>
     <g aria-hidden="true" data-hardware-decoration>
      <rect x="17" y="21" width="286" height="273" rx="12" fill="#b3b6b9" stroke="#82888d"/>
      <rect x="52" y="26" width="183" height="25" rx="4" fill="#b1b5b8" stroke="#8c9399" data-qnap-pcie/>
      <text x="143" y="42" textAnchor="middle" className="rc-qnap-print">PCIe</text>
      <g data-qnap-fan>
       <circle cx="203" cy="181" r="88" fill="#151a1e" stroke="#969ea4"/>
       {[22,37,52,67,82].map(r=><circle key={r} cx="203" cy="181" r={r} fill="none" stroke="#a5acb1" strokeWidth="7"/>)}
       {[0,60,120].map(a=><path key={a} d="M115 181h176" stroke="#a5acb1" strokeWidth="7" transform={`rotate(${a} 203 181)`}/>)}
       <circle cx="203" cy="181" r="17" fill="#292f34"/>
      </g>
      <circle cx="31" cy="61" r="1.6" fill="#17222a"/><text x="40" y="63" className="rc-qnap-print">RESET</text>
      <rect x="29" y="71" width="10" height="22" fill="#181e23" stroke="#e0e2e4"/><path d="M32 74v16" stroke="#a13932" strokeWidth="3"/>
      {[29,46].map(x=><rect key={x} x={x} y="104" width="10" height="23" fill="#171e23" stroke="#dde1e4"/>)}
      <text x="63" y="117" className="rc-qnap-print">USB</text><rect x="65" y="98" width="10" height="4" rx="1" fill="#131b23"/>
      <path d="M29 141h25l4 4v7H25v-7Z" fill="#161c22" stroke="#e3e5e6"/><text x="65" y="149" className="rc-qnap-print">HDMI</text>
      <rect x="27" y="266" width="21" height="22" fill="#d8dcdf" stroke="#69747e"/><circle cx="37.5" cy="277" r="7" fill="#131b21"/><circle cx="37.5" cy="277" r="2" fill="#78848d"/><text x="54" y="281" className="rc-qnap-print">DC IN</text>
      {[[39,35],[291,34],[291,282],[111,284]].map(([x,y])=><g key={x+','+y}><circle cx={x} cy={y} r="4" fill="#929ba2" stroke="#58626a"/><path d={`M${x-2} ${y}h4m-2-2v4`} stroke="#343f48"/></g>)}
     </g>
     {layout.ports.map(p=>{const y=p.gn===1?169:211;return <g key={p.id}>
      <foreignObject x="27" y={y} width="24" height="28"><div className="rc-qnap-socket">{renderPort(p,'qnap')}</div></foreignObject>
      <text x="58" y={y+15} className="rc-qnap-print">LAN{p.gn}</text>
      <text x="39" y={p.gn===1?316:327} textAnchor="middle" textLength={p.label?.length>6?65:undefined} lengthAdjust="spacingAndGlyphs" className="rc-qnap-label">{p.label||''}</text>
     </g>})}
    </>:<g aria-hidden="true" data-hardware-decoration>
     <rect x="12" y="14" width="250" height="285" rx="13" fill="#151618" stroke="#5b5d60" data-qnap-cover/>
     <path d="M32 21H248V292H32Z" fill="#191a1d"/><path d="M193 22h52L77 292H30Z" fill="#202124" opacity=".6"/>
     <path d="M261 14h34q13 0 13 16v252q0 17-13 17h-34Z" fill="#c8b18a" stroke="#b29b77" data-qnap-gold/>
     <text x="30" y="50" fill="#c9cdd0" fontSize="20" fontFamily="Arial,sans-serif" fontWeight="700">QNAP</text>
     <circle cx="285" cy="44" r="11" fill="#bda783" stroke="#786b55"/><path d="M285 37v8m-4-5a7 7 0 1 0 8 0" fill="none" stroke="#d8cbb4"/>
     {['STATUS','LAN','USB','1','2','3','4'].map((name,i)=><g key={name}><text x="285" y={83+i*20} textAnchor="end" className="rc-qnap-front-print">{name}</text><circle cx="296" cy={81+i*20} r="2" fill="#798b65"/></g>)}
     <rect x="281" y="235" width="10" height="22" fill="#12191f" stroke="#e5e0d7"/><path d="M284 238v16" stroke="#a33930" strokeWidth="3"/>
     <circle cx="285" cy="281" r="10" fill="#bca581" stroke="#756a56"/><path d="M282 277v6h7m-7-2-2-2m2 0 2-2" fill="none" stroke="#dccdb4"/>
     {[241,248,255,262].flatMap(y=>[30,35].map(x=><circle key={x+','+y} cx={x} cy={y} r="1" fill="#080d12"/>))}
    </g>}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{rear?words.qnapRear:words.qnapFront}</HardwareFaceCaption>
 </>;
}
export function QnapSocket(){return <svg viewBox="0 0 32 40" aria-hidden="true"><rect x="1" y="1" width="30" height="38" fill="#a9b4bc" stroke="#4f5e68"/><path d="M4 5h20v7h5v16h-5v7H4Z" fill="#101820"/>{Array.from({length:8},(_,i)=><path key={i} d={`M4 ${7+i*3.5}h8`} stroke="#cbb788" strokeWidth=".8"/>)}</svg>}
