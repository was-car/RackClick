// Search terms are presentation only. Creation still requires an exact key/revision.
export function hardwareSearchText(value: unknown): string {
 return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('en').replace(/\bfritz[!\s.-]*box\b/g,'fritzbox').replace(/\bfritz[!\s.-]*repeater\b/g,'fritzrepeater').trim();
}
const aliases: Record<string,string> = {sofos:'sophos',drytek:'draytek',avm:'fritz',repeter:'repeater',repetidor:'repeater',repetidores:'repeater',repeteur:'repeater',verstarker:'repeater','wlan-verstarker':'repeater'};
export function searchHardwareProfiles(profiles: readonly any[], query: string): any[] {
 const terms=hardwareSearchText(query).split(/\s+/).filter(Boolean).map(term=>aliases[term]||term);
 return profiles.filter(profile=>{
  const id=profile.identity;
  const text=hardwareSearchText([id?.manufacturer,id?.family,id?.model,id?.sku,profile.key,profile.revision].join(' '));
  return terms.every(term=>text.includes(term));
 });
}
