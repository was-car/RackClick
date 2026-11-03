"""Close a bounded development block without claiming QA selection or adoption."""
import json
from init_onboarding1209 import ROOT,E,BASE,sha

ER=E.relative_to(ROOT).as_posix()
def read(name):return json.loads((E/name).read_bytes())
def prepend(name,text):
    path=ROOT/name;b=path.read_bytes();heading,sep,rest=b.partition(b'\n');nl=b'\r\n' if heading.endswith(b'\r') else b'\n'
    assert b'Bloque1150' not in b[:1500]
    path.write_bytes(heading+sep+nl+text.strip().encode('utf-8').replace(b'\n',nl)+nl+nl+rest)

def main():
    out=E/'CIERRE.md';assert not out.exists()
    native=read('gui04/fixture.json');node=read('NODE-FINAL-02.json');guide=read('QA-TESTS-01.json');own=read('revision/dom01/result.json');gate=read('revision/GATE-TECNICO.json');candidate=read('CANDIDATA1209-01.json')
    assert native['result']=='PASS' and native['inputsUnchanged'] and native['labStopped'] and native['serversStopped']
    assert node['successful'] and guide['successful'] and own['successful'] and gate['approved'] and not gate['openBlockingFindings']
    report=f'''# Bloque1150–1209 · continuación guiada del alta de usuario

Se desarrolló y revisó **Cuenta creada → Membresías → Permisos efectivos** sobre la administración RC9 existente. Tras un recibo confirmado, la tarjeta muestra el nombre guardado y UUID completo, y permite continuar explícitamente a los formularios existentes. No asigna grupos ni concede acceso al navegar. Cada guardado conserva su propia autorización, revisión, idempotencia y confirmación del servidor.

**Estado real:** candidata completa de desarrollo1209-01, esquema13, sin seleccionar en QA ni incorporar al perfil Windows. QA real1089/13, recuperación969/12 y paquete1149 permanecen intactos. Catálogo87casos:84 disponibles en restaurado y8 en original; **QA85–87 planned/no disponibles** hasta integración/selección futuras. No Pass de Wascar ni adopción final.

60hitos internos, no60funciones/suites. Global aproximado **78 % sin aumento**; aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 sin cambios. Esta mejora acotada avanza una administración ya parcial y no cierra la experiencia visual integral, auditoría restante o aceptación. Base Git `{BASE}`.

## Implementación y correcciones

AdminUsers.confirmed descartaba el recurso creado al limpiar el formulario. Ahora guarda sólo un recibo en memoria actor/solicitud/UUID/nombre/revisión desde un resultado validado, antes de limpiar el journal o recargar. Se admite POST confirmado, recuperación de committed y cancelación que recupera un commit previo; notRecorded/cancelación real/respuesta incierta/error no crean tarjeta.

Las continuaciones revalidan las guardas síncronas de estado, contraseña, sesiones, permisos y membresía, incluso con el mismo UUID. Grupos se monta en oculto tras una confirmación válida para cargar el journal diferido; no abre ni navega automáticamente. No se remonta un formulario para borrar sus borradores. La consulta efectiva indica Actualizar cuentas y Consultar permisos. Si Grupos ya estaba abierto antes del alta, puede requerir Actualizar grupos, como indica el guion.

Si falla limpiar el journal, se conservan pendiente y evidencia de commit; si falla sólo la recarga, se conserva el recibo bloqueado. Actor/generación invalidan respuestas tardías, incluida A→B→A. No hay contraseña ni almacenamiento nuevo en la tarjeta. El coordinador detectó antes de compilar un P2:401/403 bloqueaba continuación pero todavía mostraba nombre/UUID. FUENTES02 introduce autorización de lectura separada: denegación retira tarjeta/lista y sólo una lectura válida restaura su presentación. El revisor precisó texto de bloqueo y rechazo explícito de estados inesperados; ambos bordes quedaron resueltos antes del build. La redacción del contrato distingue denegación de un fallo transitorio que conserva el recibo.

Cambios de producto: AdminUsers.jsx y tres archivos nuevos (AdminUserOnboarding.jsx, admin-user-onboarding.ts y sus textos EN/DE/ES). Sin API/SQL/CSS/dependencias nuevos. Usuario, grupo y cliente conservan identidad UUID; los homónimos no se fusionan. Backend1089-02 sigue autorizando lecturas/escrituras; la GUI no decide permisos.

## Candidata y fuentes

Una compilación frontend con Node24.21.0/esbuild fijado, cero compilaciones C#.193fuentes congeladas; sólo una de las190 anteriores cambia y se añaden tres. Candidata `{candidate['candidateDirectory']}`:40artefactos,22servidor+18frontend, **{candidate['totalBytes']}bytes**, manifiesto SHA256 `{sha(E/'CANDIDATA1209-01.json')}`. Los22servidor son exactos a1089-02; sólo app.js cambia entre los18frontend, con CSS/fuentes/licencias/índice exactos. No instalaciones/descargas/cambios de versiones fijadas ni publicación externa.

## Pruebas realmente ejecutadas

| Responsable | Resultado y límite |
|---|---|
| Autor frontend | Node01:14PASS sobre freeze01; auth02:1PASS focal sobre freeze02. Son etapas del bloque, no15casos nuevos adicionales al final. No ejecutó build/PG/GUI. |
| Coordinador Node | NODE-FINAL-02:15/15PASS, exit0, {node['seconds']}s, fuentes finales exactas. Primer wrapper falló al esperar resumen TAP cuando Node emitió spec Unicode:log15PASS conservado y exit original de Node no registrado. Se fijó --test-reporter=tap y se ejecutó la regresión final; no se relabela el wrapper1 como exit0. |
| Coordinador Edge/PG | gui04:PASS/exit0 en {native['seconds']}s,10observaciones de GUI y comprobaciones SQL posteriores.4altas,1cancelación real, grupoUUID correcto entre homónimos, permisos efectivos y cliente limitado, sesión independiente/recarga, pérdida de respuesta201 y recuperación, cancelación que recupera committed, notRecorded sin tarjeta, guardas/Enter, EN/DE/ES390px, AX real y retirada tras403. Reinicio ASP.NET y nuevo login/lectura limitada verificados. PostgreSQL17.11/Windows11 reales, fixture/clúster nuevos, APP/PG detenidos. |
| Revisor independiente | dom01:1escenario propio PASS/exit0 en {own['seconds']}s, Edge/DOM/IndexedDB reales con HTTP controlado; **sinPG**. Fallo de eliminación IDB conserva recibo/journal; recuperación explícita y guard para mismoUUID; respuesta tardía A→B→A no revive recibo ni borra journal nuevo. Fuentes193/artefactos40 exactos; Edge/HTTP detenidos. No se atribuye autorización/persistencia PostgreSQL a ese foco. |
| Coordinador guía | {guide['testsRun']}/{guide['testsRun']}PASS en {guide['seconds']}s:87casos,84+8disponibles,85–87planned.84casos anteriores/listas/parejas completos exactos; generador y código de notas/importación/resultados byteidénticos. |

gui01–03 **siguen FAIL de wrapper**, con fuentes y diagnósticos preservados: gui01(34.141s) interceptó un GET200 al esperar POST201 y terminó con0observaciones; gui02(19.812s) obtuvo7observaciones antes de intentar cambiar idioma con preferencias aún cargando; gui03(19.812s) completó10observaciones de navegador/exit0, pero el SQL posterior usó user_group_id en user_group_member, cuya columna es group_id. No alcanzó reinicio. Se corrigieron sólo los arneses, sin cambiar ni recompilar producto; gui04 acredita el recorrido final completo. Los cuatro laboratorios propios quedaron detenidos; CIM confirmó0Edge de sus perfiles. No convertir los parciales en suites completas PASS.

El coordinador inspeccionó capturas ESdesktop y DEmóvil reales: nombre literal<img>/Unicode, UUID y botones legibles, ajuste390px y contraseñas vacías. AX/Enter no acredita voz de lector de pantalla. El revisor inspeccionó capturas propias; una imagen del guard desplazada a paneles inferiores sólo acredita destino estable, mientras que su bloqueo se prueba por DOM.

## QA y límites de entrega

Se prepararon QA85–87 con posiciones, campos, botones, expected y partes opcionales de red; permanecen bloqueados en el snapshot real1089. No cambiar parejas heredadas ni habilitarlos por compilar. Los84casos y resultados previos de Wascar se conservan; no se leen/escriben sus observaciones. Ambas guías regeneradas desde el catálogo real. Tu QA actual sigue disponible con INICIAR-QA-RESTAURADO.cmd.

Esta tanda no ejecuta app/login/SQL contra QA real ni cambia su configuración/puntero. Sus28archivos de raíz, artefactos, secretos/configuraciones y evidencias anteriores se verifican por hash. No modifica bases existentes, versiones fijadas ni HTML RC9 adoptado. El caso de revocación SQL pertenece únicamente a una fixture sintética: no prueba ni elude la protección del último administrador en la API de producto.

Siguiente: integrar1209 en Windows/QA preservando preparados, recuperaciones y datos; habilitar después QA85–87. Continúan administración integral/auditoría, funciones RC9/Dosen/undo/formatos, servicio/identidad/PKI, Windows limpio/otro equipo/CRT elevado/licencias, recuperación integral/retención/manual y QA/adopción final. No forest/LDAP, escala universal, instalación nueva de Windows ni servidor final.

Revisión técnica favorable precede al cierre documental. Verificación final y adenda independiente preceden al diff/SHA256SUMS nuevos y commit local. No publicación ni agentes activos después de finalizar.
'''
    out.write_text(report,encoding='utf-8')
    plan_path=ROOT/'docs/PLAN-SESENTA-TANDAS-1150-1209.json';plan=json.loads(plan_path.read_bytes());assert plan['completed']==0 and len(plan['batches'])==60
    for b in plan['batches']:
        i=b['id']
        name='INICIO.json' if i<1155 else 'NODE-FINAL-02.json' if i<1180 else 'SOURCE-FREEZE-APP.json' if i==1180 else 'BUILD-01.json' if i==1181 else 'CANDIDATA1209-01.json' if i<1185 else 'gui04/fixture.json' if i<1198 else 'revision/dom01/result.json' if i==1198 else 'revision/GATE-TECNICO.json' if i==1199 else 'QA-TESTS-01.json' if i<1204 else 'CIERRE.md'
        assert (E/name).is_file();b.update(status='verified',evidence=ER+'/'+name,independentEvidence=ER+'/revision/GATE-TECNICO.json')
        if i==1207:b['title']='Preparar adenda independiente de cierre'
    plan.update(completed=60,finalProgress=78)
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary=f'''**Bloque1150–1209 cerrado ·18.10.2026: continuación guiada del alta; global78 % aproximado sin aumento.** Cuenta creada→Membresías→Permisos efectivos usa recibo/UUID confirmado y guardas de borrador/journal/actor, sin asignación automática.193fuentes,1buildfrontend/0C#, servidor/CSS/SQL/dependencias exactos. Node15, Edge/PG nativo/reinicio y revisión DOM propia favorable; fallos de arnés y correcciones preservados.

Candidata1209-01 sólo desarrollo; QA1089/13 y paquete1149 conservados.87casos en guía,84restaurado/8original disponibles; QA85–87planned,84anteriores y resultados intactos. Siguiente: integración Windows/QA1209 y funciones/operación final pendientes. [Contrato](GUI-CONTINUACION-ALTA-USUARIO-S1.md), [60hitos](PLAN-SESENTA-TANDAS-1150-1209.json), [pruebas/límites](../{ER}/CIERRE.md). Registros siguientes históricos.'''
    for name in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(name,summary)
    short=f'''**Bloque1150–1209 vigente.** Continuación guiada de alta por UUID probada/revisada en candidata1209-01, esquema13/servidor1089 exactos. QA1089 y paquete1149 conservados;87casos/84+8disponibles,QA85–87planned. Global78 % aproximado; adopción pendiente. [Contrato](GUI-CONTINUACION-ALTA-USUARIO-S1.md), [pruebas/límites](../{ER}/CIERRE.md). Registros siguientes históricos.'''
    for name in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md','docs/UX-ADMINISTRACION-ARBOL.md','docs/QA-COLABORACION-Y-RESTAURACION.md']:prepend(name,short)
    for name in ['development/server/README.md','development/frontend/README.md']:prepend(name,short.replace('](GUI-','](../../docs/GUI-').replace('](../evidence/','](../../evidence/'))
    prepend('CHANGELOG.md',f'## 18.10.2026 · Bloque1150–1209 · Continuación de alta\n\n- Tarjeta con recibo/UUID y continuaciones a membresías/permisos, guardas de borrador/journal/actor y retirada401/403. Sin asignación automática.\n- Node15, Edge/PG/reinicio y revisión DOM independiente; errores originales de arnés preservados.1buildfrontend/0C#, servidor/SQL/CSS exactos.\n- Candidata1209 de desarrollo; QA1089/paquete1149 conservados. Guía87casos/84+8disponibles,QA85–87planned. Global78 % sin aumento; QA/adopción pendientes. [Informe]({ER}/CIERRE.md).')
    path=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(path.read_bytes());assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
    m.update(revision='2026-10-18-sesenta1150-1209',snapshot='Alta guiada probada/revisada en candidata1209/13;QA1089/paquete1149 conservados.87casos/84+8disponibles,QA85–87planned.Global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1150-1209.json',evidence=ER+'/CIERRE.md'))
    tree=next(n for s in m['streams'] if s['id']=='admin' for n in s['children'] if n['id']=='admin-tree')
    tree['note']='Navegación, selección/ficha y relaciones existentes; continuación Cuenta creada→Membresías→Permisos probada/revisada en desarrollo1209. QA85–87planned; integración y experiencia integral/aceptación pendientes.'
    tree.setdefault('children',[]).append(dict(id='guided-user-creation',name='Continuación guiada de alta por recibo confirmado y UUID',status='Probado y revisado · desarrollo',qa='QA85–87planned, no disponibles en QA1089',evidence=ER+'/CIERRE.md'))
    m['nextMilestones'].insert(0,'Integrar candidata1209 de esquema13 en Windows y QA, preservando preparados/recuperaciones/datos antes de habilitar QA85–87.')
    m['history'].append(dict(id='h1150-1209',name='1150–1209 · Continuación guiada del alta',status='Probado y revisado · desarrollo',note='60hitos/1buildfrontend/0C#.QA1089/paquete1149 intactos;85–87planned;global78 % sin aumento.'))
    path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=60,progress=78,candidateRevision=1209,selectedQaRevision=1089,planned=[85,86,87])))

if __name__=='__main__':main()
