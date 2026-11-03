"""Close only after package/native/review/actual QA11 gates; keep older entries."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-713-772';E=ROOT/ER
def read(p):return json.loads((E/p).read_bytes())
def save(p,d):(ROOT/p).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def prepend(p,text):
    path=ROOT/p;old=path.read_bytes()
    if b'Grupo713' in old[:2500]:raise SystemExit('Preserve existing closure')
    first,sep,rest=old.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    path.write_bytes(first+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+rest)
def main():
    assert read('COORDINATOR-GO.json')['valid'] and read('PACKAGES-02.json')['byteIdentical']
    assert read('REAL-QA-ACTIVATE-01.json')['state']=='committed' and read('REAL-QA-VALIDATE-01.json')['valid']
    assert read('QA-MATRIX-772.json')['previous71Exact'] and read('QA-TESTS-01.json')['successful']
    assert read('QA-TESTS-01.json')['availability']==dict(manual=8,rc9=74)
    assert (E/'CIERRE.md').is_file()
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-713-772.json').read_bytes());assert plan['completed']==0
    for row in plan['batches']:
        i=row['id']
        if i<=715:ev='INICIO.json'
        elif i<=721:ev='windows/profiles03/result.json'
        elif i<=737:ev='windows/native02/result.json'
        elif i<=741:ev='MANUALES-FINAL02.json'
        elif i<=744:ev='PACKAGES-02.json'
        elif i<=760:ev='qa-transition/all01/result.json'
        elif i==761:ev='revision/GATE-TECNICO.json'
        elif i==762:ev='revision/source-activity01/result.json'
        elif i==763:ev='REAL-QA-PREFLIGHT-01.json'
        elif i==764:ev='COORDINATOR-GO.json'
        elif i==765:ev='REAL-QA-PREPARE-01.json'
        elif i<=767:ev='REAL-QA-VALIDATE-01.json'
        elif i<=769:ev='QA-MATRIX-772.json'
        elif i==770:ev='QA-TESTS-01.json'
        else:ev='CIERRE.md'
        assert (E/ev).is_file();row.update(status='verified',evidence=ER+'/'+ev,independentEvidence=ER+'/revision/GATE-TECNICO.json')
    plan.update(completed=60,finalProgress=78,closed='2026-10-18',evidenceAttribution='60 bounded internal milestones, not60 modules/suites. New native and wrapper Restore11 distinguished from own independent source-activity focus and coordinator actual QA copy/selection; failures retained.',acceptance='Internal Windows11 schema11 integration; current restored QA712 selected in NEW lab, source592/schema10 retained. Manual Wascar QA/final adoption pending.')
    save('docs/PLAN-SESENTA-TANDAS-713-772.json',plan)
    summary='''**Grupo713–772 cerrado ·18.10.2026:60/60 hitos internos; avance global estimado78/100, sin aumento.** Esquema11 integrado en perfil cerrado712, distribución/Stage/readiness y recuperación Windows. Candidata/GUI712 FINAL02 reutilizadas sin recompilar, SQL001–010 y dependencias intactos. Dos ZIP finales idénticos,25operadores y4manuales; instalaciónNew, HTTPS, preferencias por usuario/lector/otra sesión, reinicio, backup35tablas, Restore/CLI11 y foco del wrapper Restore11 probados en laboratorios nuevos. P2 real de límite18/19 corregido a18/19/20 con pruebaStage real; ZIP01 y fallos conservados.

QA restaurado712/esquema11 seleccionado por copia a clúster nuevo, con recuperación10 separada. Origen592/10 conservado, cuentas/contraseñas/permisos/sesiones y4privados de aplicación intactos; secretosPostgreSQL nuevos. Sin login ni DML de aplicación en QA real. Watermarks/locks/readiness/puntero y retorno condicionado probados; actividad incluso compensada bloquea retorno. Revisión independiente separada de implementación. Ramas detenidas al cierre.

Guías74casos disponibles en restaurado/8original: QA72–74 de idioma/tema por cuenta ya se pueden probar con INICIAR-QA-RESTAURADO.cmd, guía y credenciales privadas locales. No nuevos Pass ni cambios de resultados/observaciones de Wascar. QA/adopción final pendientes. [Contrato](INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md), [plan60](PLAN-SESENTA-TANDAS-713-772.json), [pruebas/fallos/límites](../evidence/s1-20261018/sesenta-tandas-713-772/CIERRE.md). Se integra una capacidad ya contada; sin puntos por IDs/ZIP/suites/selección. Próximo: funciones RC9/admin/Dosen/undo/formatos/herramientas/paletas y servicio/identidad/PKI/Windows limpio/recuperación integral/manualfinal. Registros siguientes históricos.'''
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md']:prepend(p,summary)
    prepend('development/server/README.md',summary.replace('](INTEGRACION-','](../../docs/INTEGRACION-').replace('](PLAN-','](../../docs/PLAN-').replace('](../evidence/','](../../evidence/'))
    short='''**Grupo713–772 vigente ·18.10.2026.** Paquete interno New/Restore11 y CLI probados; QA restaurado712 seleccionado por copia nueva, origen592/10 conservado. Guías74restaurado/8original disponibles, incluido QA72–74 de idioma/tema propios. Sin nuevos resultados manuales ni adopción. Global78/100 sin aumento por integración de capacidad ya contada. [Contrato](INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md), [pruebas/revisión/límites](../evidence/s1-20261018/sesenta-tandas-713-772/CIERRE.md). Registros siguientes históricos.'''
    for p in ['docs/BRIEFING-MAESTRO.md','docs/QA-COLABORACION-Y-RESTAURACION.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:prepend(p,short)
    prepend('CHANGELOG.md','''## 18.10.2026 · Grupo713–772 · Integración Windows y QA11

- Perfil712 cerrado,38archivos/SQL001–011, compatible con perfiles9/10 históricos. Stage/readiness11 y recuperación/grants11 comprobados. P2 real límite18/19 corregido, prueba real y fallo/ZIP01 conservados.
- Dos ZIP finales idénticos,25operadores y4manuales; New/HTTPS/otra sesión/preferencias/backup/RestoreCLI11/35tablas y foco Install-ModeRestore11 correctos, sin recompilar aplicación.
- Motor NUEVO copiaQA10→11 con recuperación10 separada; nuevo clúster/secretosPG, cuentas/permisos/sesiones/privados intactos, retorno sólo sin actividad. Revisión propia independiente y GO técnico antes de selección real.
- QA712 seleccionado y detenido; guías74+8disponibles, nuevosQA72–74 habilitados sin resultados de Wascar alterados. Global78/100 aproximado sin aumento. [Cierre](evidence/s1-20261018/sesenta-tandas-713-772/CIERRE.md).''')
    prepend('docs/PROGRESO-GLOBAL.md','''**Grupo713–772 cerrado ·18.10.2026:78/100 provisional, sin aumento.** Idioma/tema propios ya integrados en operación/paqueteWindows11 y QA712 mediante copia a nuevo clúster, conservando origen592/10. New/Restore/CLI11/wrapper,35tablas, revisión independiente y guías74restaurado/8original disponibles. Consolida capacidad personal ya contada; sin puntos por60IDs, ZIP, suites o selección. Aportes18/22/14/14/9/1, pesos20/25/15/15/15/10 intactos. [Pruebas/correcciones/fallos/límites](../evidence/s1-20261018/sesenta-tandas-713-772/CIERRE.md).

Faltan funciones RC9/admin/Dosen/undo/formatos/herramientas/paletas y comprobaciones de accesibilidad/EN/DE/ES; servicio/identidadWindows/PKIproductiva, Windowslimpio/otroequipo/CRT elevado/licencias, recuperación integral/retención/manualfinal y QA/adopción de Wascar. Estimación de alcance, no pruebas/créditos/calendario. Registros siguientes históricos.''')
    p=ROOT/'docs/PROGRESO-GLOBAL.md';lines=p.read_bytes().splitlines(keepends=True);prefix=b'| Paridad funcional/visual RC9 completa |'
    new='| Paridad funcional/visual RC9 completa | 15 | 14 | Informes, etiquetas, catálogo/plantillas/avisos e idioma/tema propios integrados en Windows/QA11. Faltan formatos/herramientas/paletas, accesibilidad y aceptación completa EN/DE/ES |'.encode()
    p.write_bytes(b''.join(new+(b'\r\n' if x.endswith(b'\r\n') else b'\n') if x.startswith(prefix) else x for x in lines))
    m=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());m.update(revision='2026-10-18-sesenta713-772',progress=78,snapshot='60/60hitos: paqueteWindows/Restore11 y QA712 seleccionados por copia nueva. Origen592/10 conservado;74+8casos disponibles;78estimado sin aumento.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-713-772.json',evidence=ER+'/CIERRE.md'))
    def visit(items):
        for x in items:
            if x.get('id')=='personal-language-theme':x.update(status='Probado y revisado · integrado Windows/QA11',qa='QA72–74 · disponible restaurado712',evidence=ER+'/CIERRE.md')
            visit(x.get('children',[]))
    visit(m['streams']);m['history'].append(dict(id='h713-772',name='713–772 · paquete/Restore11 y copiaQA10→11',status='Probado y revisado',note='60hitos internos,74+8casos disponibles, origen592/10 conservado;78sin aumento, QA/adopción pendientes.'))
    m['nextMilestones']=[x for x in m['nextMilestones'] if not x.startswith('Integrar schema11')]
    assert [x['points'] for x in m['streams']]==[18,22,14,14,9,1] and sum(x['weight'] for x in m['streams'])==100;save('docs/MAPA-ENTREGA.json',m)
    contract=ROOT/'docs/INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md'
    with contract.open('a',encoding='utf-8') as f:f.write('\n\nResultado: [cierre713–772](../evidence/s1-20261018/sesenta-tandas-713-772/CIERRE.md). Integrado y probado/revisado, QA real712/11 seleccionado por copia nueva; origen592/10 conservado,74+8casos disponibles. Sin QA manual ni adopción.\n')
    print(json.dumps(dict(completed=60,progress=78,actualQaSelectedSchema=11,manualWascarResultsWritten=False)))
if __name__=='__main__':main()
