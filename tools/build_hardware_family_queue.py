"""Reconcile a frozen family reconnaissance with current profile coverage.

Documentation only: no product, database, ledger, network or QA mutation.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION = 'evidence/s1-20261101/familias-catalogo/reconocimiento/CLASIFICACION-127.json'
COVERAGE = 'docs/COBERTURA-MODELOS-ELEGIDOS.json'
JSON_OUT = 'docs/FAMILIAS-CATALOGO-PENDIENTES.json'
MD_OUT = 'docs/FAMILIAS-CATALOGO-PENDIENTES.md'


def compile_queue(root):
    raw = {name: (root/name).read_bytes() for name in (CLASSIFICATION, COVERAGE)}
    classified = json.loads(raw[CLASSIFICATION])
    coverage = json.loads(raw[COVERAGE])
    members = [identifier for family in classified['families'] for identifier in family['members']]
    if len(members) != len(set(members)) or len(members) != classified['counts']['pending']:
        raise ValueError('family_members_invalid')
    current = {row['id']: row for row in coverage['rows']}
    pending = {row['id'] for row in coverage['rows'] if row['status'] != 'perfil_en_desarrollo'}
    if not pending <= set(members) or not set(members) <= set(current):
        raise ValueError('family_baseline_requires_new_explicit_classification')
    rows = []
    for family in classified['families']:
        remaining = [identifier for identifier in family['members'] if identifier in pending]
        covered = [identifier for identifier in family['members'] if identifier not in pending]
        rows.append(dict(familyId=family['familyId'], name=family['name'],
                         baselineMembers=family['members'], pendingIds=remaining,
                         nowCoveredIds=covered, pending=len(remaining), nowCovered=len(covered),
                         sharedRule=family['sharedRule'],
                         originalContractDependencies=family['contractDependencies'],
                         nextEvidence=family['minimumEvidence'],
                         originalReservation=family['reservationReason']))
    if sum(row['pending'] for row in rows) != coverage['counts']['selectedPending']:
        raise ValueError('family_current_count_invalid')
    report = dict(schemaVersion=1, kind='documentation_queue_not_product_completion',
                  asOf=coverage['asOf'], inputSha256={name: hashlib.sha256(data).hexdigest() for name, data in raw.items()},
                  counts=dict(reconnaissanceBaseline=len(members), families=len(rows),
                              selectedCovered=coverage['counts']['selectedWithProfile'],
                              selectedPending=len(pending),
                              coveredSinceReconnaissance=sum(row['nowCovered'] for row in rows)),
                  originalContractNotesAreHistorical=True, families=rows)
    title = '# Familias del catálogo: pendientes y próxima evidencia\n\n'
    text = (f"{coverage['asOf']}. Generado con `tools/build_hardware_family_queue.py`. "
            f"**{coverage['counts']['selectedWithProfile']}/506 cubiertos; {len(pending)} pendientes.** "
            'Son familias de reutilización, no pesos nuevos ni aceptación QA.\n\n'
            '[Procedimiento reutilizable](METODO-CATALOGO-POR-FAMILIAS.md) · '
            '[Plantilla](PLANTILLA-FAMILIA-CATALOGO.json) · '
            '[Detalle JSON](FAMILIAS-CATALOGO-PENDIENTES.json) · '
            '[Reconocimiento original de 127](../evidence/s1-20261101/familias-catalogo/reconocimiento/MAPA-FAMILIAS-127.md).\n\n'
            'El reconocimiento de origen permanece congelado. Las notas de contrato de esa fecha '
            'se conservan como antecedentes; la continuidad y el manual de la tanda que resolvió '
            'una configuración rigen su estado actual. Una configuración sobre bandeja no cierra '
            'montaje en techo, pared o mástil; una población curada no convierte un chasis base vacío '
            'en un paquete que incluya módulos de fábrica.\n\n'
            '| Familia física | Pendientes | Con perfil desde el reconocimiento |\n|---|---:|---:|\n')
    text += ''.join(f"| {row['familyId']} · {row['name']} | {row['pending']} | {row['nowCovered']} |\n" for row in rows)
    for row in rows:
        if not row['pending']:
            continue
        text += f"\n## {row['familyId']} · {row['name']}\n\n{row['sharedRule']}\n\n"
        text += '**Punto de partida del contrato/reserva:** '+row['originalReservation']+'\n\n'
        text += '**Evidencia necesaria para retomar:** '+'; '.join(row['nextEvidence'])+'.\n\n'
        text += '\n'.join(f"- `{identifier}` · {current[identifier]['manufacturer']} · {current[identifier]['model']}" for identifier in row['pendingIds'])+'\n'
    text += ('\nNo ejecutar instalaciones ni cambiar versiones desde esta lista. Cada futura familia '
             'necesita su plan, datos comprobados, pruebas y revisión independiente. No se modifica '
             'el ledger ni se calcula un nuevo porcentaje global.\n')
    return {JSON_OUT: (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf-8'),
            MD_OUT: (title+text).encode('utf-8')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = compile_queue(ROOT)
    for name, data in outputs.items():
        if args.write:
            (ROOT/name).write_bytes(data)
        elif not (ROOT/name).is_file() or (ROOT/name).read_bytes() != data:
            raise ValueError('family_queue_stale: '+name)
    report = json.loads(outputs[JSON_OUT])
    print(json.dumps(dict(result='written' if args.write else 'checked', **report['counts'],
                          writesLedgerOrProduct=False)))


if __name__ == '__main__':
    main()
