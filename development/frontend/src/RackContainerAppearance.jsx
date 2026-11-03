import {hardwareProfile} from './hardware-mounting.ts';
import {batchHardwareShellLayout} from './batch-hardware-shells.ts';
import {BatchHardwareFace} from './BatchHardwareFace.jsx';
export function RackContainerAppearance({rack,face,words}){
 if(!rack.hardwareProfileKey)return null;
 const p=hardwareProfile(rack.hardwareProfileKey,rack.hardwareProfileVersion);
 if(!p||p.kind!=='rackContainer')return <p role="status">{words.unavailable}</p>;
 const view={hardwareProfileKey:p.key,hardwareProfileVersion:rack.hardwareProfileVersion,hardwareIdentity:p.identity,u:0,mountParentId:null,mountSlotKey:null,ports:[]};
 const layout=batchHardwareShellLayout(view,face);
 return <details data-rack-container-appearance><summary>{p.identity.manufacturer} · {p.identity.model} · {words.productDetails}</summary><p>{words.containerCapacity}: {p.mounting.capacityU} U · {p.widthMm??words.unknownDimension} × {p.heightMm??words.unknownDimension} × {p.depthMm??words.unknownDimension} mm</p>{layout&&<div data-rack-container-face={face}><BatchHardwareFace layout={layout} label={rack.name+' · '+words[face]} words={words} renderPort={()=>null}/></div>}<ul>{p.reviewLimits?.map((text,index)=><li key={index}>{text}</li>)}</ul></details>;
}
