# F-09.02 · material y transición interna de pérdida MFA

> Coordinador ejecuta con planificación/TDD/verificación y un revisor de seguridad distinto. D/E, servicios, cuentas e instalaciones preservados; sin commits, push o paquetes. Se continúa D2 confirmado, sin otra aprobación de arranque.

**Objetivo:** recorrido interno explícito Prepare → Export → Apply → Publish: candidato nuevo, preservación de material opaco/recuperable, archivo cifrado de factores retirados, pending obligatorio y anillo vivo nuevo verificado. Fence permanece; CLI F0901 continúa bloqueada. No se declara servicio recuperado ni crédito de F0903–.05.

**Arquitectura:** reutilizar exclusiones/ACL/identidades/fence de WindowsMfaMaintenanceStore, writer CreateStoreFromMaterial, proveedor Windows, catálogo/retención/sobre y admission F06. Añadir partial Loss, coordinador loss-reset y adaptador DB propios, sin convertir rotate en pérdida. Migración047 aditiva para witness/archivo en schema privado sin permisos PUBLIC/runtime, preservando014/046. Validadores de mantenimiento admiten historia contigua conocida45–47; rotación46/47, sin habilitar futuras versiones. No instalador/GUI nuevos.

**Especificación:** F-09.02/paso30 y D2 §2.2/§4; custodia confirmada, gracia45/exención y pending de F08. Revocaciones y marcador local mínimos se incluyen atómicamente por seguridad al retirar factores, sin acreditar por ello F0903; el archivo nunca sustituye el sobre externo ni se anuncia como backup restaurable.

## Investigación y decisión previa

Revisados F06, F08 y F0901: rotate exige descifrar todos los factores y conserva versiones, por lo que no puede reutilizarse como loss-reset. Un factor disabled sigue presente en el censo y colisiona con el futuro enrolamiento; debe archivarse completo y salir de la tabla viva. El archivo conserva ciphertext/metadatos, separado de auditoría y sin actor app inventado. El witness registra autoridad Windows y hashes/conteos, sin ciphertext ni secretos. El GRANT amplio de public no debe abrir el archivo: schema privado revocado, tablas calificadas en listas cerradas.

Fuentes oficiales consultadas11.11.2026: [transacciones PostgreSQL17](https://www.postgresql.org/docs/17/tutorial-transactions.html), [bloqueos](https://www.postgresql.org/docs/17/explicit-locking.html), [schemas/permisos](https://www.postgresql.org/docs/17/ddl-schemas.html), [RETURNING](https://www.postgresql.org/docs/17/dml-returning.html). Se reutilizan componentes .NET10/DPAPI/RCKEY fijados y Npgsql directo; no nuevas bibliotecas, extensiones o algoritmos. Las investigaciones previas del writer/fence/sobre conservan sus límites de durabilidad y de tokens sintéticos.

## Contrato y límites

- Cada entrada productiva captura de nuevo la autorización nativa F0901, con confianza fija SYSTEM/Administradores; ningún SID/booleano del request, entorno o DI la concede. Se conserva un seam explícito interno de fixture para ensayar componentes sin elevar este equipo.
- Censo fiable de ring/archivos, DB de todos los estados, journals/witnesses y backups. Versión nueva > máximo de todos, ≤1000000; ≤64 versiones retenidas+nueva. Sin ring/censo fiables se detiene: no crearv1 ni adivinar. La alternativa de namespace nuevo para pérdida de metadata queda fuera; no se finge soportarla.
- Raíces/backups declarados y pins se revalidan bajo exclusión. Las versiones perdidas se indican expresamente; una versión aún legible no se descarta. Factores de todas esas versiones, incluso pending/disabled y global/cliente/inactivo, quedan afectados. Versiones no declaradas deben seguir legibles y sus factores autenticarse.
- Antes de DB: fence, archivo privado de los objetos originales y candidato con lectura validada/DPAPI; sobre cifrado exportado sólo en memoria y autenticado contra el candidato en Apply. Los backups que dependen de versiones perdidas se identifican como afectados; no se borran ni pasan a ser recuperables con el sobre nuevo.
- Una transacción con snapshot de factores/usuarios/políticas/sesiones/desafíos/códigos archiva filas completas, retira sólo factores afectados, fuerza required/pending/revisión, revoca lo necesario y deja witness. Mantiene inventario, cuentas, permisos y fechas gracia. Registro local real, no changed_by del afectado. Fallo→rollback; commit incierto→fence y conciliación por UUID, sin repetir cambios.
- Publish valida witness/snapshot/candidato/fuente/objetos, publica sólo nueva clave/ring previstos y comprueba factores restantes. Conserva blobs antiguos y fence. No usa el recibo rotate para liberar arranque. CLI, startup guard loss-reset, servicio/SID efectivo/HTTPS y ensayo de pérdida total quedan pendientes.

## Ejecución

- [x] **1. Referencia y rojo:** snapshot privado del árbol/metadatos228 archivos y pruebas previas; prueba de selección de versión/capacidad que falle por componente ausente, sin afirmar defecto previo.
- [x] **2. Implementación:** `047-mfa-loss-reset.sql`, SchemaMigrations; `MfaLossResetDatabase.cs`, `MfaLossResetCoordinator.cs`, `WindowsMfaMaintenanceStore.Loss.cs`; adaptación mínima de historia conocida en mantenimiento/rotación y acceso interno a la autorización existente. Archivos nuevos de pruebas propios, sin alterar pruebas históricas para esconder fallos.
- [x] **3. Verificación:** Windows/DPAPI y PG17 nuevos con roles nativos; pérdida de claves con metadata fiable, mezcla legible/perdida y todos estados, preservación, límites de versión/backups, rollback/stale/tampering/reentrada/ACL/runtime, mismos UUID/pins. Mutación pertinente y regresión acotada de fronteras afectadas. Logs/TRX/binlogs/contraseñas/sobres privados.
- [x] **4. Revisión/registro:** revisor inspecciona y repite foco crítico. Documentar exactamente fases probadas/no disponibles, actualizar continuidad/changelog/hoja/QA conservada; sólo acreditar F0902 (+1/2) si el compuesto queda satisfecho. Conservar otros checkpoints/hitos y la observación Edge.


Cierre técnico11.11: [resultados](../evidence/s1-20261111/f09-02-material-perdida/RESULTADOS.md), [dictamen](../evidence/s1-20261111/f09-02-material-perdida/review/DICTAMEN.md). Publicación interna con fence comprobada; CLI/servicio/arranque de pérdida y aceptación pendientes.
