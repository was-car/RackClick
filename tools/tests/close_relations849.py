"""Close one full-application check without selecting or changing real QA."""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ER = 'evidence/s1-20261018/tanda-849'
E = ROOT / ER


def read(name):
    return json.loads((E / name).read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    with (E / name).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def prepend(name, text):
    p = ROOT / name
    before = p.read_bytes()
    assert b'Tanda849' not in before[:2000]
    first, sep, rest = before.partition(b'\n')
    nl = b'\r\n' if first.endswith(b'\r') else b'\n'
    p.write_bytes(first + sep + nl + text.encode().replace(b'\n', nl) + nl + nl + rest)


def main():
    assert not (E / 'CIERRE.md').exists()
    fixture = read('pg-browser02/fixture.json')
    assert fixture['result'] == 'PASS' and fixture['readOnlyGroupsUnchanged']
    assert fixture['labStopped'] and fixture['serversStopped'] and fixture['inputsUnchanged']
    browser = read('pg-browser02/browser.json')
    assert len(browser['selectionAccessibility']) == 10 and not browser['errors']
    assert all(x['role'] == 'status' and x['live'] == 'polite' and x['atomic']
               and not x['ignored'] for x in browser['selectionAccessibility'])
    manifest = read('CANDIDATA849.json')
    assert manifest['fileCount'] == 38 and manifest['totalBytes'] == 7108622
    # Update only the existing, still-blocked QA78 introduction; preserve its other steps.
    p = ROOT / 'docs/QA-CASOS-WASCAR.json'
    before = p.read_bytes()
    catalog = json.loads(before)
    old = json.loads(before)
    assert len(catalog['cases']) == 78
    case = catalog['cases'][77]
    assert case['id'] == 'QA-78' and case['feature'] == 'planned'
    case['steps'][0] = 'NO DISPONIBLE en QA832 actual. La corrección848 ya está compilada en la candidata849 y comprobada dentro de la aplicación completa con PostgreSQL real. Sigue pendiente seleccionar esa candidata en el laboratorio de QA. Espera a que la cabecera marque DISPONIBLE EN TU SNAPSHOT; mientras tanto, marca Bloqueado y conserva tus resultados anteriores.'
    catalog['revision'] = '2026-10-18-tanda849'
    assert catalog['cases'][:77] == old['cases'][:77]
    assert case['steps'][1:] == old['cases'][77]['steps'][1:]
    nl = '\r\n' if b'\r\n' in before else '\n'
    p.write_bytes((json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').replace('\n', nl).encode())
    spec = importlib.util.spec_from_file_location('guide849', ROOT / 'tools/windows/qa_guide.py')
    guide = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guide)
    assert all(guide.generate(profile=p) for p in ['manual', 'rc9'])
    spec = importlib.util.spec_from_file_location('guide848tests', ROOT / 'tools/tests/test_qa_relations_status848.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with (E / 'GUIA-PRUEBAS.log').open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    save('GUIA-PRUEBAS.json', dict(testsRun=result.testsRun, successful=result.wasSuccessful(),
         failures=len(result.failures), errors=len(result.errors), previous77CasesUnchanged=True,
         caseCount=78, availableRestored=77, availableOriginal=8, qa78Available=False,
         manualWascarResultsWritten=False))
    assert result.wasSuccessful()
    summary = '''**Tanda849 · 18.10.2026: ajuste848 compilado y probado en la aplicación completa; global 78 % aproximado, sin aumento.** Frontend completo compilado una vez y unido al servidor832 exacto, sin recompilar C# ni cambiar SQL/dependencias/CSS. Candidata849 congelada: 38 archivos, sólo app.js difiere de832. Edge/PostgreSQL17.11 en laboratorio nuevo verificó estado accesible por nodo exacto, UUID/homónimos, EN/DE/ES, teclado/390px, borrador conservado y limpieza tras403 real. Comparación de lectura: ocho tablas de grupos, no35. Un primer fallo del arnés por serializar un nodo React queda conservado; corregido sin reconstruir la candidata, segunda ejecución PASS22,578s. Revisión independiente separada de ejecución.

QA832 y ZIP847 conservados. QA-78 sigue pendiente de selección en el laboratorio y de voz con lector de pantalla; catálogo78 con77 disponibles restaurado/8original, sólo su introducción actualizada, tres pruebas focales de guía correctas. No resultados de Wascar modificados. Siguiente: integrar candidata849 en Windows/QA con verificación antes de habilitar QA-78. [Evidencias y límites](../evidence/s1-20261018/tanda-849/CIERRE.md). Registros siguientes históricos.'''
    for path in ['docs/CONTINUIDAD-CODEX.md', 'docs/INICIO-IMPLEMENTACION-S1.md',
                 'docs/PROGRESO-GLOBAL.md', 'docs/ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md']:
        prepend(path, summary)
    prepend('development/frontend/README.md', summary.replace('](../evidence/', '](../../evidence/'))
    prepend('CHANGELOG.md', '''## 18.10.2026 · Tanda849 · Comprobación completa del aviso accesible

- Frontend completo compilado una vez; servidor832 y sus SQL/dependencias exactos. Candidata849 separada de38archivos; sólo cambia app.js.
- Edge/PG17.11 nuevo:10comprobaciones DOM/AX en un recorrido compuesto con grupos reales, idiomas/teclado/390px/borrador/403; ocho tablas de grupos conservadas antes de revocación del fixture. Procesos app/PG detenidos, inputs intactos.
- Intento01 de arnés fallido conservado; dos expresiones CDP corregidas y segundo intento PASS sin nuevo build. QA-78 sigue bloqueado, QA832/ZIP847 conservados; tres pruebas focales de guía correctas. Global78 aproximado. [Informe](evidence/s1-20261018/tanda-849/CIERRE.md).''')
    p = ROOT / 'docs/MAPA-ENTREGA.json'
    m = json.loads(p.read_bytes())
    assert m['progress'] == 78
    m.update(revision='2026-10-18-tanda849', snapshot='Tanda849: candidata completa probada con Edge/PostgreSQL; QA832 conservado, QA78 pendiente de selección y voz. Global78 aproximado.', currentBatch=dict(count=1, completed=1, ledger=ER + '/CIERRE.md', evidence=ER + '/CIERRE.md'))
    m['history'].append(dict(id='h849', name='849 · Ajuste accesible en aplicación completa', status='Candidata probada · QA pendiente', note='Un buildfrontend, servidor832 exacto; PG/Edge/AX/390px/teclado/403 correctos. Sin voz/selecciónQA/paquete nuevo;78sin aumento.'))
    p.write_bytes((json.dumps(m, ensure_ascii=False, indent=2) + '\n').encode())
    (E / 'CIERRE.md').write_text('''# Tanda849 · Aviso accesible en la aplicación completa

La corrección848 ya forma parte de una compilación completa de la GUI, candidata849. Se verificó con Edge y PostgreSQL17.11 real en un laboratorio nuevo. No se seleccionó en QA832 ni se produjo otro ZIP Windows; QA-78 permanece bloqueado hasta esa integración. Global **78 % aproximado**, sin aumento por una comprobación aislada.

## Construcción y distribuciones

BaseGit834cc776c98f4a8c08d6db40b75480a709373dc2. `tools/tests/build_relations849.py` ejecuta un único buildfrontend con Node24.21.0 y dependencias ya fijadas, sin descargas. Verifica175fuentes frente a832: sólo AdminGroupRelations.jsx difiere y coincide con la fuente7f0d…8b9f revisada en848. Se copian los20archivos del servidor832, SQL001–011 y todas sus dependencias byte a byte. De18frontend sólo app.js cambia; CSS, fuentes, React y licencias conservados. Build0,484s, sin publicar/recompilar C#.

CANDIDATA849.json: esquema11,38archivos,7.108.622bytes, SHA256 `1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`. Distribución nueva bajo .local/candidates, con hashes individuales y175fuentes congeladas. No se incorpora aún a los perfiles cerrados Windows.

## Pruebas y corrección del arnés

Se amplió el mismo escenario existente `browser-admin-group-relations.mjs`/`test_admin_group_relations_gui.py`. Una prueba compuesta, no diez suites: diez observaciones del nodo status exacto en el árbol accesible, selección inicial/homónimos/tipo, EN/DE/ES y retirada tras403. La aplicación completa tiene otras regiones status; se usa backendDOMNodeId. Persiste el nodo, texto literal con UUID reales y polite/atomic; el artículo no anuncia listas completas. Se comprueban 390px sin desbordamiento, Tab entre selectores, borrador/usuario conservados y cero escrituras administrativas HTTP al navegar.

El fixture SQL revoca seguridad de su administrador sintético; el servidor devuelve403 y al actualizar retira relaciones/aviso anteriores. Se comparan ocho tablas de grupos antes de esa revocación, no toda la base35tablas. Credenciales y logs de servidor quedan privados bajo .local. No se utiliza el laboratorio de Wascar.

Intento01: FAIL17,812s, «Object reference chain is too long», debido al nuevo Runtime.evaluate del arnés que intentó serializar un nodo DOM con referencias React. Guion exacto y resultado fallido conservados. Se añadieron dos `;true` para devolver un booleano y mantener el nodo en window; no se cambió ni recompiló el producto. Intento02: PASS22,578s, inputs intactos y app/PG propios detenidos. Ambos intentos usan clusters/bases nuevos y conservan sus evidencias separadas. INCIDENCIA-01.md explica la causa.

Comando de reproducción desde C:\\RackClick_SVR; pasar rutas serverDll/frontend del manifiesto y un output NUEVO:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_admin_group_relations_gui.py --output <directorio-nuevo> --dll <serverDll> --frontend <frontend>
```

Capturas reales EN/DE/ES390 y browser.json/fixture.json en pg-browser02. Coordinador inspeccionó capturaES: ficha y texto literal legibles, el aviso recortado no añade bloques visibles. No es una revisión visual completa de RC9. La revisión independiente especifica qué archivos/capturas/controles leyó y no se atribuye nuestras ejecuciones. No se repite la suite nativa por inercia en revisión.

## QA y continuidad

Catálogo78casos: primeros77exactos, sólo introducciónQA-78 actualizada para candidata849 ya probada pero pendiente de selección. Las otras instrucciones y expected deQA-78 se conservan. Sigue `planned`:77disponibles restaurado/8original. Ambas guías regeneradas; tres tests focales de848 PASS, sin repetir las40 ya ejecutadas allí. No notas/resultados de Wascar leídos ni sobrescritos; no voz de lector de pantalla probada.

Siguiente: integración Windows/QA conservadora con revisión y verificación antes de habilitarQA-78; después voz real por Wascar. Persisten funciones RC9/Dosen/undo/admin, operación Windows completa, recuperación/manual y QA/adopción final. No se certifican Windows limpio, instalación/recuperación de849, todos35datos, accesibilidad universal ni voz AT. El paquete847 y candidato/QA832 se conservan. La nueva evidencia se sella con diff/SHA256SUMS y commit sólo local.
''', encoding='utf-8')
    print(json.dumps(dict(completed=1, progress=78, candidate=849, selectedQa=832,
                         newQaAvailable=False, guideTests=result.testsRun)))


if __name__ == '__main__':
    main()
