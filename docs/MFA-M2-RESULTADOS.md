# MFA · lote M2 · resultados

Fecha: 23.10.2026. Responsable: Claude. Alcance: núcleo criptográfico de TOTP, sin base de datos, sin endpoints y sin interfaz. El servidor QA no se ha tocado.

## Decisiones aplicadas

- **D1 (GO de Wascar):** dependencia `Otp.NET` fijada a `[1.4.1]` en `development/server/src/RackClick.Server/RackClick.Server.csproj`. Licencia MIT según la API de GitHub (`kspearrin/Otp.NET`, no archivado). El nuspec del paquete no declara la licencia en su campo habitual; se verificó en el repositorio.
- **D2 (propuesta, pendiente de revisión de Codex):** clave de cifrado fuera de PostgreSQL, descrita en [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md). M2 solo implementa el cifrado que consume esa clave; no implementa la custodia.

## Código nuevo

- `development/server/src/RackClick.Server/MfaTotp.cs`: TOTP de RFC 6238, 6 dígitos, SHA-1, paso de 30 s, ventana de ±1 paso y rechazo de pasos ya consumidos.
- `development/server/src/RackClick.Server/MfaSecretCipher.cs`: AES-256-GCM, nonce aleatorio por registro, formato nonce|etiqueta|texto cifrado. El contexto autenticado liga el secreto a la instalación, el usuario y la versión de clave.
- `development/server/tests/RackClick.Quality.Tests/MfaTotpTests.cs` y `MfaSecretCipherTests.cs`.
- Archivos de bloqueo actualizados por la restauración: `packages.lock.json` del servidor y del proyecto de pruebas. Deben revisarse con el resto.

## Pruebas ejecutadas

Comando: `dotnet test tests/RackClick.Quality.Tests` desde `development/server`, SDK 10.0.401 fijado en `global.json`.

| Conjunto | Resultado |
|---|---|
| `FullyQualifiedName~Mfa` | 26 de 26 OK |
| Sin pruebas de Docker (`!~PostgresContainer`) | 36 de 36 OK |

Las pruebas de TOTP usan los vectores de RFC 6238 (SHA-1, seis últimos dígitos). Cubren: código del paso actual, rechazo de repetición, ventana de un paso hacia atrás, rechazo a dos pasos, formatos incorrectos y secreto de longitud errónea. Las de cifrado cubren: ida y vuelta, nonce distinto en cada cifrado, rechazo con otro usuario, otra versión de clave, otra instalación, texto alterado, entrada truncada y claves que no son de 256 bits.

## Lo que M2 NO demuestra

- No hay persistencia: la base de laboratorio de M1 no se ha conectado al código todavía.
- No hay enrolamiento ni verificación en el flujo de login: M3.
- No hay gestión de la clave (creación, DPAPI, sobre de recuperación, rotación): depende de la revisión de D2.
- Las pruebas que necesitan PostgreSQL real (`PostgresContainer`) no se han ejecutado: requieren Docker y este PC no lo tiene.
- No hay revisión independiente todavía.

## Siguiente paso

M3: conectar `app_mfa_*` de M1 con el código de login, emitir desafíos de corta vida y sesión nueva solo tras verificar el código. Antes, Codex revisa D2 y los bloqueos del servidor.
