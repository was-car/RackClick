import {HardwareFaceCaption} from './HardwareFaceCaption.jsx';
import {specializedFaceMinimum} from './hardware-face-sizing.ts';
import {BatchHardwareFace} from './BatchHardwareFace.jsx';
import {Aruba1930Face} from './Aruba1930Face.jsx';
import {FortiGate60FFace} from './FortiGate60FFace.jsx';
import {SynologyRS1221Face} from './SynologyRS1221Face.jsx';
import {DiskStation423Face} from './DiskStation423Face.jsx';
import {QnapTS464Face} from './QnapTS464Face.jsx';
// Manufacturer photographs are references for this flat, interactive drawing.
// Socket buttons retain inventory UUIDs and the existing RC9 event handlers.
// No image loader/marker can replace the operational face with a photograph.
export function HardwareShellFace({layout,renderPort,label,words}) {
 if(layout.family==='batch50')return <BatchHardwareFace layout={layout} renderPort={renderPort} label={label} words={words}/>;
 if(layout.family==='qnap-ts464')return <QnapTS464Face layout={layout} renderPort={renderPort} label={label} words={words}/>;
 if(layout.family==='diskstation-ds423plus')return <DiskStation423Face layout={layout} renderPort={renderPort} label={label} words={words}/>;
 if(layout.family==='synology-rs1221plus')return <SynologyRS1221Face layout={layout} renderPort={renderPort} label={label} words={words}/>;
 if(layout.family==='fortigate60f')return <FortiGate60FFace layout={layout} renderPort={renderPort} label={label} words={words}/>;
 if(layout.family==='aruba1930')return <Aruba1930Face layout={layout} renderPort={renderPort} label={label} words={words}/>;
 if(layout.face==='rear')return <RearFace layout={layout} renderPort={renderPort} label={label} words={words}/>;
 return <>
  <div className="rc-shell-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering="interactive-front" data-front-revision="startech-flat-v2">
   <svg className="rc-startech-front" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 1088 100" aria-label={label}>
    <rect x="1" y="1" width="1086" height="98" rx="3" fill="#202124" stroke="#525358"/>
    <path d="M48 2v96M1040 2v96M49 5h990M49 97h990" fill="none" stroke="#101114" strokeWidth="2"/>
    {[9,82].flatMap(y=>[9,1051].map(x=><rect key={x+'-'+y} x={x} y={y} width="28" height="9" rx="4.5" fill="#090b0e" stroke="#a1a2a6" strokeWidth="1.2"/>))}
    <rect x="5" y="40" width="39" height="13" rx="4" fill="none" stroke="#e0e0e3"/>
    <text x="24.5" y="49" textAnchor="middle" fill="#f0f0f1" fontSize="6.4" fontFamily="Arial,sans-serif">StarTech.com</text>
    <text x="1063" y="48" textAnchor="middle" fill="#ececef" fontSize="6.4" fontWeight="700" fontFamily="Arial,sans-serif">CAT 6 Â· UTP</text>
    {layout.blocks.map((ports,index)=>{
     const x=54+index*245;
     return <g key={index} data-shell-block={index+1}>
      <rect x={x} y="7" width="240" height="78" rx="2" fill="#18191c" stroke="#0c0d10"/>
      <rect x={x+7} y="12" width="226" height="16" rx="1" fill="#111214" stroke="#4c4d51"/>
      <path d={`M${x+7} 12v16M${x+233} 12v16`} stroke="#090a0c" strokeWidth="5"/>
      {ports.map((p,i)=>{
       const px=x+11+i*37;
       return <g key={p.id}>
        <text x={px+15} y="23" textAnchor="middle" textLength={p.label?.length>5?32:undefined} lengthAdjust="spacingAndGlyphs" className="rc-front-user-label">{p.label||''}</text>
        <rect x={px-2} y="34" width="34" height="44" fill="#44464b" stroke="#08090c" strokeWidth="1.5"/>
        <text x={px+15} y="43" textAnchor="middle" fill="#17181b" fontSize="6.5" fontWeight="700" fontFamily="Arial,sans-serif" aria-hidden="true">CAT 6</text>
        <foreignObject x={px-1} y="45" width="32" height="32"><div className="rc-front-socket">{renderPort(p,true)}</div></foreignObject>
        <text x={px+15} y="94" textAnchor="middle" className="rc-front-number" aria-hidden="true">{p.gn}</text>
       </g>;
      })}
     </g>;
    })}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{words.interactiveFront}</HardwareFaceCaption>
 </>;
}

// Its bounds, rather than a number/label or invisible photo area, anchor the cable.
export function StarTechJack({rear=false}) {
 return <svg viewBox="0 0 30 28" aria-hidden="true" data-front-jack>
  <rect x=".75" y=".75" width="28.5" height="26.5" fill={rear?'#1b1d20':'#2d2f34'} stroke={rear?'#45484c':'#63666d'} strokeWidth="1.5"/>
  <path d="M3 3H27V19H22V24H8V19H3Z" fill="#040507" stroke="#15171a"/>
  {Array.from({length:8},(_,i)=><path key={i} d={`M${6+i*2.55} 4v5`} stroke={rear?'#aaa69d':'#6b6760'} strokeWidth=".9"/>)}
  {rear&&<path d="M10 21h10v4H10Z" fill="#d6d6d1"/>}
 </svg>;
}

function RearFace({layout,renderPort,label,words}) {
 return <>
  <div className="rc-shell-scroll" tabIndex={0} role="group" aria-label={label} data-shell-rendering="interactive-rear" data-rear-revision="startech-rear-v1">
   <svg className="rc-startech-front rc-startech-rear" style={{minWidth:specializedFaceMinimum(layout)}} viewBox="0 0 1088 136" aria-label={label}>
    <rect x="1" y="1" width="1086" height="98" rx="3" fill="#202124" stroke="#525358"/>
    {[9,82].flatMap(y=>[9,1051].map(x=><rect key={x+'-'+y} x={x} y={y} width="28" height="9" rx="4.5" fill="#090b0e" stroke="#a1a2a6" strokeWidth="1.2"/>))}
    <rect x="49" y="5" width="990" height="90" rx="2" fill="#0e0f11" stroke="#4b4d51" strokeWidth="2"/>
    {layout.blocks.map((ports,index)=>{
     const x=54+index*245;
     return <g key={index} data-shell-block={index+1}>
      <rect x={x} y="7" width="240" height="82" rx="1" fill="#18191c" stroke="#55565a"/>
      {ports.map((p,i)=>{
       const px=x+11+i*37;
       return <g key={p.id}>
        <path d={`M${px-2} 11h34v15h-5v-4h-24v4h-5ZM${px+3} 26v5h24v-5`} fill="#1e2023" stroke="#4a4d51" strokeWidth="1.2"/>
        <rect x={px-2} y="30" width="34" height="49" fill="#202225" stroke="#0a0b0d" strokeWidth="1.5"/>
        <text x={px+15} y="41" textAnchor="middle" fill="#aaaeb2" fontSize="6.5" fontFamily="Arial,sans-serif" aria-hidden="true">CAT 6</text>
        <foreignObject x={px-1} y="45" width="32" height="32"><div className="rc-front-socket">{renderPort(p,true)}</div></foreignObject>
        <path d={`M${px-2} 83h34M${px} 86h30`} stroke="#44464a"/>
        <text x={px+15} y="113" textAnchor="middle" className="rc-front-number" data-rear-logical-number aria-hidden="true">{p.gn}</text>
        <text x={px+15} y="130" textAnchor="middle" textLength={p.label?.length>5?32:undefined} lengthAdjust="spacingAndGlyphs" className="rc-front-user-label" data-rear-logical-label>{p.label||''}</text>
       </g>;
      })}
     </g>;
    })}
   </svg>
  </div>
  <HardwareFaceCaption words={words}>{words.interactiveRear} {words.rearLogical}</HardwareFaceCaption>
 </>;
}
