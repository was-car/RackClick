"""Write the attributable final report from completed gates; never edit raw outputs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-593-652';E=ROOT/ER
def read(p):return json.loads((ROOT/p).read_bytes())
def main():
    p=E/'CIERRE.md'
    if p.exists():raise SystemExit('Preserve final report')
    gates=read(ER+'/CLOSURE-GATES.json');assert gates['valid']
    assert read(ER+'/REAL-QA-ACTIVATE-01.json')['state']=='committed'
    package=read(ER+'/PACKAGES-03.json');native=read(gates['evidence']['native']);continuation=read(gates['evidence']['nativeContinuation'])
    assert native['recoverySnapshotExact'] and continuation['successful'] and read(gates['evidence']['windowsSummary'])['compositeNativeComplete']
    qa=read(ER+'/QA-TESTS-01.json');assert qa['successful'] and qa['availability']=={'manual':8,'rc9':71}
    source=read(ER+'/REAL-QA-PREFLIGHT-01.json');target=read(ER+'/REAL-QA-ACTIVATE-01.json')
    output=package['outputs'][0]
    s=f'''# Cierre593–652 · Windows/QA esquema10 ·18.10.2026

60/60 hitos internos de integración; no60 módulos nuevos ni60 suites. Avance global aproximado **78/100 sin aumento**, aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 intactos. Consolida plantillas compartidas ya contabilizadas; no acredita aceptación final. Base Git8391aff37019af8271b69a1e88335d0a906aba11.

## Resultado concreto

Perfil592 FINAL02/schema10 incorporado a productor/lector, Stage, New, Restore y arranque Windows, manteniendo perfiles337/397/532/schema9.19+18 archivos,37 totales/6.939.574B; secuencia SQL001–010 exacta. Aplicación/GUI592 sin recompilar,157 fuentes de producto y37 artefactos inmutables; RC9 adoptada/Click-Click/CSS/idiomas y dependencias fijadas conservados. Nuevo administrador de bootstrap/recuperación10 tiene templates.publish; migración/copia de QA no lo concede a usuarios históricos.

Dos ZIP definitivos idénticos: `{output['path']}` y su pareja `-b.zip`; **{output['bytes']:,}B**,1978 archivos, SHA256 `{output['sha256']}`.37 aplicación,25 operadores,4 manuales, runtime10.0.12 y PostgreSQL17.11-4. No SDK/Node/Python/Git para operar desde content. [Informe productor](packaging/build03-a/REPORT.json), [dos ejecuciones](PACKAGES-03.json), [33 fuentes congeladas](SOURCE-FREEZE-OPERATORS-03.json). Paquetes anteriores intactos y sin publicar; las dependencias se verifican desde archivos oficiales fijados, sin descargas/versiones nuevas.

## Pruebas nuevas y atribución

| Ejecutor | Ejecución real | Evidencia y límites |
|---|---|---|
|windows652|15 pruebas productor Python y10 lector WindowsPS5.1 correctas; regresión de provisión9 con PG real correcta|[Resumen]({gates['evidence']['windowsSummary'].removeprefix(ER+'/')}). Ejecutadas antes del arreglo final de Start; productor/lector conservan sus fuentes y el cambio de Start tiene foco posterior propio. No se sustituyen salidas históricas.|
|windows652|Alcance nativo paquete10 cubierto por04+05: New en otroROOT/clúster, HTTPS/Unicode/roles, escritura/otra sesión, compartir/instanciar/retirar, Stop/restart, backup y Restore10|[04]({gates['evidence']['native'].removeprefix(ER+'/')}) ({native['seconds']}s) termina FAIL por una expectativa obsoleta del arnés después de Restore; [05]({gates['evidence']['nativeContinuation'].removeprefix(ER+'/')}) completa sólo lo pendiente sobre los mismosROOT.33 tablas/32 digests exactos, cuentas/bibliotecas/bytes/recibos preservados con excepciones administrativas explícitas; sesiones copiadas revocadas, admin/TLS nuevos. Regreso al origen del ensayo y rechazo9→Stage10 en otro parcial. [Compuesto revisado](revision/NATIVO-COMPUESTO.json). Runtime desde content, sin aprovisionar/restaurar por Python. No se declara04 como suitePASS.|
|qa_transition652|3 contratos,1 recorrido Windows/PG poblado y1 negativo estático init-password correctos|[Resumen](qa-transition/SUMMARY.json). Copia9→10+recuperación9, selección/retorno, falloafter_pointer, arranque incierto, PID/puerto/PG ajeno conservado, actividad compensada que bloquea rollback y autovacuum normal. Recorrido338,438s; corrección posterior del sello probada focalmente y en fixture propia del revisor.|
|review_integration652|Cuatro perfiles reales Python+PS5.1, negativas/IO, foco PG propio de actividad de origen y foco de readiness|[Gate final](revision/GATE-TECNICO-02.json), [revisión](revision/REVISION-INDEPENDIENTE.md), focos originales separados. Segunda base histórica incluida; UPDATE+ROLLBACK deja30 digests iguales pero cambiaXID y bloquea selección antes de app. No ejecutó la instalación completa ni el QA real.|
|Coordinador|Copia y selección reales sólo después de paquete nativo, revisión y GO; validación estática final sin login/DML de aplicación|[GO](COORDINATOR-GO.json), [preparación](REAL-QA-PREPARE-01.json), [selección](REAL-QA-ACTIVATE-01.json), [validación](REAL-QA-VALIDATE-01.json). No son pruebas funcionales nuevas del GUI ni QA manual de Wascar.|
|Coordinador|{qa['testsRun']} pruebas existentes de guía y reproducción exacta de ambas guías|[Salida](QA-TESTS-01.json).71 casos disponibles en restaurado/8original. Pruebas de metadatos, sin abrir aplicación/PG/navegador del QA real.|

La matriz JSON de [60 hitos](../../../docs/PLAN-SESENTA-TANDAS-593-652.json) enlaza el soporte de cada tanda; varios hitos comparten un mismo recorrido integrado. Los informes anteriores conservan su fecha, fuente y resultado y no se presentan como ejecuciones de este bloque.

## Fallos y correcciones conservados

1. Primer helper de empaquetado omitió el padre de evidencia; productor rechazó antes de reservar ZIP. [Error](PACKAGE-ATTEMPT01-FAILED.json) y freeze01 conservados. Se creó el padre y se usaron destinos nuevos; ningún cambio de producto para ese fallo.
2. `windows/native01`: NameError por alias faltantes del arnés copiado, antes de Windows/PG. `native02`: New10 real preparado y detenido, después NameError NO_WINDOW del arnés antes de app. Fuentes exactas archivadas; la continuación03 validó primero recibos/content/quietud de esa fixture, sin reanudar un instalador failed.
3. **Fallo real de operador en native03:** Start exigía readiness schema9 aunque Stage/aplicación fueran10. El arranque agotó timeout y detuvo procesos propios. La búsqueda estática anterior centrada en -ne9 omitió -eq9. Se corrigió a igualdad exacta con esquema SQL del Stage validado, no versión del formato del recibo; negativas cruzadas9/10 y revisión independiente. [Bloqueo original](BLOQUEO-READINESS-03.json). Gate01, dosZIP02 y ensayos previos se conservan; gate02, dosZIP03 y un New10 definitivo nuevo sustituyen su promoción. Ninguno de esos fallos llegó a seleccionar QA real.
4. Revisor `closed-profiles01`: los4 positivos pasaron pero una negativa falló por ruta relativa del arnés. Se conserva fuente/log/result; se repitieron sólo negativas/IO en02 con ruta absoluta.
5. El sello inicial de candidata omitía init-password.txt. Se añadió a inputHashes y se probó su modificación/rechazo sin repetir toda la suitePG; fuentes iniciales archivadas. El foco propioPG del revisor usó ya la fuente final.
6. `windows/native04` completó New10/HTTPS/compartidas/backup/Restore10 y comparación32tablas, pero luego comparó clientes contra una respuesta capturada antes de crear inventario (revisión1 frente a5). Era una expectativa obsoleta del arnés. Fuente/resultFAIL04 conservados; el foco05 verifica sólo los pasos restantes sobre los mismosROOT, recibos yZIP03 (administrador/cuenta original, fuente33 exactas y rechazo9→10). Corrección del test futuro y atribución del compuesto revisadas; no se reinstaló ni se convirtió04 enPASS.
7. Primer intento del coordinador de emitir GO se rechazó porque el implementador aún no había publicado SUMMARY.json. No se escribió GO ni se inició PG real. [Registro](GO-ATTEMPT01-NOT-ISSUED.json); tras recibir el resumen se revalidaron todos los gates y la quietud, sin corregir producto ni repetir pruebas.

No se borraron parciales ni bases, ni se parcheó content ya congelado. Cada variante fallida queda junto a la fuente que realmente ejecutó. Los [resúmenes Windows]({gates['evidence']['windowsSummary'].removeprefix(ER+'/')}) y [QA](qa-transition/SUMMARY.json) identifican hashes y alcances.

## QA de Wascar

Fuente conservada: `{source['sourceDirectory']}`. Nueva selección: `{target['candidateDirectory']}`, con candidata10 y base de recuperación9/DLL532 en un clúster distinto. Ambas ramas detenidas al cerrar. Se conservaron30 tablas históricas salvo historia010 aditiva, cuentas/contraseñas/sesiones, grupos/permisos, privados y secretos de aplicación byteexactos;3 tablas compartidas nuevas vacías. Nuevos roles/contraseñas PostgreSQL, sin reutilizar los de ninguna base histórica. Origen sólo leído bajo guardas de quietud; no login ni DML de aplicación real. Preview y arranque de selección sólo comprobaron readiness y app.js exacto, sin autenticación. Retorno al puntero9 sólo con ambas ramas intactas y sin actividad: no es rollback de datos tras nuevas escrituras.

Para probar después: `INICIAR-QA-RESTAURADO.cmd`, credenciales en su ACCESO-PRIVADO.txt local y `GUIA-QA-RESTAURADO.html`. QA69–71 explican publicación por cliente; el administrador concede explícitamente el permiso mediante grupos/QA14. Un editor no obtiene publicar por editar. QA67 aclara que las privadas no se heredan y que las compartidas se prueban por separado;69–71 cambian su introducción de disponibilidad. El resto de casos/pasos/esperados se conserva; [matriz](QA-MATRIX-652.json). No se escribió almacenamiento del navegador ni resultados/observaciones exportados de Wascar; la guía conserva notas y avisa de cambio de versión/caso. Ningún Pass manual nuevo ni adopción del desarrollador.

## Reproducción y límites

Desde este workspace, usar Python312 -Xutf8 -B para `tools/tests/build_offline652.py` sólo con un intento/destinos de evidencia nuevos; el productor se invoca directamente según el manual si los intentos01–03 ya existen. No sobrescribir evidencia. Pruebas: `tools/tests/test_offline_bundle_builder.py`, `tools/tests/test_offline_bundle_windows.py`, `development/server/tests/test_offline_shared652.py --archive <ZIP03> --archive-sha <hash confiable> --evidence <directorio nuevo>` y `development/server/tests/test_qa_schema10_update652.py --group all --evidence <directorio nuevo>`. Los motores qa_schema10_update652 son de desarrollo y fijan532→592: no repetir una operación real sobre el QA ya seleccionado10.

Windows11/PowerShell5.1/PostgreSQL17.11 reales en laboratorio de desarrollo, CRT compatible existente; no Linux presentado como Windows. Faltan servicioSCM/identidad mínima, reinicio de Windows, PKI/DNS/renovación productivos, Windows limpio/otro equipo, rama CRT elevada, revisión de redistribución/LGPL, backup integral del host/retención/NAS/USB, manual visual final y QA/adopción de Wascar. También quedan funciones RC9/admin/Dosen/undo/preferencias/herramientas/formatos; ver PROGRESO-GLOBAL y MAPA-ENTREGA. El paquete es interno, sin publicación ni declaración de servidor final/R3 adoptado. Próximo bloque: elegir tres tareas funcionales pendientes independientes y verificables, manteniendo revisión y gasto moderado.
'''
    p.write_text(s,encoding='utf-8');print(json.dumps({'report':str(p.relative_to(ROOT)),'scopeProgress':78,'manualQaRecorded':False}))
if __name__=='__main__':main()
