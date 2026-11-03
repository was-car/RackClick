"""Close fifteen internal milestones after actual selected QA and guide checks."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/quince-tandas-833-847';E=ROOT/ER
def read(p):return json.loads((E/p).read_bytes())
def save(p,v):(ROOT/p).write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def prepend(p,t):
    path=ROOT/p;old=path.read_bytes();assert b'Grupo833' not in old[:2000]
    first,sep,rest=old.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n';path.write_bytes(first+sep+nl+t.strip().encode().replace(b'\n',nl)+nl+rest)
def main():
    assert read('revision/GATE-TECNICO.json')['valid'] and read('COORDINATOR-GO.json')['valid']
    assert read('PACKAGES-01.json')['valid'] and read('REAL-QA-ACTIVATE-01.json')['state']=='committed'
    assert read('REAL-QA-VALIDATE-01.json')['valid'] and read('QA-TESTS-01.json')['successful'] and read('QA-TESTS-01.json')['availability']==dict(manual=8,rc9=77)
    assert (E/'CIERRE.md').is_file()
    plan=json.loads((ROOT/'docs/PLAN-QUINCE-TANDAS-833-847.json').read_bytes());assert plan['completed']==0
    evidence=['INICIO.json','MANUALES-01.json','windows/profiles01/result.json','PACKAGES-01.json','windows/native01/result.json','windows/native01/result.json','qa-copy/all01/result.json','qa-copy/all01/result.json','revision/GATE-TECNICO.json','COORDINATOR-GO.json','REAL-QA-PREPARE-01.json','REAL-QA-VALIDATE-01.json','QA-TESTS-01.json','CIERRE.md','CIERRE.md']
    for row,ev in zip(plan['batches'],evidence):
        assert (E/ev).is_file();row.update(status='verified',evidence=ER+'/'+ev,independentEvidence=ER+'/revision/GATE-TECNICO.json')
    plan.update(completed=15,finalProgress=78,closed='2026-10-18',attribution='15 internal milestones, not15 modules/suites. Operator/profile/native and copy author executions separate from independent recovery activity focus; coordinator alone prepared/selected actual new QA. All previous reports retained.',acceptance='QA832 selected in a NEW schema11 lab, source712 retained; manual Wascar QA and final server adoption pending.')
    save('docs/PLAN-QUINCE-TANDAS-833-847.json',plan)
    summary='''**Grupo833–847 cerrado ·18.10.2026:15/15 hitos internos; avance global estimado78/100, sin aumento.** Candidata832-02/XLSHTML RC9 integrada en perfil Windows cerrado832, paquete nuevo reproducible y QA restaurado por copia nueva11→11. Aplicación/GUI probadas anteriormente se reutilizan sin compilar; SQL001–011/dependencias/CSS exactos. DosZIP847 idénticos,25operadores y4manuales, con entradas públicas New y Restore comprobadas: HTTPS, dosactores/permisos, XLS, replay/reinicio y35tablas/recibos/bytes exactos tras recuperación administrativa. Sin cambios del CRT del host.

Adaptador qa_xls11_*847 copia sólo la base principal11 a dosbases nuevas11 (832 y recuperación712), con35tablas/historia/cuentas/sesiones/privados exactos y cinco secretosPG nuevos, sin migrate/bootstrap/recover-admin en la copia. Origen712 completo, sus perfiles/recuperación histórica y ZIPanteriores conservados. Identidad/locks/watermarks/readiness/puntero y retorno condicionado probados; actividad compensada también bloquea retorno. Revisión independiente con focoPG propio separado antes del GO. Coordinador comprobó fuente quieta, preparó/seleccionó nueva832 y validó; sin login ni DML de aplicación en QAreal, procesos propios detenidos.

**QA75–77 ya disponibles** mediante INICIAR-QA-RESTAURADO.cmd y su guía/credenciales privadas. Catálogo77casos,77disponibles restaurado/8original; sólo6intros de disponibilidad actualizadas (75–77 activación y60–62 avisoQA185 obsoleto). Pasos restantes/expected y otras71definiciones exactos, sin notas/resultados de Wascar sobrescritos ni Pass nuevos. XLS es HTML, distinto de XLSX: Office previo observado87valores exactos/sin fórmulas, tres tablas enDevices y otras dos hojas vacías; no nueva ejecución Office ni compatibilidad universal en847. [Contrato](INTEGRACION-XLS-WINDOWS-QA-S1.md), [plan15](PLAN-QUINCE-TANDAS-833-847.json), [pruebas/atribución/límites](../evidence/s1-20261018/quince-tandas-833-847/CIERRE.md).

Integración de capacidad ya contada; sin puntos por IDs/ZIP/pruebas. Siguiente: formatos/PDF/herramientas/paletas, Dosen pasante/undo general/admin visual y servicio/identidadWindows/PKIproductiva/Windowslimpio/otroequipo/licencias/recuperaciónintegral/manualfinal. QA/adopción final corresponden a Wascar. Registros siguientes históricos.'''
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md']:prepend(p,summary)
    prepend('development/server/README.md',summary.replace('](INTEGRACION-','](../../docs/INTEGRACION-').replace('](PLAN-','](../../docs/PLAN-').replace('](../evidence/','](../../evidence/'))
    short='''**Grupo833–847 vigente ·18.10.2026.** Perfil/ZIPWindows832 y copiaQA11→11 probados y revisados; nuevaQA832 seleccionada con origen712 conservado.77casos disponibles restaurado/8original, incluidos QA75–77 XLSHTML. New/Restore públicos, HTTPS/multiusuario/recibos/35tablas y rechazo de retorno con actividad probados; app/GUI/SQL/dependencias sin nuevas compilaciones/versiones. Sólo6intros corregidas, sin resultados de Wascar modificados. Global78/100, adopción final pendiente. [Contrato](INTEGRACION-XLS-WINDOWS-QA-S1.md), [evidencias y límites](../evidence/s1-20261018/quince-tandas-833-847/CIERRE.md). Registros siguientes históricos.'''
    for p in ['docs/BRIEFING-MAESTRO.md','docs/QA-COLABORACION-Y-RESTAURACION.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:prepend(p,short)
    prepend('CHANGELOG.md','''## 18.10.2026 · Grupo833–847 · Integración Windows/QA del XLS RC9

- Perfil cerrado832 con38artefactos/esquema11 y dosZIP reproducibles; versiones y perfiles anteriores conservados,0compilaciones.
- New y Restore públicos del ZIP comprobados con HTTPS/doscuentas/XLS/replay/reinicio,35tablas/recibos/bytes y sesiones revocadas sólo en recuperación administrativa. CRT intacto.
- Nuevo motor de copia11→11: cuentas/sesiones/privados/historia exactos, nuevasbases/secretos y recuperación712; selección por puntero tras revisión propia independiente y GO técnico. Actividad compensada impide retorno.
- NuevaQA832 seleccionada con origen712 conservado,77+8casos disponibles. Seisintros corregidas sin cambiar pasosrestantes/expected/notas. Global78/100; servidor final y adopción pendientes. [Cierre](evidence/s1-20261018/quince-tandas-833-847/CIERRE.md).''')
    prepend('docs/PROGRESO-GLOBAL.md','''**Grupo833–847 cerrado ·18.10.2026:78/100 provisional, sin aumento.** XLSHTML RC9 ya integrado en perfilWindows/ZIP832 reproducible y nuevaQA832/schema11, con origen712 conservado. New+Restore públicos/HTTPS/multiusuario/35tablas/recibos y motor de copia/retorno probados, revisiónPG propia independiente antes de selección.77casos disponibles restaurado/8original, QA75–77 habilitados; sólo6intros de guía corregidas, sin resultados de Wascar alterados. Aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 intactos: integra un formato ya contado, sin puntos por15IDs/ZIP/suites. [Evidencias/atribución/límites](../evidence/s1-20261018/quince-tandas-833-847/CIERRE.md).

Pendientes: formatos/PDF/herramientas/paletas/accesibilidad/aceptaciónEN/DE/ES, Dosen/undo/admin, servicio/identidadWindows/PKIproductiva/Windowslimpio/otroequipo/CRT elevado/licencias, recuperaciónintegral/retención/manualfinal y QA/adopción de Wascar. Estimación de alcance, no créditos/calendario ni porcentaje de pruebas aprobadas. Registros siguientes históricos.''')
    path=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(path.read_bytes());m.update(revision='2026-10-18-quince833-847',progress=78,snapshot='15/15hitos: Windows/ZIP832 y copiaQA11→11 probados/revisados; nueva832 seleccionada,origen712 conservado.77+8casos disponibles,78estimado.',currentBatch=dict(count=15,completed=15,ledger='docs/PLAN-QUINCE-TANDAS-833-847.json',evidence=ER+'/CIERRE.md'))
    def visit(items):
        for x in items:
            if x.get('id')=='rc9-excel-html':x.update(status='Probado y revisado · integrado Windows/QA832',qa='QA75–77 · disponibles restaurado832',evidence=ER+'/CIERRE.md',note='Perfil832/ZIP reproducible/New/Restore/35tablas y copiaQA11→11 probados; origen712 conservado. Office anterior87valores exactos/sinfórmulas,tablasenDevices; no treshojaspobladas ni adopción.')
            if 'QA75–77 pendientes de integrar832' in x.get('note',''):x['note']=x['note'].replace('QA75–77 pendientes de integrar832','QA75–77 disponibles en nuevaQA832')
            if 'QA75–77 pendientes de integración' in x.get('note',''):x['note']=x['note'].replace('QA75–77 pendientes de integración','QA75–77 disponibles en nuevaQA832')
            visit(x.get('children',[]))
    visit(m['streams']);m['history'].append(dict(id='h833-847',name='833–847 · PerfilWindows/ZIP832 y copiaQA11→11',status='Probado y revisado',note='15hitos internos,77+8casos disponibles,origen712 conservado;78sin aumento,adopción pendiente.'))
    m['nextMilestones']=[x for x in m['nextMilestones'] if not x.startswith('Integrar candidata832-02')]
    assert [x['points'] for x in m['streams']]==[18,22,14,14,9,1];save('docs/MAPA-ENTREGA.json',m)
    print(json.dumps(dict(completed=15,progress=78,actualQaRevision=832,availableRestoredCases=77,manualWascarResultsWritten=False)))
if __name__=='__main__':main()
