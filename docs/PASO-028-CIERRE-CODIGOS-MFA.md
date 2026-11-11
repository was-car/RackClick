# Paso 28 · cierre técnico de códigos y reenrolamiento MFA

11.11.2026 · F-08.05. Cerrado técnicamente con revisión independiente favorable. **Se conserva D y E.**

## Resultado que se contrasta

La recuperación disponible conserva la cuenta y su autoridad: contraseña válida y un código previamente guardado permiten configurar otro autenticador. Sólo confirmar ese factor nuevo concede una sesión API. El código presentado no permite entrar directamente al dashboard, y tampoco lo permite la exención del administrador global mientras exista un reenrolamiento pendiente.

La generación es **expresa**, desde **Mi seguridad → Códigos de recuperación**, con contraseña y sesión MFA. Se muestran diez valores sólo en la respuesta inicial confirmada; recibo, repetición y estado no los revelan. La aplicación guarda hashes con sal ligados a la cuenta. El plan numerado ya concilia este flujo con el texto histórico D2: no se promete generación automática al enrolar ni se garantiza que el usuario haya custodiado los valores.

Este paso reúne las pruebas y revisiones de [24](PASO-024-GENERACION-CODIGOS-MFA.md), [25](PASO-025-RECUPERACION-RESTRINGIDA-MFA.md), [26](PASO-026-CONSUMO-CODIGOS-MFA.md) y [27](PASO-027-ULTIMO-ADMINISTRADOR-MFA.md). No se reimplementa el canje ni se vuelve a desplegar la instalación.

## Uso previsto

El [paso 27](PASO-027-ULTIMO-ADMINISTRADOR-MFA.md) mantiene el recorrido detallado, sin pedir ejecutarlo ahora sobre D:

1. Con el autenticador disponible, generar y custodiar privadamente los códigos fuera del servidor.
2. Si se pierde el autenticador, iniciar sesión con contraseña y elegir **Perdí mi autenticador**.
3. Presentar un código guardado. Se retira el conjunto antiguo y sus sesiones/desafíos; sólo se permite el enrolamiento nuevo.
4. Confirmar el autenticador nuevo antes de abrir la aplicación. La identidad, grupos y capacidades se conservan.
5. Generar expresamente otro conjunto y guardarlo. Los anteriores ya no sirven.

No enviar códigos, QR, semillas, contraseñas ni cookies en capturas, informes o chat. Si faltan contraseña, cuenta utilizable, almacén de claves o códigos válidos, ésta no es la vía de pérdida total; corresponde a F-09 y a los procedimientos de custodia/recuperación pertinentes.

## Evidencia y aceptación

[Plan](PLAN-F0805-CIERRE-CODIGOS.md) · [resultados](../evidence/s1-20261111/f08-05-cierre/RESULTADOS.md) · [matriz conjunta](../evidence/s1-20261111/f08-05-cierre/MATRIZ-CIERRE.md).

El cierre técnico se distingue de integrar la corrección en la candidata Windows objetivo y de la aceptación/custodia manual de Wascar. Esos hitos permanecen pendientes. La evidencia de HTTP/navegador usa claves sintéticas y PostgreSQL de laboratorio, sin convertirla en prueba del SID efectivo, DPAPI o HTTPS de D/E. Los casos QA existentes y sus resultados personales se conservan.


## Cierre registrado

[Dictamen independiente](../evidence/s1-20261111/f08-05-cierre/review/DICTAMEN.md). Foco12/12 y revisor6/6 PASS. Hay positivos actuales del dashboard y la recuperación en Edge en corridas distintas, con fallos intermitentes del guion de recuperación conservados; [observación](../evidence/s1-20261111/f08-05-cierre/OBSERVACION-NAVEGADOR.md). No se presenta una batería íntegramente verde ni una corrección por reintento. Producto y cuatro tests anteriores intactos.

Sólo F-08.05 añade **1/2 punto**: índice de cierre restante **24,13→24,63/100**, sin porcentaje global nuevo. Cuatro hitos técnicos F-08 quedan done; integración y aceptación manual permanecen pending. Siguiente paso29/F-09.01, emergencia local por pérdida total.
