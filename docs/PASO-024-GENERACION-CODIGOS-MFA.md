# Paso 24 · generación y entrega única de códigos MFA

11.11.2026 · F-08.01. Cerrado técnicamente con dictamen independiente favorable. **D y E permanecen intactas.** No hay instalación, cambios de cuentas, MFA o datos reales.

## Resultado comprobado

Se reutiliza el generador existente. Cada solicitud propia autorizada produce diez códigos de 128 bits aleatorios, con una sal aleatoria independiente por hash. PostgreSQL conserva formato/versionado, sal y hash ligado a Systemhaus/usuario; no guarda los valores en claro en tablas, auditoría o recibos.

Sólo la primera respuesta de una operación entrega los diez valores. Repetirla o consultar su recibo confirma el resultado sin mostrarlos otra vez. Una nueva prueba fuerza dos solicitudes iguales a esperar simultáneamente en PostgreSQL: sólo una obtiene valores, quedan diez hashes y un único recibo/evento. El generador no se modifica.

Los códigos no se derivan de la clave TOTP. Esto es independencia criptográfica: no promete que el host arranque si perdió su almacén de claves ni cierra el procedimiento de emergencia.

[Resultados y límites](../evidence/s1-20261111/f08-01-generacion/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f08-01-generacion/MATRIZ-CRITERIO.md) · [plan](PLAN-F0801-GENERACION-CODIGOS.md).

## Dónde está la función

La GUI existente permite entrar con MFA y abrir **Mi seguridad → Códigos de recuperación**. La generación es expresa: contraseña actual, confirmación de reemplazo y **Generar diez códigos de recuperación**. Los valores pueden guardarse privadamente y después ocultarse; los recibos no los recuperan. Se conserva el [procedimiento ya documentado](PUNTO3-FUNCIONES-PENDIENTES.md).

No se ha comprobado ni alterado ahora esa función en D. No hace falta copiar archivos o repetir su instalación. Custodia/uso en la candidata objetivo y aceptación de Wascar mantienen su verificación separada.

## Límites de este paso

El cuerpo histórico D2 menciona generación al confirmar enrolamiento. El flujo implementado y revisado en punto 3 es una acción posterior explícita con contraseña y sesión MFA. Aquí se acredita generación/entrega única, sal e independencia; **no se afirma generación automática al confirmar ni códigos guardados por todos los administradores**.

«Una vez» se refiere a una respuesta con valores por operación: el usuario puede leer/copiar/descargar esa respuesta mientras la tiene visible. No se promete borrar todas las copias de strings de la memoria administrada o el archivo privado que el propio usuario descargue.

Canje, reenrolamiento restringido, consumo concurrente de un código, último administrador y cierre completo de F08 son los pasos siguientes; no se acreditan por esta prueba de generación.


Sólo F-08.01 acredita **1/2 punto**: índice del cierre restante **22,13→22,63/100**, sin porcentaje global nuevo. [Dictamen](../evidence/s1-20261111/f08-01-generacion/review/DICTAMEN.md). Siguiente paso 25/F-08.02.
