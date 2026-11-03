"""Close the reviewed 60 milestones only after native package/real QA gates pass.

Updates continuity metadata, never application data or Wascar's observations.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ER = 'evidence/s1-20261018/sesenta-tandas-473-532'
E = ROOT / ER


def load(path):
    return json.loads((ROOT / path).read_bytes())


def write(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepend(path, text):
    p = ROOT / path
    old = p.read_text(encoding='utf-8-sig')
    if 'Grupo473–532 cerrado' in old[:2200]:
        raise SystemExit('Closure already recorded; preserve historical entries')
    lines = old.splitlines(keepends=True)
    p.write_text(lines[0] + '\n' + text.strip() + '\n\n' + ''.join(lines[1:]).lstrip('\n'), encoding='utf-8')


def main():
    native = load(ER + '/packaging/native04/result.json')
    qa = load(ER + '/QA-SELECTED-03.json')
    assert native['successful'] and native['freshClustersInitialized'] == 2
    assert native['inputsUnchanged'] and native['ownedProcessesStopped']
    assert qa['state'] == 'committed' and qa['activationConfirmed'] and qa['leftRunning'] is False
    assert qa['pointerUnchanged'] and qa['privateInputsUnchanged'] and qa['old185ArtifactsRetained']
    assert set(qa['changedFields']) == {'artifactDirectory', 'dllSha256', 'bundleSha256'}

    plan_path = 'docs/PLAN-SESENTA-TANDAS-473-532.json'
    plan = load(plan_path)
    assert plan['completed'] == 0 and len(plan['batches']) == 60
    for b in plan['batches']:
        n = b['id']
        if n <= 481:
            ev = 'backend/postgres-focus02/result.json' if n in (476, 477, 478) else 'CIERRE.md'
        elif n <= 505:
            ev = 'frontend/gui02/fixture.json'
        elif n <= 511:
            ev = 'backend/postgres-focus02/result.json' if n == 508 else 'CIERRE.md'
        elif n == 512:
            ev = 'frontend/NODE-FOCO-02.log'
        elif n == 513:
            ev = 'frontend/gui02/fixture.json'
        elif n == 514:
            ev = 'frontend/gui-layout04/browser.json'
        elif n <= 517:
            ev = 'revision/REVISION-INDEPENDIENTE.md'
        elif n in (518, 519):
            ev = 'packaging/profile03/result.json'
        elif n == 520:
            ev = 'PACKAGES-03.json'
        elif n <= 524:
            ev = 'integration/native01/result.json'
        elif n <= 526:
            ev = 'packaging/native04/result.json'
        elif n == 527:
            ev = 'QA-OPERATIONAL-GO-03.json'
        elif n == 528:
            ev = 'QA-SELECTED-03.json'
        else:
            ev = 'CIERRE.md'
        assert (E / ev).is_file(), ev
        b.update(status='verified', evidence=ER + '/' + ev,
                 independentEvidence=ER + '/revision/REVISION-INDEPENDIENTE.md')
    plan.update(completed=60, finalProgress=77, closed='2026-10-18',
                evidenceAttribution='CIERRE.md distingue ejecución propia, revisión, focos, errores conservados y FINAL02/03. Los 60 hitos no son 60 suites ni 60 módulos.',
                acceptance='QA manual y adopción final de Wascar pendientes.')
    write(plan_path, plan)

    summary = '''**Grupo473–532 cerrado · 18.10.2026: 60/60 hitos internos; avance global aproximado 77/100 (76→77).** Editor tipado de configuraciones privadas para rack, Dose y dispositivo final; borrador vacío, BASE o plantilla propia, grupos/puertos explícitos y vista previa. Guarda una plantilla NUEVA e inmutable, sin alterar originales ni equipos existentes. Recuperación con recibo de servidor y diario compacto sin blueprint durable; RC9, Click-Click e idiomas conservados.

Pruebas Windows/PostgreSQL/Edge, revisión independiente y fallos de arnés originales conservados, con focos correctivos atribuidos. Dos ZIP532 idénticos de 117.055.538 B; instalación/backup/recuperación nativas PASS en dos clústeres nuevos, sin SDK. Selección real 185→532 confirmada en QA restaurado52346: misma base/OID/cuentas/claves/URL/puntero, sólo tres campos de artefactos modificados, versión185 retenida y APP/PG apagados. No login ni DML de aplicación en el QA real. Guías actualizadas: 68 casos disponibles en restaurado y 8 en original; disponibilidad no equivale a Pass de Wascar.

[Plan de 60 hitos](PLAN-SESENTA-TANDAS-473-532.json), [contrato del editor](API-EDITOR-PLANTILLA-PRIVADA-S1.md), [actualización compatible](ACTUALIZACION-ARTEFACTOS9-532-S1.md), [informe con pruebas, errores y límites](../evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md). Inventario20→21/25 por creación libre tipada antes ausente; pesos y otros aportes intactos. No puntos por IDs, ZIP o repetir pruebas. Próximo: compartición/publicación y funciones RC9/Dosen/undo/admin restantes; servicio/identidad Windows, PKI productiva, Windows limpio/otro equipo, licencias, recuperación integral/retención/manual final y QA/adopción. Los registros siguientes son históricos.'''
    prepend('docs/CONTINUIDAD-CODEX.md', summary)
    prepend('docs/INICIO-IMPLEMENTACION-S1.md', summary)
    prepend('docs/PROGRESO-GLOBAL.md', '''**Grupo473–532 cerrado · 18.10.2026: 77/100 provisional (76→77).** Inventario20→21/25 por nueva creación libre tipada de configuraciones privadas de rack/Dose/final, con semillas y editor antes ausentes, persistencia, instanciación, recuperación y autorización real probadas/revisadas. La captura previa y su simple renombrado no cubrían esa capacidad. Paridad14/15 sigue parcial: compartir/publicar y otras funciones faltan. Aportes18/21/14/14/9/1, pesos20/25/15/15/15/10 sin cambio. No puntos por contar60hitos, ZIP reproducibles, tests o seleccionar QA. [Cierre y atribución](../evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md).

Paquete532 instalado y recuperado en laboratorios nuevos de Windows; QA restaurado seleccionado en532 conservando datos/cuentas y apagado. Guías68/8 disponibles, sin resultados manuales nuevos. Estimación de alcance, no porcentaje de tests, créditos o calendario. Faltan funciones RC9/Dosen/undo/admin, servicio/identidad/PKI productiva, Windows limpio/otro equipo/CRT elevado, licencias, recuperación integral/retención/manual final y QA/adopción de Wascar. Registros siguientes históricos.''')
    # Keep the current table consistent as well as the new historical entry.
    progress_path = ROOT / 'docs/PROGRESO-GLOBAL.md'
    current_rows = {
        '| Jerarquía e inventario compartido |': '| Jerarquía e inventario compartido | 25 | 21 | Lotes por IDs, conexiones y borrado conjunto atómicos; compensación acotada de puertos; captura/instanciación privada y editor libre tipado que guarda una copia nueva, QA55–58/66–68. Pendientes undo general, Dose pasante y combinaciones restantes |',
        '| Paridad funcional/visual RC9 completa |': '| Paridad funcional/visual RC9 completa | 15 | 14 | Avisos descriptivos, PoE, búsqueda/consultas, CSV/XLSX tabulares, informes HTML, etiquetas, SVG y catálogo/favoritos/plantillas privadas con editor disponibles; RC9 y Click-Click conservados. Faltan compartición/publicación, PDF nativo/paridad del XLS RC9, herramientas y preferencias restantes, accesibilidad y aceptación completa EN/DE/ES |',
        '| Instalación Windows y recuperación operativa |': '| Instalación Windows y recuperación operativa | 15 | 9 | Paquete local con runtime.NET/PG/VC++ y aplicación; instalación nueva y recuperación de ROOT completo desde ZIP+backup probadas en clústeres nuevos. CRT compatible reutilizado; faltan CRT elevado/Windows limpio, servicio/identidad/PKI/otro equipo/licencias y recuperación integral del host |',
        '| **Total** |': '| **Total** | **100** | **77** | **Servidor final pendiente** |',
    }
    lines = progress_path.read_text(encoding='utf-8').splitlines()
    lines = [next((new for prefix, new in current_rows.items() if line.startswith(prefix)), line) for line in lines]
    progress_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    prepend('development/server/README.md', summary.replace('](PLAN-', '](../../docs/PLAN-').replace('](API-', '](../../docs/API-').replace('](ACTUALIZACION-', '](../../docs/ACTUALIZACION-').replace('](../evidence/', '](../../evidence/'))
    for path in ['docs/ESTADO-ACEPTACION-S1.md', 'docs/ACEPTACION.md', 'docs/MAPA-RC9-R3.md']:
        prepend(path, '''**Grupo473–532 cerrado · 18.10.2026.** Editor privado libre tipado probado/revisado, guardando una NUEVA configuración inmutable. Paquete532 y actualización compatible del QA restaurado verificados; QA66–68 detallados y disponibles con60–65 anteriores. No se marca aceptación manual: los resultados previos de Wascar se conservan y requieren repetición cuando cambió la versión. S-26 continúa parcial por compartición/publicación; faltan funciones y operación Windows final. [Pruebas y límites](../evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md). Global77/100 estimado; no servidor final ni adopción.''')
    prepend('CHANGELOG.md', '''## 18.10.2026 · Grupo473–532 cerrado · Editor privado y candidata QA532

- Crear configuraciones tipadas de rack/Dose/final desde vacío, BASE o privada propia; grupos/puertos explícitos y preview. Guardar copia nueva inmutable, sin modificar plantilla/equipos anteriores. API cerrada, Unicode/límites, permiso actual de servidor, commit/idempotencia/cancelación/auditoría y diario compacto sin definición durable.
- Windows/PostgreSQL/Node/Edge y revisión independiente, atribuyendo FINAL02/03 y conservando fallos originales de arnés. Dos ZIP532 idénticos; instalación, backup y restauración nativas PASS en dos clústeres nuevos con bytes/recibo/propietario de configuración intactos.
- QA restaurado185→532 confirmado, misma base/OID/cuentas/claves/puntero/URL y sólo tres campos de artefactos; anterior185 retenida, APP/PG apagados. Guías68/8 disponibles, QA66–68 nuevos y notas antiguas conservadas. SQL001–009 y versiones fijadas intactos.
- [Cierre, reproducción y límites](evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md). Global77/100 aproximado (inventario20→21/25); compartir/publicar, funciones restantes, instalación Windows final y QA/adopción siguen pendientes.''')

    contract = ROOT / 'docs/API-EDITOR-PLANTILLA-PRIVADA-S1.md'
    text = contract.read_text(encoding='utf-8')
    text = text.replace('Estado: desarrollo autorizado, pruebas y revisión pendientes.', 'Estado: implementado, probado en Windows/PostgreSQL/Edge y revisado independientemente; QA restaurado532 disponible, aceptación manual pendiente.')
    text = text.replace('Avance inicial76/100;60hitos internos propuestos, no60módulos ni60suites.', 'Avance77/100 aproximado;60/60hitos internos cerrados, no60módulos ni60suites.')
    text += '\n## Resultado del 18.10.2026\n\n[Informe completo y atribución FINAL02/03](../evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md). Creación y recuperación probadas; legacy conserva digest y definiciones exactas. El único cambio de producto02→03 es ancho mínimo620px de la tabla de preview con scroll contenido; servidor idéntico. GuíasQA66–68 con ubicaciones y botones exactos; sin Pass de Wascar. Paquete532 y selección compatible confirmados; SQL9 y dependencias fijadas intactas.\n'
    contract.write_text(text, encoding='utf-8')
    op = ROOT / 'docs/ACTUALIZACION-ARTEFACTOS9-532-S1.md'
    op.write_text(op.read_text(encoding='utf-8') + '\n## Operación real del 18.10.2026\n\nSelección FINAL03 confirmada por `QA-SELECTED-03.json`: tres campos exactos, puntero/entradas privadas/filas/historia/OID intactos, fuente185 retenida, APP/PG apagados. Sin autenticación ni DML de aplicación en QA real. [Evidencia](../evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md). No hay rollback posterior a actividad del usuario ni adopción implícita.\n', encoding='utf-8')

    catalog = load('docs/QA-CASOS-WASCAR.json')
    catalog['globalProgressEstimate'] = 77
    write('docs/QA-CASOS-WASCAR.json', catalog)
    mp = load('docs/MAPA-ENTREGA.json')
    mp.update(revision='2026-10-18-sesenta473-532', progress=77,
              snapshot='60/60 hitos: editor de configuración privada, paquete532 instalado/recuperado y selección compatible real. Guías68/8 disponibles; aceptación manual pendiente. Global77/100 estimado.',
              currentBatch=dict(count=60, completed=60, ledger=plan_path, evidence=ER+'/CIERRE.md'))
    inventory = next(s for s in mp['streams'] if s['id'] == 'inventory')
    inventory['points'] = 21
    inventory['children'].append(dict(id='private-configuration-editor',
        name='Editor libre tipado guarda copia privada nueva e inmutable', status='Probado y revisado',
        qa='QA66–68 · restaurado532', evidence=ER+'/CIERRE.md',
        note='Rack/Dose/final; semillas vacío/BASE/propia, grupos y GN explícitos; originales/equipos intactos. Sin compartir/publicar.'))
    def visit(items):
        for x in items:
            if x.get('id') == 'templates':
                x['note'] = 'BASE, favoritos, captura/renombrado/instanciación y editor libre privado probados; compartición/publicación y preferencias restantes pendientes.'
            if x.get('id') == 'private-templates':
                x.update(name='Captura, retiro, renombrado, editor de copia nueva y creación privados', qa='QA55–58/66–68',
                    note='Edición libre guarda UUID nuevo, conserva definición/bytes/hash/version previos. Compartición/publicación pendientes.', evidence=ER+'/CIERRE.md')
            visit(x.get('children', []))
    visit(mp['streams'])
    mp['history'].append(dict(id='h473-532', name='473–532 · editor privado, paquete y QA532',
        status='Probado y revisado', note='60hitos; instalación/backup/recuperación nuevas y selección185→532. Global76→77; QA manual pendiente.'))
    mp['nextMilestones'] = [x.replace('Seleccionar de forma revisada la pareja472 y actualizar el paquete; completar', 'Completar').replace('edición libre/plantillas compartidas', 'plantillas compartidas') for x in mp['nextMilestones']]
    assert sum(s['points'] for s in mp['streams']) == 77 and sum(s['weight'] for s in mp['streams']) == 100
    write('docs/MAPA-ENTREGA.json', mp)
    print(json.dumps(dict(completed=60, progress=77, realQaSelected=True, wascarResultsWritten=False)))


if __name__ == '__main__':
    main()
