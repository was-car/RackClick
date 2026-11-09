# D2 · Límites de amenaza de la custodia MFA

03.11.2026 · Paso10/F-03.03. Registra el modelo de confianza del diseño existente; no cambia la custodia, los algoritmos, las cuentas o D. Complementa la [decisión de custodia](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md), las [condiciones técnicas F-03.02](D2-CONDICIONES-TECNICAS-F03-02.md) y la [política45](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md). No es una aceptación de producción ni una prueba de aislamiento ejecutada hoy.

## 1. Frontera de confianza

La clave que cifra los secretos TOTP vive fuera de PostgreSQL, en `mfa-keys` de cada instancia, protegida con DPAPI **LocalMachine**. El servicio estándar necesita leerla y usarla para el funcionamiento de MFA. SYSTEM y Administradores gestionan el almacén; el SID real del servicio sólo debe leerlo. La integridad del host Windows, sus administradores y el proceso que verifica MFA forman parte de la confianza del diseño.

**DPAPI LocalMachine no aísla las claves del administrador local, de SYSTEM ni del proceso de servicio comprometido.** El cifrado en reposo no crea una frontera frente a quien controla el equipo o el proceso que debe descifrar. La restricción de escritura del servicio protege el almacén, pero no impide que un atacante con ejecución en ese proceso use su lectura autorizada o capture material mientras se utiliza.

Microsoft documenta que el ámbito LocalMachine permite descifrar a otros usuarios del mismo equipo. En RackClick, impedir que otra cuenta obtenga el blob depende de las ACL y de los controles del lector; **no de un vínculo criptográfico exclusivo al SID del servicio**. El acceso efectivo depende del token Windows, sus grupos/privilegios y la DACL. No se presenta la validación del descriptor como prueba universal de todos los tokens y sistemas de archivos. [DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [DACL y tokens](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object).

La entropía adicional de RackClick se deriva del formato, `installationId` y versión. Es contexto de vinculación, **no otra contraseña secreta**. Los IDs del anillo o conocer ese contexto no autorizan a leer los archivos. Si alguien ya obtiene el blob en el host y ese contexto, no se promete que DPAPI lo distinga del servicio legítimo.

## 2. Qué cubre cada control

| Escenario | Protección prevista y límite |
|---|---|
| Sólo lectura de PostgreSQL o su dump | Los secretos TOTP siguen cifrados mientras no se obtengan las claves. No significa que todo el inventario, contraseñas verificables, códigos almacenados u otros datos de la DB estén cifrados o sean inocuos |
| Otra cuenta Windows estándar | DACL y lector deben negar lectura de `mfa-keys`; validación de propietario, tipo/ruta/identidad y permisos evita aceptar material inseguro. La comprobación efectiva bajo tokens reales pertenece a F-04 |
| Proceso del servicio estándar | Tiene lectura autorizada y puede descifrar las claves de sus versiones accesibles. Su compromiso puede exponer claves/TOTP y permitir actuar con los permisos DB/API del proceso; MFA no protege frente al servidor comprometido |
| Administrador local/SYSTEM, control del host o hipervisor | Pueden alterar permisos/programas, controlar o inspeccionar procesos o acceder a estado del equipo. Están fuera del aislamiento ofrecido; no se promete resistencia criptográfica a ese control |
| Copiar sólo un blob DPAPI a otro host independiente | El blob y los IDs no son una recuperación portable. El recorrido autorizado utiliza el sobre y su contraseña, con adaptación explícita de la instalación. No se extrapola esta separación a una copia completa del host |
| Imagen, clon, snapshot o volcado de memoria de la VM | Puede transportar memoria, secretos de plataforma, archivos y cuentas; debe tratarse como material privado del servidor. Un snapshot completo no equivale al blob aislado y no es una custodia externa cifrada por sí mismo |
| Robo del sobre portable | RCKEYv1 cifra/autentica su contenido con la contraseña y el KDF acotado. Permite intentos offline: no garantiza seguridad ante una contraseña débil o la obtención conjunta de sobre y contraseña. Los medios separados reducen su exposición conjunta, no protegen un host activo ya comprometido |
| Alteración, pérdida de archivos o corte durante mantenimiento | Las validaciones y el arranque cerrado deben impedir aceptar material incoherente. No regenerar claves ni desactivar MFA como reparación. Journal/fence/rotación/recuperación se especifican en F-03.02 y siguen pendientes de sus ensayos; un rename o doble lectura del anillo no demuestra atomicidad disco/DB |

El cifrado autenticado vincula el material y detecta alteraciones cuando las claves permanecen fuera del atacante. No impide denegación de servicio por quien puede borrar archivos, ni sustituye los permisos de cliente, grupos o capacidades comprobados en el servidor. Tener un rol de administrador en RackClick tampoco concede por sí mismo administración de Windows.

## 3. Memoria, diagnósticos y copias

El servicio necesita material descifrado durante la operación; no se afirma que nunca esté en memoria. Poner a cero buffers concretos no demuestra borrado de todas las copias del runtime, de contraseñas `string`, de memoria paginada o de volcados. Los ensayos existentes no son una inspección universal de memoria.

Claves, TOTP, contraseñas, connection strings, códigos, sobres privados y archivos DPAPI no se incorporan a capturas públicas, informes sanitizados, GitHub o paquetes documentales. Dumps de memoria, binlogs y registros crudos se conservan privados. Un hash de integridad identifica bytes; no convierte el archivo de origen en información publicable ni prueba que no contenga secretos.

El dump SQL no reemplaza al sobre. Copiar la VM completa puede ayudar a una recuperación operativa, pero no sustituye la custodia externa ni acredita Restore en otro Windows. La retención, cifrado de copias y recuperación de sus versiones se verifican en R-03/R-04/F-05/F-06; esta ficha no autoriza borrar copias o VM.

## 4. Consecuencia ante una exposición confirmada

La respuesta debe partir de un host y autoridad de mantenimiento confiables, delimitar usuarios/versiones/material expuestos y revocar sesiones/códigos/factores afectados según el procedimiento correspondiente. **Recifrar el mismo secreto TOTP con otra clave no revoca una semilla TOTP ya sustraída**: en ese caso se requiere un secreto/factor nuevo y reenrolamiento de los afectados, no sólo reenvoltura.

Se conserva el requisito de recuperación restringida de F-03.02 hasta confirmar el nuevo factor, incluso para un administrador global exento de gracia45. No se concede sesión API por contraseña, un código o una marca de recuperación pendientes.

Esta descripción no identifica un incidente en D ni autoriza rotaciones o resets por conjetura. El antecedente F-01 archivado con incertidumbre mantiene su disposición y reapertura si aparece evidencia concreta. El modelo de amenaza no lo convierte en exposición demostrada ni en falso positivo.

## 5. Evidencia reutilizada y alcance del cierre

D2v2 ya enunciaba los límites de administrador/proceso; la confirmación25.10 mantiene LocalMachine y el SID real. Se contrastaron las constantes DPAPI del escritor, `CryptUnprotectData` del proveedor, `MfaKeyRing.EntropyFor` y las condiciones F-03.02. Se reutilizan sus revisiones anteriores y sus límites por lectura/hash, sin ensayar ataques, abrir claves o volver a autenticar cuentas.

La investigación oficial se limita a DPAPI y a la evaluación de acceso por Windows, consultadas03.11.2026. No se incorporan bibliotecas, nuevas versiones o mecanismos de custodia alternativos. Las explicaciones de riesgo combinan esas primitivas con el código de RackClick; no son una certificación de Microsoft sobre este producto.

F-03.03 cierra **registro del límite**, tras revisión independiente. Con F-03.01 y F-03.02 documentados, puede completarse F-03 como decisión registrada; no acredita proveedor/ACL, sobre portable, emergencia, rotación, backup/Restore o QA en los resultados posteriores. Peso del paso y de F-03:0. D permanece sin operaciones; no se cambia la política45 ni se solicita otra confirmación de custodia.

Evidencia y dictamen: [F-03.03](../evidence/s1-20261103/f03-03-amenazas/RESULTADOS.md).
