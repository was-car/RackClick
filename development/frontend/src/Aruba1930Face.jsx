import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {specializedFaceMinimum} from './hardware-face-sizing.ts';
// Flat own drawing from the JL682A reference. LEDs/reset/mode are decorative.
// Existing UUID-bound buttons are the only connectable parts.
export function Aruba1930Face({layout,renderPort,label,words}) {
 const rear=layout.face==='rear';
 return <>
  <div key={layout.face} className="rc-shell-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering={rear?'aruba1930-rear':'aruba1930-front'}>
   <svg className="rc-aruba-face" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 1280 160" aria-label={label}>
    <rect x="1" y="1" width="1278" height="126" rx="3" fill="#d7d9dc" stroke="#6b7076"/>
    <rect x="33" y="3" width="1214" height="122" rx="2" fill="#eef0f1" stroke="#a8adb2"/>
    {[12,104].flatMap(y=>[9,1252].map(x=><rect key={x+'-'+y} x={x} y={y} width="18" height="9" rx="4" fill="#242930" stroke="#79818a"/>))}
    {rear?<>
     <rect x="64" y="26" width="75" height="75" rx="2" fill="#c5c9cc" stroke="#767c82"/>
     <path d="M82 18h37" stroke="#70777e" strokeWidth="3"/>
     <text x="101" y="117" textAnchor="middle" fill="#323940" fontSize="9" fontFamily="Arial">AC</text>
     {Array.from({length:7},(_,r)=>Array.from({length:72},(_,c)=><circle key={r+'-'+c} cx={223+c*11.6} cy={47+r*6.5} r="1.35" fill="#6d747a"/>))}
     {layout.ports.map(p=><g key={p.id}>
      <foreignObject x="76" y="37" width="51" height="52"><div className="rc-aruba-socket">{renderPort(p,'aruba')}</div></foreignObject>
      <text x="101" y="148" textAnchor="middle" textLength={p.label?.length>12?120:undefined} lengthAdjust="spacingAndGlyphs" className="rc-aruba-label">{p.label||''}</text>
     </g>)}
    </>:<>
     <text x="42" y="111" fill="#585e66" fontSize="12" fontFamily="Arial">aruba</text>
     <text x="1100" y="13" fill="#444b53" fontSize="8" fontFamily="Arial">Instant On Â· 1930 Â· JL682A</text>
     {[625,877].map(x=><rect key={x} x={x} y="24" width="242" height="87" fill="#999fa4" stroke="#565d65"/>)}
     <rect x="1129" y="24" width="87" height="87" fill="#b5b9bf" stroke="#565d65"/>
     {layout.ports.map(p=>{
      const sfp=p.type==='sfp',col=Math.floor((p.gn-1)/2),row=(p.gn-1)%2;
      const x=sfp?1135+col*42:630+col*40+(col>=6?12:0),y=row?77:27,number=sfp?24+p.gn:p.gn;
      return <g key={p.id}>
       <text x={x+16} y={row?121:21} textAnchor="middle" fill="#454c54" fontSize="8" fontFamily="Arial">{number}</text>
       <foreignObject x={x} y={y} width="32" height="32"><div className="rc-aruba-socket">{renderPort(p,'aruba')}</div></foreignObject>
       <text x={x+16} y={row?155:142} textAnchor="middle" textLength={p.label?.length>5?34:undefined} lengthAdjust="spacingAndGlyphs" className="rc-aruba-label">{p.label||''}</text>
      </g>;
     })}
     <g aria-hidden="true" data-hardware-decoration>
      {[37,50,64].map(y=><rect key={y} x="1234" y={y} width="5" height="4" fill="#8e969d"/>)}
      <circle cx="1228" cy="85" r="3.5" fill="#6d757e"/>
      <circle cx="1228" cy="106" r="1.7" fill="#606973"/>
     </g>
    </>}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{rear?words.arubaRear:words.arubaFront}</HardwareFaceCaption>
 </>;
}

export function ArubaSocket({type,ordinal}) {
 if(type==='power')return <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M8 6h24l5 6v22H3V12Z" fill="#11161c" stroke="#9aa3ad"/><path d="M12 18v7M28 18v7M20 12v7" stroke="#d9dde2" strokeWidth="3"/></svg>;
 if(type==='sfp')return <svg viewBox="0 0 40 40" aria-hidden="true"><rect x="2" y="7" width="36" height="26" fill="#747d86" stroke="#e1e5e9"/><rect x="5" y="11" width="30" height="18" fill="#080d12"/><path d="M7 28h26M10 31h20" stroke="#abb2b9"/></svg>;
 return <svg viewBox="0 0 40 40" aria-hidden="true"><g transform={ordinal%2===1?'rotate(180 20 20)':undefined}><rect x="1" y="1" width="38" height="38" fill="#aab0b6" stroke="#e5e8ea"/><path d="M4 7h32v21h-8v7H12v-7H4Z" fill="#080d12"/>{Array.from({length:8},(_,i)=><path key={i} d={`M${8+i*3.4} 8v7`} stroke="#c2ae7d" strokeWidth="1"/>)}</g></svg>;
}
