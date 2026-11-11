# Integración esquema10 · bloque593–652

Estado inicial: desarrollo autorizado; nuevas pruebas y revisión pendientes. Aplicación/GUI592 FINAL02 ya probadas y congeladas, sin recompilar en este bloque. QA vigente532/esquema9 permanece hasta una selección nueva verificada. Avance inicial78/100; los60hitos no son60módulos ni60suites.

## Distribución e instalación Windows

Mantener los perfiles cerrados337/397/532 (esquema9,18servidor+18GUI) y añadir exclusivamente592FINAL02 (esquema10,19+18,6.939.574B), pin `66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9`. No overrides de schema/digest/versión, no cambios en SDK/runtime/PG/VC/pins, SQL001–009 ni assets aprobados. SQL010 ya pertenece a la candidata592.

Los lectores de distribución/stage/instancia derivan secuencia1..N y recuentos36/37 del manifiesto validado; admiten sólo9/10. New crea ROOT/clúster/base/roles/claves nuevos. Restore exige backup confiable de la misma secuenciaSQL que el stage. No migra un backup9 por efecto lateral para usarlo con aplicación10. Si detecta incompatibilidad después de pg_restore, conserva el destino NUEVO fallido, sin invocar recover-admin ni publicar recibo. No borra ni reutiliza destinos.

Restore10 se verifica positivamente: administrador/grupo nuevos con permisos de versión10, sesiones copiadas revocadas, cuentas originales y33tablas conservadas salvo cambios transaccionales explícitos de recuperación. Privadas siguen privadas; compartidas conservan cliente/autor/bytes/recibos. Probar loginUnicode/HTTPS, escritura/otra sesión, permisos, restart, backup y recuperación desde content con runtime sinSDK. No afirmar instalación limpia, servicioSCM o PKIproductiva por operar en este equipo.

Construir dos ZIP byteidénticos desde fuentes congeladas,25operadores y4manuales actualizados. Hash externo del ZIP, bundlemanifest y perfiles vinculados. Paquetes anteriores se conservan como históricos; no se presentan sus hashes como los nuevos.

## Copia QA9→10

Cuatro módulos NUEVOS `qa_schema10_{source,candidate,switch,update}652.py`; no cambiar motores históricos. Fuente532 exacta del perfil restaurado schema9, pin `c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e`. No usar el Source9 de actualización185→532 como fuente532.

Requiere fuente quieta/identidad/PID/paths/secrets verificados y control.lock. Sólo PG propio temporalmente autovacuumoff; no cambiar postgresql.conf. Watermark ANTES de snapshot/dump; no login ni DML de aplicación en origen. Preparar directorio/clúster nuevo, dos bases y cuatro secretosPG nuevos, distintos entre sí y de todas las credenciales del laboratorio fuente. Copiar cuatro secretos privados de aplicación exactamente para conservar sesiones/credenciales del QA.

Dump custom del origen y dos restores transaccionales sin clean/owner/ACL. Candidata migra únicamente9→10;30tablas/historia1..9 intactas y tres tablas010vacías. Base de recuperación conserva9 con DLL/GUI532. No bootstrap/recover-admin ni autoconcesión templates.publish en esta copiaQA. El administrador podrá conceder el nuevo permiso explícitamente desde Concesiones/QA14, como explican QA69–71.

Sellar configuración/roles/artefactos y baseline de actividad de candidata DESPUÉS de preparación/restores/migración/grants técnicosPG. Preview sin login en puerto propio; validar readiness/GUIexacta, seleccionar directorio nuevo por puntero atómico y confirmar otra vez. Arranques normales con autovacuumON. Terminar procesos propios parados; no detener procesos ajenos.

Retorno únicamente por puntero a origen9 intacto y si ambas ramas siguen sin actividad demostrada; nunca DLL9 contra DB10. Actividad netacero, secretos/puntero cambiados o incertidumbre requieren recovery_required, conservar ramas y no declarar retorno. No hay promesa de rollback posterior al trabajo de Wascar.

## Puertas y evidencia

Contrato/negativos y recorrido de fixture9 poblada nueva con cuentas/sesiones/grupos/clientes/cables/favoritos/privadas/audit. Preparar/select/return, sourceexacto, secretosnuevos, recovery9 arrancable, falloafterpointer/netzero/PID/lock/puertoclienteajeno/autovacuum. Revisor distinto del implementador; pruebas propias acotadas y observaciones atribuidas.

Operación real únicamente después de paquete10 ensayado, revisión favorable y GO operacional documentado por coordinador bajo S1 ya autorizado. Si fuente activa o identidad incierta, no se selecciona ni se detienen usuarios. Conservar original y evidencia incluso tras éxito. Adopción final sigue pendiente de Wascar.

Casos QA01–71/observaciones se conservan. Registrar la pareja592 en las matrices pertinentes sólo con evidencia; después de selección real confirmar disponibilidad y regenerar ambas guías. No habilitar por existir código. QA manual no se atribuye al desarrollador. Porcentaje global según PROGRESO-GLOBAL; integrar10 no suma puntos automáticamente por repetir capacidad ya contada.


Resultado: integrado y probado/revisado según [cierre593–652](../evidence/s1-20261018/sesenta-tandas-593-652/CIERRE.md). QA real592 seleccionado en otro laboratorio con origen532 intacto; guías71+8 disponibles, sin QA manual ni adopción.
