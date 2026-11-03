"""Close the palette development block after positive Windows evidence; no QA activation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-910-969'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads((E/p).read_bytes())


def prepend(relative,text):
    p=ROOT/relative
    raw=p.read_bytes()
    first,rest=raw.split(b'\n',1)
    p.write_bytes(first+b'\n\n'+text.replace('\n','\r\n').encode()+b'\r\n'+rest)


def main():
    assert not (E/'CIERRE.md').exists()
    build=load('BUILD-01.json');backend=load('backend01/result.json');gui=load('gui02/result.json')
    node=load('frontend-node01/result.json');reg=load('regression01/result.json');guide=load('QA-TESTS-02.json')
    assert build['successful'] and backend['successful'] and gui['result']=='PASS' and reg['successful'] and guide['successful']
    assert load('revision/PG-SESION-01.json')['successful']
    sys.path.insert(0,str(ROOT/'tools/tests'))
    import qa_port_colors969
    suite=__import__('unittest').defaultTestLoader.loadTestsFromTestCase(qa_port_colors969.GuidePalette969)
    with (E/'QA-FOCAL-03.log').open('x',encoding='utf-8') as log:
        tests=__import__('unittest').TextTestRunner(stream=log,verbosity=2).run(suite)
    assert tests.wasSuccessful()
    (E/'QA-FOCAL-03.json').write_text(json.dumps(dict(testsRun=tests.testsRun,successful=True,
        scope='Final exact button wording in the three new planned cases; no previous case/gate/result logic changes.'),indent=2)+'\n',encoding='utf-8')
    common=('**Bloque910–969 cerrado ·18.10.2026: paleta personal de tipos RC9 implementada y probada en desarrollo12; global78 % aproximado, sin aumento.** '
      'Diez tipos independientes, borrador/Guardar/restablecer individual y completo, propietario de sesión y persistencia PostgreSQL. '
      'API/journal/revisión personal y SQL012 aditiva; no cambios SQL001–011 ni preferencias011. Sólo GET confirmado aplica colores; puerto/cable explícitos y estados conservan prioridad. '
      'Candidata969-01 de39archivos, una publicaciónC# y un buildfrontend; CSS/dependencias/referenciaRC9 exactos.\n\n'
      'Pruebas nuevas Windows:4focosPG (migración11→12 dosveces y restore37tablas), Node19, Edge/PG7observaciones y reinicio; regresión76dominio/16Node/2PG anteriores. '
      'Revisión independiente propiaPG1foco/2invalidaciones y lectura; sin voz acreditada. FalloGUI inicial de fixture(aliasPoE) y fallos de arnés de guía conservados, corregidos sin cambiar producto ni recompilar.\n\n'
      '**QAreal conserva849/esquema11 y paquete909.** Catálogo81, disponibles78restaurado/8original; QA79–81 detallados permanecen NO DISPONIBLES hasta integrar y revisar Windows/QA12 en copia nueva. '
      'Casos01–78, listas de parejas, generador y notas/resultados de Wascar intactos. Siguiente: perfil/operadores/backup/restore12 y actualización conservadora antes de habilitar paleta; después paleta de grupos y restantes funciones/Windowsfinal/QAadopción. '
      '[Contrato](API-PALETA-TIPOS-PERSONAL-S1.md), [plan60](PLAN-SESENTA-TANDAS-910-969.json), [evidencias y límites](../evidence/s1-20261018/sesenta-tandas-910-969/CIERRE.md). Registros siguientes históricos.\n')
    for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:
        prepend(p,common)
    short=('**Desarrollo910–969 ·18.10.2026.** Paleta personal RC9 por10tipos implementada y probada en candidata969-01/esquema12; '
      'persistencia/actores/reset/replay/cancelación/migración/restore37tablas/Edge y revisión independiente verificadas. '
      'QA849/paquete909 conservados; QA79–81 pendientes de integración12 (81catálogo,78+8disponibles). '
      'Global78 % aproximado y adopción pendiente. [Contrato](API-PALETA-TIPOS-PERSONAL-S1.md), '
      '[pruebas/fallos/límites](../evidence/s1-20261018/sesenta-tandas-910-969/CIERRE.md). Registros siguientes históricos.\n')
    for p in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md']:
        prepend(p,short)
    for p in ['development/server/README.md','development/frontend/README.md']:
        prepend(p,short.replace('(API-','(../../docs/API-').replace('(../evidence/','(../../evidence/'))
    prepend('CHANGELOG.md','## 18.10.2026 · bloque910–969 · paleta personal de tipos\n\n'
       '- API `/me/port-colors`, SQL012, journal/revisión/auditoría propios y editor EN/DE/ES. Guarda con confirmación+GET; mantiene prioridadesRC9 y aislamiento por actor.\n'
       '- Candidata969-01 interna:4focosPG/Node19/Edge y regresión76dominio+16Node+2PG; revisiónPG independiente. Fallos de arnés preservados, sin recompilar.\n'
       '- QA849/paquete909 intactos. QA79–81 documentados aún pendientes;78casos previos/resultados preservados. Global78 %, servidor final/adopción pendientes.\n')
    titles=[
      ('Contrastar editor de paleta en RC9 adoptada','contract'),('Fijar diez claves de tipo independientes','contract'),
      ('Conservar colores iniciales exactos RC9','contract'),('Conservar precedencia puerto y cable sobre tipo','contract'),
      ('Conservar selección, estados y PoE de RC9','contract'),('Asignar paleta exclusivamente a cuenta vigente','contract'),
      ('Separar revisión personal de inventario y Systemhaus','contract'),('Definir reset individual y completo explícitos','contract'),
      ('Cerrar DTO y errores antes de GUI','contract'),('Separar paleta por parejas de categorías, todavía pendiente','contract'),
      ('Implementar GET sin escritura ni selector de propietario','backend'),('Implementar SET de mapa completo cerrado','backend'),
      ('Implementar consulta de operación histórica por actor','backend'),('Implementar cancelación durable original','backend'),
      ('Validar diez claves y RGB minúscula sin extras/duplicados','backend'),('Canonicalizar orden para digest y comparación','backend'),
      ('Exigir ETag personal exacto y límites seguros','backend'),('Exigir CSRF, actor y clave de idempotencia','backend'),
      ('Añadir agregado SQL012 sin tocar migraciones previas','backend'),('Añadir journal con shape, hash y fences SQL','backend'),
      ('Serializar intenciones por actor y petición','backend'),('Revalidar sesión después de esperas','backend'),
      ('Confirmar mapa, recibo y auditoría en una transacción','backend'),('Tratar no-op sin aumentar revisión','backend'),
      ('Recuperar replay original incluso con revisión posterior','backend'),('Rechazar clave reutilizada con otra intención','backend'),
      ('Documentar rutas y schemas OpenAPI ejecutables','backend'),('Aislar cuenta lectora y usuario sin clientes','backend'),
      ('Probar máximo de revisión y conflictos concurrentes','backend'),('Probar rollback y recibo corrupto sin efectos parciales','backend'),
      ('Añadir adaptador frontend con validación de recibo y ETag','node'),('Añadir diario IndexedDB separado por familia/actor','node'),
      ('Conservar intención original para consultar/reintentar/cancelar','node'),('Invalidar resultados tardíos por generación y actor','node'),
      ('Añadir acceso Paleta en Settings existente','gui'),('Añadir diez controles nativos con preview de borrador','gui'),
      ('Añadir Guardar explícito y estado confirmado por servidor','gui'),('Añadir restablecer tipo y todos en borrador','gui'),
      ('Aplicar overrides confirmados al rack RC9','gui'),('Conservar EN/DE/ES y controles a390px con Tab','gui'),
      ('Congelar fuentes y publicar C# una vez','build'),('Compilar frontend una vez sin cambiar CSS/dependencias','build'),
      ('Sellar candidata12 separada con39archivos','build'),('Probar creación, recarga y otra sesión con PostgreSQL','gui'),
      ('Probar cuenta distinta y cambio de actor en navegador','gui'),('Probar precedencia gráfica de tipo explícito y cable','gui'),
      ('Probar503 no enviado, consulta y cancelación sin éxito fantasma','gui'),('Probar persistencia al reiniciar ASP.NET de fixture','gui'),
      ('Migrar base poblada11→12 dos veces conservando datos','backend'),('Respaldar y restaurar37tablas y recibos/fences exactos','backend'),
      ('Ejecutar regresión de76pruebas de dominio','regression'),('Ejecutar16pruebas Node de preferencias previas','regression'),
      ('Ejecutar2focosPG de preferencias previas sobre esquema12','regression'),('Reproducir sesión expirada y revocada en focoPG independiente','review'),
      ('Conservar diagnóstico y fallo inicial GUI sin atribuir éxito','gui'),('Añadir QA79–81 con ubicaciones y etiquetas reales','guide'),
      ('Conservar78casos y regenerar guías según snapshot real','guide'),('Corregir arneses históricos de disponibilidad y comprobar43casos','guide'),
      ('Actualizar mapa, continuidad y próximos pendientes sin sumar puntos','closure'),('Preparar cierre local con diff/hashes y revisión independiente','closure')]
    assert len(titles)==60
    links=dict(contract='docs/API-PALETA-TIPOS-PERSONAL-S1.md',backend=str((E/'backend01/result.json').relative_to(ROOT)).replace('\\','/'),
      node=str((E/'frontend-node01/result.json').relative_to(ROOT)).replace('\\','/'),gui=str((E/'gui02/result.json').relative_to(ROOT)).replace('\\','/'),
      build=str((E/'BUILD-01.json').relative_to(ROOT)).replace('\\','/'),regression=str((E/'regression01/result.json').relative_to(ROOT)).replace('\\','/'),
      review=str((E/'revision/PG-SESION-01.json').relative_to(ROOT)).replace('\\','/'),guide=str((E/'QA-TESTS-02.json').relative_to(ROOT)).replace('\\','/'),
      closure=str((E/'CIERRE.md').relative_to(ROOT)).replace('\\','/'))
    plan=dict(revision='2026-10-18',scope='60 hitos internos de una función y su verificación; no60funciones ni60suites.',
      completed=60,total=60,progress=78,batches=[dict(id=910+i,title=title,status='verified',evidence=links[kind]) for i,(title,kind) in enumerate(titles)])
    (ROOT/'docs/PLAN-SESENTA-TANDAS-910-969.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(p.read_bytes());assert m['progress']==78
    m['revision']='2026-10-18-sesenta910-969'
    m['nextMilestones'].insert(0,'Integrar candidata969/esquema12 en perfil Windows, New/backup/Restore y copia QA nueva conservando849; revisión antes de habilitarQA79–81.')
    m['snapshot']='Paleta personal por10tipos probada/revisada en desarrollo12; QA849/Windows909 conservados.81casos,78+8disponibles.60hitos internos, global78estimado.'
    m['currentBatch']=dict(first=910,last=969,completed=60,total=60,status='Cerrado: función en desarrollo12; integración Windows/QA12 siguiente',evidence='evidence/s1-20261018/sesenta-tandas-910-969/CIERRE.md')
    parity=next(s for s in m['streams'] if s['id']=='parity')
    parity['children'].append(dict(id='personal-port-type-palette',name='Paleta personal RC9 por tipo de puerto',status='Probado y revisado en desarrollo12; QA pendiente',
      qa='QA79–81 no disponibles en QA849',note='10tipos/override, Guardar y reset; prioridad puerto/cable/estado conservada. Paleta por parejas de categorías pendiente.',evidence='evidence/s1-20261018/sesenta-tandas-910-969/CIERRE.md'))
    assert [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report='''# Cierre910–969 · paleta personal de tipos RC9

18.10.2026 · Windows11 build26300 · S1 autorizado · global78 % aproximado, sin aumento. 60 hitos internos de una función y sus pruebas; no60funciones ni60suites. Adopción de servidor pendiente de Wascar.

La candidata969-01 incorpora paleta personal de diez tipos, restauración individual/completa y Guardar explícito. PostgreSQL deriva propietario de sesión, usa agregado/journal/revisión propios, CSRF/actor/revisión/idempotencia y auditoría atómica. El frontend aplica GET confirmado; borrador y operaciones pendientes no producen éxitos fantasma. RC9 conserva puerto/cable explícitos sobre tipo y estados/PoE/Click-Click. SQL012 aditiva; SQL001–011, DTO de preferencias anteriores, CSS, versiones/dependencias y referencia adoptada exactos.

## Ejecuciones nuevas y atribución

| Ejecución | Resultado real | Autor/alcance |
|---|---|---|
| BUILD-01 | C#7,985s; frontend0,875s;39archivos congelados | Coordinador, una publicación+unbuild; sin descarga/instalación |
| frontend-node01 |19/19PASS,220,2656ms | Autor frontend; DTO, transporte, diario simulado, respuestas tardías; no navegador real |
| backend01 |4/4focosPASS;86,448s runner/99,016s total | Coordinador ejecuta arnés del autor: validación/actores/replay/noop/fences/rollback/carreras/límites/revocación, migración11→12 dosveces y dump/restore37tablas exactas |
| gui01 |FAIL23,937s conservado | Fixture esperaba aliasRJ45PoE en tipoRJ45 con poe=true; error de fixture, no defecto del producto. HARNESS/DIAGNOSTICO originales conservados |
| gui02 |PASS24,546s,7observaciones Edge155/PG17.11 | Coordinador: lector/sinclientes/otra sesión/logout/reset/error503/paleta física/ENDEES/390px/Tab;6journal/audit, inventario/revisiones exactos y persistencia tras reiniciar ASP.NET |
| regression01 |76dominio+16Node+2PGPASS | Coordinador; pruebas existentes de preferencias sobre esquema12. Sin build de aplicación/frontend adicional |
| revision/PG-SESION-01 |1focoPASS con2invalidaciones | Revisor distinto: esperaSQL real, expiración y revocación de sesión producen401, sin escritura en36tablas salvo sesión; fixture propio |
| QA-TESTS-01 |43pruebas,3FAIL conservados | Dos listas negativas históricas asumían que todo ID futuro era disponible; otro test comparaba texto normalizado con CRLF de Git |
| QA-TESTS-02 |43/43PASS0,984s | Arneses corregidos manteniendo expectativas históricas; generador y resultados sin editar |
| QA-FOCAL-03 |3/3PASS | Etiquetas finales exactas Paleta/Restablecer todo/Cancelar original en los tres guiones nuevos |

Las capturas desktop y390px fueron inspeccionadas por el coordinador. Prueba de teclado/estado accesible no acredita voz de lector de pantalla. El revisor distingue su ejecución propia de los resultados observados del autor/coordinador. Fuentes y artefactos permanecen congelados; todos los procesos propios de los laboratorios terminaron.

## QA y límites de entrega

QAreal849/esquema11, cuentas/punteros/artefactos y paquete909 se conservan. No hubo login, HTTP ni DML de aplicación en el QAreal. No se leen ni escriben notas/exportaciones de Wascar. El catálogo tiene81casos:78disponibles en restaurado y8en original. Los78guiones previos y listas de builds son iguales; QA79–81 permanecen NO DISPONIBLES. Se regeneraron ambas guías con el snapshot vigente.

La paleta está probada en una candidata de desarrollo separada. Antes de anunciarla disponible hay que integrar perfil12, operadores New/backup/Restore/readiness y preparar/seleccionar una copia QA nueva con preservación de la actual y revisión independiente. El restore probado aquí es de base nueva mediante pg_dump/pg_restore, no una instalación Windows final ni recuperación integral de otro host. No se presenta instalador12, servicio/identidadWindows/PKIproductiva, compatibilidad universal, voz o QA manual/adopción como completados.

La paleta automática por parejas de categorías, formatos/herramientas restantes, Dosen pasante/undo general/administración visual, servicio/instalación limpia/otro equipo/licencias/recuperación integral/manualfinal y QAadopción siguen pendientes. Aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 no cambian: esta función no completa por sí sola el criterio entero restante de paridad.

Plan detallado: docs/PLAN-SESENTA-TANDAS-910-969.json. Contrato: docs/API-PALETA-TIPOS-PERSONAL-S1.md. Reproducción: tools/tests/block969.py build --attempt <nuevo>, test_user_port_colors969.py con --dll/--baseline-dll/--baseline-sha256/--frontend/--evidence/--case, test_user_port_colors_gui969.py --manifest/--output, regression_palette969.py. Todos los destinos deben ser nuevos; las ejecuciones anteriores nunca se sobrescriben. El manifiesto SHA256SUMS de este cierre es independiente del recibido históricamente.
'''
    (E/'CIERRE.md').write_text(report,encoding='utf-8')
    print(json.dumps(dict(internalMilestones=60,progress=78,qaCases=81,available=dict(rc9=78,manual=8),qaSelected=849)))


if __name__=='__main__':
    main()
