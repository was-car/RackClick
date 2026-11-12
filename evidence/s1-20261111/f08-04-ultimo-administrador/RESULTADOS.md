# F-08.04 · único administrador y reenrolamiento pendiente

11.11.2026. Cierre técnico con revisión independiente favorable, tras corregir el hallazgo D2. D y E sin operaciones, sin VM, servicios, cuentas o bases instaladas, commits, push o despliegue.

## Alcance reutilizado y hallazgo corregido

Se reutilizan generación/canje/enrolamiento de punto 3 y F-08.01–.03; no se construye otro login. El caso nuevo acredita que un único administrador global activo, identificado por ambas capacidades globales, recupera con su contraseña/código sin otro administrador, mantiene autoridad y vuelve a operar tras confirmar el factor nuevo. Un administrador limitado a cliente no cuenta como segundo global.

Durante la revisión se encontró y reprodujo independientemente **D2-RECOVERY-DISABLE**, preexistente: con el usuario en gracia y recuperándose, otro administrador con MFA podía ejecutar disable; desaparecía pending y un login posterior daba sesión sólo por contraseña. Contradecía D2/F-03.02 §5. La corrección modifica únicamente `MfaAccountManagement.cs`: rechaza disable con pending mediante 409 `mfa_enrollment_required` y publica `CanDisable=false`. Conserva desactivación propia de factor activo/no pendiente durante gracia o exención global.

Consulta oficial del 11.11.2026: [OWASP MFA, recuperación](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html#resetting-mfa). Se mantiene el contrato confirmado, sin bibliotecas, migraciones, endpoints, algoritmo o política nuevos. Node usa esbuild 0.25.10 ya fijado, copiado de las dependencias existentes y comprobado, sin instalar o cambiar versiones.

## Qué se comprueba

- Único global: hay dos usuarios activos, sólo uno con `security.manage` y `systemhaus.manage` globales. Con contraseña/código propios queda en enrolamiento sin sesión; otro login también queda restringido. No se necesita otro global con MFA.
- Tras confirmar el nuevo factor: misma identidad/contraseña/grupos/concesiones, sesión y CSRF nuevos, lectura de usuarios y capacidades originales. Repone expresamente diez códigos nuevos y habilita MFA de otra cuenta mediante una escritura administrativa protegida del almacén.
- La guarda existente rechaza desactivar al único administrador de seguridad global y revierte ese intento. Esa guarda usa `security.manage` global; la exención MFA requiere ambas capacidades. No se confunden ambas definiciones ni se redefine A-02.
- Dos negativos con código válido: cuenta deshabilitada y factor bloqueado no se reactivan ni consumen el conjunto. Sólo puede invalidarse el desafío presentado. El SQL que prepara una revocación externa pertenece al fixture, no elude la guarda de producto en una instalación.
- Dos regresivos D2: disable de otra cuenta recuperándose durante gracia, y defensa de la ruta propia global con sesión verificada sintética, reciben 409, `CanDisable=false`, snapshot invariable y login todavía enroll sin sesión. La sesión propia se inyecta sólo en ese fixture; no es una sesión que el login normal emita durante pending.

## Ejecuciones y errores conservados

Windows, SDK 10.0.401/runtime 10.0.12, PostgreSQL 17.11, esquema 46. Copia `.local/f0804-24f412cc/freeze`; conexiones, valores, TRX, logs y binlogs privados. Build final: exit 0, cero errores y advertencias.

| Ejecución | Resultado real |
|---|---|
| Primer foco anterior al hallazgo D2 | 6/7 PASS; el nuevo positivo esperaba Purpose=verify, pero el contrato de almacén usa null como valor por defecto que Program convierte en verify. Se corrigió sólo la aserción, manteniendo desafío presente y sesión ausente |
| Repetición focal tras esa corrección | 3/3 PASS, sobre el producto anterior |
| Sonda roja del revisor | Reproducción real de disable→password-only, con administrador y usuario enrolados antes; no es sólo lectura estática |
| Rojo versionado antes del cambio de producto | 0/2 PASS: ambos nuevos regresivos fallan con No exception was thrown |
| Verde versionado con la corrección | 2/2 PASS, sin omisiones |
| Regresión ampliada final | 49 seleccionados: **48 PASS, 0 FAIL, 1 NotExecuted de navegador opcional** |
| Comprobación posterior de selección | Sólo discovery, salida 0: los 48 nombres del ámbito requerido coinciden exactamente con los 48 UnitTestResult Passed anteriores. No ejecutó otras 48 pruebas |
| Node final | **68/68 PASS**, 0 fallos/omitidas; cuenta MFA, API y recuperación, incluido bundle en memoria del componente existente |
| Revisor sobre binarios finales | 5/5 casos nuevos PASS y sonda verde propia con administrador/usuario enrolados, ejecutadas por él en otros clústeres |

La regresión amplió la selección a siete clases de gestión, gracia, HTTP y recuperación. Se descubrieron 49 casos y uno era `MfaDashboardHttpTests.BrowserDashboardShowsGraceAndManagesPersonalAndSelectedUserMfa`: requiere build frontend y runner de navegador explícitos, no aportados en este foco. El driver salió 1 por exigir 49 PASS; el código del hijo no se guardó antes de esa aserción. El TRX conserva 48 PASS/0 FAIL/1 omitido; no se reescribe como una ejecución nueva 48/48 o salida 0. Se corrigió el filtro para excluir ambos navegadores opcionales y se contrastó sólo su discovery con los resultados ya ejecutados, evitando repetir 48 casos para ocultar el salto. SCOPE-RECONCILIACION.json conserva esa separación.

El primer Node registró 20 PASS y un fallo de carga de módulo porque la copia aislada omitía esbuild, que necesita el test de cuenta. Se copiaron esbuild/@esbuild-win32 fijados desde node_modules existente con comparación de hashes; se conservó el intento y la pasada final 68/68. No se modificaron fuentes frontend ni se instaló dependencia. El aviso MODULE_TYPELESS_PACKAGE_JSON preexistente se conserva.

Las pruebas de producto no se debilitaron para conseguir verde. La corrección D2 sí tiene rojo previo real; el ajuste inicial del Purpose fue un error del fixture y no se presenta como defecto del producto.

## Identidad y procedimiento

Base de 227 archivos de producto: **226 invariables y uno corregido**. El diff de producto contiene dos adiciones de guarda y una condición de CanDisable. La única prueba nueva es `MfaLastAdministratorRecoveryTests.cs`; las tres pruebas nuevas de F-08.01/.02/.03 se conservan. FUENTES.json distingue esas categorías y las 29 fuentes asignadas del punto 3 que aún coinciden; no sostiene identidad de MfaAccountManagement con la revisión histórica.

[Ficha y procedimiento del último administrador](../../../docs/PASO-027-ULTIMO-ADMINISTRADOR-MFA.md). Se extendió QA-163 para pending/Desactivar y recuperación del único global, sin cambiar disponibilidad planificada, pasos anteriores o los otros 174 casos. No se alteran resultados de Wascar. El cambio queda en fuentes, **sin actualizar D/E ni una distribución instalada**.

Comandos de build/test/discovery incluyen `-bl:<privado>/*-{}.binlog`. Los drivers usan `dotnet test ... -c Release --no-build --no-restore --filter <selección>` y Node 24.21.0 `--test mfa-account.test.mjs mfa-api.test.mjs mfa-recovery.test.mjs`. Los tests y el helper PG son fuentes del repositorio; los drivers privados sólo fijan herramientas, entorno y clústeres nuevos. No son operadores para D.

## Límites de aceptación

La vía presupone host/proveedor disponible, cuenta utilizable, contraseña conocida y códigos válidos guardados privadamente. No garantiza que siempre exista material custodiado ni reactiva una cuenta revocada. La exención global permite quitar voluntariamente un factor activo propio; pending no equivale a esa condición.

El foco nuevo usa almacén/PG y claves sintéticas; las operaciones administrativas se prueban directamente en el almacén, no todos los controles HTTP de reautenticación de F-11. Los dos casos HTTP existentes se incluyen en la regresión. El navegador antiguo se reutiliza con atribución; no se ejecutó navegador, TLS, SID/DPAPI/servicio real o instalación en esta tanda.

La comparación de autoridad cubre fila de usuario, grupos, miembros y concesiones; el snapshot habitual diez tablas y los negativos nueve excluyendo el desafío invalidable. No son toda la DB ni análisis de memoria, todos los logs o historial. F-08.05, custodia operativa, emergencia local F-09, candidata instalada y aceptación de Wascar siguen pendientes. No se añaden puntos por tests o por corregir el hallazgo; sólo el 1/2 de F-08.04 si la revisión es conforme.


Pines finales: servidor `dd285c4f7561d8f7e678178a12d399782f0c2142712d16bff10ec87762f85d0e`; pruebas `1d0332b69238239aa6b8f4214f7a8fd186c26945dc99f6e7c905998a028605c4`. La prueba nueva tiene SHA256 `cbf89d394abac2427cd7df5fdfb8de4950f0e67bf5ca1e32ae901d003b022c6f`. Las referencias anteriores quedan inmutables; sólo este lote incorpora la corrección D2.

Precisión de inventario: MfaAccountManagement era un soporte ya existente y no integra la comparación de treinta archivos asignados del punto 3. Su hash histórico se contrasta en el soporte de F-08.01 y coincide con el before de este cambio; por eso hay 29 archivos asignados idénticos más ese soporte modificado, no 28.


## Revisión y conciliación

[Dictamen independiente](review/DICTAMEN.md): cinco casos nuevos propios y sonda roja/verde con enrolamientos reales de aplicación y claves sintéticas; todo delimitado de la regresión y Node del coordinador. Hallazgo D2 corregido y sin bloqueantes abiertos en alcance. Sólo F-08.04 suma 1/2: 1985/84 → 2027/84 = 24,130952…/100 del cierre restante. No se adopta ni instala la corrección. F-08.05/hitos operativos siguen pendientes.
