// Offline worksheet. No requests, credentials, application access or adoption.
export const FORMAT = 'RackClick-QA-Candidate-v1';
export const RESULTS = ['Sin probar', 'Pass', 'Not Pass', 'Bloqueado'];
export function exactKeys(value, wanted) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === [...wanted].sort().join(',');
}
export function validOrigin(value) {
  if (value === '') return true;
  try {
    const u = new URL(value);
    return value.length <= 300 && /^https:\/\/[^/?#]+\/?$/.test(value) && u.protocol === 'https:' && !!u.hostname
      && !u.username && !u.password && !u.search && !u.hash && u.pathname === '/'
      && (!u.port || (Number(u.port) >= 1 && Number(u.port) <= 65535))
      && !/[\u0000-\u0020\u007f]/u.test(value);
  } catch { return false; }
}
export function validateReport(data, spec) {
  if (!exactKeys(data, ['format', 'candidate', 'environment', 'records']) || data.format !== FORMAT
      || !exactKeys(data.candidate, ['edition', 'schema', 'archiveSha256'])
      || data.candidate.edition !== spec.candidate.edition
      || data.candidate.schema !== spec.candidate.schema
      || data.candidate.archiveSha256 !== spec.candidate.archiveSha256) throw Error('candidate_mismatch');
  if (!exactKeys(data.environment, ['origin', 'candidateConfirmed'])
      || typeof data.environment.origin !== 'string' || !validOrigin(data.environment.origin)
      || typeof data.environment.candidateConfirmed !== 'boolean'
      || (data.environment.candidateConfirmed && data.environment.origin === '')) throw Error('environment_invalid');
  if (data.records === null || typeof data.records !== 'object' || Array.isArray(data.records)
      || Object.keys(data.records).length > spec.cases.length) throw Error('records_invalid');
  const ids = new Set(spec.cases.map(row => row.id));
  for (const [id, row] of Object.entries(data.records)) {
    if (!ids.has(id) || !exactKeys(row, ['result', 'notes', 'caseSha256', 'updatedUtc'])
        || !RESULTS.includes(row.result) || typeof row.notes !== 'string' || row.notes.length > 20000
        || typeof row.caseSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(row.caseSha256)
        || typeof row.updatedUtc !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?Z$/.test(row.updatedUtc)
        || !Number.isFinite(Date.parse(row.updatedUtc)) || Number(row.updatedUtc.slice(0,4)) < 1
        || new Date(row.updatedUtc).toISOString().slice(0,19) !== row.updatedUtc.slice(0,19)) throw Error('record_invalid');
  }
  return data;
}
export function summarize(data, spec) {
  validateReport(data, spec);
  const counts = {'Sin probar': 0, Pass: 0, 'Not Pass': 0, Bloqueado: 0, Desactualizado: 0};
  for (const item of spec.cases) {
    const row = data.records[item.id];
    if (!row) counts['Sin probar']++;
    else if (row.caseSha256 !== item.caseSha256) counts.Desactualizado++;
    else counts[row.result]++;
  }
  return {counts, selectedCases: spec.cases.length,
    manualChecklistComplete: data.environment.candidateConfirmed && counts.Pass === spec.cases.length,
    adoption: false, productionReady: false, source: 'operator_self_report_not_machine_verification'};
}
if (typeof document !== 'undefined') {
  const spec = JSON.parse(document.getElementById('qa-spec').textContent);
  const key = 'rackclick.qa.candidate11.' + spec.candidate.archiveSha256;
  const fresh = () => ({format: FORMAT, candidate: {...spec.candidate},
    environment: {origin: '', candidateConfirmed: false}, records: {}});
  let data = fresh(), storageWritable = true;
  const notice = document.getElementById('notice'), summary = document.getElementById('summary');
  try {
    const raw = localStorage.getItem(key);
    if (raw) data = validateReport(JSON.parse(raw), spec);
  } catch {
    storageWritable = false;
    notice.textContent = 'No se pudo recuperar el guardado. Se conserva sin sobrescribirlo. Exporta JSON antes de cerrar.';
  }
  function save() {
    if (storageWritable) try { localStorage.setItem(key, JSON.stringify(data)); }
    catch { storageWritable = false; }
    notice.textContent = storageWritable
      ? 'Guardado en este navegador. Exporta una copia al terminar; el HTML no recibe tus notas.'
      : 'Guardado local no disponible: exporta JSON antes de cerrar. Las notas anteriores no se sobrescribieron.';
    paintSummary();
  }
  function paintSummary() {
    const s = summarize(data, spec);
    summary.textContent = s.counts.Pass + '/' + s.selectedCases + ' Pass · ' + s.counts['Not Pass']
      + ' Not Pass · ' + s.counts.Bloqueado + ' bloqueados · ' + s.counts.Desactualizado
      + ' desactualizados. Es tu lista manual, no el porcentaje global ni la aceptación del producto.';
    document.querySelectorAll('[data-case]').forEach(el => {
      const row = data.records[el.dataset.case], item = spec.cases.find(c => c.id === el.dataset.case);
      el.querySelector('[data-badge]').textContent = row && row.caseSha256 !== item.caseSha256
        ? 'Desactualizado: conserva tus notas y repite el caso' : (row?.result || 'Sin probar');
    });
  }
  function paint() {
    document.getElementById('origin').value = data.environment.origin;
    document.getElementById('confirmed').checked = data.environment.candidateConfirmed;
    document.querySelectorAll('[data-case]').forEach(el => {
      const row = data.records[el.dataset.case];
      const item = spec.cases.find(c => c.id === el.dataset.case);
      el.querySelector('[data-result]').value = row && row.caseSha256 === item.caseSha256 ? row.result : 'Sin probar';
      el.querySelector('[data-notes]').value = row?.notes || '';
    });
    paintSummary();
  }
  for (const id of ['origin', 'confirmed']) document.getElementById(id).addEventListener('change', () => {
    const env = {origin: document.getElementById('origin').value.trim(), candidateConfirmed: document.getElementById('confirmed').checked};
    try {
      validateReport({...data, environment: env}, spec); data.environment = env; save();
    } catch { notice.textContent = 'Usa URL HTTPS sin credenciales, ruta o parámetros. Para confirmar la edición indica su URL.'; paint(); }
  });
  document.querySelectorAll('[data-case]').forEach(el => {
    for (const selector of ['[data-result]', '[data-notes]']) el.querySelector(selector).addEventListener('change', () => {
      const item = spec.cases.find(c => c.id === el.dataset.case);
      const prior = data.records[item.id], staleNotesOnly = selector === '[data-notes]' && prior && prior.caseSha256 !== item.caseSha256;
      data.records[item.id] = {result: staleNotesOnly ? prior.result : el.querySelector('[data-result]').value,
        notes: el.querySelector('[data-notes]').value,
        caseSha256: staleNotesOnly ? prior.caseSha256 : item.caseSha256, updatedUtc: new Date().toISOString()};
      save();
    });
  });
  document.getElementById('export').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob);
    link.download = 'Resultados-QA-RackClick-11-' + new Date().toISOString().slice(0, 10) + '.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  });
  document.getElementById('import').addEventListener('change', async e => {
    try {
      const file = e.target.files[0]; if (!file) return;
      if (file.size > 2000000) throw Error('size');
      const imported = validateReport(JSON.parse(await file.text()), spec);
      if (!confirm('¿Importar esta copia11? Sólo se reemplazan los casos incluidos; los demás se conservan.')) return;
      data = {...imported, records: {...data.records, ...imported.records}}; save(); paint();
    } catch { notice.textContent = 'Copia rechazada: formato, versión o datos incorrectos. Tus notas actuales se conservaron.'; }
    finally { e.target.value = ''; }
  });
  paint();
}
