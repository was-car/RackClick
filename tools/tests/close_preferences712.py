"""Close the bounded personal-preferences block after native and independent evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-653-712';E=ROOT/ER
def read(p):return json.loads((E/p).read_bytes())
def save(p,d):(ROOT/p).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def prepend(p,text):
    path=ROOT/p;old=path.read_bytes()
    if b'Grupo653' in old[:2500]:raise SystemExit('Preserve closure; do not repeat')
    first,sep,rest=old.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    path.write_bytes(first+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+rest)
def main():
    assert read('backend/postgres01/result.json')['successful'] and read('backend/postgres01/result.json')['testsRun']==8
    assert read('frontend/edge-02/fixture.json')['result']=='PASS'
    assert read('frontend/edge-03-visual-final02/fixture.json')['result']=='PASS'
    assert read('native-backup01/result.json')['successful'] and read('native-backup01/result.json')['observations']['tableCount']==35
    assert read('legacy-smoke-final02/fixture.json')['result']=='PASS' and read('QA-TESTS-01.json')['successful']
    assert read('revision/SEAL-REVISION.json')['ownPostgresFocusPassed']
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-653-712.json').read_bytes());assert plan['completed']==0
    for row in plan['batches']:
        i=row['id']
        if i<=671 or 694<=i<=700:ev='backend/postgres01/result.json'
        elif i<=690:ev='frontend/CIERRE-FRONTEND.json'
        elif i<=693:ev='BUILD-01.json' if i!=693 else 'BUILD-02.json'
        elif i<=702:ev='frontend/edge-02/fixture.json'
        elif i<=704:ev='frontend/edge-03-visual-final02/fixture.json'
        elif i==705:ev='native-backup01/result.json'
        elif i<=707:ev='revision/REVISION-INDEPENDIENTE.md'
        elif i<=709:ev='QA-TESTS-01.json'
        else:ev='CIERRE.md'
        assert (E/ev).is_file()
        row.update(status='verified',evidence=ER+'/'+ev,independentEvidence=ER+'/revision/REVISION-INDEPENDIENTE.md')
    plan.update(completed=60,finalProgress=78,closed='2026-10-18',
        evidenceAttribution='60 bounded milestones, not 60 modules/suites. C#01/PG/Node/fullEdge02 and frontend-only visualFINAL02 distinguished; CLIRecovery11 constant reviewed but CLI not executed.',
        acceptance='New personal language/theme in development11. Current selected QA592/schema10 and Windows652 package retained. QA72–74 unavailable; manual Wascar QA/adoption pending.')
    save('docs/PLAN-SESENTA-TANDAS-653-712.json',plan)
    summary='''**Grupo653–712 cerrado ·18.10.2026:60/60 hitos internos; avance global estimado78/100, sin aumento.** Nueva persistencia personal de idioma EN/DE/ES y tema claro/oscuro, por usuario autenticado incluso lector/sin clientes. Reutiliza Settings RC9; login sin preferencia mantiene fallback anónimo sin escribir; logout/switch no heredan al actor anterior. Commit+GET, revisión propia, conflictos, recibos/fences y recuperación original, sin cambiar inventario/Systemhaus ni otorgar edición.

SQL011 aditiva (35tablas), C#11 y GUI712 FINAL02 probados en Windows/PostgreSQL/Edge. Domain76, backend8/8, Node16/16, Edge multisesión/reinicio y foco visual390px, backup/restore35tablas y regresión existente14comprobaciones correctos. Revisión independiente PG1/Node1 y capturas, con atribución separada. Una publicaciónC# y2buildsfrontend (segundo sólo clase visual); SQL001–010, dependencias, CSS/RC9/Click-Click conservados. Fallos de arnés originales y límites documentados.

Función lista en desarrollo11; QA restaurado592/esquema10 y ZIP652 conservados. Guías74casos con71restaurado/8original disponibles; nuevos QA72–74 NO DISPONIBLES hasta integración Windows/QA11 verificada. No login/DML/selección en QA real, ni cambios de resultados/observaciones de Wascar. [API/contrato](API-PREFERENCIAS-PERSONALES-S1.md), [plan60](PLAN-SESENTA-TANDAS-653-712.json), [informe/pruebas/límites](../evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md). Nueva capacidad personal comprobada; no cierra el punto entero restante de paridad mientras faltan herramientas/formatos/paletas/accesibilidad/aceptación. Aportes18/22/14/14/9/1 y pesos intactos. Próximo: integración11 conservadora, funciones pendientes y entrega Windows completa. Registros siguientes históricos.'''
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md']:prepend(p,summary)
    prepend('development/server/README.md',summary.replace('](API-','](../../docs/API-').replace('](PLAN-','](../../docs/PLAN-').replace('](../evidence/','](../../evidence/'))
    for p in ['docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:
        prepend(p,'''**Grupo653–712 cerrado ·18.10.2026.** Idioma/tema propios persistidos en desarrollo11, sin cliente ni capacidad de inventario requerida; commit/revisión/recuperación y aislamiento probados/revisados. CSS, RC9 y datos de inventario conservados. S-26 no se completa por preferencias personales. QA/ZIP10 intactos, QA72–74 no disponibles; global78/100 sin aumento por criterio entero de paridad todavía parcial. [Contrato](API-PREFERENCIAS-PERSONALES-S1.md), [pruebas y límites](../evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md). Registros siguientes históricos.''')
    prepend('docs/BRIEFING-MAESTRO.md','''**Grupo653–712 vigente ·18.10.2026.** S1 autorizado, nueva configuración personal idioma/tema probada/revisada en desarrollo11. QA592/10 y paquete652 retenidos,74casos/71+8disponibles; nuevos72–74 pendientes de integración. Global78/100 estimado; sin QA/adopción de Wascar. [Continuidad](CONTINUIDAD-CODEX.md), [cierre y próximos pasos](../evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md). Estados siguientes históricos.''')
    prepend('CHANGELOG.md','''## 18.10.2026 · Grupo653–712 · Idioma y tema propios de cada usuario

- SQL011 y API/me/preferences: propietario de sesión, revisión personal, patch explícito, idempotencia/fences/rollback/auditoría; cualquier usuario activo, sin cliente ni permisos nuevos. GET ausente0/null sin escritura.
- Settings RC9 conservado: fallback anónimo separado, commit+GET, diario compacto y recuperación por actor/generación. Reauth tardía fuerza entrada segura; ajuste visual mínimo con clase RC9 existente, sin CSS nuevo.
- Domain76, PG8/8, Node16/16, Edge completo/visual390px, independientePG1/Node1, backup/restore35 y regresión existente14checks correctos. Fallos de arnés preservados;1publishC#+2frontbuilds. CLIrecover11 alineado estáticamente, no ejecutado.
- QA592/10 y ZIP652 intactos;74casos/71+8disponibles, nuevos72–74 pendientes. Global78/100 aproximado sin aumento; [informe y límites](evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md).''')
    prepend('docs/PROGRESO-GLOBAL.md','''**Grupo653–712 cerrado ·18.10.2026:78/100 provisional, sin aumento.** Nueva capacidad idioma/tema personal persistida por actor, sin herencia entre cuentas, probada/revisada Windows/PostgreSQL/Edge y recuperación de datos35tablas. Es avance funcional real, pero no cierra el punto entero restante de paridad14/15 mientras faltan formatos/herramientas/paletas/accesibilidad/aceptación. No puntos por60IDs o suites. Aportes18/22/14/14/9/1, pesos20/25/15/15/15/10 intactos. [Pruebas, correcciones y límites](../evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md).

Candidata712 FINAL02/esquema11 sólo desarrollo; QA592/10 y ZIP652 retenidos. Guías74casos/71restaurado+8original disponibles,72–74pendientes. Falta integrar11 en operación/QA, funciones RC9/admin/Dosen/undo/formatos/herramientas/paletas, servicio/identidad/PKI/Windows limpio/otro equipo/licencias/recuperación integral/retención/manualfinal/QAadopción. Estimación de alcance entero provisional, no porcentaje de tests, créditos o calendario. Registros siguientes históricos.''')
    p=ROOT/'docs/PROGRESO-GLOBAL.md';lines=p.read_bytes().splitlines(keepends=True)
    prefix=b'| Paridad funcional/visual RC9 completa |';replacement='| Paridad funcional/visual RC9 completa | 15 | 14 | Informes, etiquetas, catálogo/plantillas y avisos disponibles; idioma/tema personal probado en desarrollo11. Faltan integración11, formatos/herramientas/paletas restantes, accesibilidad y aceptación completa EN/DE/ES |'.encode()
    p.write_bytes(b''.join(replacement+(b'\r\n' if line.endswith(b'\r\n') else b'\n') if line.startswith(prefix) else line for line in lines))
    contract=ROOT/'docs/API-PREFERENCIAS-PERSONALES-S1.md'
    with contract.open('a',encoding='utf-8') as f:f.write('\n\nResultado: implementado y comprobado/revisado en [cierre653–712](../evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md), candidata712 FINAL02. Nuevos QA72–74 no disponibles en QA592/10. Instalación/recuperación de aplicación/CLI11 y selecciónQA11 pendientes; backup/restore ejecutado sólo de datos en base aislada.\n')
    m=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());m.update(revision='2026-10-18-sesenta653-712',progress=78,
        snapshot='60/60hitos: idioma/tema personal probado y revisado en desarrollo11. QA592/10 y ZIP652 retenidos;74casos/71+8disponibles,72–74pendientes.78/100sin aumento.',
        currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-653-712.json',evidence=ER+'/CIERRE.md'))
    parity=next(x for x in m['streams'] if x['id']=='parity');parity['children'].append(dict(id='personal-language-theme',name='Idioma y tema personales por cuenta, con confirmación de servidor',status='Probado y revisado · desarrollo11',qa='QA72–74 · no disponible en592/10',evidence=ER+'/CIERRE.md'))
    m['history'].append(dict(id='h653-712',name='653–712 · idioma/tema persistidos por usuario',status='Probado y revisado',note='60hitos internos,78sin aumento por paridad aún incompleta; QA/ZIP10 conservados.'))
    m['nextMilestones']=['Integrar schema11 en operadores/paquete/QA con copia nueva, CLI11 probado, rollback guardado y datos/cuentas conservados.']+[x.replace('preferencias,','paletas/preferencias restantes,') for x in m['nextMilestones']]
    assert [s['points'] for s in m['streams']]==[18,22,14,14,9,1] and sum(s['weight'] for s in m['streams'])==100
    save('docs/MAPA-ENTREGA.json',m);print(json.dumps({'completed':60,'progress':78,'actualQaSelectionPerformed':False}))
if __name__=='__main__':main()
