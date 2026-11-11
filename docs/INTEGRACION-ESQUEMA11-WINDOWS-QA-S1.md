# Integración esquema11 ·713–772

Desarrollo S1 ya autorizado. Inicio: commit7680381, global78/100 estimado, QA592/esquema10 y ZIP652. Se integra la candidata712 FINAL02 probada; no se recompila aplicación/interfaz ni se cambian versiones fijadas, CSS, RC9 o Click-Click. Los 60 hitos son internos, no 60 módulos/suites. Sin adopción ni QA manual de Wascar.

## Windows y recuperación

Añadir exclusivamente el perfil cerrado712 FINAL02, manifiesto SHA256 `f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd`, esquema11,20archivos servidor+18GUI,7.028.507bytes. Conservar perfiles337/397/532(9) y592(10) y sus artefactos históricos. Sin override arbitrario de esquema/pin/manifiesto. La secuencia SQL001–011 y todos sus digests son obligatorios; SQL001–010/dependencias permanecen exactos.

New crea ROOT/clúster/base/roles/secretos nuevos. Restore exige backup del mismo esquema e historia/digests exactos; no migra10→11 por efecto lateral. Incompatibilidad después de pg_restore se conserva en destino nuevo fallido y se rechaza antes de recover-admin, sin recibo exitoso. Probar CLI recover-admin11 real mediante recuperación operativa nativa: administrador/grupo/secretos/TLS nuevos, sesiones copiadas revocadas,35tablas conservadas salvo cambios explícitos de recuperación. Preferencias y recibos/fences siguen perteneciendo al usuario original; el administrador nuevo no hereda ajustes ajenos. Permisos administrativos de11 incluyen templates.publish; preferencias propias no añaden capacidades de inventario.

Dos ZIP idénticos desde fuentes congeladas (25operadores y4manuales), fuentes oficiales ya fijadas. Ensayar desde content con runtime sinSDK: instalación, HTTPS, escritura/otra sesión, preferencias personales/lector, reinicio, backup/Restore y negativo de esquema. No atribuir servicioSCM, PKI productiva, CRT elevado ni Windows limpio/otro equipo a este ensayo.

## Copia QA10→11

Crear cuatro módulos NUEVOS qa_schema11_{source,candidate,switch,update}772.py; conservar motores anteriores. Fuente592 FINAL02/schema10 pin `66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9`; no usar el Source532/schema9 como identidad fuente. Candidata712 cerrada según el pin anterior.

Exigir fuente quieta con identidad/PID/paths y archivos privados comprobados, control.lock, watermark antes de dump y baseline después de preparar candidata. PG propio temporal con autovacuumoff, sin editar postgresql.conf. No login ni DML de aplicación en QA origen. Directorio/clúster nuevo, dos bases y cuatro secretosPG nuevos, distintos entre sí y de los del origen. Los cuatro privados de aplicación se copian exactamente para conservar credenciales/sesiones; no bootstrap ni recover-admin en esta copiaQA.

Restore transaccional sin clean/owner/ACL. Candidata migra sólo10→11: las32tablas previas distintas de schema_migration quedan idénticas; schema_migration conserva sus10filas históricas y añade únicamente11; dos tablas011 inicialmente vacías. Recuperación separada conserva el snapshot completo de33tablas en10 con DLL/GUI592. No cambios de permisos/cuentas/contraseñas ni autoconcesiones. Sellar configuración/artefactos/privados/baseline de actividad. Preview sin login en puerto propio comprueba readiness11 y GUI exacta. Selección por puntero atómico, confirmación posterior y procesos propios detenidos. Arranque normal con autovacuumON.

Retorno por puntero a origen10 conservado sólo mientras ambas ramas demuestren ausencia de actividad, incluida actividad compensada. Nunca DLL10 contra DB11. Puntero/secreto cambiado, identidad incierta o actividad implican recovery_required y conservar ramas; no prometer rollback después de trabajo de Wascar. No detener servidores ajenos o usuarios activos.

## Puertas y cierre

Pruebas nuevas Windows/PostgreSQL de copia/select/return,33tablas/historia/sesiones/datos de biblioteca/audit poblados, secretos nuevos, recuperación10 arrancable, fallo después de puntero/netzero/PID/lock/puerto/autovacuum. Revisión por otro agente con ejecución propia acotada y observación de suites atribuida.

Operación QA real sólo tras paquete11 probado, fixture de transición y revisión favorable, con GO operacional documentado por coordinador bajo la autorización existente. Fuente activa o incierta: no seleccionar ni detenerla. Conservar orígenes y evidencia de fallos.

Catálogo74casos y resultados/observaciones de Wascar intactos. Registrar pareja712 en matrices pertinentes con evidencia de funciones heredadas y, después de selección real compatible, regenerar ambas guías. QA72–74 sólo disponibles entonces; retirar su aviso temporal de no disponibilidad si ya es cierto. No marcar Pass de Wascar. Global según PROGRESO-GLOBAL: sin puntos automáticos por integrar capacidad ya contada o contar60IDs.


Resultado: [cierre713–772](../evidence/s1-20261018/sesenta-tandas-713-772/CIERRE.md). Integrado y probado/revisado, QA real712/11 seleccionado por copia nueva; origen592/10 conservado,74+8casos disponibles. Sin QA manual ni adopción.
