// Display only. Recorded dimensions and mounting remain authoritative in DB.
export function repeaterRoomWidth(width: unknown): number {
 return typeof width==='number'&&Number.isFinite(width)&&width>0?Math.max(180,Math.min(340,width*2)):280;
}
