# Paso 14 · criterio de validación RCKEY

03.11.2026. Criterio original F-05.01: «Validar magia/versión/algoritmo, tamaños, codificación canónica y límites min/max de iteraciones antes de KDF; autenticar cabecera completa como AAD». Se conserva su peso1/2, sin modificar el formato ni abrir recuperación real.

| Parte del criterio | Implementación actual y evidencia existente | Alcance verificado |
|---|---|---|
| Magia | `RequireHeader` exige los5bytes `RCKEY`; caso de cabecera alterada con contador0 | Rechazo antes de derivar |
| Versión | Byte5=1; cualquier otra versión se rechaza con `UnsupportedVersion` | Perfil v1 cerrado, sin negociación |
| Algoritmos | Bytes6/7=1:PBKDF2-HMAC-SHA256 y AES-256-GCM; negativos KDF/AEAD con contador0 | Rechazo antes de KDF, sin elegir algoritmos desde datos arbitrarios |
| Tamaños del sobre | `Open` exige60..1048576bytes antes de leer campos; `Seal` payload1..1048517bytes antes de derivar | Truncado/sin payload, exceso y máximo tienen pruebas. Codec en memoria; no afirma lectura de archivo acotada por el operador final |
| Tamaños y forma de cabecera | Sal16, nonce12, tag16 en offsets fijos y longitudes exactas, sin campos opcionales ni reservados ignorados | Longitudes incorrectas rechazadas antes de derivar |
| Iteraciones mínimo/máximo | `ReadUInt32BigEndian` compara con600000 antes de `Derive`; min=max600000 según F-03.02 | El caso600001 da contador0; la igualdad de uint rechaza cualquier otro valor, no sólo valores grandes. No se amplía el perfil ni se acredita medición de coste de otro equipo |
| Codificación de entrada | Cabecera binaria fija, enteros big-endian, sin representación textual/base64 que normalizar. Contraseña12..256puntos de código, UTF-8 estricto sin normalización; sustitutos sin pareja rechazados | Pruebas de límites, Unicode astral y normalización. No se promete que formas NFC/NFD equivalgan: son contraseñas distintas |
| Canonicalidad del contenido | L2e `Serialize` ordena versiones y regenera JSON canónico desde el anillo; análisis exige orden/identidad/coherencia y fin exacto | `Deserialize` admite variantes JSON válidas del parser; no exige igualdad byte a byte con su serialización. El contenido cifrado se analiza después de autenticar/descifrar, no antes de KDF |
| Cabecera completa como AAD | `Seal` y `Open` pasan exactamente bytes0..42 (43bytes) a GCM: magia, versión, algoritmos, coste, longitudes, sal y nonce | El tag43..58 se verifica como etiqueta, no se incluye circularmente en AAD. Ciphertext desde59 hastaEOF |
| Prueba de vinculación AAD | L2d independiente: lector de referencia abre `Seal`; `Open` abre referencia con AAD completa; referencia de cabecera válida pero tag calculado sin AAD se rechaza tras una derivación | Control independiente de offsets literales, mismo backend .NET; no otra plataforma/vector público |
| Sin bytes extra aceptados | La longitud de ciphertext se deduce de todo el resto del sobre; byte añadido y segundo sobre concatenado fallan autenticación en controles independientes | No se ignora cola. El parser del payload exige además fin exacto |
| Correspondencia actual | Codec y pruebas idénticos a L2d; payload y pruebas idénticos a L2e; referencias y recibos se contrastan por hash | Evidencia histórica reutilizada, cero nuevas ejecuciones de producto en este lote |

## Orden de validación

Tamaño total → forma/perfil de la cabecera clara → límites/codificación de contraseña → PBKDF2 fijo → autenticación GCM de cabecera/ciphertext → texto claro para el llamador/parser. No se exige conocer el contenido cifrado antes de KDF ni se presenta la contraseña incorrecta como un rechazo previo a derivar. Una cabecera fuera de perfil conserva su error propio; con entradas bien formadas, contraseña incorrecta o autenticación alterada producen `AuthenticationFailed`.

## Límites y propuesta

El borrado de buffers no prueba ausencia física de copias del runtime; contraseña `string` no borrable. La cuenta de runas recorre la cadena recibida; el operador final debe acotar la entrada antes de materializarla y no se acredita ese recorrido por el codec. No hay endpoint anónimo, exportación real, recuperación en otra VM, login recuperado o rotación ensayados en esta tanda.

F-05.01 puede cerrarse sólo tras revisión independiente de esta cobertura. Los34casos de L2d y36de L2e son ejecuciones del26.10, sin repetición hoy. No acreditan automáticamente F-05.02/.03/.04/.05. Propuesta exclusiva: **+1/2**,1397/84→1439/84 =**17,13/100 del cierre restante**. D se conserva sin operaciones; no hay porcentaje global nuevo ni aceptación de producción.
