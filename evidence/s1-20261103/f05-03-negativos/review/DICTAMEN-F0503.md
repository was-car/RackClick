# Revisión independiente · F-05.03 · paso16

03.11.2026. **Favorable para cerrar exclusivamente F-05.03 (+1/2)**. El criterio congelado de negativos está cubierto por pruebas existentes y por la identidad de las fuentes actuales. No se justifica repetir la suite ni modificar el codec. Esta revisión no acredita F-05.04/.05, una recuperación operativa entre equipos ni la aceptación del resultado F-05 completo.

## Evidencia contrastada

- Comprobación documental independiente: **21 referencias**, **6 fuentes idénticas** a sus manifiestos históricos y **7 entradas** del sello público L2d correctas. [Comprobación y hashes](COMPROBACION-F0503.json).
- L2d conserva **26 casos del autor y 8 controles independientes PASS**, sin fallos u omisiones, ejecutados el26.10 con SDK10.0.401. El log público conserva los26 nombres/PASS; el recibo independiente registra ambos grupos y sus salidas0. Son resultados históricos reutilizados, incluidos controles positivos; no34 negativos distintos ni pruebas ejecutadas hoy.
- Contraseña errónea, cambios de sal/nonce/tag/ciphertext y truncado con ciphertext restante: `AuthenticationFailed`. Los contadores instrumentados prueban una derivación en la llamada bajo prueba. Cabecera/versión/KDF/AEAD/longitudes/coste600001 y tamaños ilegales: rechazo antes de derivar, con contador0 donde la prueba lo instrumenta. Ese cero no incluye la preparación del sobre válido ni significa duración0ms.
- Byte añadido y sobre concatenado se rechazan mediante autenticación; esos dos controles independientes **no instrumentan el número de derivaciones**. El control de etiqueta calculada sin AAD también se rechaza. No se promete que todas las entradas mal formadas tengan el mismo código o tiempo.
- `WindowsMfaKeyRecovery.Recover` autentica con `Open`, después deserializa y finalmente llama al escritor. Su negativo existente comprueba contraseña errónea/ciphertext alterado, categoría de autenticación y destino ausente. El cambio posterior del escritor F-04 no se alcanza en esas rutas. Recovery/RecoveryFiles y sus pruebas conservan las seis identidades recogidas en la conciliación.

La [matriz del coordinador](../MATRIZ-NEGATIVOS.md) describe correctamente los casos y los límites. El [perfil D2](../../../../docs/D2-CONDICIONES-TECNICAS-F03-02.md) sigue fijando600000 como mínimo=máximo; su fe de erratas reciente sólo precisa la unidad de las duraciones históricas.

## Hallazgos y límites

- **Bloqueantes, altos o medios: ninguno** para este subpaso.
- **Informativo · amplitud del coste:** el valor fuera del perfil ejecutado fue600001. No se ejecutaron aquí0/599999/todos losuint. `RequireHeader` compara desigualdad exacta con600000 antes de `Derive`: los valores inferiores y superiores usan la misma rama de rechazo. La cobertura de esa categoría, complementada con la revisión de fuente, es suficiente para el criterio literal; añadir enteros por acumulación no justifica un build nuevo.
- **Informativo · precisión histórica:** el comentario de `altered[^1]` en la prueba de integración dice «etiqueta», pero modifica el ciphertext final. La adenda L2f ya lo aclara; esta revisión usa el cambio real de tag en offset43 de L2d para acreditar ese caso.
- Se probaron tamaños/prefijos concretos de truncado, no todos los posibles; no hay fuzzing exhaustivo. Tampoco se acredita borrado físico universal de memoria, ausencia de copias administradas, portabilidad DPAPI entre equipos, latencia de D o recuperación de factores/sesiones en una instalación real.

## Archivos y símbolos consultados

- `MfaKeyRecoveryEnvelope.cs`: `Open`, `Seal`, `RequireHeader`, `PasswordBytes`, `Derive`, errores y límites del formato.
- `MfaKeyRecoveryEnvelopeTests.cs`: casos de contraseña, cabecera, alteraciones/truncado, tamaños y Unicode; `Derivations`.
- `MfaL2dIndependentReviewTests.cs`: referencia por offsets, AAD ausente, datos añadidos/concatenados y límites astrales.
- `WindowsMfaKeyRecovery.cs`: `Recover`, `MapEnvelope`; `WindowsMfaKeyRecoveryTests.cs`: `WrongPasswordOrAlteredEnvelopeFailsWithoutCreatingAnything`. RecoveryFiles/pruebas: identidad documental, sin ensayo nuevo.
- Criterio del ledger, D2 técnico, revisiones L2d/L2f/L2g, recibos y manifiestos públicos históricos; matriz, investigación y conciliación actuales. Las rutas y SHA256 completos figuran en el JSON adjunto.

## Ejecutado y no ejecutado

Ejecuté `CONCILIAR-NEGATIVOS.py` en verificación de referencias y [Verify-Negative-Evidence.py](Verify-Negative-Evidence.py), además de lecturas acotadas de código/documentos y estado Git. Ambos auxiliares documentales terminaron con salida0; el segundo vuelve a extraer los26 PASS, contrasta los8 controles y comprueba las seis identidades históricas sin ejecutar producto.

**No ejecuté** restore/build/test/publish, PBKDF2/GCM nuevos, sobres, recuperación, PostgreSQL, HTTP, comandos de invitado/VM, cuentas/servicios, cambios de ACL ni lectura de credenciales/binlogs privados. D/E y los planes permanecieron intactos durante esta revisión. No revisé de nuevo endpoints, ámbitos o revocación: no cambiaron y pertenecen a sus propios criterios.

**Recomendación contable:** sólo+1/2 del cierre pendiente;1523/84 = **18,13/100** si el coordinador registra este dictamen. No es un porcentaje global nuevo del producto. Esta revisión no modifica el ledger ni declara integrada/aceptada una candidata operativa.
