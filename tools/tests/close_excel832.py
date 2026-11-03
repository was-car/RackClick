"""Reconcile the completed internal block with continuity and the visible roadmap."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-773-832';E=ROOT/ER
def read(p):return json.loads((E/p).read_bytes())
def save(p,d):(ROOT/p).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def prepend(p,text):
    path=ROOT/p;old=path.read_bytes();assert b'Grupo773' not in old[:2400]
    first,sep,rest=old.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    path.write_bytes(first+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+rest)
def main():
    assert read('revision/GATE-TECNICO.json')['valid'] and read('revision/GATE-TECNICO.json')['recommendedProgress']==78
    assert read('backend/INFORME.json')['successful'] and read('office/office03/result.json')['successful']
    assert read('backup/native02/result.json')['successful'] and read('frontend/edge03/fixture.json')['result']=='PASS'
    assert read('qa-guide03/result.json')['successful'] and read('QA-DISPONIBILIDAD-02.json')['successful']
    assert (E/'CIERRE.md').is_file()
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-773-832.json').read_bytes());assert plan['completed']==0
    for row in plan['batches']:
        i=row['id']
        if i<=775:ev='INICIO.json'
        elif i==776:ev='contract/API-before-office.md'
        elif i<=795:ev='backend/INFORME.json'
        elif i<=803:ev='frontend/INFORME.json'
        elif i<=806:ev='BUILD-01.json'
        elif i==807:ev='CANDIDATA832-02.json'
        elif i<=812:ev='backend/INFORME.json'
        elif i<=815:ev='frontend/edge03/fixture.json'
        elif i<=818:ev='office/office03/office.json'
        elif i<=820:ev='backup/native02/result.json'
        elif i==821:ev='revision/GATE-TECNICO.json'
        elif i==822:ev='revision/group-status01/result.json'
        elif i==823:ev='QA-PAIR-FINAL02.json'
        elif i==824:ev='QA-DISPONIBILIDAD-02.json'
        elif i==825:ev='qa-guide03/result.json'
        else:ev='CIERRE.md'
        assert (E/ev).is_file();row.update(status='verified',evidence=ER+'/'+ev,independentEvidence=ER+'/revision/GATE-TECNICO.json')
    plan.update(completed=60,finalProgress=78,closed='2026-10-18',evidenceAttribution='60 bounded internal milestones, not modules/suites. Final02 renderer3 + initial authorization4 explicitly attributed after reviewed delta; own independent PG1 remains initial candidate authorization focus. Office real and native backup final02 executed by coordinator; failures retained.',acceptance='Development candidate only; QA712/schema11 and Windows ZIP772 retained. New QA75-77 pending integration, manual Wascar QA/adoption pending.')
    save('docs/PLAN-SESENTA-TANDAS-773-832.json',plan)
    summary='''**Grupo773–832 cerrado ·18.10.2026:60/60 hitos internos; avance global estimado78/100, sin aumento.** Nuevo informe de rack RC9 **XLS (HTML RC9)**, tres tablas Devices/Connections/Summary desde PostgreSQL por UUID y grupo/tipo, con rutas de sala explícitas. Mantiene XLSX tabular separado. Generación/recuperación/descarga requieren lectura y exportación vigentes; recibo/bytes/fecha/auditoría atómicos y replay original, sin cambiar inventario. Technician vacío porque no existe campo persistido; Created legacy literal o creaciónPG, nunca fecha de exportación.

Dos defectos reales corregidos antes del cierre: datos vacíos en Excel por TDx:str vacío y P2 de UUID cortado en móvil. Candidata832-02 separada, SQL001–011/dependencias/CSS intactos. Windows:76dominio,13Node,7focosPG compuestos con atribución explícita, Edge con3descargas/dosactores/errores/reinicio y UUID legible, Excel16.0build20430 con87valores exactos/sin fórmulas, backup/restore35tablas/recibo exactos y focoPG independiente de revocación de grupo durante espera. Fallos y fuentes iniciales conservados; no presentar corridaPG01 comoPASS. Excel observado pone las tres tablas en Devices y deja vacías las otras dos hojas declaradas: no prometer tres hojas pobladas ni compatibilidad universal.

QA712/esquema11 y ZIP772 conservados.77casos en catálogo,74disponibles restaurado/8original; nuevosQA75–77 detallados permanecen pendientes de integrar/seleccionar832 en Windows/QA. Sin acceso de aplicación al QA real ni resultados/observaciones de Wascar alterados. [Contrato](API-XLS-HTML-RC9-S1.md), [plan60](PLAN-SESENTA-TANDAS-773-832.json), [pruebas/correcciones/revisión/límites](../evidence/s1-20261018/sesenta-tandas-773-832/CIERRE.md). Próximo: integrar la candidata832 en operadores/paquete/QA por copia conservadora; continuar PDF/herramientas/paletas, Dosen/undo/admin y servicio/identidad/PKI/Windows limpio/recuperación/manualfinal. Adopción pendiente de Wascar. Registros siguientes históricos.'''
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md']:prepend(p,summary)
    prepend('development/server/README.md',summary.replace('](API-','](../../docs/API-').replace('](PLAN-','](../../docs/PLAN-').replace('](../evidence/','](../../evidence/'))
    short='''**Grupo773–832 vigente ·18.10.2026.** Informe XLS(HTMLRC9) por rack,3tablas, API/GUI/celdas Office/UUID móvil probados y revisados en candidata832-02 separada. Excel observado:87valores exactos sin fórmulas, tablas en Devices; no tres hojas pobladas. QA712/ZIP772 intactos,74+8casos disponibles; QA75–77 pendientes de integración. Global78/100 sin aumento por formato parcial; sin QA/adopción ni resultados de Wascar alterados. [Contrato](API-XLS-HTML-RC9-S1.md), [evidencias/fallos/límites](../evidence/s1-20261018/sesenta-tandas-773-832/CIERRE.md). Registros siguientes históricos.'''
    for p in ['docs/BRIEFING-MAESTRO.md','docs/QA-COLABORACION-Y-RESTAURACION.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:prepend(p,short)
    prepend('CHANGELOG.md','''## 18.10.2026 · Grupo773–832 · XLS HTML RC9 por rack

- Nuevo endpoint/DTO e informe cerrado Devices/Connections/Summary, UUID/grupo/tipo explícitos, autorización vigente y guardia de rutas genéricas, persistencia/auditoría/replay/rollback; sin SQL/dependencias nuevos.
- GUI RC9 plegable EN/DE/ES, validación SHA/Base64/UTF8/gramática/identidades, recuperaciónRAM y status antes de Blob; borradores/Click-Click conservados.
- Defecto de apertura Office corregido: atributo textual x:str con valor canónico igual a contenido preserva87valores exactos sin fórmulas. P2 UUID móvil visible en párrafo envolvente. Evidencias fallidas/controles/candidata01 retenidas; FINAL02 probada/revisada, alcance de Office limitado explícitamente.
- Guías77casos;74restaurado/8original disponibles, nuevosQA75–77 pendientes. QA712 y ZIP772 sin cambios. Global78/100 sin aumento; servidor final/adopción pendientes. [Cierre](evidence/s1-20261018/sesenta-tandas-773-832/CIERRE.md).''')
    prepend('docs/PROGRESO-GLOBAL.md','''**Grupo773–832 cerrado ·18.10.2026:78/100 provisional, sin aumento.** Nuevo formato XLS(HTMLRC9) de tres tablas por rack, con API/GUI y comprobación real de87valores en Excel; celdas vacías en Office y UUID móvil corregidos antes del cierre. Candidata832-02 probada/revisada en desarrollo; QA712 y ZIP772 intactos,77casos/74+8disponibles, QA75–77 pendientes de integración. Un formato específico no cierra el punto restante completo de paridad: PDF/herramientas/paletas/accesibilidad/aceptación aún pendientes. Aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 sin cambios; sin puntos por60IDs/suites/documentos. [Evidencias/atribución/fallos/límites](../evidence/s1-20261018/sesenta-tandas-773-832/CIERRE.md).

Siguiente: integración conservadora832 en Windows/QA, funciones RC9/Dosen/undo/admin, servicio/identidad/PKI productiva, Windows limpio/otro equipo/CRT elevado/licencias, recuperación integral/retención/manual y QA/adopción de Wascar. Estimación de alcance, no pruebas/créditos/calendario. Registros siguientes históricos.''')
    p=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(p.read_bytes());m.update(revision='2026-10-18-sesenta773-832',progress=78,snapshot='60/60hitos: XLS(HTMLRC9)3tablas por rack probado/revisado en832-02; Office/UUID móvil corregidos. QA712/ZIP772 intactos;77casos74+8disponibles;78estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-773-832.json',evidence=ER+'/CIERRE.md'))
    parity=next(x for x in m['streams'] if x['id']=='parity') if any(x['id']=='parity' for x in m['streams']) else m['streams'][3]
    assert parity['points']==14
    parity['children'].append(dict(id='rc9-excel-html',name='XLS HTML RC9: Devices/Connections/Summary por rack UUID',status='Probado y revisado · desarrollo832-02',qa='QA75–77 · pendientes, QA712 conservado',evidence=ER+'/CIERRE.md',note='Office real87valores exactos/sin fórmulas; tablas enDevices,otras dos hojas vacías. API,grupos/tipos,permisos,recibos/rollback/replay/backup y GUI probados; integración Windows/QA posterior.'))
    def visit(items):
        for x in items:
            if x.get('id') in ['xls','xls-export','excel']:x.update(status='Probado y revisado · desarrollo832-02',qa='QA75–77 pendientes',evidence=ER+'/CIERRE.md',note='XLS HTML RC9 distinto de XLSX tabular. Tres tablas; Office observado no tres hojas pobladas. Integración Windows/QA832 pendiente.')
            if 'frontalSVG/PDF nativo/XLS restantes' in x.get('note',''):x['note']=x['note'].replace('frontalSVG/PDF nativo/XLS restantes','SVG y XLSHTML probados en sus candidatas; PDF nativo y demás herramientas pendientes')
            if x.get('id')=='pdf-xls-labels':x.update(name='PDF nativo y formatos restantes',note='SVG y XLSHTML RC9 de tres tablas probados/revisados en sus candidatas; QA75–77 pendientes de integrar832. PDF nativo y formatos restantes pendientes.')
            if 'XLSHTML RC9 Devices/Summary, PDF nativo y formatos restantes pendientes;' in x.get('note',''):x['note']='CSV/HTML imprimible/SVG/XLSX tabular ya existentes. XLSHTML RC9 Devices/Connections/Summary probado/revisado en832-02, QA75–77 pendientes de integración. PDF nativo y formatos restantes pendientes.'
            visit(x.get('children',[]))
    visit(m['streams']);m['history'].append(dict(id='h773-832',name='773–832 · XLS HTML RC9 y correcciones Office/UUID móvil',status='Probado y revisado',note='60hitos internos; QA712/ZIP772 retenidos,QA75–77 pendientes,78sin aumento. No QA/adopción.'))
    m['nextMilestones'].insert(0,'Integrar candidata832-02/XLS HTML RC9 en perfil Windows/paquete/QA nuevo por copia conservadora; QA75–77 sólo tras selección comprobada.')
    m['nextMilestones']=[x.replace('PDF nativo/XLS,','PDF nativo,') for x in m['nextMilestones']]
    assert [x['points'] for x in m['streams']]==[18,22,14,14,9,1];save('docs/MAPA-ENTREGA.json',m)
    print(json.dumps(dict(completed=60,progress=78,currentQaChanged=False,manualWascarResultsWritten=False)))
if __name__=='__main__':main()
