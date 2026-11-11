# F-08.04 · plan de recuperación del último administrador con códigos

> Ejecución del coordinador y revisión independiente acotada. Skills de planificación, ejecución y verificación ya aplicadas a los pasos anteriores. Continuación autorizada por Wascar; sin commits ni operaciones en D/E.

**Objetivo:** demostrar que el único administrador global activo puede recuperar su propia cuenta con contraseña/código válidos, conservar identidad y permisos y volver a administrar después de confirmar un factor nuevo.

**Arquitectura:** reutilizar generación/canje/enrolamiento de F-08.01–.03 y HTTP de F-08.02. Añadir sólo pruebas de almacén para la condición explícita de un único global por capacidades, preservación de permisos, reposición de códigos y guarda de último administrador. El reset web de otra cuenta no sustituye la autorrecuperación; no crear un bypass ni un operador local.

**Especificación:** F-08.04 del [ledger](PLAN-CIERRE-RACKCLICK.json), paso 27 del [plan numerado](PLAN-PENDIENTES-NUMERADO.md), [decisiones confirmadas](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md), [condiciones D2](D2-CONDICIONES-TECNICAS-F03-02.md) §2.1 y [gracia45/exención global](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md). El acceso completo requiere confirmar otro factor; no se recupera por código una cuenta deshabilitada ni se omite un bloqueo vigente.

**Tecnologías:** .NET 10.0.401, PostgreSQL 17.11, Npgsql directo y xUnit existentes; clave sintética de laboratorio. Producto, SQL, dependencias, interfaz y política sin cambios. Propietario de DB y rol runtime separados; pruebas y binlogs en copia privada aislada.

## Investigación y decisión

Se reutilizan fuentes, revisiones y resultados de punto 3 y F-08.01–.03. Investigación proporcional del 11.11.2026: [OWASP, recuperación y cambio de MFA](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html#resetting-mfa), que trata códigos de recuperación y el riesgo de convertir la recuperación en una vía de elusión. Se conserva el contrato ya confirmado, sin copiar código ni adoptar un proveedor/dependencia nueva. No se implementa otra política de emergencia.

## Tareas

- [x] **1. Conciliar alcance e identidad.** Conservar los 227 archivos de producto y evidencia previa. Contrastar `RedeemRecoveryCode`, `AuthenticateForLogin`, enrolamiento, gestión MFA, capacidades globales y guardas de último administrador. Distinguir autorrecuperación con códigos, reset de otro usuario y emergencia local F-09.
- [x] **2. Probar condición de último global.** Crear sólo `development/server/tests/RackClick.Quality.Tests/MfaLastAdministratorRecoveryTests.cs`. Un caso positivo con un único global activo y otro administrador limitado a cliente: contraseña/código → pending sin sesión, permisos/identidad conservados, confirmación nueva → sesión MFA, reposición explícita de diez códigos, administración de otra cuenta y rechazo de desactivar al único administrador. Dos negativos: cuenta deshabilitada y factor bloqueado no se reactivan ni consumen el juego de códigos por tener un código válido.
- [x] **3. Foco y revisión.** Compilar copia fijada con binlogs privados. Ejecutar tres casos nuevos, dos HTTP existentes de F-08.02, negativo de capacidades limitadas a cliente y reset anterior que invalida códigos. Revisor distinto repite sólo los tres casos nuevos en otro clúster. Reutilizar consumo/rollback F-08.03 y Node/Edge anteriores sin presentarlos como ejecuciones nuevas.
- [x] **4. Registrar cierre y procedimiento.** Ficha 27 con pasos de autorrecuperación y límites, evidencia sanitizada, hashes, dictamen, changelog/continuidad. Sólo F-08.04 (+1/2) si corresponde; F-08.05 e hitos operativos siguen pendientes. Conservar los 175 casos QA y reutilizar QA-163 sin alterar resultados/disponibilidad. Regenerar/verificar índices y guía.

## Foco de revisión y límites

- «Último global» deriva de cuenta activa y capacidades globales `security.manage` y `systemhaus.manage`; no del nombre del grupo o una concesión limitada a cliente.
- El pending sigue prevaleciendo sobre la exención global de gracia45; códigos no conceden acceso administrativo antes de confirmar un nuevo factor.
- Recuperar preserva usuario, contraseña, grupos y permisos; la sesión nueva debe superar una operación administrativa real del almacén y la guarda contra desactivar al único administrador.
- El caso de cuenta deshabilitada se prepara sólo mediante SQL de fixture para representar una revocación externa: no modifica ni elude la guarda del producto.
- La condición presupone host disponible, contraseña válida y códigos previamente guardados. No prueba custodia real, disponibilidad sin almacén, pérdida de contraseña, cuenta eliminada o emergencia local F-09. La exención global permite quitar voluntariamente el MFA propio; no se inventa una prohibición que contradiga a Wascar ni se garantiza que siempre conserve códigos.

## Ajuste durante la revisión · D2-RECOVERY-DISABLE

El revisor reprodujo en un laboratorio independiente que `disable` administrativo durante la gracia puede borrar `enrollment_pending` tras un canje y permitir una sesión de contraseña sin nuevo factor. Es un fallo preexistente contrario a D2/F-03.02 §5, no una decisión de política pendiente. Antes de cerrar esta tanda se incorpora una corrección acotada en `MfaAccountManagement.cs`: rechazar `disable` mientras hay pending y reflejarlo en `CanDisable`. Mantener permitido desactivar un factor activo/no pendiente según gracia45 y la exención global.

Se añaden dos negativos versionados al archivo de prueba nuevo antes de corregir producto: acción de otro administrador sobre usuario en gracia y defensa de la ruta propia global con sesión verificada sintética. Esta última sesión se inyecta sólo en el fixture; el login normal no puede emitirla mientras pending. Conservar rojo real y verde. Ampliar una sola regresión final a gestión MFA y sus dos casos HTTP; repetir Node de cuenta/API/recuperación por el cambio visible de `CanDisable`. Extender QA-163 con ese estado, manteniendo los 175 casos, disponibilidad y resultados de Wascar. La afirmación inicial de producto completamente intacto queda sustituida por **226 fuentes conservadas y una corrección revisada**, sin despliegue en D/E ni peso adicional.


Cierre técnico del 11.11: [resultados](../evidence/s1-20261111/f08-04-ultimo-administrador/RESULTADOS.md), [dictamen](../evidence/s1-20261111/f08-04-ultimo-administrador/review/DICTAMEN.md). El ajuste D2 se rige por la adenda anterior, con rojo previo, una corrección de producto y QA-163 extendido; D/E sin desplegar.
