# F-05.01 · dictamen independiente de validación RCKEY

03.11.2026. Revisor `rackclick_security`, distinto del autor del codec y del coordinador. **Favorable al cierre de F-05.01, exclusivamente 1/2 de punto.** No hay bloqueante concreto que requiera modificar el codec o repetir una suite para este subpaso. F-05 completo y sus otros checkpoints siguen abiertos.

## Correspondencia y evidencia reutilizada

El codec actual coincide byte a byte con la fuente revisada L2d: `8a7b06ee0441086c40aba3cc8735c21fc562eee08383a58e6ed169b01b7d7fe1`; sus pruebas, `5d15b220d6d12cfe9ab8e340fe39a8e902b47f609af434989f84db96060e4a1f`. Payload, sus pruebas y parser del anillo conservan las otras tres identidades registradas. Se revisaron código, aserciones, pruebas independientes de offsets literales y la [matriz del criterio](../MATRIZ-CRITERIO.md).

[Verificador independiente](Verify-F0501-References.py), salida 0: **25 referencias públicas por hash y cinco fuentes exactas**, con resultados en [COMPROBACION-F0501.json](COMPROBACION-F0501.json). Se conciliaron los contadores históricos L2d **26+8 PASS** y L2e **28+8 PASS**, SDK10.0.401, restore/build y grupos de pruebas con salida 0, sin fallos u omisiones. No se ejecutaron otra vez ni se abrieron sus binlogs/TRX privados.

## Contraste del criterio congelado

- **Magia, versión y algoritmos:** `RequireHeader` exige RCKEY y bytes 1/1/1 para versión, PBKDF2-HMAC-SHA256 y AES-256-GCM. Las demás formas se rechazan antes de `Derive`; no se selecciona una implementación desde datos arbitrarios.
- **Tamaños:** `Open` rechaza contenedores menores de 60 o mayores de 1.048.576 bytes antes de acceder a campos o derivar. `Seal` exige payload de 1 a 1.048.517 bytes. Sal16, nonce12 y tag16 tienen posiciones/longitudes exactas; no hay campos reservados ignorados.
- **Iteraciones antes de KDF:** lectura uint32 big-endian y comparación de igualdad con **600000**, antes de llamar a PBKDF2. Según F-03.02 el perfil v1 tiene mínimo=máximo600000. La igualdad rechaza tanto valores inferiores como superiores; el negativo ejecutado 600001 conserva contador de derivación cero. No se afirma que todos los enteros posibles hayan sido probados ni se fija por esta revisión un coste universal de producción.
- **Codificación:** la cabecera es binaria y de posiciones fijas, sin alternativa textual/base64 que normalizar. La contraseña usa UTF-8 estricto y 12..256 puntos de código, sin normalización; los sustitutos sin pareja se rechazan antes de KDF. Los controles existentes de límites y Unicode astral distinguen puntos de código de unidades UTF-16.
- **AAD completa:** `Seal` y `Open` pasan exactamente los bytes **0..42**, que contienen toda la metadata clara: magia, versión, algoritmos, coste, longitudes, sal y nonce. El tag43..58 se verifica por GCM, no se incorpora circularmente como AAD; ciphertext empieza en59 y ocupa todo el resto.
- **Evidencia independiente de AAD:** el lector de referencia abre Seal y Open abre una referencia construida con primitivas .NET y offsets literales. Una referencia de cabecera válida cuyo tag se calculó sin AAD es rechazada después de una derivación. Eso acredita la vinculación sin limitarse a modificar campos que el parser ya rechazaría antes de descifrar. Sigue siendo el mismo backend .NET, no otra plataforma o vector público de conformidad.

## Precisiones de canonicalidad y orden

No es bloqueante la precisión aceptada de L2e: `Serialize` produce el anillo en JSON canónico, mientras `Deserialize` admite variantes JSON semánticamente válidas del parser aprobado. **No se declara rechazo universal de JSON no idéntico a la serialización canónica**, ni se cambia ese contrato por la palabra del checkpoint.

La validación previa a KDF corresponde al tamaño/forma de la cabecera y a la codificación de contraseña. El contenido cifrado sólo puede validarse después de autenticar/descifrar. El codec recibe un payload opaco; su parser aplica después identidad, orden, límites y fin exacto. No se promete inspeccionar ese contenido antes de derivar. Tampoco se normaliza NFC/NFD: representan contraseñas distintas por contrato.

La ausencia de longitud explícita de ciphertext no ignora una cola: todo el resto forma parte del dato autenticado. Los controles independientes de byte añadido y segundo sobre concatenado fallan autenticación. Esto no convierte esos rechazos en errores previos a KDF ni afirma indistinguibilidad de todos los errores de formato.

## Alcance y crédito

Sólo se leyeron documentos, fuentes y recibos públicos y se ejecutó el comprobador documental/hash. **Cero compilaciones, pruebas criptográficas nuevas, sobres nuevos, VM/D/E, servicios, DB, credenciales o material de claves.** Ningún producto, dependencia, peso, criterio o ledger fue modificado por este revisor.

La recuperación portable real, coste Windows F-05.02, negativos finales F-05.03, restauración de factores/AAD en otra instancia F-05.04 y revisión global F-05.05 conservan sus criterios. La memoria del runtime, contraseña string no borrable, durabilidad/rotación y operación final no se acreditan por el codec en memoria.

Recomendación exclusiva: **F-05.01 +1/2**, `1397/84 → 1439/84`, **17,13/100 del cierre restante**, cuando lo registre el coordinador. No es porcentaje global nuevo ni aceptación de producción.
