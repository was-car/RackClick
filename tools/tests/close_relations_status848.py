"""Record source-only accessibility work, preserving selected QA and old evidence."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ER = 'evidence/s1-20261018/tanda-848'
E = ROOT / ER


def read(name):
    return json.loads((E / name).read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepend(name, text):
    path = ROOT / name
    data = path.read_bytes()
    assert b'Tanda848' not in data[:2500]
    first, sep, rest = data.partition(b'\n')
    nl = b'\r\n' if first.endswith(b'\r') else b'\n'
    path.write_bytes(first + sep + nl + text.encode().replace(b'\n', nl) + nl + nl + rest)


def main():
    assert not (E / 'CIERRE.md').exists()
    start = read('INICIO.json')
    assert not read('baseline01/result.json')['successful']
    final = read('final01/result.json')
    assert final['successful'] and final['ownedEdgeStopped'] and final['sourceUnchanged']
    assert read('GUIA-PRUEBAS.json')['successful']
    allowed = {'development/frontend/src/AdminGroupRelations.jsx', 'docs/QA-CASOS-WASCAR.json'}
    assert all(sha(ROOT / p) == h for p, h in start['guards'].items() if p not in allowed)
    git = str(ROOT / '.local/git-2.55.0.5/cmd/git.exe')
    assert subprocess.check_output([git, 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == start['baseCommit']
    summary = '''**Tanda848 · 18.10.2026: aviso accesible de relaciones de grupos corregido en fuentes; global 78 % aproximado, sin aumento.** La selección dispone de una región de estado persistente y compacta; cambiar tipo o perder datos limpia el aviso anterior. Conserva EN/DE/ES, nombres literales, diseño y autorización. Reproducción del defecto y prueba del componente en Edge/Windows correctas; 40 pruebas de guía correctas. No se probó voz de lector de pantalla, PostgreSQL ni aplicación completa en esta tanda.

El QA restaurado sigue en832 y el paquete847 se conserva. Catálogo: 78 casos, 77 disponibles en restaurado y 8 en original. QA-78 queda **pendiente/no disponible** hasta integrar y revisar la corrección en el laboratorio; los 77 guiones anteriores y las observaciones de Wascar no cambian. [Alcance y siguiente paso](ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md), [evidencias](../evidence/s1-20261018/tanda-848/CIERRE.md). Registros siguientes históricos.'''
    prepend('docs/CONTINUIDAD-CODEX.md', summary)
    prepend('docs/PROGRESO-GLOBAL.md', summary)
    prepend('docs/GUI-RELACIONES-GRUPOS-S1.md', summary)
    prepend('development/frontend/README.md', summary.replace('](ACCESIBILIDAD-', '](../../docs/ACCESIBILIDAD-').replace('](../evidence/', '](../../evidence/'))
    prepend('CHANGELOG.md', '''## 18.10.2026 · Tanda848 · Aviso accesible al seleccionar un grupo

- Región de estado persistente, compacta y recortada visualmente; ya existe antes de la primera selección. Retirado el anuncio de listas completas y el estado duplicado al faltar datos.
- Reproducción del fallo anterior y prueba Edge del componente con cambios de tipo, datos ausentes, Unicode y EN/DE/ES; guías 40/40 correctas. QA-78 documentado como pendiente, sin modificar los 77 casos anteriores ni resultados de Wascar.
- Fuentes de desarrollo únicamente; QA832 y ZIP847 conservados. Global 78 % aproximado. [Resultado y límites](evidence/s1-20261018/tanda-848/CIERRE.md).''')
    path = ROOT / 'docs/MAPA-ENTREGA.json'
    m = json.loads(path.read_bytes())
    assert m['progress'] == 78
    m.update(revision='2026-10-18-tanda848', snapshot='Tanda848: aviso accesible de grupos corregido en fuentes; QA832 conservado. 78 casos/77+8 disponibles; QA-78 pendiente. Global78 estimado.',
             currentBatch=dict(count=1, completed=1, ledger=ER + '/CIERRE.md', evidence=ER + '/CIERRE.md'))
    m['history'].append(dict(id='h848', name='848 · Aviso accesible al seleccionar un grupo', status='Fuentes probadas · QA pendiente', note='Región persistente y compacta; Edge del componente y guías verificados. Sin voz de lector, despliegue ni aumento del78%.'))
    path.write_bytes((json.dumps(m, ensure_ascii=False, indent=2) + '\n').encode())
    (ROOT / 'docs/ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md').write_text('''# Aviso accesible en relaciones de grupos

La tanda848 corrige una región de anuncio que se montaba junto con el artículo seleccionado. Ahora una región `role="status"`, polite y atómica, permanece desde el primer render. Su texto indica el grupo actual, la necesidad de elegirlo o la ausencia de datos. Los detalles de miembros y permisos conservan su contenido y dejan de ser una región viva completa. El texto recortado visualmente reutiliza los rótulos EN/DE/ES existentes; no añade controles, CSS ni decisiones de autorización.

La comprobación monta el componente real con React y props sintéticas en un Edge aislado. Verifica identidad del mismo nodo, cambios A→B y tipo usuario→cliente, snapshot ausente, grupo retirado, nombres Unicode/HTML literales y árbol accesible polite/atomic. Es una prueba del componente; no acredita pronunciación de Narrador/NVDA, certificación de accesibilidad, recorrido completo de aplicación o persistencia PostgreSQL.

QA-78 contiene ubicaciones y pasos detallados para Wascar, pero está marcado `planned`: el laboratorio sigue en832. Integrar en una futura candidata con revisión y pruebas antes de habilitarlo mediante un par cerrado GUI/DLL. QA-34 y los otros 76 casos conservan sus definiciones. No se sobrescriben observaciones, resultados ni paquetes anteriores.

Siguiente: integración futura del ajuste y comprobación manual con lector; continúan formatos/herramientas, Dosen/undo/admin, operación Windows completa y QA/adopción final. Global78 aproximado, sin puntos por una corrección aislada. [Evidencia y reproducción](../evidence/s1-20261018/tanda-848/CIERRE.md).
''', encoding='utf-8')
    (E / 'CIERRE.md').write_text('''# Tanda848 · Aviso accesible al elegir un grupo

La corrección mantiene una región de estado antes de la primera selección, anuncia sólo nombre/ID actuales y limpia el estado al cambiar tipo o faltar datos. El diseño, textos EN/DE/ES, permisos y datos compartidos se conservan. Implementador: coordinador; revisión independiente separada bajo revision/.

Windows11, Node24.21.0, Edge155.0.4283.62. El defecto anterior se reprodujo en baseline01: fallo esperado «Live status must exist BEFORE first selection», fuente intacta. Tras corregir AdminGroupRelations.jsx, final01 pasó los cuatro focos del componente. Ambos procesos Edge propios finalizaron. El árbol accesible expone un status polite/atomic; no se ejecutó voz de lector de pantalla.

Comandos desde C:\\RackClick_SVR (cada --output exige directorio nuevo):

```powershell
.local/node-v24.21.0-win-x64/node.exe development/frontend/tests/admin-relations-status848.mjs --output evidence/s1-20261018/tanda-848/final01
C:/Python312/python.exe -X utf8 -B tools/windows/qa_guide.py
C:/Python312/python.exe -X utf8 -B tools/windows/qa_guide.py --profile rc9
C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_qa_guide tools.tests.test_rc9_excel_guide832 tools.tests.test_qa_relations_status848
```

Guías: 40/40 PASS, registro GUIA-PRUEBAS.json/log. Catálogo78, disponibles77restaurado/8original; QA-78 planificado y bloqueado incluso con identidades futuras arbitrarias. Los primeros77casos son exactamente los de Git60684dd; sus resultados/observaciones no se han leído ni sobrescrito. Dos tests históricos se adaptan sólo al apéndice78; mantienen los negativos y baseline previos. Se conservan CRLF del catálogo y el componente.

El navegador de pruebas usa sólo React verificado y props sintéticas, sin API ni base de datos. Esbuild compila un bundle del componente, no la aplicación completa; no se publican ni seleccionan nuevos artefactos. QA832, cuentas, contraseñas, punteros y ZIP847 permanecen conservados. El primer comando de preparación apuntó por error a global.json en raíz y se detuvo sin editar; INICIO.json registra la ruta correcta y esa incidencia, que no fue una prueba de producto.

Avance global **78 % aproximado, sin aumento**. Esta tanda es una corrección de accesibilidad en fuentes. Faltan integración posterior, voz de lector, funciones RC9 restantes, Dosen/undo/admin y operación Windows/manual/QA/adopción final. La revisión documenta lo que ejecutó realmente; se conserva baseline fallido y evidencia nueva por separado. Diff y SHA256SUMS nuevos se sellan después de esa revisión; commit local, sin publicación.
''', encoding='utf-8')
    print(json.dumps(dict(progress=78,completed=1,sourceOnly=True,actualQaRevision=832,caseCount=78)))


if __name__ == '__main__':
    main()
