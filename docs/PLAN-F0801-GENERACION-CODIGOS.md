# F-08.01 · conciliación de la generación de códigos de recuperación

11.11.2026. Paso 24 autorizado por Wascar. Se conservan D y E, sin operaciones sobre VM, instalaciones o cuentas reales. Ejecución del coordinador con revisión independiente acotada; sin commits, push o despliegue.

**Objetivo:** generar y entregar una sola vez diez códigos propios; almacenar sólo hashes con sal y vínculo por usuario, independientes de la clave TOTP. No implementar otro generador ni cerrar F-08.02–.05 por este paso.

**Diseño existente:** `MfaRecoveryCodeCodec`, `GenerateOwnRecoveryCodes`, rutas propias y panel Mi seguridad ya implementados/revisados en punto 3. Se elige contrastar identidad de fuente y repetir sólo sus focos de generación, frente a reescribir el generador o repetir todo el canje/reenrolamiento y la instalación.

## Investigación y alcance

Se reutilizan D2, decisiones confirmadas, gracia45, punto 3 y sus revisiones/recibos/Edge; el registro numerado ya ordena conciliar esta generación existente. Códigos de 128 bits aleatorios y sal independiente de 128 bits; hash SHA256 versionado y ligado a Systemhaus/usuario. No se incorporan bibliotecas o dependencias. Consulta oficial el 11.11: RandomNumberGenerator.GetBytes y CryptographicOperations.FixedTimeEquals (.NET 10, Microsoft Learn); sus garantías de primitiva no prueban por sí solas la entrega única de RackClick.

El cuerpo histórico D2 §3a menciona generación al confirmar enrolamiento. La implementación revisada y el procedimiento punto 3 usan generación **explícita posterior**, con contraseña actual y sesión MFA. Este paso acredita el literal técnico de generación/entrega/hash; no declara generación automática al confirmar ni custodia garantizada de todos los administradores. Último administrador y custodia/uso en candidata instalada quedan pendientes en sus criterios/hitos.

«Una vez» significa primera respuesta de la operación; no un límite a renders o a copiar/descargar mientras el usuario mantiene visible esa respuesta. Los recibos y replays nunca recuperan valores. La independencia criptográfica respecto a TOTP no promete que un servicio pueda arrancar con su almacén perdido.

## Tareas

- [x] **1. Identidad y criterio.** Matriz literal→fuente/evidencia/límite. Contrastar los módulos actuales con el manifiesto final y revisión del punto 3, incluida GUI/Node. Confirmar CSPRNG/sal/hash/contexto sin inferir entropía de una muestra estadística.
- [x] **2. Verificación focal existente.** Reutilizar las fuentes de producto fijadas de F-07.05 y compilarlas en una copia aislada para incorporar únicamente la nueva prueba. Ejecutar los 9 casos del codec, 4 casos de generación de almacén y 1 HTTP de generación/recibo/guardas en un PostgreSQL 17.11 nuevo; añadir únicamente una prueba de dos generaciones de la misma solicitud realmente solapadas bajo bloqueo SQL, con una sola entrega de valores,10hashes y1recibo/auditoría; verificar los 10 Node de recuperación existentes en la misma copia de fuentes. Reutilizar el producto exacto; compilar sólo para incorporar la nueva prueba en una copia aislada, sin cambiar el generador.
- [x] **3. Revisión independiente.** Revisor distinto contrasta transacción, autoridad y entrega única, atribuye por separado ejecuciones propias/históricas y determina si hay brecha. Ante defecto, reproducir antes de corregir; si todo existe, no fabricar fase roja.
- [x] **4. Continuidad y crédito.** Ficha24 y evidencia sanitizada; actualizar changelog/continuidad y sólo F-08.01 peso 1/2 si es conforme. Mantener F08 completo y custodia/instalación/QA sin cerrar. Preservar resultados QA y regenerar/verificar índices y guía.

## Foco de revisión

- Ni códigos ni formas normalizadas entran en DB, auditoría o recibo; la primera respuesta es la única entrega.
- Los mismos códigos con distinta sal no producen un valor almacenado reutilizable entre cuentas/Systemhaus.
- Otro actor, sesión sin MFA, contraseña incorrecta o revisión incompatible no acceden a códigos.
- Una respuesta perdida/replay permite consultar resultado, sin volver a mostrar secretos ni generar otro conjunto automáticamente.
- No confundir valor de hash, independencia criptográfica y disponibilidad del host ante pérdida de claves; no cerrar canje o emergencia por probar generación.

Cierre técnico del 11.11: [resultados](../evidence/s1-20261111/f08-01-generacion/RESULTADOS.md), [dictamen](../evidence/s1-20261111/f08-01-generacion/review/DICTAMEN.md). Generador/UI/SQL intactos; sólo nueva prueba de solapamiento y documentación.
