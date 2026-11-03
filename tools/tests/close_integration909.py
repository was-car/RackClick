"""Update continuity and60 concrete milestones after confirmed real QA849 selection."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ER = 'evidence/s1-20261018/sesenta-tandas-850-909'
E = ROOT / ER


def read(name):
    return json.loads((E / name).read_bytes())


def prepend(name, text):
    path = ROOT / name
    old = path.read_bytes()
    assert b'Bloque850' not in old[:2200]
    first, sep, rest = old.partition(b'\n')
    nl = b'\r\n' if first.endswith(b'\r') else b'\n'
    path.write_bytes(first + sep + nl + text.strip().encode().replace(b'\n', nl) + nl + nl + rest)


def main():
    assert (E / 'CIERRE.md').is_file()
    assert read('revision/GATE-TECNICO.json')['approved'] and read('COORDINATOR-GO.json')['valid']
    assert read('REAL-QA-ACTIVATE-01.json')['state'] == 'committed'
    assert read('REAL-QA-VALIDATE-01.json')['valid'] and read('QA-TESTS-01.json')['successful']
    assert read('QA-TESTS-01.json')['availability'] == dict(manual=8, rc9=78)
    plan_path = ROOT / 'docs/PLAN-SESENTA-TANDAS-850-909.json'
    plan = json.loads(plan_path.read_bytes())
    assert plan['completed'] == 0 and len(plan['batches']) == 60
    evidence = {850: 'INICIO.json', 851: 'INICIO.json', 852: 'INICIO.json', 853: 'INICIO.json',
                854: 'INICIO.json', 865: 'SOURCE-FREEZE-OPERATORS-01.json',
                866: 'PACKAGES-01.json', 867: 'PACKAGES-01.json',
                892: 'revision/GATE-TECNICO.json', 893: 'revision/source-recovery-activity01/result.json',
                894: 'revision/GATE-TECNICO.json', 895: 'REAL-QA-PREFLIGHT-01.json',
                896: 'COORDINATOR-GO.json', 897: 'REAL-QA-PREPARE-01.json',
                898: 'REAL-QA-ACTIVATE-01.json', 899: 'REAL-QA-ACTIVATE-01.json',
                900: 'REAL-QA-VALIDATE-01.json', 901: 'QA-MATRIX-909.json',
                902: 'QA-MATRIX-909.json', 903: 'QA-TESTS-01.json', 904: 'QA-TESTS-01.json'}
    for i in range(855, 861):
        evidence[i] = 'windows/profiles01/result.json'
    for i in range(861, 865):
        evidence[i] = 'MANUALES-01.json'
    for i in range(868, 882):
        evidence[i] = 'windows/native01/result.json'
    for i in range(882, 892):
        evidence[i] = 'qa-copy/all01/result.json'
    for i in range(905, 910):
        evidence[i] = 'CIERRE.md'
    assert set(evidence) == set(range(850, 910))
    for row in plan['batches']:
        ev = evidence[row['id']]
        assert (E / ev).is_file()
        row.update(status='verified', evidence=ER + '/' + ev,
                   independentEvidence=ER + '/revision/GATE-TECNICO.json')
    # The last milestones are preparations; the actual seal/commit follow independent closure metadata.
    plan['batches'][57]['title'] = 'Preparación de verificación final y adenda independiente'
    plan.update(completed=60, closed='2026-10-18', finalProgress=78,
                attribution='60 internal checks of one integration protocol, not60features/suites. Windows/copy authors, independent ownPG focus and coordinator actual QA actions are separate.',
                acceptance='New QA849 selected; QA832 and its recovery712 conserved. Voice/manualWascarQA/final server adoption pending.')
    plan_path.write_bytes((json.dumps(plan, ensure_ascii=False, indent=2) + '\n').encode())
    summary = '''**Bloque850–909 cerrado · 18.10.2026: 60/60 hitos internos; avance global aproximado78 %, sin aumento.** La candidata849 está integrada en perfil Windows cerrado, paquete nuevo reproducible y copia nueva del QA. Se reutilizan sus38artefactos sin compilar; servidor832, SQL001–011, dependencias y CSS exactos. Dos ZIP idénticos,25operadores y4manuales congelados. New/Restore públicos, HTTPS/dosactores/recibos/XLS/reinicio y35tablas comprobados; app.js transportado exacto con descriptor status848. Esto no es una nueva ejecución GUI/AX/voz.

La copia832→849 protege por separado principal832 y recuperación712 del origen, incluidos preparado/sello847. Copia sólo primaria a nuevas849 y recuperación832, ambas11, sin migrate/bootstrap/recover-admin.35tablas/historia/cuentas/sesiones/privados exactos y cinco secretosPG nuevos; fuente completa conservada. Revisión independiente con focoPG propio: actividad compensada sólo en recuperación712 del origen impide retorno, aunque snapshots no cambien. Coordinador reconfirmó quietud y gates, preparó/seleccionó la copia real y validó; sin login/DML de aplicación en origen, procesos propios detenidos.

**QA-78 disponible** en INICIAR-QA-RESTAURADO.cmd, guía y acceso privado locales. Catálogo78, disponibles78restaurado/8original;77guiones exactos, sólo feature/introducción deQA78 y listas de parejas heredadas actualizadas. Guía exige par849 completo/roles/configuración; test848 evoluciona deplanned a par cerrado, fuente anterior conservada. Resultados/observaciones de Wascar intactos. Voz con lector sigue pendiente: si no se dispone de lector habitual, registrar Bloqueado, no Pass automático. [Contrato](INTEGRACION-AVISO-GRUPOS-WINDOWS-QA-S1.md), [plan60](PLAN-SESENTA-TANDAS-850-909.json), [atribución/pruebas/límites](../evidence/s1-20261018/sesenta-tandas-850-909/CIERRE.md).

No puntos por IDs/ZIP/suites; aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 intactos. Continúan formatos/PDF/herramientas/paletas/accesibilidad/idiomas, Dosen/undo/admin y servicio/identidad/PKI/Windows limpio/otroequipo/licencias/recuperaciónintegral/manualfinal y QA/adopción de Wascar. Registros siguientes históricos.'''
    for path in ['docs/CONTINUIDAD-CODEX.md', 'docs/INICIO-IMPLEMENTACION-S1.md', 'docs/PROGRESO-GLOBAL.md',
                 'docs/ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md']:
        prepend(path, summary)
    for path in ['development/server/README.md', 'development/frontend/README.md']:
        adjusted = summary.replace('](INTEGRACION-', '](../../docs/INTEGRACION-').replace('](PLAN-', '](../../docs/PLAN-').replace('](../evidence/', '](../../evidence/')
        prepend(path, adjusted)
    short = '''**Bloque850–909 vigente ·18.10.2026.** Candidata849 en perfil/ZIPWindows y nuevaQA849, con origen832/recuperación712 conservados.60hitos internos, no60funciones. New/Restore/35tablas/copia/retorno probados y revisiónPG propia independiente; sin builds nuevos ni voz acreditada.78casos disponibles restaurado/8original, incluido QA78 con lector habitual;77casos previos/resultados de Wascar conservados. Global78 % aproximado, adopción final pendiente. [Contrato](INTEGRACION-AVISO-GRUPOS-WINDOWS-QA-S1.md), [evidencias y límites](../evidence/s1-20261018/sesenta-tandas-850-909/CIERRE.md). Registros siguientes históricos.'''
    for path in ['docs/BRIEFING-MAESTRO.md', 'docs/ACEPTACION.md', 'docs/ESTADO-ACEPTACION-S1.md',
                 'docs/MAPA-RC9-R3.md', 'docs/QA-COLABORACION-Y-RESTAURACION.md']:
        prepend(path, short)
    prepend('CHANGELOG.md', '''## 18.10.2026 · Bloque850–909 · Candidata849 en Windows y QA

- Perfil849 cerrado y dos ZIP nuevos idénticos; tres operadores y cuatro manuales actualizados, versiones/perfiles anteriores conservados y0compilaciones.
- New/Restore públicos con HTTPS/multiusuario/XLS/replay/reinicio/35tablas y transporte app.js849 exacto. CopiaQA832→849 en clúster nuevo con recuperación832; origen832/recuperación712 y sesiones/privados protegidos por separado.
- Revisión independiente PG propia bloquea retorno tras actividad compensada en recuperación712 del origen. Preparación/selección real después del GO, sin login/DML de aplicación en fuente; procesos propios detenidos.
- QA78 disponible con par exacto;78restaurado/8original,77guiones previos y resultados intactos. Voz pendiente.60hitos internos, global78 % sin aumento; QA/adopción final pendientes. [Informe](evidence/s1-20261018/sesenta-tandas-850-909/CIERRE.md).''')
    path = ROOT / 'docs/MAPA-ENTREGA.json'
    data = json.loads(path.read_bytes())
    assert data['progress'] == 78 and [s['points'] for s in data['streams']] == [18, 22, 14, 14, 9, 1]
    data.update(revision='2026-10-18-sesenta850-909', progress=78,
                snapshot='60/60hitos internos: candidata849 en Windows/ZIP y nuevaQA; fuente832+recuperación712 conservadas.78+8casos,QA78disponible,voz pendiente;78estimado.',
                currentBatch=dict(count=60, completed=60, ledger='docs/PLAN-SESENTA-TANDAS-850-909.json', evidence=ER + '/CIERRE.md'))
    def visit(items):
        for item in items:
            if item.get('id') == 'group-relations-readonly':
                item.update(status='Probado y revisado · aviso accesible en Windows/QA849', qa='QA34 yQA78 · disponibles restaurado849', evidence=ER + '/CIERRE.md', note='Relaciones por UUID y aviso compacto persistente; voz manual pendiente. Navegar no asigna permisos ni inventa herenciaAD.')
            if item.get('id') == 'rc9-excel-html':
                item.update(status='Probado y revisado · integrado Windows/QA849', qa='QA75–77 · disponibles restaurado849')
            visit(item.get('children', []))
    visit(data['streams'])
    data['history'].append(dict(id='h850-909', name='850–909 · Integración Windows/QA849', status='Probado y revisado', note='60hitos,78+8casos disponibles,origen832+recuperación712 conservados;78sin aumento,voz y adopción pendientes.'))
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps(dict(completed=60, progress=78, actualQaRevision=849, availableRestoredCases=78, manualWascarResultsWritten=False)))


if __name__ == '__main__':
    main()
