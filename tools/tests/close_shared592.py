"""Close the shared-template milestones after native evidence; never changes QA data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-533-592';E=ROOT/ER
def load(p):return json.loads((ROOT/p).read_bytes())
def save(p,d):(ROOT/p).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def prepend(p,text):
    path=ROOT/p;old=path.read_bytes()
    if b'Grupo533' in old[:1800]:raise SystemExit('Preserve existing closure; do not repeat')
    first,sep,rest=old.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    addition=text.strip().encode().replace(b'\n',nl)
    path.write_bytes(first+sep+nl+addition+nl+rest)
def main():
    b=load(ER+'/backend/postgres01/result.json');r=load(ER+'/revision/pg-own01/result.json')
    f=load(ER+'/frontend/gui-notice03/fixture.json');n=load(ER+'/native-backup02/result.json')
    assert b['successful'] and b['testsRun']==8 and r['successful'] and r['testsRun']==2
    assert f['result']=='PASS' and n['successful'] and n['observations']['tableCount']==33
    assert all(d['labStopped'] and d['serversStopped'] for d in [b,r,f,n])
    plan=load('docs/PLAN-SESENTA-TANDAS-533-592.json');assert plan['completed']==0
    for x in plan['batches']:
        i=x['id']
        if i<=559 or 578<=i<=586:ev='backend/postgres01/result.json'
        elif i<=577:ev='frontend/gui02/fixture.json'
        elif i==587:ev='CIERRE.md'
        elif i==588:ev='revision/pg-own01/result.json'
        elif i==589:ev='QA-TESTS-01.json'
        else:ev='CIERRE.md'
        if i==568:ev='frontend/gui-notice03/fixture.json'
        if i==586:ev='native-backup02/result.json'
        assert (E/ev).is_file()
        x.update(status='verified',evidence=ER+'/'+ev,independentEvidence=ER+'/revision/REVISION-INDEPENDIENTE.md')
    plan.update(completed=60,finalProgress=78,closed='2026-10-18',
        evidenceAttribution='CIERRE distinguishes original592 PG/full GUI/native DB backup and FINAL02 feed focal;60milestones are not60suites/modules.',
        acceptance='Development schema10 only; real QA and ZIP532/schema9 unchanged. Wascar QA/adoption pending.')
    save('docs/PLAN-SESENTA-TANDAS-533-592.json',plan)
    summary='''**Grupo533–592 cerrado · 18.10.2026: 60/60 hitos internos; avance global estimado78/100 (77→78).** Plantillas compartidas por cliente: publicar copia privada propia nueva e inmutable, consulta/uso por otros técnicos y retirada sin afectar originales/equipos. `templates.publish` por grupos y ámbitos separa publicación de edición; migración10 no autoconcede permisos. RC9, Click-Click y EN/DE/ES conservados.

Windows/PostgreSQL: backend8/8 y revisión independiente propia2/2; Edge multiactor y focoFINAL02 de avisos correctos. Backup/restore nativos genéricos conservan33tablas en otra base/propietario; no recuperación de aplicación ni instalación10. DosP2 independientes corregidos (generación/avisos); fallos iniciales de arnés y fuentes originales conservados. SQL001–009 y versiones fijadas intactos.

Candidata592/schema10 sólo desarrollo probado: QA restaurado y ZIP532/schema9 intactos. Guías71casos, disponibilidad68restaurado/8original; QA69–71 nuevos NO DISPONIBLES. No Pass de Wascar ni adopción. [Contrato](API-PLANTILLAS-COMPARTIDAS-S1.md), [plan60](PLAN-SESENTA-TANDAS-533-592.json), [informe/pruebas/atribución/límites](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md). Inventario21→22/25 por biblioteca publicada multiusuario antes ausente, sin puntos porIDs/tests/DDL/backup. Próximo: integrar/verificar esquema10 en operadores/paquete/QA y cerrar funciones/Windows/QA final. Registros siguientes históricos.'''
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md']:
        prepend(p,summary)
    prepend('development/server/README.md',summary.replace('](API-','](../../docs/API-').replace('](PLAN-','](../../docs/PLAN-').replace('](../evidence/','](../../evidence/'))
    for p in ['docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:
        prepend(p,'''**Grupo533–592 cerrado · 18.10.2026.** Publicación compartida por cliente, permiso específico y creación por otros técnicos probadas/revisadas en laboratorio10; no privadas ajenas ni cambios en originales/equipos. S-26 tiene compartición implementada en desarrollo, con integración/QA manual todavía pendientes; no aceptación total de paridad. QA/ZIP532 de esquema9 intactos; QA69–71 documentados NO DISPONIBLES. Global78/100 estimado. [Contrato](API-PLANTILLAS-COMPARTIDAS-S1.md), [pruebas, fallos y límites](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md). Los registros siguientes son históricos.''')
    prepend('CHANGELOG.md','''## 18.10.2026 · Grupo533–592 cerrado · Plantillas compartidas por cliente

- SQL010 aditiva y permiso templates.publish por grupos/ámbitos; publicación privada propia como copia inmutable, consulta, retirada y uso por otros técnicos. Sin autoconcesiones ni cambios en SQL001–009/digests privados. Bootstrap nuevo incluye la capacidad; admin histórico puede concederla explícitamente.
- GUI RC9 EN/DE/ES, diario compacto y recuperación, validadores administrativos10capacidades y avisos de instanciación. DosP2 independientes corregidos; errores y fuentes anteriores conservados.
- Backend8/8PG, independiente2/2PG, Edge multiactor/focoFINAL02 y backup/restore aislado33tablas correctos. Una publicaciónC# y dosbuildsfrontend, segundo sólo por arreglo del feed; no suites completas repetidas por cada hito.
- QA/ZIP532 schema9 sin cambios; guías71casos/68+8disponibles, nuevos69–71 pendientes. [Cierre reproducible y atribución](evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md). Global78/100 aproximado; paquete/operación10 y QA/adopción final pendientes.''')
    prepend('docs/PROGRESO-GLOBAL.md','''**Grupo533–592 cerrado · 18.10.2026:78/100 provisional (77→78).** Inventario21→22/25 por biblioteca publicada multiusuario por cliente antes ausente, con permiso específico separado de edición, copias inmutables e instanciación por otro técnico probadas en Windows/PostgreSQL/Edge y revisión independiente. Aportes18/22/14/14/9/1, pesos20/25/15/15/15/10 intactos. No puntos por60IDs, DDL, tests o backup genérico. [Cierre y límites](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md).

Esquema10 de desarrollo; QA/ZIP532 en9 conservados. Guías71casos con68/8disponibles y69–71pendientes; sin nueva QA manual. Paridad14/15 continúa parcial por funciones restantes/integración/aceptación. Windows9/15 no aumenta: restauración aislada de datos10 no es instalación/recuperación completa. Faltan operadores/paquete/QA10, preferencias/formatos/herramientas/Dosen/undo/admin restantes, servicio/identidad/PKI, Windowslimpio/otro equipo/CRT elevado, licencias, recuperación integral/retención/manualfinal y QA/adopción. Es alcance estimado, no tests/créditos/calendario. Registros siguientes históricos.''')
    p=ROOT/'docs/PROGRESO-GLOBAL.md'
    rows={
        '| Jerarquía e inventario compartido |':'| Jerarquía e inventario compartido | 25 | 22 | Lotes por IDs, creación/edición, compensación acotada, privadas/editor y biblioteca publicada por cliente probadas. Publicación y edición tienen permisos distintos. Falta integración compartida10 en QA/paquete, undo general, Dose pasante y combinaciones restantes |',
        '| Paridad funcional/visual RC9 completa |':'| Paridad funcional/visual RC9 completa | 15 | 14 | Avisos, PoE, consultas, CSV/XLSX, HTML, etiquetas, SVG y catálogo/favoritos/plantillas/editor disponibles o probados. Compartidas10 probadas en laboratorio; faltan integración/QA, PDF nativo/paridad XLS RC9, preferencias/herramientas, accesibilidad y aceptación completa EN/DE/ES |',
        '| **Total** |':'| **Total** | **100** | **78** | **Servidor final pendiente** |'}
    lines=p.read_bytes().splitlines(keepends=True);updated=[]
    for line in lines:
        replacement=next((new for prefix,new in rows.items() if line.startswith(prefix.encode())),None)
        updated.append(replacement.encode()+(b'\r\n' if line.endswith(b'\r\n') else b'\n') if replacement else line)
    p.write_bytes(b''.join(updated))
    c=load('docs/QA-CASOS-WASCAR.json');assert len(c['cases'])==71;c['globalProgressEstimate']=78;save('docs/QA-CASOS-WASCAR.json',c)
    p=ROOT/'docs/API-PLANTILLAS-COMPARTIDAS-S1.md';text=p.read_text(encoding='utf-8')
    text=text.replace('Estado inicial: implementación autorizada, todavía sin evidencia nueva. Base532 y avance77/100;',
        'Estado: implementado y probado/revisado en laboratorios Windows/PostgreSQL/Edge, candidata592/schema10; avance78/100 estimado. Base532 conservada;')
    text+='\n## Resultado del bloque\n\n[Informe completo](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md): ocho focosPG de backend, dos propios del revisor, Edge multiactor y foco de avisosFINAL02, backup/restore de datos aislado33tablas. QA69–71 detallados pero no disponibles enQA532. No operadores/paquete/recuperación de aplicación10 ni QA manual/adopción.\n'
    p.write_text(text,encoding='utf-8')
    m=load('docs/MAPA-ENTREGA.json');m.update(revision='2026-10-18-sesenta533-592',progress=78,
        snapshot='60/60hitos: biblioteca compartida por cliente probada/revisada en laboratorio10. QA/ZIP532 intactos;71casos/68+8disponibles,69–71pendientes.78/100estimado.',
        currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-533-592.json',evidence=ER+'/CIERRE.md'))
    inv=next(x for x in m['streams'] if x['id']=='inventory');inv['points']=22
    inv['children'].append(dict(id='shared-customer-templates',name='Biblioteca compartida por cliente con permiso específico e instanciación multiusuario',
        status='Probado y revisado · desarrollo10',qa='QA69–71 · no disponible en532',evidence=ER+'/CIERRE.md'))
    def visit(items):
        for x in items:
            if x.get('id')=='templates':x['note']='BASE, favoritos, privadas/editor y publicación compartida por cliente probados; compartidas10 aún sin paquete/QA y preferencias restantes pendientes.'
            if x.get('id')=='shared-templates':x.update(name='Publicación/retirada por cliente con templates.publish y uso por otros técnicos',status='Probado y revisado · desarrollo10',qa='QA69–71 · no disponible en532',evidence=ER+'/CIERRE.md')
            visit(x.get('children',[]))
    visit(m['streams']);m['history'].append(dict(id='h533-592',name='533–592 · compartidas por cliente y prueba de migración10',status='Probado y revisado',note='60hitos internos; QA/ZIP532 conservados.77→78; integración10/QA/adopción pendientes.'))
    m['nextMilestones']=['Integrar y verificar schema10 en operadores/paquete/QA conservando datos, cuentas, disponibilidad previa y recuperación.']+[x.replace('plantillas compartidas, ','').replace('publicación/preferencias','preferencias') for x in m['nextMilestones']]
    assert sum(x['points'] for x in m['streams'])==78 and sum(x['weight'] for x in m['streams'])==100
    save('docs/MAPA-ENTREGA.json',m)
    print(json.dumps(dict(completed=60,progress=78,qaSelectionPerformed=False,newQaCasesAvailable=False)))
if __name__=='__main__':main()
