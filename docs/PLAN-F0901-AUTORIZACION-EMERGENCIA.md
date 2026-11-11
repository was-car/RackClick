# F-09.01 · autorización local de emergencia MFA

> Ejecución del coordinador con superpowers:executing-plans y revisión de seguridad independiente acotada. Plan derivado de las decisiones D2 ya confirmadas; no otra aprobación de arranque. Sin commits/push, VM, instalación o cambios en D/E.

**Objetivo:** introducir la compuerta real del futuro operador local de pérdida total: SYSTEM o Administradores con token elevado, sin suplantación, sin autoridad desde HTTP, entorno, roles web o contraseña.

**Arquitectura:** conservar `--recover-admin` para Restore y los operadores de F-06. Nueva rama temprana `--mfa-emergency-recovery` de `Program.cs`, antes de configuración, SQL y listener. `MfaEmergencyRecoveryCommand` captura identidad Windows real y evalúa una política interna cerrada. Hasta implementar el protocolo de F-09.02/.03, incluso un operador autorizado recibe `mfa_emergency_transition_unavailable`, salida1 y cero operaciones; no se simula una recuperación ni se emite un recibo reutilizable como permiso.

**Tecnología:** .NET10.0.401 fijado, WindowsIdentity/WindowsPrincipal y GetTokenInformation(TOKEN_ELEVATION), sin dependencias, SQL o GUI nuevos. Build privado separado del árbol concurrente, con binlogs privados.

**Especificación:** F-09.01 del ledger y paso29; `docs/D2-CONDICIONES-TECNICAS-F03-02.md` §1/§2.2; custodia confirmada y gracia45/exención global. Una autorización local no concede sesión API. Los pasos30–33 y todos los hitos completos F-09 conservan su alcance pendiente.

## Decisión e investigación previa

Se reutilizan las consultas de token de `MfaMaintenanceCommand` y `MfaKeyStoreInitCommand`, la exclusión de modos de `Program`, y el login/pending probado en F-08. No se reutiliza `--recover-admin` para pérdida total: crea un administrador de Restore y no tiene el protocolo requerido. Extenderlo mezclaría autoridades y efectos ya revisados. Tampoco se añade una ruta web ni se admite un booleano de configuración como autoridad.

Microsoft Learn consultado11.11.2026: [GetCurrent .NET10](https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsidentity.getcurrent?view=net-10.0), [IsInRole .NET10](https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsprincipal.isinrole?view=net-10.0), [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation), [TOKEN_ELEVATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_elevation). Se comprueban pertenencia efectiva y elevación del token, no nombre/grupo textual o claims. Los tipos están en el framework existente; no se copia código externo, instala biblioteca o cambia lock/licencia. La lectura nativa falla cerrada si no puede determinar la elevación. SYSTEM se identifica por SID conocido; no se acepta suplantación ni para SYSTEM. «Local» significa autoridad del proceso Windows ejecutado en ese host; no exige consola física ni prohíbe una sesión RDP administrativa autenticada.

## Propiedad y pruebas

- [x] **1. Referencia y rojo.** Snapshot privado de Git/metadatos/fuentes y copia aislada del servidor vigente. Crear `MfaEmergencyAuthorizationTests.cs` con tabla de autoridad y `MfaEmergencyProcessTests.cs` con conflicto/modo/entrada aislada. Ejecutar negativos del modo ausente sobre producto anterior; conservar fallo por ausencia de la rama, sin inventar un fallo de seguridad existente.
- [x] **2. Compuerta mínima.** Crear `development/server/src/RackClick.Server/MfaEmergencyRecoveryCommand.cs` e integrar sólo la rama temprana/exclusión en `Program.cs`. Rechazar plataformas ajenas, impersonación, usuario estándar, token filtrado/no elevado o lectura desconocida; reconocer SYSTEM y administrador elevado en política. No leer stdin/DB, claves o configuración en esta fase; no listener, efecto o éxito operativo. La decisión pura interna sólo sirve a pruebas; CLI no la toma de DI/JSON/env.
- [x] **3. Verificación pertinente.** Build nuevo en copia privada, tabla/identidad Windows real y proceso CLI; conservar casos de operadores anteriores y host afectados. PostgreSQL nuevo para negativos de rutas HTTP y dos casos restringidos F0802, con rol runtime y proveedor sintético. No repetir navegador/Node de F0805 ni atribuirle estabilidad; su observación permanece abierta. Mutación acotada: permitir usuario estándar y/o saltarse la rama temprana debe hacer fallar el foco correspondiente.
- [x] **4. Revisión y registro.** Revisor distinto inspecciona autoridad/aislamiento y repite casos pertinentes sin modificar producto. Ficha29, matriz/evidencia/sellos/escaneo, continuidad y changelog; sólo F-09.01 puede pasar done y sumar1/2 tras conformidad. Los otros cuatro checkpoints/hitos F-09 permanecen pendientes; sin adopción o instalación de la compuerta.

## Foco de revisión

- Administrador global de RackClick no equivale a Administradores de Windows; contraseña/claims/variables no autorizan el operador.
- Token filtrado o no consultable y suplantación fallan cerrados; no se cambian privilegios del token.
- Todas las combinaciones con siete modos anteriores dan conflicto antes de configurar host/leer secretos; argumentos extra tampoco abren el host.
- Configuración de SQL/MFA/origen deliberadamente inválida no se procesa por esta rama; respuesta constante sin pila, ruta, SID, entrada ni contraseña.
- Estado tras pérdida sigue exigiendo factor nuevo: se reutiliza F-08 para el no-bypass. No se declara pérdida total, nuevo anillo, revocación o recuperación ya implementados.

**Límite de entorno:** los positivos SYSTEM/elevación de la política no equivalen a lanzar un proceso elevado real. Sin utilizar D/E ni modificar privilegios del host, se probará el token disponible y la suplantación propia controlada; el ensayo elevado real sigue en la aceptación operativa de F-09.04/.05.


Cierre técnico11.11: [resultados](../evidence/s1-20261111/f09-01-autorizacion-local/RESULTADOS.md), [dictamen](../evidence/s1-20261111/f09-01-autorizacion-local/review/DICTAMEN.md). Compuerta real revisada; no transición de pérdida total disponible ni cambio de D/E.
