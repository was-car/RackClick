# Para Claude · MFA-L1 autorizado y asignado · 25.10.2026

**Ampliación autorizada · 25.10.2026:** opción A aprobada: Microsoft.AspNetCore.Mvc.Testing[10.0.12] sólo en pruebas, csproj/lock de Quality.Tests y composición DI mínima. [Instrucción vigente para completar HTTP y corregir cuatro hallazgos](MENSAJE-PARA-CLAUDE-MFA-L1-HTTP-25-10-2026.md). Esta ampliación sustituye únicamente la prohibición anterior sobre esos archivos de pruebas; no autoriza cambiar otras versiones, C2, frontend, instaladores o QA. Custodia/recuperación de Wascar siguen confirmadas. La entrega parcial aún no está cerrada.

**Wascar confirmó ambas políticas:** custodia definitiva y recuperación MFA. Lee [DECISIONES-MFA-CONFIRMADAS-25-10-2026.md](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md). No volver a pedir autorización de arranque, ubicación del almacén o esas políticas de recuperación. Los parámetros técnicos y condiciones de D2 se resuelven durante implementación y revisión.

## Prioridad y resultado concreto

Tu siguiente bloque es **MFA-L1: enrolamiento restringido y pruebas HTTP con PostgreSQL real**. El foco de Dosen fue entregado y su revisión ya es conforme; véase MENSAJE-PARA-CLAUDE-C2-SALA-REVISADO-25-10-2026.md. Conserva ese trabajo; no repetirlo ni abrir ambos lotes a la vez. Continúa con implementación y pruebas MFA dentro de los archivos asignados.

La revisión de seguridad confirmó que `CompleteVerify` existe, pero Authenticate aún devuelve409 al faltar factor/enrolamiento y no hay rutas de enrolamiento. La migración014 ya soporta factores pending/active y desafíos enroll/verify. Está activa en la lista del producto y dentro del bundle14-08; no reabrir C para comprobarlo.

Entrega de este bloque:

1. Tras contraseña válida, un usuario que debe enrolarse recibe desafío `enroll` restringido, sin sesión API. No romper el desafío `verify` existente ni el login de los casos de laboratorio cuya política aún no exige MFA.
2. Iniciar/confirmar enrolamiento con rutas precisas, cookie de desafío y CSRF propios. Secreto sólo al titular autorizado durante el flujo; nunca en URL, logs, auditoría o diagnóstico público. No reutilizar una sesión previa como prueba del factor.
3. Confirmar TOTP, activar el factor, consumir el desafío y emitir sesión/CSRF nuevos en una transacción. Cuenta/política/caducidad se revalidan tras bloqueos con reloj de PostgreSQL; finalidad, intentos, replay y concurrencia explícitos.
4. Probar el flujo HTTP real, con sus mismos endpoints y middleware: `/me`, clientes y mutaciones rechazan el desafío; Origin/CSRF incorrectos, código erróneo/caducado/repetido y doble consumo no abren sesión; forzar rollback y revocación concurrente conserva atomicidad.

## Proveedor y límites del bloque

Usa un proveedor sintético exclusivamente dentro del fixture/host de pruebas para estas pruebas HTTP; la revisión D2 ya permitía esta vía. Reutiliza composición/mapeo real del producto, no una réplica del middleware. No añadir una clave fija, variable de entorno de bypass ni selector de proveedor de pruebas utilizable por el modo normal.

Sin proveedor en el modo normal, conservar `MfaAvailable=false` y el rechazo explícito. Si la política exige MFA, no emitir allí nuevos desafíos de enrolamiento/verificación ni sesión completa. Probar también ese negativo, además de los positivos del host de laboratorio.

No se promete custodia DPAPI operativa por pasar estos tests. El proveedor real con ACL/SID, sobre/rotación/Restore y recuperación completa corresponde al bloque siguiente, ahora con la política de Wascar ya decidida. Si el diseño de enrolamiento necesita métodos mínimos adicionales del proveedor, documenta y prueba ese contrato. No elevar el servicio ni cambiar versiones o bibliotecas sin necesidad.

## Propiedad de archivos

Puedes modificar exclusivamente:

- `development/server/src/RackClick.Server/PostgresStore.Authentication.cs`.
- `development/server/src/RackClick.Server/MfaStore.cs` y nuevos archivos `MfaStore.Enrollment.cs` / auxiliares de enrolamiento, si son necesarios.
- `development/server/src/RackClick.Server/Program.cs`: sólo composición/mapeo MFA, login y las excepciones **exactas** del middleware necesarias. Preservar el resto.
- Nuevas pruebas `MfaEnrollmentTests.cs` y `MfaHttpTests.cs` en `development/server/tests/RackClick.Quality.Tests/`, más fixture específico necesario, sin alterar las pruebas históricas para hacerlas pasar.
- `docs/MFA-L1-RESULTADOS.md` y `evidence/s1-20261025/mfa-l1-claude/`.

No estamos solos: Codex trabaja en inventario C2. No tocar InventoryPanel, OperationDialog, frontend, PostgresStore.cs compartido, SQL014 ni anteriores, migraciones, instaladores, locks/versiones, ledger, CHANGELOG o continuidad. Si un cambio adicional resulta imprescindible, conserva el fallo y comunica el archivo concreto para asignarlo sin pisarnos; no hace falta trasladar decisiones técnicas rutinarias a Wascar.

## Verificación y entrega

Base/laboratorio nuevos, secretos generados localmente y salidas privadas `.local/`. Publica sólo evidencia sanitizada, comandos, hashes, fases rojas si existen, resultados y límites. Prueba primero lo afectado y una regresión MFA pertinente al estabilizar; no repetir la entrega completa ni usar logs históricos como ejecuciones nuevas.

Implementación: Claude. Revisión independiente de código y pruebas: Codex con revisor distinto cuando proceda. No anunciar MFA disponible, habilitarlo en QA, construir paquetes, cambiar C/A/B/QA ni hacer commits/push. La VM C permanece apagada y su ensayo cerrado. La interfaz MFA se integra después, con contrato de API estable y sin colisión con inventario.
