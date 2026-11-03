// Own schematic mouths with distinct physical identities. No speed/breakout inference.
export function OpticalConnectorShape({type,inline=false}){
 if(!['sfp56','qsfpdd'].includes(type))return null;
 const wide=type==='qsfpdd',drawing=wide?<><rect x="1" y="7" width="62" height="28" rx="2" fill="#b7c1c9" stroke="#596b78"/><rect x="5" y="10" width="54" height="21" fill="#101923"/><path d="M8 30h48M18 32v5h28v-5" fill="none" stroke="#8d9da8"/><text x="32" y="24" textAnchor="middle" fontSize="9" fill="#fed7aa">DD</text></>:<><rect x="2" y="5" width="36" height="30" fill="#b7c1c9" stroke="#596b78"/><rect x="5" y="8" width="30" height="24" fill="#101923"/><path d="M8 31h24" stroke="#8d9da8"/><text x="20" y="23" textAnchor="middle" fontSize="9" fill="#a5f3fc">56</text></>;
 const identity={'data-hardware-connector':type,'data-physical-media':type,'aria-hidden':true};
 return inline?<g {...identity} transform={wide?'scale(0.625 1)':undefined}>{drawing}</g>:<svg {...identity} viewBox={wide?'0 0 64 40':'0 0 40 40'}>{drawing}</svg>;
}
