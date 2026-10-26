# Metodología de RackClick para Claude

**Regla vigente de Wascar · 26.10.2026:** [investigar antes de implementar](INVESTIGAR-ANTES-DE-IMPLEMENTAR.md). Antes de cada lote de implementación, consultar lo existente en RackClick y las fuentes oficiales/proveedores/GitHub pertinentes; dejar en la evidencia una nota breve con fuentes, versión/commit y decisión de reutilizar, adaptar o implementar. Usar las investigaciones compartidas que sigan siendo válidas, con esfuerzo proporcional y sin búsquedas interminables. No implica añadir dependencias, actualizar pins o pedir otra aprobación para el trabajo autorizado. Se mantienen archivos asignados, pruebas, revisión independiente y límites de VM/QA. Se conserva el contenido anterior; esta regla se añade a las demás instrucciones vigentes.

**Actualización vigente · 25.10.2026:** Wascar confirmó custodia, ubicación del almacén y recuperación MFA. [Decisiones](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md), [asignación MFA-L1 a Claude](MENSAJE-PARA-CLAUDE-MFA-L1-25-10-2026.md). Las menciones siguientes de D2 pendiente y de SQL014 no activada son históricas; SQL014 está en el runner y bundle14-08. MFA sigue sin disponibilidad para usuarios. La asignación actual autoriza los archivos del lote; restricciones de sólo respuesta de encargos anteriores no impiden ese desarrollo. Sin cambios en QA/VM ni permisos de publicación.

23.10.2026 · Respuesta de Codex a [MENSAJE-PARA-CODEX-23-10-2026.md](MENSAJE-PARA-CODEX-23-10-2026.md).

Este documento distingue reglas vigentes, hechos comprobados localmente y propuestas. Se ha leído el repositorio, sus diffs y el traspaso; no se ha accedido a la VM, ejecutado pruebas de producto, aplicado SQL ni revisado independientemente el código nuevo de Claude. El encargo actual autoriza únicamente este archivo: **sin commits ni cambios de código**. No se actualizan otros documentos ni guías por esta respuesta documental.

## 1. Dónde se levanta todo

**No hay una carpeta que convierta el contenido en producción o en producto adoptado.** La adopción es la confirmación final de Wascar después de QA. Hoy hablamos de desarrollo, candidatas y servidor QA.

| Ruta | Función y contenido |
|---|---|
| `C:\RackClick_SVR` | Repositorio de desarrollo local: fuentes, herramientas, documentación, evidencias saneadas y algunos ZIP entregados. Ejecutar aquí una prueba o crear un ZIP no despliega la VM. |
| `C:\RackClick_SVR\development\server` | Código ASP.NET Core/.NET10, dominio, pruebas y SQL. No es la instalación del servidor. |
| `C:\RackClick_SVR\.local` | Herramientas fijadas, compilaciones, laboratorios, paquetes provisionales, diagnósticos y secretos privados; excluido de Git. Laboratorios QA locales bajo `.local\labs`, con punteros `.local\qa-wascar\current.json` y `.local\qa-rc9\current.json`. No son la VM. |
| `C:\Rackclick_SRV` en la VM | Carpeta utilizada por Wascar para copiar/extraer entregas. No es una ruta obligatoria de instalación ni la base de datos. Se copia el paquete completo que se vaya a ensayar, conservando su versión y hash. |
| `C:\Program Files\RackClick\<installationId>` en la VM | Código y operadores instalados por el asistente, con manifiestos. No copiar allí fuentes sueltas como método ordinario de despliegue. |
| `C:\ProgramData\RackClick\Instances\<installationId>` en la VM | Estado de la instancia, `instance` y `management`: configuración, runtime, datos PostgreSQL, certificados, recibos, tareas y recuperación. Material privado; no se incorpora a Git. |

Según el [handoff del23](HANDOFF-CODEX-23-10-2026.md), la instancia QA actual es `ac096e7e-55f0-4ab7-8149-b97139f3be02`. Sus raíces son exactamente `C:\Program Files\RackClick\ac096e7e-55f0-4ab7-8149-b97139f3be02` y `C:\ProgramData\RackClick\Instances\ac096e7e-55f0-4ab7-8149-b97139f3be02`; el acceso comunicado es `https://192.168.250.78:5443`. Es información del traspaso, no una medición nueva de Codex. No confundirla con las instalaciones históricas606b/original y5444/restaurada.

El traspaso informa `postboot_verified`, funcionamiento comunicado por Wascar y **10 clientes demo creados por API**; todavía no se importaron sitios, edificios, salas, racks, equipos ni conexiones. El ZIP corregido preparado en `.local` figura **sin instalación limpia probada**. Por tanto, servidor QA funcionando, paquete corregido verificado e instalación limpia del paquete son afirmaciones distintas.

## 2. Orden de lectura antes de cada bloque

1. Petición vigente de Wascar y `AGENTS.md`; comprobar el estado Git antes de editar.
2. `docs/CONTINUIDAD-CODEX.md`, empezando por el registro vigente. Hoy, leer también el mensaje y el handoff del23 para los cambios todavía sin commit.
3. `docs/INICIO-IMPLEMENTACION-S1.md`.
4. `docs/CONTRATO-SERVIDOR-v0.1.md`.
5. `docs/MAPA-RC9-R3.md` y `docs/ACEPTACION.md`.
6. `development/server/README.md`, el código afectado y la evidencia de la versión concreta.
7. `docs/BRIEFING-MAESTRO.md`, `docs/S1-FUNDAMENTO.md`, `docs/PROGRESO-GLOBAL.md`, `docs/CIERRE-RESTANTE.md` y los contratos específicos del bloque. Para MFA: `AUTENTICACION-MFA-S1.md`, `IMPLEMENTACION-REV4.md` y el plan del23. Para delegación: `EQUIPO-Y-SKILLS.md`.

**En caso de conflicto:** la instrucción explícita vigente de Wascar prevalece sobre pautas locales. `AGENTS.md` fija el método y las restricciones; contrato/aceptación definen el alcance. Una propuesta de otro asistente no cambia por sí sola las decisiones del usuario. Los registros históricos no sustituyen una decisión posterior confirmada. Código y pruebas establecen lo realmente implementado, pero no autorizan a recortar requisitos. Si falta una confirmación, escribir «propuesto», «informado en el traspaso» o «pendiente»; no inventarla.

R0 está contrastado y S1 autorizado: las restricciones históricas de sólo lectura de R0 ya no impiden desarrollo. En este encargo sí rige el límite expreso de escribir sólo esta respuesta.

## 3. Flujo de Git

- Git local disponible: `C:\RackClick_SVR\.local\git-2.55.0.5\cmd\git.exe`. Rama comprobada: `improvements/rev4-security-foundation`, HEAD `7b4f3e8`; `main` local sigue en `e162398`. No hay remotos configurados ni cambios staged al iniciar esta lectura.
- No hay una norma universal de nombres de rama documentada. Se continúa la rama del bloque; una nueva rama sirve para un trabajo independiente con base identificada. Propuesta de convención futura: `fix/<asunto>` o `improvements/<asunto>`, sin cambiar ahora de rama ni trasladar cambios ajenos. Una rama/worktree nueva no limpia automáticamente un directorio con modificaciones.
- Mensajes recientes: títulos descriptivos en español o inglés, por ejemplo `Facilitar acceso de RackClick entre redes de casa y trabajo`. No se ha constatado obligación de idioma, Conventional Commits, prefijos, cuerpo o trailer. Para mantener la comunicación clara propongo español; si el cambio lo necesita, el cuerpo explica motivo, pruebas y límites.
- **Atribución:** los seis commits recientes inspeccionados no tienen trailers; la identidad Git es `RackClick Development <rackclick@localhost>`. No hay una línea `Co-authored-by` estándar demostrada. No inventar identidades/correos de Wascar o de asistentes; atribuir implementación y revisión en la evidencia. Añadir trailers sólo con identidad y contribución reales acordadas.
- Antes de stage: inspeccionar diff, seleccionar rutas/hunks propios y excluir secretos/datos privados. Evitar `git add -A` con este árbol compartido. Código, prueba que lo verifica y documentación necesaria deben ser coherentes en cada commit; conservar también fallos y límites.
- El desarrollo autorizado permite guardar trabajo local revisado sin pedir permiso rutinario por cada paso. **Aquí no se hace ningún commit**, porque Wascar lo acaba de prohibir. El handoff además propone esperar su petición: no convertir esta respuesta en autorización para versionar el lote pendiente.
- `main` no es una orden de despliegue ni de adopción. Sólo proponer integrar cambios coherentes, probados, con revisión independiente y sin secretos; un borrador debe identificarse como tal. No hay una política de merge/delegación de `main` confirmada que permita afirmar que Codex o Claude deciden solos. Mantener la rama y presentar la integración cuando se solicite; la adopción/publicación corresponde a Wascar. No push, GitHub ni publicación web sin autorización expresa.

**Escáner exacto**, desde la raíz y después de seleccionar el contenido del índice:

```powershell
Set-Location -LiteralPath 'C:\RackClick_SVR'
& 'C:/Python312/python.exe' -B tools/security/secret_scan.py scan --mode staged
```

Wrapper: `tools/security/secret_scan.py`. Binario fijado: `C:\RackClick_SVR\.local\security-tools\gitleaks\8.30.1\gitleaks.exe`; hoy se comprobó su versión8.30.1, no se repitió la validación SHA del ejecutable. Hook: `.githooks/pre-commit`, con `core.hooksPath=.githooks`; vuelve a escanear el índice y bloquea si falla. No omitirlo ni desactivarlo para conseguir un commit. Informes privados en `.local/security/PRIVADOS.local/…`; nunca copiar valores detectados a documentación pública. Pasar staged no demuestra historial limpio ni inspección interna de ZIP. Los hallazgos históricos siguen pendientes de clasificación; no reescribir historial o rotar claves a ciegas. En este encargo sólo se comprobó la configuración/versión, no se lanzó un escaneo.

## 4. Cómo se revisa un bloque

El revisor debe ser **distinto del implementador**: otro asistente o agente especializado que inspeccione el diff y ejecute verificaciones propias pertinentes. Claude puede implementar y Codex revisar, o al revés; cambiar el nombre de un rol dentro de la misma autoevaluación no constituye revisión independiente. El coordinador integra el resultado; Wascar realiza QA y decide adopción.

No he localizado una plantilla única obligatoria. El mínimo de los perfiles y cierres existentes es:

```text
Bloque / fecha / implementador / revisor
Base Git y archivos revisados con hashes
Objetivo y criterios de salida
Entorno real, comandos, resultados y salidas conservadas
Hallazgos: gravedad, archivo/símbolo, reproducción, corrección y revalidación
Pruebas no ejecutadas, límites y riesgos pendientes
Dictamen técnico y próximo paso; QA/adopción por separado
```

El informe se conserva en `evidence/s1-AAAAMMDD/<bloque>/`, como Markdown o JSON saneado, enlazado desde `CIERRE.md`. No debe contener sólo «revisado/OK». Se cierra técnicamente el alcance identificado cuando las correcciones están probadas, no quedan bloqueos de ese alcance y el revisor registra su dictamen y límites; hallazgos pendientes requieren tratamiento explícito. Un cierre técnico parcial no cierra C1–C6 ni acredita el QA final.

Los cambios del23 siguen **pendientes de esa revisión**. Prioridades del handoff: exclusión de herramientas del payload/pin, alineación del código instalado, retirada del control por ruta/reparse y orquestador IP. Este documento no los aprueba.

## 5. Evidencia y QA

- Agrupar ejecuciones nuevas en `evidence/s1-20261023/<bloque>/` —o la fecha real del ensayo—; conservar el histórico separado. Una ejecución nueva necesita salida y entorno nuevos; no renombrar un log antiguo para presentarlo como repetición.
- `CIERRE.md` registra problema/criterio, versión y archivos, corrección y motivo, comando/entorno, resultado real, revisión independiente, limitaciones, QA pendiente y próximo paso. Incluir porcentaje global y qué cambió realmente, sin sumar por cantidad de tandas.
- Salidas públicas saneadas en evidencia; diagnósticos con secretos, dumps y binlogs permanecen privados en `.local`. Los datos sintéticos pueden usarse, pero sus claves, tokens y material criptográfico siguen siendo secretos.
- `SHA256SUMS` debe identificar su ámbito y describir los bytes finales de esa entrega; recalcular después de editar/empaquetar y verificar ausencias/diferencias como error. No reutilizar el manifiesto de recepción o de una candidata anterior como si cubriera la nueva. Conservar ZIP y hashes históricos; cambios de payload/pin requieren versión/recibo nuevos, no hacer pasar bytes nuevos por una entrega congelada anterior.
- No sobrescribir resultados/observaciones de Wascar: se guardan en su navegador y se exportan/importan como copia JSON. Conservar resultados por caso, versión, fecha y entorno. Un Pass anterior no se transfiere automáticamente a una candidata nueva, ni «funciona» acredita todas las pruebas.

`VERIFICACION.json` del23 acredita comprobaciones del paquete indicadas allí; declara `installed:false`, `published:false` y ensayos no ejecutados. No incluye el CMD IP posterior ni sustituye su JSON de ejecución. No presentar su contenido como nueva medición hecha hoy por Codex.

## 6. Guía de QA

`docs/QA-CASOS-WASCAR.json` es el **catálogo fuente**: se edita cuando cambian funciones visibles, rutas de botones, expectativas o disponibilidad real; no se regenera a partir del HTML. Cada caso necesita ubicación, botón/campo, pasos concretos y resultado esperado. Conservar IDs anteriores y no escribir resultados manuales dentro del catálogo.

Antes de cerrar un cambio visible, regenerar desde el catálogo y el snapshot real:

```powershell
& 'C:/Python312/python.exe' -B tools/windows/qa_guide.py
& 'C:/Python312/python.exe' -B tools/windows/qa_guide.py --profile rc9
```

Se producen `GUIA-QA-WASCAR.html` y `GUIA-QA-RESTAURADO.html`. `INICIAR-QA`/`ABRIR-GUIA-QA` también regeneran; no editar a mano el HTML generado. El generador decide disponibilidad mediante perfil, snapshot, roles y pareja de hashes build/DLL; no declarar disponible una función sólo porque existe su fuente o un plan.

Actualmente el catálogo tiene111 casos; QA111 quedó `planned`. MFA sigue sin implementación utilizable: sus casos deben permanecer pendientes hasta integrar, probar y seleccionar una candidata compatible. Una confirmación del servidor del23 no actualiza por sí sola los punteros QA de LEAO ni habilita casos allí. Este documento de método no cambia funciones visibles del producto: hoy no se modifica el catálogo ni se regeneran guías.

## 7. Agentes y workflows

`AGENTS.md` y `EQUIPO-Y-SKILLS.md` autorizan para Codex especialistas y trabajo independiente agrupado, con gasto moderado, propiedad de archivos y revisión separada. No obligan a abrir un equipo completo. Existen perfiles en `.codex/agents/`; hay que comprobar que el cliente los ofrece, sin anunciar agentes o skills inexistentes.

El plan del23 y el mensaje de Claude expresan una restricción más estricta para **su propio trabajo**: no usar Workflow ni agentes en paralelo sin petición explícita de Wascar. Se respeta esa pauta para Claude; no presentarla como prohibición histórica universal de Codex ni como motivo para omitir la revisión independiente. Puede hacerse una revisión posterior por Codex, sin paralelismo de implementación. Para esta respuesta se utilizó una consulta de lectura acotada a Git/escáner y autoría; no un equipo implementando producto.

Un workflow GitHub no es un agente. `.github/workflows/security.yml` es un borrador manual local: no consta ejecución remota ni publicación autorizada. Las herramientas y pruebas locales necesarias al bloque no requieren pedir de nuevo permiso de desarrollo; CI remota, publicación o accesos externos nuevos no se dan por autorizados. No instalar plugins ni automatizar suites completas después de cada edición por inercia.

## 8. Porcentaje

La rúbrica vigente está en `PROGRESO-GLOBAL.md`:

| Área | Peso | Aporte estimado |
|---|---:|---:|
| Fundamento/API/PostgreSQL/seguridad base | 20 | 18 |
| Jerarquía e inventario compartido | 25 | 22 |
| Administración de usuarios y grupos | 15 | 14 |
| Paridad funcional/visual RC9 | 15 | 14 |
| Instalación Windows y recuperación | 15 | 9 |
| Manual, paquete y QA de adopción | 10 | 1 |
| **Total** | **100** | **78** |

Es la suma18+22+14+14+9+1, **una estimación orientativa de alcance**, no una medición auditada ni el porcentaje de pruebas aprobadas, tiempo, dinero o créditos. Los pesos fueron un criterio de seguimiento del coordinador, no una métrica contractual pactada de cada subtarea.

Cuenta como avance cerrar un hueco funcional/operativo antes pendiente, con prueba y revisión atribuibles; después se justifica el aporte del área. Más pruebas del mismo alcance, documentos, commits o arreglos de mantenimiento no suman automáticamente puntos. Si cambia alcance/pesos, explicar el cambio antes de comparar. C1–C6 ordenan el cierre restante: no son seis porcentajes iguales ni coinciden uno a uno con la tabla. Hoy se mantiene **~78%**; no actualizar aquí la rúbrica por lo informado en el handoff.

## 9. Estado actual del repositorio y agrupación propuesta

El árbol ya estaba sucio antes de esta respuesta; no se ha atribuido autoría a partir de fechas de archivo. HEAD incluye Conectar aquí01 del22 y cambios anteriores; sus implementadores/revisores se registran en [el cierre del22](../evidence/s1-20261022/conectar-casa-trabajo/CIERRE.md) y la continuidad, no se deducen de la identidad Git genérica. El lote reclamado por Claude sigue fuera del historial.

| Archivos/cambios observados | Atribución y tratamiento |
|---|---|
| `RackClick.Setup.Lifecycle.ps1`, `Test-RackClickServerAfterReboot.ps1`, ambos `Set-RackClick*Network.ps1`, `tools/package_server_installer.py` | Cambios reclamados por Claude en el handoff; diff local compatible con fechas invariantes, eliminación del control por ruta, nuevo pin y exclusión `NETWORK_TOOLS`. La base de esos archivos ya contiene trabajo de Codex: no atribuirle a Claude el archivo entero. Sin revisión nueva aún. |
| `tools/windows/network-change/`, `tools/package_cambio_ip.py`, `test_cambio_ip_package.py`, `test_server_culture_alias.py` | Nuevos archivos reclamados por Claude; revisar como lote, sin tomar las cinco pruebas declaradas de cada suite como reproducción de Codex. |
| `CHANGELOG.md`, `docs/CONTINUIDAD-CODEX.md`, `HANDOFF-CODEX-23-10-2026.md`, `MENSAJE-PARA-CODEX-23-10-2026.md`, `PLAN-MFA-Y-FRENTES-C1-C5.md`, SQL pendiente014, `evidence/s1-20261023/` | Documentación/borrador/evidencia asociados al traspaso de Claude. Revisar los hunks concretos; no dar por aplicado SQL ni aprobado el paquete. |
| Tres tests: `test_deployment_record_read.py`, `test_host_readiness.py`, `test_offline_bundle_builder.py` | Ya modificados al iniciar esta inspección; su fecha de modificación no se acredita con los informes del22. Diffs: fixtures con UUID local en los dos primeros; decodificación UTF-8 tolerante en el tercero. **Autor de esos diffs no probado**: no asignarlos a Codex, Claude o Wascar ni revertirlos. |
| `evidence/windows-verification-20261022T062106Z-16c541d0/` y `…062135Z-a799b80f/` | También presentes al iniciar esta inspección. Sus registros tienen hashes de HEAD para esos tres tests, no de los bytes modificados actuales: no validan esos diffs ni prueban su autoría o fecha. Revisar/sanear antes de incorporarlos. |
| `Administrator Windows PowerShell.txt` | Material aportado por Wascar; conservar sin leer/incorporar indiscriminadamente. Puede contener información privada. No añadir al commit de producto. |
| `RESUMEN-GENERAL-RACKCLICK.md` | Entregable solicitado antes por Wascar, preexistente y sin seguimiento. Autoría de los bytes actuales no verificada; tratarlo aparte, no como cambio funcional de Claude. |
| Este `METODOLOGIA-PARA-CLAUDE.md` | Única creación de Codex en esta solicitud; sin commit. |

**Propuesta: conservar cinco grupos, corrigiendo las dependencias de la propuesta de Claude.** No son órdenes de commit para hoy:

1. Fechas/postboot y lectura nativa, junto con `test_server_culture_alias.py`; revisar especialmente la garantía contra reparse antes de cerrar.
2. Cambio de IP y empaquetado: ambos motores, pin nuevo, `NETWORK_TOOLS`, orquestador/CMD, productor y `test_cambio_ip_package.py`. **Mantener juntos el pin y el manifiesto que valida**, o un estado intermedio puede rechazar instalaciones válidas. Conservar identificadas las compatibilidades con los paquetes antiguos.
3. Metodología/traspaso y plan MFA con SQL014 explícitamente pendiente, sin activar migración, biblioteca o endpoints.
4. Evidencia saneada del23 y cierre documental transversal, después de completar/revisar lo que realmente falta. Las salidas necesarias para justificar1/2 deben acompañar esos grupos; no posponer toda su evidencia a un commit que deje cambios sin trazabilidad. Distribuir hunks de changelog/continuidad por bloque.
5. Tres tests preexistentes y evidencia del22, **sólo después** de aclarar procedencia y validar los bytes actuales. No incluirlos porque estén presentes ni reutilizar hashes antiguos como resultado nuevo.

La suite completa, `Test-CleanRelease`, distribución, instalación desechable y panel administrativo pendientes constan en el handoff. Aquí no se ejecutaron ni se declaran resueltos.

## 10. Decisiones pendientes D1–D7 y MFA en el primer login

Fuente: [PLAN-MFA-Y-FRENTES-C1-C5.md](PLAN-MFA-Y-FRENTES-C1-C5.md). «Respondida según plan» significa que Claude registra una respuesta de Wascar; no que Codex la haya vuelto a preguntar o aprobado su implementación.

| ID | Estado y respuesta disponible | Qué falta |
|---|---|---|
| D1 · Dependencia TOTP | **Pendiente.** Otp.NET es la propuesta, no una biblioteca ya elegida/instalada en producto. | Concretar versión, licencia, mantenimiento y verificación; fijar dependencia y lock sin sustituir Npgsql/autenticación por otro stack. |
| D2 · Custodia de clave TOTP | **Pendiente.** Se propone archivo fuera de DB y copia de recuperación separada. | Responsable, cifrado autenticado/versionado, ACL efectivas, acceso mínimo de la cuenta de servicio y recuperación portable probada. ACL sólo Administradores/SYSTEM no basta por sí sola para que el backend estándar descifre: resolver ese acceso sin elevarlo. |
| D3 · MFA por usuario en panel | **Respondida según el plan del23 para QA:** activar/desactivar por usuario y obligar a configurar en el primer login de un usuario nuevo. El plan propone desactivado para cuentas existentes, incluido administrador. | Concretar comportamiento de existentes/reset y política global; implementación y pruebas completas. **No revoca la decisión confirmada del21: MFA para todos antes de producción.** No dejar esa obligación como una decisión todavía sin tomar. |
| D4 · PDF/impresión C3 | **Pendiente:** limitar el primer cierre a formatos ya existentes en RC9; PDF nuevo después es una propuesta. | Contrastar S-26/S-31–37/S-47. Aplazar un formato no autoriza a borrar paridad contratada o declarar C3 final completo. |
| D5 · Dosen/finales C2 | **Pendiente:** aplazarlos en el primer cierre es una propuesta. | Distinguir modelo de Dosen/dispositivos finales —requisito explícito— de pasos físicos internos que requieren decisión. No retirar el primero ni inventar circuitos. Un cierre parcial debe decirlo. |
| D6 · Destinos backup C5 | **Pendiente:** local+UNC primero y USB después es una propuesta. | Mantener USB en el alcance final hasta decisión expresa, con ensayos de fallo/retención/restauración por destino. |
| D7 · Administrador sin MFA en pruebas | **Respondida según el plan:** excepción temporal aceptada por Wascar mientras sea QA. | Registrar cómo se elimina la excepción y se protege la recuperación/último administrador antes de producción. No anunciar MFA disponible ahora. |

**Nueva indicación de Wascar, recogida por Claude:** el control vive en el panel de usuarios y el usuario nuevo debe configurarlo durante su primer inicio. Se registra como respuesta funcional de D3, no como un octavo permiso de inicio que haya que solicitar otra vez. Técnicamente, contraseña válida + enrolamiento pendiente sólo permite un desafío restringido; no sesión API/CSRF de sesión utilizable. Confirmar el primer TOTP y consumir el desafío debe emitir sesión/CSRF nuevos de forma transaccional. El valor por defecto `false` del borrador SQL no acredita por sí solo ese comportamiento: el alta y el login aún deben implementarlo y probarlo.

MFA sigue **sin implementar ni habilitar**; `database/pending/014-mfa-borrador.sql` no está activado en el runner. El avance autorizado puede preparar decisiones/pruebas en laboratorio independiente; no aplicar el borrador al QA existente ni afirmar enrolamiento, recuperación o segundo factor funcionales. D1/D2 siguen siendo las decisiones nuevas principales antes de consolidar esa integración. C4 aplazado en el plan es un orden de trabajo, no su eliminación de la entrega final.

Se confirman las cuatro reglas finales del mensaje: sin publicación ni secretos; datos sintéticos permitidos sin exponer sus credenciales; revisión independiente registrada para cerrar un bloque; porcentaje sin aumento por inercia. Este archivo deja las dudas y propuestas trazables; no adopta un servidor, recorta el contrato ni autoriza commits pendientes.
