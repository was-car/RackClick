"""Enable QA78 and append the exact849 pair only after selected real QA validation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-850-909'


def main():
    output = E / 'QA-MATRIX-909.json'
    assert not output.exists()
    selected = json.loads((E / 'REAL-QA-ACTIVATE-01.json').read_bytes())
    validated = json.loads((E / 'REAL-QA-VALIDATE-01.json').read_bytes())
    assert selected['valid'] and selected['state'] == 'committed' and selected['selectedRevision'] == 849
    assert validated['valid'] and validated['selectedRevision'] == 849
    target = json.loads((ROOT / 'evidence/s1-20261018/tanda-849/CANDIDATA849.json').read_bytes())
    old = json.loads((ROOT / 'evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json').read_bytes())
    pair = dict(bundle=target['distributions']['frontend']['app.js'], dll=target['distributions']['server']['RackClick.Server.dll'])
    source = dict(bundle=old['distributions']['frontend']['app.js'], dll=old['distributions']['server']['RackClick.Server.dll'])
    pointer = json.loads((ROOT / '.local/qa-rc9/current.json').read_bytes())
    assert Path(pointer['directory']).resolve() == (ROOT / selected['candidateDirectory']).resolve()
    cfg = json.loads((Path(pointer['directory']) / 'manual-qa.json').read_bytes())
    assert cfg['bundleSha256'] == pair['bundle'] and cfg['dllSha256'] == pair['dll']
    path = ROOT / 'docs/QA-CASOS-WASCAR.json'
    before = path.read_bytes()
    catalog = json.loads(before)
    original = json.loads(before)
    inherited = []
    for key, items in catalog.items():
        if key.endswith('Builds') and isinstance(items, list) and source in items and pair not in items:
            assert all(isinstance(x, dict) and set(x) == {'bundle', 'dll'} for x in items)
            items.append(pair)
            inherited.append(key)
    assert 'adminGroupRelationsAnnouncementBuilds' not in catalog
    catalog['adminGroupRelationsAnnouncementBuilds'] = [pair]
    case = catalog['cases'][77]
    assert case['id'] == 'QA-78' and case['feature'] == 'planned'
    case['feature'] = 'adminGroupRelationsAnnouncementGui'
    case['steps'][0] = 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Ejecuta INICIAR-QA-RESTAURADO.cmd y usa su guía y ACCESO-PRIVADO.txt; elige Español y pulsa Ctrl+F5. La candidata849 ya está seleccionada. La comprobación de voz necesita tu lector de pantalla habitual: si no dispones de uno, anota la variante no realizada y marca Bloqueado. Tus resultados y observaciones anteriores se conservan.'
    assert len(catalog['cases']) == 78 and catalog['cases'][:77] == original['cases'][:77]
    assert case == {**original['cases'][77], 'feature': case['feature'], 'steps': [case['steps'][0]] + original['cases'][77]['steps'][1:]}
    catalog['revision'] = '2026-10-18-grupo850-909'
    newline = '\r\n' if b'\r\n' in before else '\n'
    path.write_bytes((json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').replace('\n', newline).encode())
    row = dict(pair=pair, sourcePair=source, inheritedBuildLists=inherited, caseCount=78,
               unchangedCompleteCases=77, changedCases=['QA-78'],
               changedFields=['feature', 'steps[0]'], otherStepsAndExpectedUnchanged=True,
               beforeCatalogSha256=hashlib.sha256(before).hexdigest(),
               afterCatalogSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               manualWascarResultsWritten=False, qaDatabaseDml=False)
    output.write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=78, inheritedLists=len(inherited), newlyAvailable='QA-78', manualWascarResultsWritten=False)))


if __name__ == '__main__':
    main()
