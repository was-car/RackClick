// Display scale only: never changes physical dimensions, port IDs or occupancy.
// Keep every connectable socket at least 24 CSS pixels. A face without sockets
// has no interaction-driven minimum and may shrink with its container.
export function socketFaceMinimum(viewWidth: number, sockets: readonly {w:number,h:number}[]): number {
 const sizes=sockets.flatMap(s=>[s.w,s.h]).filter(n=>Number.isFinite(n)&&n>0);
 return sizes.length&&Number.isFinite(viewWidth)&&viewWidth>0?Math.ceil(viewWidth*24/Math.min(...sizes)):0;
}
export function specializedFaceMinimum(layout: any): number {
 if(!layout.ports?.length)return 0;
 const family=layout.family, rear=layout.face==='rear';
 if(family==='aruba1930')return socketFaceMinimum(1280,[{w:rear?51:32,h:rear?52:32}]);
 if(family==='fortigate60f')return socketFaceMinimum(1000,[{w:50,h:50}]);
 if(family==='synology-rs1221plus')return socketFaceMinimum(1280,layout.ports.map((p:any)=>p.type==='power'?{w:176,h:99}:{w:39,h:39}));
 if(family==='diskstation-ds423plus')return socketFaceMinimum(320,[{w:18,h:23}]);
 if(family==='qnap-ts464')return socketFaceMinimum(320,[{w:24,h:28}]);
 return socketFaceMinimum(1088,[{w:32,h:32}]);
}
export function mountedDeviceWidthStyle(width: unknown, usableWidth: unknown) {
 if(typeof width==='number'&&typeof usableWidth==='number'&&Number.isFinite(width)&&Number.isFinite(usableWidth)&&width>0&&usableWidth>0&&width<=usableWidth)
  // On narrow screens a literal millimetre ratio can leave only 78px for the
  // name and controls. Keep a readable panel floor, bounded by available space;
  // this is display magnification, never a change to mounting/fit data.
  return {maxWidth:'100%',minWidth:'min(100%, 220px)',width:(100*width/usableWidth)+'%'};
 // An unavailable revision is not permission to invent its physical size.
 return {maxWidth:'100%',width:'min(100%, 550px)'};
}
