# Integración849 en Windows y QA · bloque850–909

Se integra la candidata849 ya compilada y probada en848/849. El bloque comprende60hitos internos de un solo recorrido de instalación, recuperación y copia QA; no equivale a60módulos ni60suites. Avance inicial78aproximado; los IDs o pruebas no suman porcentaje por sí mismos. S1 autorizado y adopción final de Wascar pendiente.

## Distribución cerrada y paquete

Manifiesto `evidence/s1-20261018/tanda-849/CANDIDATA849.json`, SHA256 `1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`. Esquema11,20archivos servidor+18frontend,7.108.622bytes. Sólo app.js cambia respecto a832; servidor completo, SQL001–011, dependencias, CSS, fuentes y licencias exactos. No se compila aplicación/frontend ni se cambian versiones en este bloque.

Productor, lector y verificador Windows añaden sólo ese perfil; conservan337/397/532/592/712/832. Stage/start/recuperación que ya admiten11 no se modifican por arrastre. Se congelan25operadores y4manuales más productor/locks/helper antes de construir dos ZIP nuevos idénticos. Se conservan los anteriores, sin copiar DLL del sistema, instalar servicios ajenos o publicar.

New y Restore se prueban desde los operadores extraídos del propio ZIP en destinos/clústeres nuevos. Runtime sin SDK, HTTPS/cookies, roles/ámbitos de exportación, XLS y replay, reinicio, backup/Restore de35tablas y diferencias administrativas enumeradas. Servir el app.js esperado comprueba transporte; DOM/AX/390px/teclado corresponden a849 previamente ejecutado, no se presentan como nuevas pruebas GUI de este bloque. Voz de lector no probada.

## Copia nueva y recuperación

QA832 actual procede de847 y contiene recuperación712 separada. Se conserva completo, incluidos preparado/sello/configuración, secretos y artefactos originales. La actualización en el mismo directorio invalidaría esos contratos; se prepara un laboratorio independiente con849 y recuperación832, ambas de esquema11. Sólo se copia el estado actual de la base principal832, no se mezclan datos de su recuperación712.

No se supone igualdad entre las dos bases del origen después del QA. Se capturan y protegen sus snapshots e historias por separado. Las dos nuevas bases parten del mismo snapshot principal832 y35tablas/historia exactas. No migración, bootstrap ni recuperación administrativa en esta copia. Cuentas, sesiones, permisos y cuatro privados de aplicación se conservan; identidades y secretosPG nuevos y privados sólo en destino.

Se reutilizan los helpers puros de snapshots readonly, locks, watermark global y procesos propios. Fuente/candidata se identifican por manifiestos cerrados y versión de aplicación, no sólo por schema11. Preview, readiness, parada y comprobación de ambas ramas preceden al puntero atómico. Cualquier actividad posterior, incluso INSERT+DELETE compensado, impide retornar o aceptar actividad como si fuera quietud; conservar ramas y `recovery_required`. Nunca forzar bloqueo, detener procesos ajenos o borrar bases existentes.

## Revisión y operación real

Implementación Windows y copia tienen dueños separados. Revisión independiente de fuentes y resultados, con focoPG propio, antes del GO operativo del coordinador. El gate liga fuentes, manuales, paquete y pruebas reales; quietud e inputs se reconfirman antes de preparar. No se consulta la aplicación ni se hace login/DML en el QAreal. Sólo dump/snapshots readonly y procesos temporales propios de la transición.

La operación real exige preflight→GO→prepare→activate→validate. Si algún gate falla o aparece actividad, conservar evidencia/ramas y resolver la causa, sin habilitar la guía por haber código de desarrollo.

## QA y alcance pendiente

Después de selección confirmada849, QA-78 deja `planned` y exige par exacto GUI/DLL, roles y configuración. Su introducción indica disponibilidad real; otros pasos/expected y los77casos anteriores se conservan. Las listas heredadas sólo añaden849 donde ya se admitía832. El catálogo y ambas guías se regeneran sin leer ni sobrescribir resultados/observaciones de Wascar.

La prueba manual de voz se registra aparte con lector/versión/idioma. No habilitar macros ni cambiar seguridad de Office. Permanecen pendientes funciones RC9/Dosen/undo/admin, formatos/herramientas/paletas/accesibilidad global, identidad/servicio/PKIproductiva, Windows limpio/otroequipo, licencias, recuperación integral/retención/manualfinal y QA/adopción de Wascar. No se presenta R3 como producto final ni se sustituye PostgreSQL por SQLite.

Plan: [60hitos](PLAN-SESENTA-TANDAS-850-909.json). Evidencia nueva: `evidence/s1-20261018/sesenta-tandas-850-909/`; informes847/848/849 históricos conservados. La atribución final distinguirá autores, revisión y coordinador, ejecuciones nuevas de pruebas anteriores, y fallos reales de negativos esperados.
