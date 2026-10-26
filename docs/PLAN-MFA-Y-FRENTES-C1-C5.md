# Plan de trabajo: MFA y frentes C1, C2, C3, C5

**Actualización vigente · 25.10.2026:** Wascar confirmó custodia, ubicación del almacén y recuperación MFA. [Decisiones](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md), [asignación MFA-L1 a Claude](MENSAJE-PARA-CLAUDE-MFA-L1-25-10-2026.md). Las menciones siguientes de D2 pendiente y de SQL014 no activada son históricas; SQL014 está en el runner y bundle14-08. MFA sigue sin disponibilidad para usuarios. La asignación actual autoriza los archivos del lote; restricciones de sólo respuesta de encargos anteriores no impiden ese desarrollo. Sin cambios en QA/VM ni permisos de publicación.

Fecha: 23.10.2026. Alcance acordado con Wascar: MFA y los frentes C1, C2, C3 y C5. C4 (Windows limpio, servicio y prerrequisitos) queda para después. Porcentaje global: 78 % sin cambio hasta QA y revisión independiente.

Regla de trabajo (`AGENTS.md`): lotes pequeños y verificables, resultado visible por lote, revisión independiente antes de cerrar cada bloque, sin agentes en paralelo salvo que Wascar lo pida. Cada lote termina con: archivos cambiados, prueba ejecutada, resultado y siguiente paso.

## Decisiones que necesito de Wascar

| # | Decisión | Propuesta por defecto |
|---|---|---|
| D1 | Dependencia TOTP | **GO de Wascar (23.10.2026)**: usar `Otp.NET`, versión fijada tras revisión. Implementación en M2. |
| D2 | Custodia de la clave TOTP | **Propuesta v2 de Claude** en [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), corrigiendo los seis hallazgos de Codex: almacén separado con lectura solo para el SID del servicio, códigos de recuperación independientes y restablecimiento local de emergencia, sobre portable con KDF, anillo de versiones. **Pendiente**: revisión de Codex sobre la v2 y confirmación de Wascar. |
| D3 | MFA por usuario, administrado desde el panel de usuarios (Wascar, 23.10.2026) | Activar o desactivar por usuario. Por defecto desactivado, incluido el administrador. Un usuario nuevo se crea con "configurar MFA en el primer inicio de sesión". Antes de producción, el contrato exige MFA para todos: eso se decidirá entonces. |
| D7 | Administrador sin MFA durante las pruebas | Aceptado por Wascar mientras no haya producción. Antes de producción debe revisarse. |
| D4 | Alcance de C3 en PDF e impresión | Incluir solo los formatos que RC9 ya exporta. PDF nuevo queda fuera del primer cierre. |
| D5 | Dispositivos finales y pasos físicos Dosen (C2) | Fuera del primer cierre; se registran como límite explícito. |
| D6 | Destinos de copia (C5) | Local y UNC en el primer cierre; USB después. |

## MFA

| Lote | Contenido | Prueba de salida |
|---|---|---|
| M0 | Decisiones D1 y D2 | Respuesta de Wascar registrada. |
| M1 | Migración 014 aditiva. Borrador en `development/server/database/pending/014-mfa-borrador.sql`, sin activar. | **Hecho 23.10.2026 en laboratorio**: 001–013 y 014 aplicadas a PostgreSQL 17.11; 14 pruebas de restricciones OK. Detalle en [MFA-M1-RESULTADOS.md](MFA-M1-RESULTADOS.md). Pendiente: prueba con el runner real y la aplicación (M2 y M3). |
| M2 | TOTP con Otp.NET: secreto cifrado, enrolamiento que se confirma con un primer código, ventana pequeña y último intervalo consumido. | **Núcleo hecho 23.10.2026**: `MfaTotp` y `MfaSecretCipher`, 26 pruebas OK; detalle en [MFA-M2-RESULTADOS.md](MFA-M2-RESULTADOS.md). Pendiente: enrolamiento en el flujo de login (M3) y custodia de la clave (D2). |
| M3 | Login con segundo paso: desafío de 202 sin sesión utilizable, verificación que emite sesión y CSRF nuevos en la misma transacción, cookie de desafío propia. | **Correcciones de la revisión de Codex aplicadas el 23.10.2026**: 014 integrada, esquema 14, reset invalida desafíos, política revalidada, caducidad con reloj de PostgreSQL y CSRF del desafío. 57 pruebas OK contra PostgreSQL 17. **No desplegable**: faltan pruebas HTTP, reset real, publicación/instalador en Windows, pruebas Python de arranque y la regresión C1 de la candidata. Detalle en [BUILD-M3-CORRECCIONES-23-10-2026.md](BUILD-M3-CORRECCIONES-23-10-2026.md). |
| M4 | Panel de usuarios: interruptor MFA por usuario, reinicio de MFA por administrador y revocación de sus sesiones al cambiar el interruptor. Códigos de recuperación de un solo uso. Protección del último administrador. | Pruebas de auditoría sin secretos, de último administrador y de revocación. Interruptor cambiado en paralelo: gana una sola escritura por revisión. |
| M5 | Interfaz: segundo paso de login y reautenticación en formularios sensibles, sin perder borradores. | Prueba en navegador real, EN/DE/ES. |
| M6 | Backup cifrado y restauración en otra instancia con la clave recuperada. | Restauración en laboratorio nuevo. Sin clave, error explícito. |
| M7 | Revisión independiente y guiones QA, no habilitados hasta la candidata seleccionada. | Informe de revisión registrado. |

## C1 · Administración

- Conciliar S-38 a S-42 con la evidencia actual de grupos, sesiones, permisos y auditoría.
- Lista de diferencias concretas, cada una con operación, criterio y prueba.
- Corregir las diferencias y completar la QA administrativa.
- No incluir Active Directory, GPO ni grupos anidados en esta fase: el contrato los excluye.

## C2 · Inventario

- Cerrar la edición de grupos, conectores, caras y alimentación.
- Compensación autorizada de S-13, S-14, S-22, S-23 y S-30.
- Lista explícita de operaciones soportadas y no soportadas, con pruebas de persistencia, conflicto, permiso y atomicidad.
- Dosen y dispositivos finales según D5.

## C3 · Paridad con RC9

- Conciliar S-26 y S-31 a S-37, S-47 con exportaciones, importaciones e informes ya desarrollados.
- Registrar solo huecos reales, con referencia a código o evidencia.
- Idiomas EN/DE/ES, teclado y accesibilidad.
- Prueba de ida y vuelta por cada formato soportado.

## C5 · Recuperación y paquete

- Copias programadas con retención, destinos local y UNC (D6), y fallos de destino sin perder la última copia válida.
- Recuperación de configuración, secretos y certificados, e identidad del servicio.
- Actualización con reversión compatible.
- Manual y contenido de entrega.
- Ensayos S-44, S-45, S-46, S-53, S-54 y S-56 en destinos nuevos.

## Dependencias

- C5 depende de M6: la copia de seguridad debe incluir la estrategia de la clave TOTP.
- C1 depende de M3 y M4: las sesiones y reautenticación afectan a la administración de usuarios.
- Todo el paquete depende de la revisión independiente de los cambios de instalación ya pendientes (ver `docs/HANDOFF-CODEX-23-10-2026.md`).

## Primer paso propuesto

M1 y la validación de D1 y D2. Con tus respuestas, empiezo por M1 en el laboratorio PostgreSQL local, sin tocar el servidor QA.
