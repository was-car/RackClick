// RC9 irPoeEnabled/irPoeStats: connectivity status does not turn documented PoE off.
export function poeEnabled(port: { type: string; poe?: boolean | null }) {
 return ['rj45', 'rj45_poe'].includes(port.type) && (port.poe === true || port.type === 'rj45_poe' && port.poe !== false);
}
// Exact arithmetic on the decimals represented by the JSON Numbers, including e notation.
// Precision already lost by parsing JSON cannot be recovered here.
function decimal(value: number) {
 const [mantissa, exponent = '0'] = value.toString().split('e'), dot = mantissa.indexOf('.');
 return { coefficient: BigInt(mantissa.replace('.', '')), exponent: Number(exponent) - (dot < 0 ? 0 : mantissa.length - dot - 1) };
}
export function poeBudget(device: { poeBudget?: number | null }, ports: { type: string; poe?: boolean | null; watts?: number | null }[]) {
 const eligible = ports.filter(poeEnabled), known = eligible.filter(p => typeof p.watts === 'number' && Number.isFinite(p.watts) && p.watts >= 0);
 const unknown = eligible.length - known.length;
 const budget = typeof device.poeBudget === 'number' && Number.isFinite(device.poeBudget) && device.poeBudget >= 0 ? device.poeBudget : null;
 const values = known.map(p => decimal(p.watts!)), limit = budget === null ? null : decimal(budget);
 let exponent = limit?.exponent ?? 0;
 for (const value of values) exponent = Math.min(exponent, value.exponent);
 const scaled = (value: { coefficient: bigint; exponent: number }) => value.coefficient * 10n ** BigInt(value.exponent - exponent);
 const total = values.reduce((sum, value) => sum + scaled(value), 0n);
 // Parse once after summing, never round the comparison or multiply a Number by a huge power.
 const sum = Number(`${total}e${exponent}`), exceeded = limit !== null && total > scaled(limit);
 return { sum, unknown, eligible: eligible.length, budget, exceeded, incomplete: unknown > 0 || budget === null };
}
