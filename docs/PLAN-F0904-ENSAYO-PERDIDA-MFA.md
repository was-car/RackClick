# F-09.04 · ensayo operativo de pérdida de claves MFA

> Coordinador implementa/prueba por fases, con revisión independiente de seguridad. Continuación D2/F09 autorizada; D permanece intacta. No commits, push, adopción ni actualización de instalaciones existentes.

**Objetivo:** pérdida de todas las claves con metadatos fiables → arranque normal rechazado → recuperación local explícita → publicación comprobada y fence liberado → host normal → enrolamiento restringido → TOTP nuevo y acceso. No confundir prueba backend con servicio Windows recuperado.

**Arquitectura decidida:** reutilizar el protocolo loss-reset232fuentes/F0903 y su archivo/auditoría047. Añadir recibo de arranque propio de pérdida y finalización explícita; una proyección48 sólo de metadatos e intrínsecamente no actualizable para runtime. El guard arbitra pérdida/rotación por versión e identidades, conserva ambos historiales y no fabrica un recibo rotate. La CLI mantiene autoridad nativa anterior a stdin y usa JSON cerrado/acotado, sobre externo y confirmaciones por UUID. No cambia la autenticación web.

**Tecnologías:** SDK10.0.401/.NET10, Npgsql/PG17.11, Windows/DPAPI y writer/reader/sobre aprobados. Sin bibliotecas/versiones nuevas. Binlogs/credenciales/diagnósticos privados. Manual/QA175 y resultados personales se conservan.

## Investigación previa y límites reales

Contrastados planes/resultados/sellos F0901–.03, D2§2.2/§4, mantenimiento/rotación/guardas/Program y arneses F06/F04. F06 prueba componentes/procesos/PG, no servicio real+HTTPS+MFA; no se reutiliza ese límite como evidencia operativa nueva. El instalador16 y runtime publicados todavía fijan45: no sustituir DLL dentro de esos paquetes ni ejecutarlos sobre48. El ensayo nativo necesita instancia sintética, identidades/puertos/rutas exclusivos y un harness fijado, conservando las instalaciones existentes.

Fuentes oficiales consultadas: [vistas y actualizabilidad PG17](https://www.postgresql.org/docs/17/sql-createview.html), [transacciones](https://www.postgresql.org/docs/17/tutorial-transactions.html), [rutas largas Win32](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation). La investigación previa de ACL/handles/rename/DPAPI se reutiliza. Decisión: vista con campos explícitos y GROUP BY, no grants del archivo privado; extendidos Win32 sólo si el rojo demuestra el límite en rutas nativas, sin debilitar anclaje/ACL.

Riesgos ya identificados: rotate viejo rechazaría pérdida posterior; runtime no lee schema privado; el root de claves security y el root SCM son diferentes en layout nativo; el candidato profundo puede superarMAX_PATH. Se escribirán negativos antes de cada adaptación.

## Tareas y archivos

- [x] **1. Referencia/rojo:** freeze privado y comparación232fuentes/sello31. Pruebas nuevas de finalización, guard/metadatos, arbitraje con rotación y layout/rutas; preservar tests históricos. No modificar producto antes de observar el rojo pertinente.
- [x] **2. Finalización y guard:** `048-mfa-loss-startup.sql`, `MfaLossStartupGuard.cs`, parcial `WindowsMfaMaintenanceStore.LossStartup.cs`; adaptar coordinator/lector witness/historia conocida/SchemaMigrations y entrada del guard de rotación. Recibo legible por servicio, identidad/hash propios, completion privado; sólo tras verificación DB/material y exclusión se retira el fence por identidad. Arranque siempre de sólo lectura; recibo/DB faltante, rollback o incoherencia rechazan antes del listener. Reentrada no convierte sesión nueva en razón para repetir la transición.
- [x] **3. CLI:** componer `--mfa-emergency-recovery` con parser cerrado y límites de entrada, acciones explícitas, SCM parado/vinculado, custodia externa y mensajes sanitizados. No password-only, env/DI de autorización ni exportación por stdout. Conservar rechazo nativo estándar y pruebas F0901.
- [x] **4. Host/laboratorio:** positivo y negativos con PG nuevo/owner-runtime/DPAPI/HTTPS; pérdida de claves reales del fixture, sin sobre/códigos anteriores útiles, inventario conservado. Reutilizar F0903 para último global; contrastar el recorrido HTTP completo con cookie/CSRF nuevos y API inaccesible hasta TOTP. No afirmar desaparición de toda metadata o namespace nuevo.
- [x] **5. Ensayo nativo:** cuando Wascar encienda E u otra VM asignada, comprobar binding/Tools/identidad sin tocarD. Harness nuevo atribuido con servicio/cuenta/DB/rutas/puertos exclusivos; versión48 fijada, guard y HTTPS reales, cuenta estándar del servicio y operador elevado. No limpiar/reinstalar E ni usar sus contextos históricos como instancia nueva. Recoger resultado sanitizado, parar sólo procesos propios y conservar evidencia.
- [x] **6. Revisión/conciliación:** revisión independiente acotada, regresión pertinente única tras estabilizar, scan y sellos; continuidad/changelog/guía/hoja. F0904 sólo podría pasar done con evidencia suficiente (+1/2,26,13→26,63); si el ensayo nativo falta, mantener in_progress sin crédito. F0905/adopción permanecen pendientes.

## Reglas de parada

No recrear versión1, adivinar un censo, retirar archivos ajenos, borrar inventario o desactivar el proveedor para arrancar. El CLI no inicia sesión y su fase data_verified no significa servicio/usuario recuperados. Fallo de arranque tras publicación conserva commit/material y repone fence; no rollback automático de claves. Sin VM encendida se prepara/prueba lo independiente y se registra exactamente el ensayo pendiente. Encendido/apagado/snapshots siguen en manos de Wascar.

## Cierre técnico

Recorrido nativo completado y revisión favorable: ver [paso32](PASO-032-ENSAYO-PERDIDA-MFA.md). Sólo F-09.04 acreditado. La reposición de fence tras un fallo operativo posterior a Complete no se ensayó; no se acredita por el arranque exitoso. El cliente HTTP final fue Admin, mantenimientoSYSTEM y servicio estándar. D e instalaciones previas de E conservadas; propios detenidos. F-09.05 e integración/adopción pendientes.
