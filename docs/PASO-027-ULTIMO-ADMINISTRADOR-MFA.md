# Paso 27 · recuperar al último administrador con códigos válidos

11.11.2026 · F-08.04. Cerrado técnicamente con revisión independiente favorable y corrección D2 verificada. **D y E permanecen intactas.** No se usan cuentas o factores personales de Wascar.

## Qué vía se conserva

El único administrador global activo puede recuperar **su propia cuenta** con contraseña válida y un código que haya guardado. No necesita que otro administrador con MFA le restablezca el factor. El canje concede únicamente enrolamiento: se confirman un autenticador nuevo y una sesión MFA nueva antes de volver a administrar.

La recuperación conserva UUID, nombre, contraseña, grupos y concesiones; no crea otro administrador ni eleva un administrador de cliente. La condición global se deriva de las dos capacidades globales `security.manage` y `systemhaus.manage`. La guarda existente contra desactivar al único administrador sigue vigente.

Se reutiliza el núcleo de F-08.01–.03. La revisión encontró y reprodujo un fallo preexistente contrario a D2: desactivar podía cancelar un reenrolamiento pendiente. Se corrige sólo `MfaAccountManagement.cs`: rechazo 409 `mfa_enrollment_required` y `CanDisable=false` mientras pending. El botón existente refleja esa bandera. No se alteran gracia45, exención de un factor activo no pendiente, endpoints, esquema SQL o dependencias. La corrección queda en fuentes, sin desplegar en D/E.

## Procedimiento para la candidata instalada, pendiente de aceptación

No se pide ejecutarlo ahora sobre D. Se reutiliza QA-163 y el [procedimiento general](PUNTO3-FUNCIONES-PENDIENTES.md); no deben incluirse códigos o secretos en capturas, informes o chat.

1. **Antes de perder el factor**, entrar y completar MFA; abrir **Mi seguridad → Códigos de recuperación**. Generar expresamente con contraseña actual y guardar privadamente los diez valores fuera del servidor. Un recibo confirma la generación sin volver a mostrarlos.
2. Con la URL HTTPS de la instalación correcta, iniciar sesión con el usuario y su contraseña. En el desafío del autenticador, elegir **Perdí mi autenticador**.
3. Introducir un código guardado y pulsar **Recuperar y configurar un autenticador nuevo**. Debe aparecer el enrolamiento, sin dashboard ni acceso administrativo. Se retira todo el juego anterior de códigos y las sesiones/desafíos previos de esa cuenta.
4. Configurar el autenticador nuevo y confirmar su TOTP. Sólo entonces se abre la aplicación. Comprobar identidad y permisos originales en el panel administrativo.
5. En **Mi seguridad**, generar expresamente otro juego de códigos y guardarlo: los diez anteriores ya no sirven. Conservar el material de prueba hasta terminar la comprobación; no modificar manualmente tablas para recuperar una instalación.

La exención global de gracia45 permite administrar el propio MFA según la decisión confirmada; no omite un reenrolamiento ya pendiente ni se cambia para exigir otro administrador. Tampoco garantiza custodia: si se descartan los códigos, se pierde la contraseña, se deshabilita/elimina la cuenta o el host no arranca por pérdida del almacén, esta vía no resuelve ese estado. La emergencia local se trata por separado en F-09.

## Evidencia y límites

[Resultados](../evidence/s1-20261111/f08-04-ultimo-administrador/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f08-04-ultimo-administrador/MATRIZ-CRITERIO.md) · [plan](PLAN-F0804-ULTIMO-ADMINISTRADOR.md).

La prueba nueva ejecuta almacén/PG con roles separados y claves sintéticas; no es un ensayo nuevo de GUI, servicio Windows, SID, DPAPI, TLS o instalación. Se reutilizan los dos casos HTTP de F-08.02 y la evidencia Edge anterior con atribución. La operación administrativa comprobada directamente en el almacén no equivale a ensayar todos los controles HTTP de reautenticación de F-11.

F-08.05, custodia efectiva y los hitos operativos de F-08/aceptación permanecen pendientes. QA-163 incorpora el paso de Desactivar deshabilitado durante pending y el escenario del único global. Sus pasos anteriores, disponibilidad planificada, los otros 174 casos y los resultados personales se conservan; no se habilita por estas pruebas.


Precisión de definición: la condición global y su exención MFA requieren ambas capacidades globales. La guarda `last_admin_required` existente protege al último `security.manage` global, no una conjunción general de ambas capacidades. El fixture positivo satisface las dos condiciones; este lote no redefine las guardas generales de A-02.


Sólo F-08.04 acredita **1/2 punto**: índice del cierre restante **23,63 → 24,13/100**, sin porcentaje global nuevo. [Dictamen](../evidence/s1-20261111/f08-04-ultimo-administrador/review/DICTAMEN.md). Siguiente paso 28 / F-08.05.
