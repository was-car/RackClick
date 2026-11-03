"""Close integration milestones only after native/review/real-selection gates."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-593-652';E=ROOT/ER
def load(p):return json.loads((ROOT/p).read_bytes())
def save(p,d):(ROOT/p).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def prepend(p,text):
    path=ROOT/p;old=path.read_bytes()
    if b'Grupo593' in old[:2500]:raise SystemExit('Preserve existing closure; do not repeat')
    first,sep,rest=old.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    path.write_bytes(first+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+rest)
def main():
    assert load(ER+'/COORDINATOR-GO.json')['valid']
    assert load(ER+'/REAL-QA-ACTIVATE-01.json')['state']=='committed'
    assert load(ER+'/REAL-QA-VALIDATE-01.json')['valid']
    assert load(ER+'/QA-MATRIX-652.json')['previous68Except67Unchanged']
    assert load(ER+'/PACKAGES-03.json')['byteIdentical']
    gates=load(ER+'/CLOSURE-GATES.json');assert gates['valid'] and all((ROOT/p).is_file() for p in gates['evidence'].values())
    plan=load('docs/PLAN-SESENTA-TANDAS-593-652.json');assert plan['completed']==0
    for x in plan['batches']:
        i=x['id']
        if i<=597 or i==607:ev=gates['evidence']['windowsSummary']
        elif i<=606 or 614<=i<=622:ev=gates['evidence']['windowsSummary']
        elif i<=611:ev=ER+'/MANUALES-FINAL02.json'
        elif i<=613:ev=ER+'/PACKAGES-03.json'
        elif i<=646:ev=gates['evidence']['transition']
        elif i==647:ev=ER+'/revision/GATE-TECNICO-02.json'
        elif i==648:ev=gates['evidence']['independentTransition']
        elif i==649:ev=ER+'/REAL-QA-ACTIVATE-01.json'
        elif i==650:ev=ER+'/QA-TESTS-01.json'
        else:ev=ER+'/CIERRE.md'
        assert (ROOT/ev).is_file()
        x.update(status='verified',evidence=ev,independentEvidence=ER+'/revision/GATE-TECNICO-02.json')
    plan.update(completed=60,finalProgress=78,closed='2026-10-18',
        evidenceAttribution='CIERRE distinguishes implementers Windows/PG tests, independent own focuses and coordinator real copy/selection.60 milestones are not60 modules/suites.',
        acceptance='Internal schema10 package and QA selected in a NEW lab. Source532/schema9 and old packages retained. Manual Wascar QA/final adoption pending.')
    save('docs/PLAN-SESENTA-TANDAS-593-652.json',plan)
    summary='''**Grupo593–652 cerrado · 18.10.2026:60/60 hitos internos; avance global estimado78/100, sin aumento.** Esquema10 integrado en distribución, instalación New y recuperación Restore de Windows, con perfiles337/397/532 de esquema9 preservados. Candidata/GUI592 reutilizadas sin recompilar; dependencias y SQL001–009 intactos. Dos ZIP idénticos y cuatro manuales actualizados; instalación nueva, HTTPS/roles/escritura/otra sesión, compartidas, reinicio, backup y Restore10 comprobados en laboratorios Windows/PostgreSQL. Backup9 con Stage10 se rechaza en un parcial nuevo antes de crear administrador.

QA restaurado seleccionado en592/esquema10 mediante copia a clúster nuevo con candidata10 y recuperación9 separada. Origen532, datos/cuentas/contraseñas/sesiones/permisos y archivos privados conservados; nuevos secretos PostgreSQL. Sin login ni DML de aplicación en el QA real y sin concesión automática de templates.publish. Actividad, incluso compensada, bloquea retorno/conmutación; fallos de arnés conservados, revisión independiente separada. Ambas ramas detenidas al cerrar.

Guías71casos disponibles en restaurado/8original, sin resultados manuales nuevos; QA69–71 ya preparados para publicación explícita mediante grupos. Usa INICIAR-QA-RESTAURADO.cmd y su guía/credenciales privadas locales. QA/adopción final siguen siendo de Wascar. [Contrato de integración](INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md), [plan60](PLAN-SESENTA-TANDAS-593-652.json), [pruebas/atribución/fallos/límites](../evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md). Próximo: funciones RC9/admin/Dosen/undo pendientes y servicio/identidad/PKI/Windows limpio/recuperación integral/manualfinal. Registros siguientes históricos.'''
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md']:prepend(p,summary)
    for p in ['docs/BRIEFING-MAESTRO.md','docs/QA-COLABORACION-Y-RESTAURACION.md']:
        prepend(p,'''**Grupo593–652 vigente ·18.10.2026:78/100 estimado.** S1 sigue autorizado y adopción pendiente. Paquete interno Windows/New/Restore10 probado; QA restaurado592 seleccionado por copia a otro clúster, conservando fuente532/9, cuentas/permisos/sesiones y privados.71casos disponibles en restaurado/8original; publicación exige permiso explícito mediante grupos. No nuevos Pass de Wascar ni cambios de sus notas. [Continuidad](CONTINUIDAD-CODEX.md), [atribución/fallos/límites](../evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md). Fechas/estados siguientes son históricos.''')
    prepend('development/server/README.md',summary.replace('](INTEGRACION-','](../../docs/INTEGRACION-').replace('](PLAN-','](../../docs/PLAN-').replace('](../evidence/','](../../evidence/'))
    for p in ['docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:
        prepend(p,'''**Grupo593–652 cerrado ·18.10.2026.** Operadores/paquete/Restore10 verificados en Windows y QA restaurado592 seleccionado por copia conservadora a otro clúster. Fuente532/esquema9 y paquetes históricos conservados;71casos disponibles en restaurado/8original, sin nuevos Pass manuales. S-26 compartidas habilitado para QA con permiso explícito, sin aceptación total. Global78/100 estimado sin aumento: consolida funciones ya contadas. [Integración](INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md), [pruebas/revisión/límites](../evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md). Registros siguientes históricos.''')
    prepend('CHANGELOG.md','''## 18.10.2026 · Grupo593–652 cerrado · Integración Windows y QA esquema10

- Perfil592 cerrado de37 archivos y SQL001–010, compatible con los tres perfiles9 históricos. New10 y Restore10 en destinos nuevos; esquema mezclado rechazado antes de recuperación administrativa, sin migración implícita.
- Dos ZIP idénticos, runtime/PG fijados,25operadores y4manuales; recorrido nativo Windows/PG de instalación, permisos, compartidas, persistencia, otra sesión, backup, recuperación10 y regreso al origen. Fallos de arnés originales conservados.
- Motor nuevo de copia532→592: nuevo clúster con candidata10 y recuperación9, secretosPG nuevos, cuentas/sesiones/permisos intactos, watermarks/locks/readiness/puntero atómico/retorno guardado. Focos independientes separados de implementación.
- QA real seleccionado tras GO técnico y detenido; guías71+8 disponibles sin resultados de Wascar alterados. Global78/100 sin aumento; servicio/PKI/Windows limpio/recuperación integral/manual final y QA/adopción pendientes. [Cierre reproducible](evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md).''')
    prepend('docs/PROGRESO-GLOBAL.md','''**Grupo593–652 cerrado ·18.10.2026:78/100 provisional, sin aumento.** Perfil10 integrado en operadores/ZIP New/Restore y QA592 seleccionado mediante copia verificada a laboratorio nuevo; fuente532/9 conservada. Windows/PG nativos, revisión independiente y guías71restaurado/8original disponibles, sin nueva QA manual. Consolida la capacidad compartida ya contabilizada; no suma por60IDs, ZIP, suites o selección. Aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 intactos. [Pruebas/fallos/atribución](../evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md).

Faltan funciones RC9/admin/Dosen/undo/preferencias/herramientas/formatos, servicio/identidad Windows/PKI productiva, Windows limpio/otro equipo/CRT elevado, licencias, recuperación integral/retención/manualfinal y QA/adopción de Wascar. Es estimación de alcance, no porcentaje de tests/créditos/calendario. Registros siguientes históricos.''')
    p=ROOT/'docs/PROGRESO-GLOBAL.md';lines=p.read_bytes().splitlines(keepends=True);updated=[]
    rows={
        '| Jerarquía e inventario compartido |':'| Jerarquía e inventario compartido | 25 | 22 | Lotes por IDs, creación/edición, compensación acotada, privadas/editor y biblioteca publicada por cliente probadas. Publicación y edición separadas; integración10 en QA/paquete verificada. Faltan undo general, Dose pasante y combinaciones restantes |',
        '| Paridad funcional/visual RC9 completa |':'| Paridad funcional/visual RC9 completa | 15 | 14 | Avisos, PoE, consultas, CSV/XLSX, HTML, etiquetas, SVG y catálogo/favoritos/plantillas/editor disponibles. Compartidas10 integradas para QA; faltan PDF nativo/paridad XLS RC9, preferencias/herramientas, accesibilidad y aceptación completa EN/DE/ES |'}
    for line in lines:
        replacement=next((new for prefix,new in rows.items() if line.startswith(prefix.encode())),None)
        updated.append(replacement.encode()+(b'\r\n' if line.endswith(b'\r\n') else b'\n') if replacement else line)
    p.write_bytes(b''.join(updated))
    contract=ROOT/'docs/INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md';s=contract.read_text(encoding='utf-8')
    s+='\n\nResultado: integrado y probado/revisado según [cierre593–652](../evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md). QA real592 seleccionado en otro laboratorio con origen532 intacto; guías71+8 disponibles, sin QA manual ni adopción.\n';contract.write_text(s,encoding='utf-8')
    m=load('docs/MAPA-ENTREGA.json');m.update(revision='2026-10-18-sesenta593-652',progress=78,
        snapshot='60/60hitos: paquete Windows New/Restore10 probado y QA592 seleccionado por copia en laboratorio nuevo. Fuente532/9 conservada;71+8casos disponibles.78/100estimado sin aumento.',
        currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-593-652.json',evidence=ER+'/CIERRE.md'))
    def visit(items):
        for x in items:
            if x.get('id') in ('shared-customer-templates','shared-templates'):
                x.update(status='Probado y revisado · integrado Windows/QA10',qa='QA69–71 · disponible en restaurado592',evidence=ER+'/CIERRE.md')
            if x.get('id')=='templates':x['note']='BASE, favoritos, privadas/editor y publicación compartida probados; compartidas10 integradas en paquete/QA. Preferencias y aceptación restantes pendientes.'
            visit(x.get('children',[]))
    visit(m['streams']);m['history'].append(dict(id='h593-652',name='593–652 · paquete/Restore10 y copia QA9→10',status='Probado y revisado',note='60hitos internos; origen532/9 conservado,71+8casos disponibles;78sin aumento. QA/adopción pendientes.'))
    m['nextMilestones']=[x for x in m['nextMilestones'] if not x.startswith('Integrar y verificar schema10')]
    assert [s['points'] for s in m['streams']]==[18,22,14,14,9,1] and sum(s['weight'] for s in m['streams'])==100
    save('docs/MAPA-ENTREGA.json',m)
    print(json.dumps(dict(completed=60,progress=78,qaSelectionPerformed=True,manualWascarResultsWritten=False)))
if __name__=='__main__':main()
