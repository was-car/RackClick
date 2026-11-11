# F-09.04 · ensayo de pérdida y recuperación

11.11.2026. **Cerrado técnicamente con revisión independiente favorable.** Se reutilizó F-09.01–.03 antes de implementar. D no se accedió; las instalaciones anteriores de E se conservaron. Sin commits, push, adopción ni actualización de instalaciones existentes.

## Fuentes y producto

SDK10.0.401, runtime10.0.12 y PostgreSQL17.11. Npgsql directo, SQL y componentes Windows/DPAPI aprobados, sin dependencias nuevas. Fuentes/binarios congelados antes del ensayo. DLL servidor:

`d9366dbe9be377d4147417fd8c51e40aaa302b82c8d3bd9b830c67d68980b909`

DLL pruebas: `f15ec85332b379819c6a6462ab24a20dab7bfe45409f56e354fd6e7463c7e829`. Manifiesto de revisión: `16e57ef88178b5b0cf01eb507f979f85514c634b5d98df7a1169cb0936641161` (514archivos de fuentes/577binarios). El contraste final conserva513de514archivos; la única diferencia es el README, actualizado después para documentar el resultado. Código, pruebas, SQL, proyectos y locks no difieren. La publicación nativa conserva la DLL revisada.

Se conservan221de232fuentes de producto del paso31; cambian11 y se añaden4, total236. Nuevos: SQL048, `MfaLossStartupGuard`, la parcial `WindowsMfaMaintenanceStore.LossStartup` y `MfaLossRecoveryCommand`. [FUENTES.json](FUENTES.json) fija hashes; [CAMBIOS.patch](CAMBIOS.patch), el diff. Dos clases nuevas aportan40casos; los fixtures históricos de esquema47 e inicialización se corrigieron sin relajar aserciones.

La proyección48 contiene19campos explícitos de metadatos y no es actualizable. La finalización comprueba disponibilidad/permisos runtime antes de publicar recibo y liberar el fence por identidad. La guarda arbitra historias de pérdida/rotación por versión e identidades; recibo, material o testigo incoherentes rechazan antes del listener. El rol runtime sigue sin DDL ni acceso al archivo privado de factores.

La CLI acepta hasta65536caracteres UTF-16, no65536bytes. Exige autoridad Windows nativa antes de stdin, JSON cerrado, confirmaciones e identidades explícitas, SCM detenido/vinculado y sobre fuera de toda la raíz nativa y backups. Sus respuestas distinguen datos verificados de servicio recuperado; nunca crean sesión.

## Pruebas de componentes

| Ejecución | Resultado | Alcance |
|---|---|---|
| Rojo de guarda/recibo/layout | 0/7 PASS | Antes de implementar el recorrido48. |
| Rojo CLI válido, secuencial | 0/21 PASS | El intento anterior solapado con build es inválido y no se cuenta. |
| Rojo de proyección requerida | 0/1 PASS | No liberar fence sin proyección runtime. |
| Regresión final del coordinador | **378/378 PASS,0omitidas** | Windows/PG nuevo y hashes finales. |
| Repetición independiente previa | **40/40 PASS,0omitidas** | Copia inmutable/PG nuevo, revisor distinto del implementador. |

Se usaron restore locked-mode, build Release sin incremental y test sin recompilar/restaurar, con filtros pertinentes y binlogs privados. [FOCOS.json](FOCOS.json) conserva casos, resultados y hashes de TRX, incluidos fallos intermedios. No se volvió a ejecutar la regresión por cambiar sólo el arnés; no se suman rondas ni se presenta toda la suite histórica como ejecutada. Binlogs, conexiones y diagnósticos completos quedan privados.

## Ensayo nativo final en E

Instancia nueva con servicios SCM y PostgreSQL propios. Servidor con cuenta Windows estándar, secreto SQL runtime protegido y proveedor DPAPI real. Mantenimiento SYSTEM mediante tareas acotadas/retiradas. Cliente HTTP final Administrador Windows, autenticándose por contraseña y TOTP de aplicación; sin bypass ni proveedor sintético.

| Fase real | Resultado |
|---|---|
| Preparación y arranque | Schema48, runtime SQL restringido, DPAPI, certificado propio sin importarlo al almacén raíz global y MFA habilitado. |
| Baseline | HTTPS/pin/nombre, último global con factorv1, cliente/rack/equipo sintéticos, sesión válida, desafío pendiente y diez códigos. API denegada antes del TOTP. |
| Pérdida | App detenida; se retira su única clavev1 sin copiar material y se conserva anillo. |
| Arranque perdido | ServicioStopped, cero listener y stderr exacto `mfa_keystore_version_missing`. Start solicitado no se contó como readiness. |
| Prepare/export/apply/publish/complete | Cinco salidas0, misma operación, v2 y sobre privado297bytes. Todas con sessionGranted=false y serviceVerified=false. |
| Recuperación | HTTPS y guardas con rol runtime; sesión vieja y solicitudes antiguas rechazadas; revocación/testigo SQL; inventario sentinel igual. Sólo TOTP nuevov2 emite sesión/CSRF nuevos y permite leer el sentinel por API. |
| Cierre | Sólo servicios propios detenidos. Dos servicios previos Running con igual PID, puertos propios cerrados, cero tareas propias; intento archivado conservado. |

Son16fases finales con salida0:14tareasSYSTEM completas/retiradas y2fasesHTTPAdmin, no16instalaciones ni puntos de progreso. [NATIVO.json](NATIVO.json) fija recibos/hashes/estado final.

La solicitud sobre desafío antiguo usa un TOTP inválido: no se presenta como canje de TOTP antiguo válido. La solicitud de recuperación sí usa un código emitido antes de la pérdida. También se comprueban conteos SQL y revocación. Se compara el sentinel del laboratorio, no los50clientes de D.

## Incidentes preservados

No fue una secuencia íntegramente verde. Se conservan staging rechazado por padre ausente; Provision01 bloqueado por EOF heredado; intento archivado íntegro con catálogo desconocido/estado no limpio; P02 con retorno PowerShell inesperado tras crear dos roles; P03 con fallo de lectura del PID cuya causa interna original no se midió; rechazo Scheduler por contexto de acción ausente; y fallos iniciales del cliente HTTP.

P04 terminó sobre el mismo clúster limpio y credenciales, tras comprobar catálogo; no se recrearon roles ni se reparó el intento archivado. Launcher49 añade contexto explícito sin reescribir el48 histórico/plan. El cliente final usa TLS1.2, pin/nombre intactos y un máximo de tres GET de salud ante Timeout. No repite POST, seed ni transición SQL. Antes del Baseline final, siete relaciones se comprobaron vacías por SQL de sólo lectura. Los clientes HTTP SYSTEM fallidos no se convierten en PASS ni reciben una causa retrospectiva no medida.

[INVESTIGACION-NATIVA.md](INVESTIGACION-NATIVA.md) documenta causas medidas y límites. El paquete inicial y helpers congelados no se reescribieron para aparentar que contenían los cambios del arnés. DLL/perfil del servidor conservados durante esas correcciones.

## Revisión y alcance restante

[DICTAMEN.md](review/DICTAMEN.md) es favorable. Los40casos pertenecen al revisor previo; el revisor nativo final ejecutó focos locales PS5.1 y leyó fuentes/recibos, **sin operar E ni repetir SQL/HTTP nativos**. La ejecución nativa se atribuye al coordinador.

[SCAN.json](SCAN.json) registra Gitleaks8.30.1 sobre el subconjunto público del lote: un hallazgo conservado, clasificado independientemente como contraseña constante de usuarios sintéticos en una clase de pruebas. No es contraseña de conexión ni token de proveedor y no forma parte del paquete nativo. No se cambió la constante ni se añadieron exclusiones; no se declara escaneo limpio ni barrido de todo el historial/diagnóstico privado. La salida nativa del scanner fue10 y el wrapper inicial devolvió1; la verificación posterior conserva esa información y la clasificación contextual.

F-09.05 y seis hitos completos del módulo siguen pendientes. También instalación/Restore48, candidata/operadores/manual de entrega, mantenimiento Admin sin SYSTEM, custodia externa efectiva, segunda pérdida independiente, retirada después de loss sin rotación y QA/adopción. No se ensayaron pérdida de todos los metadatos, apagón/reinicio ni namespace nuevo. Tampoco se acredita reposición de fence tras un fallo operativo posterior a Complete por haber tenido un arranque final exitoso.

Sólo F-09.04 cambia pending→done: **+1/2**,2195/84→**2237/84=26,630952…**, redondeado **26,63/100 del cierre restante**.55done/223pending/2in_progress;53resultados/280checkpoints/268números. No es porcentaje global nuevo. Siguiente: paso33/F-09.05.
