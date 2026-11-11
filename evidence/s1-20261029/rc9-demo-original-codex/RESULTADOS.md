# Carga del Full Backup original con MFA conservado

29.10.2026. Wascar comunica prueba satisfactoria de MFA administrativo y confirma usar el **original**, no la copia modificada del laboratorio. No se toman sus palabras como aprobación de cada caso del catálogo, recuperación completa o producción.

## Resultado operativo

**Carga confirmada en la instalación10 actual de C**, Windows Server2025, ID `643a8251-23e8-4ecb-8a5c-a2ceaa465da8`, esquema15, mismo servicio RackClick y cuenta estándar RackClickSvc10. Fuente original SHA256 `cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0`.

| Entidad | Cantidad confirmada |
|---|---:|
| Clientes | 10 |
| Sitios | 15 |
| Edificios | 25 |
| Salas | 68 |
| Racks | 68 |
| Equipos | 311 |
| Grupos de puertos | 633 |
| Puertos | 5.408 |
| Conexiones | 623 |

565 conexiones internas y58 entre racks. El CLI comprueba filas y constraints antes del commit. La comparación de todos los atributos originales se ejecutó en PostgreSQL de laboratorio; no se hizo un recorrido visual completo en la VM con el MFA de Wascar.

`CHECK-VM.json`: destino vacío, UUID/revisión ligados y runtime restringido; sin mutaciones. `APLICACION-VM.json`: una única aplicación, `demo_original_import_verified`, commit y conservación de seguridad confirmados. La huella transaccional de doce tablas incluye usuarios, grupos, permisos, sesiones, políticas, factores, desafíos y códigos MFA. Los bytes y ACL del almacén Windows no cambiaron. No se leyó ni exportó el secreto TOTP de Wascar.

Servicio Running y HTTPS ready después de cargar. Se ejecutaron las tareas oficiales de backup con la cuenta ya registrada; cada copia exige nueva ejecución, ruta/manifiesto nuevos, fecha reciente y dump verificado:

- Antes: manifiesto SHA256 `eec0cda5818b9d937566a7ebf8d82d969cdee0f5cc34729a0f1acbcb03e03c60`.
- Después: manifiesto SHA256 `4630267fc819d7ed5f587c129bf429e3714ae273fadb4def99af3a9dfa9ac457`.

La configuración runtime permanece sellada. Se usó una tarea SYSTEM temporal para ejecutar el mantenimiento autorizado, sin cambiar ACL ni usar credenciales del propietario PostgreSQL. Check y Apply terminaron con salida0 y tarea retirada. No se modificaron cuentas, servicio, red, snapshots ni otra VM. No reinicio ni nueva instalación.

## Implementación y pruebas

- Investigación previa en `INVESTIGACION.md`: reutilización del analizador RC9 y Npgsql publicado; distinción entre datos, dump y sobre MFA. No nuevas dependencias, versiones, migraciones o cambios de aplicación/GUI instalada.
- `tools/prepare_rc9_demo_load.py`: fuente y segunda lectura ligadas por hash; original exacto y plan canónico en directorio nuevo privado. Plan SHA256 `cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7`.
- `tools/rc9-demo-load/`: tablas/columnas internas cerradas, parámetros Npgsql tipados, sólo loopback/runtime restringido, actor activo con cuatro capacidades globales, esquema/digests15, inventario vacío, UUID/revisión y una transacción con auditoría y recibo idempotente. Conserva nombre Systemhaus. Error durante commit devuelve estado incierto; replay conocido conserva estado de commit confirmado.
- Build con SDK10.0.401, referencia a Npgsql de la publicación10 verificada:0errores/0advertencias. Binlogs y logs bajo `.local`, no en Git ni en el paquete de datos.
- Regresión final: **11/11 PASS,0omitidas**, PostgreSQL17.11 nuevo, roles nuevos y runtime sin propietario/DDL. Cubre check sin escritura, cada atributo original, conservación de seguridad, idempotencia, destino poblado, revisión/UUID/permisos, plan alterado, propietario/BYPASSRLS/digest rechazados, rollback por auditoría y concurrencia de duplicados. Laboratorio detenido.
- Revisión independiente `backup_paths_review`:11focos de la referencia y6del endurecimiento, con PG17.11 nuevos detenidos; revisó por fuente los ajustes finales de reporte y los envoltorios. No le atribuir pruebas sobre la DLL definitiva ni la VM. Dictamen y hashes en `REVISION.md`.

Los hashes finales de fuentes/DLL y la confirmación de ZIP10 intacto están en `HASHES-Y-VERIFICACION.json`. Comando reproducible de tests en `tools/rc9-demo-load/README.md`; publicación10 y plan privado se proporcionan explícitamente, sin depender de una DB existente.

## Desviaciones conservadas

Los Check previos se detuvieron antes de aplicar: rutas iniciales de binarios equivocadas (`server_layout_invalid`), acceso administrativo común al privado sellado denegado y nombre de actor no canónico (`Wascar` frente al `wascar` guardado por el producto). Se corrigieron las rutas del envoltorio y el dato de invocación; se mantuvieron los permisos y la política de nombres del producto. Los informes originales se conservan en el directorio privado de trabajo.

La revisión también corrigió la vinculación de backups nuevos y el reporte de commit incierto/replay. Se conservan builds y corridas previas; el resumen final cuenta sólo los11tests sobre la DLL definitiva, sin sumar repeticiones como cobertura nueva.

Directorio privado de trabajo: `.local/rc9-demo-1cc8b27987674cd7af903a2fb1c85388/`. Contiene logs, binlogs, plan, copias de verificación e informes. Los envoltorios operativos privados están fijados a C; no son un instalador general para otras máquinas.

## Entrega y pendientes

Paquete de datos `RackClick-Datos-Demo-Original-01.zip`, SHA256 `c0c0844c29ebf8642cd7334406c969885e1858054301ea62afff184d73a09f15`, junto a `.local/entregas/servidor10/`. Cuatro entradas verificadas: original, inventario, LEEME y sumas. Sin cuenta/MFA de la instalación actual. Los ZIP instalador10 y envoltorio documental anterior se conservan intactos.

Guía visual detallada: `docs/QA-DATOS-ORIGINALES-MFA10-WASCAR.md`. No se sobrescriben resultados de Wascar. Catálogo QA actualizado sin habilitar casos en otros perfiles y guía central regenerada.

Exportación/importación **desde dashboard web todavía no implementada**; alcance en `docs/DATOS-DE-PRUEBA-Y-COPIAS-DASHBOARD-29-10-2026.md`. El cargador local del original no es P-01 completo ni un restore íntegro. La recuperación de claves MFA/sobre, bases nuevas, canal operativo web y QA visual siguen pendientes. La copia nativa por sí sola no permite reconstruir MFA en otra máquina.

Índice de cierre restante **9,76/100 sin incremento**, mismos pesos/denominador. Sin commits ni push.
