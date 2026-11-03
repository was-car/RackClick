import {BatchSocket} from './BatchHardwareFace.jsx';
import {ArubaSocket} from './Aruba1930Face.jsx';
import {FortinetSocket} from './FortiGate60FFace.jsx';
import {SynologySocket} from './SynologyRS1221Face.jsx';
import {DiskStationSocket} from './DiskStation423Face.jsx';
import {QnapSocket} from './QnapTS464Face.jsx';
import { IRPortShape, irPortTooltip, irPortFace, PT, IntegratedPhysicalRack } from '../generated/rc9.jsx';
import { hardwareProfile, mountOccupancy } from './hardware-mounting.ts';
import { hardwareWords, hardwareSlotLabel } from './hardware-words.ts';
import { hardwareShellLayout } from './hardware-shells.ts';
import { HardwareShellFace, StarTechJack } from './HardwareShellFace.jsx';
import {RackContainerAppearance} from './RackContainerAppearance.jsx';
import {mountedDeviceWidthStyle} from './hardware-face-sizing.ts';


// The adopted renderer remains the path for racks without mounted/reference hardware.
// This view owns only its layout; all port actions still use InventoryPanel's IDs,
// transactional commands, pending journal and server-confirmed save workflow.
export function MountedPhysicalRack(props) {
 if (!props.rack.hardwareProfileKey&&!props.rack.devs.some(d=>d.hardwareProfileKey||d.mountParentId)) return <IntegratedPhysicalRack {...props}/>;
 return <MountedRack {...props}/>;
}
function MountedRack(props) {
 const {project,hardwareCanEdit,hardwareCanDelete,hardwareBlocked,rack,allConns,selection,onPort,onContext,onLabel,onEdit,onDelete,face,lang,selectedDevs,onSelect,search,ptColors}=props;
 const w=hardwareWords[lang]||hardwareWords.en;
 const [expandedDevice,setExpandedDevice]=React.useState(null);
 const viewId=React.useId();
 // RC9 listens for resize to measure cable endpoints. Width-only changes of a
 // generic face need that notification even when the outer rack stays the same.
 React.useEffect(()=>{const frame=requestAnimationFrame(()=>window.dispatchEvent(new Event('resize')));return()=>cancelAnimationFrame(frame)},[expandedDevice]);
 const zoomWords=lang==='de'?['Ansicht vergrößern','Maßstäbliche Ansicht']:lang==='es'?['Ampliar vista','Volver a proporciones']:['Enlarge view','Return to proportions'];
 const detailsWord=lang==='de'?'Modelldetails':lang==='es'?'Detalles del modelo':'Model details';
 const devices=rack.devs, used=mountOccupancy(devices);
 function deviceView(d,nested=false) {
  const profile=hardwareProfile(d.hardwareProfileKey,d.hardwareProfileVersion),parent=devices.find(p=>p.id===d.mountParentId);
  const children=devices.filter(child=>child.mountParentId===d.id),dimensions=d.physicalDimensionsMm,identity=profile?.identity||d.hardwareIdentity;
  const parentProfile=parent&&hardwareProfile(parent.hardwareProfileKey,parent.hardwareProfileVersion);
  const expanded=nested&&expandedDevice===d.id;
  const childStyle=nested?(expanded?{maxWidth:'100%',width:'100%'}:mountedDeviceWidthStyle(dimensions?.width??profile?.widthMm,parentProfile?.slot?.widthMm)):undefined;
  const ownPorts=d.ports.filter(p=>irPortFace(d,p)===face);
  const shell=hardwareShellLayout(d,face);
  function renderPort(p,specific=false) {
   const title=irPortTooltip(d,p,allConns,project,rack,lang),connected=allConns.some(c=>c.fp===p.id||c.tp===p.id);
   return <button key={p.id} type="button" data-vport={p.id} data-ir-hit={p.id} data-port-owner={d.id} data-port-status={p.status} data-port-color={p.portColor?'custom':undefined} data-port-connected={connected?'true':'false'} data-shell-port={specific?p.gn:undefined} className={'rc-hardware-port '+(specific?'rc-shell-port ':'')+(selection?.pid===p.id?'selected':'')} aria-label={title} aria-pressed={selection?.pid===p.id} title={title} onClick={()=>onPort(d.id,p.id)} onContextMenu={e=>onContext(e,d.id,p.id)} onDoubleClick={e=>onLabel(e,d.id,p.id)} style={{'--port-color':p.portColor||ptColors[p.type]||PT[p.type]?.color||'#94a3b8'}}>{specific==='batch50'?<BatchSocket type={p.type} physicalConnector={p.rackclickPhysicalConnector}/>:specific==='qnap'?<QnapSocket/>:specific==='diskstation'?<DiskStationSocket/>:specific==='synology'?<SynologySocket type={p.type}/>:specific==='fortinet'?<FortinetSocket/>:specific==='aruba'?<ArubaSocket type={p.type} ordinal={p.gn}/>:specific?<StarTechJack rear={face==='rear'}/>:<svg viewBox="0 0 40 40" aria-hidden="true"><IRPortShape type={p.type} role={p.rackclickPowerRole}/></svg>}<span>{specific?'':p.groupPrefix}{p.gn}</span><small>{p.label}</small></button>;
  }
  if(profile?.identity&&face==='rear')ownPorts.reverse();
  const dim=search&&!`${d.name} ${d.preset} ${JSON.stringify(d.notes||{})} ${d.ports.map(p=>p.label||'').join(' ')}`.toLowerCase().includes(search.toLowerCase());
  return <article key={d.id} data-devid={d.id} data-mounted-on={d.mountParentId||undefined} data-hardware-key={d.hardwareProfileKey||undefined} data-hardware-version={d.hardwareProfileVersion||undefined} className={'rc-mount-device '+(nested?'rc-mount-child ':'')+(selectedDevs.has(d.id)?'selected ':'')+(dim?'dim':'')} style={childStyle}>
   <header className="ir-device-head"><label><input type="checkbox" aria-label={w.select+' '+d.name} checked={selectedDevs.has(d.id)} disabled={!hardwareCanDelete||hardwareBlocked} onChange={()=>onSelect(d.id)}/></label><button className="ir-device-name" title={d.name} disabled={!hardwareCanEdit||hardwareBlocked} onClick={()=>onEdit(d)}><b>{d.name}</b></button><span data-device-reservation>{nested?'0 '+w.additional:d.u+' U'}</span><button type="button" aria-label={(lang==='es'?'Editar':lang==='de'?'Bearbeiten':'Edit')+' '+d.name} disabled={!hardwareCanEdit||hardwareBlocked} data-hardware-edit={d.id} onClick={()=>onEdit(d)}>✎</button><button type="button" aria-label={(lang==='es'?'Eliminar':lang==='de'?'Entfernen':'Delete')+' '+d.name} disabled={!hardwareCanDelete||hardwareBlocked} onClick={()=>onDelete(d.id)}>×</button></header>
   {parent&&<p className="rc-mount-caption rc-mounted-parent"><span>{w.mounted}</span> <span className="rc-parent-name" title={parent.name}>{parent.name}</span> <span>· {d.mountSlotKey}</span></p>}
   {!profile&&<p className="ir-warning" data-hardware-revision-unavailable role="status">{w.unavailable}</p>}
   {nested&&<button type="button" className="rc-mount-view-toggle" data-hardware-enlarge={d.id} aria-expanded={expanded} aria-controls={viewId+d.id} onClick={()=>setExpandedDevice(expanded?null:d.id)}>{zoomWords[expanded?1:0]}</button>}
   <div id={viewId+d.id} className={'rc-hardware-face rc-hardware-face-'+(profile?.kind||'legacy')+(shell?' rc-shell-specific':'')} data-shell-mode={shell?'specific':'generic'} data-commercial-hardware={profile?.identity?.model||undefined} data-hardware-face={face} role="group" aria-label={d.name+' · '+w[face]}>
    {shell?<HardwareShellFace layout={shell} renderPort={renderPort} words={w} label={d.name+' · '+w[face]+' · '+w.shellScroll}/>:profile?.kind==='shelf'?<div className="rc-shelf-floor" aria-hidden="true"><span>●</span><span>●</span><span>●</span><span>●</span></div>:<>
     <div className="rc-hardware-mark" aria-hidden="true">{profile?.kind==='desktop'?'◈':profile?.key==='switch-24'?'⇄':'▥'}</div>
     <div className="rc-hardware-ports">{ownPorts.map(p=>renderPort(p))}</div>
     {!ownPorts.length&&<span className="rc-muted">{w.empty}</span>}
    </>}
   </div>
   {identity&&!shell&&<p className="rc-mount-caption" data-shell-caption>{w.genericShell}</p>}
   {profile?.passthrough&&<p className="rc-mount-caption">{w.continuity}</p>}
   <details className="rc-model-details"><summary>{detailsWord}</summary><p className="rc-mount-caption" data-profile-revision>{d.hardwareProfileKey||d.preset} · {d.hardwareProfileVersion||w.unknownRevision}</p>{dimensions&&<p className="rc-mount-caption">{dimensions.width} × {dimensions.height} × {dimensions.depth} mm</p>}{parent&&<p className="rc-mount-caption">{w.mounted} {parent.name}</p>}{identity&&<p className="rc-mount-caption" data-commercial-identity>{identity.manufacturer} · {identity.model} · {w.modelIdentity}{face==='rear'&&profile?.rearLogicalNumbering?' '+w.rearLogical:''}</p>}</details>
   {(profile?.kind==='shelf'||children.length>0)&&<div className="rc-shelf-bay" data-mount-slot={children.some(child=>child.mountSlotKey==='shared')?'shared':'main'}><span className="rc-mount-caption">{profile?.kind==='shelf'?hardwareSlotLabel(profile,w):w.sharedLimit}</span>{children.map(child=>deviceView(child,true))}</div>}
  </article>;
 }
 return <section data-mounted-rack><p data-mount-occupancy>{w.used}: {used}/{rack.size} U · {w.free}: {rack.size-used} U</p><RackContainerAppearance rack={rack} face={face} words={w}/><small>{w.order}</small>
  <IntegratedPhysicalRack {...props} renderHardware={(d,start)=><section key={d.id} className="rc-mount-row"><div className="ir-units" data-root-u={d.id}>{Array.from({length:d.u},(_,i)=><span key={i}>{start+i}</span>)}</div>{deviceView(d)}</section>}/>
  <small>{w.limits}</small>
 </section>;
}
