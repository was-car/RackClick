# Paso 16 · negativos del sobre MFA

03.11.2026. Criterio original F-05.03: «Probar contraseña errónea, alteración, truncado, datos extra, versión/algoritmo desconocidos y coste/tamaño fuera de rango». Peso1/2, sin sumar pruebas como resultados nuevos.

| Negativo | Caso existente | Resultado demostrado | ContadorKDF |
|---|---|---|---|
| Contraseña errónea bien formada | `WrongPasswordIsRejectedWithoutEchoingThePasswordOrThePayload` | `AuthenticationFailed`; el mensaje no contiene contraseña ni payload |1asertado |
| Sal, nonce, tag o ciphertext alterados | `SaltNonceTagCiphertextOrTruncationFailAuthenticationAfterOneDerivation`, cuatro variantes | `AuthenticationFailed`, sin devolver texto claro |1asertado por variante |
| Truncado conservando parte del ciphertext | Mismo caso, variante `truncado`, último byte retirado | `AuthenticationFailed` |1asertado |
| Truncado/sin payload de tamaño0,1,58,59 | `EnvelopesWithoutPayloadAreRejectedBeforeDerivation` | `InvalidFormat` |0asertado |
| Byte añadido y segundo sobre concatenado | Independiente `AppendingOneByteOrAnotherEnvelopeFailsAuthentication`, dos variantes | `AuthenticationFailed`; el ciphertext comprende todo el resto del sobre, sin cola ignorada |No instrumentado en esos dos casos |
| Versión desconocida | `HeaderOutsideTheProfileIsRejectedBeforeDerivation`, versión2 | `UnsupportedVersion` |0asertado |
| KDF/AEAD desconocidos | Mismo caso, KDF2/AEAD2 | `UnsupportedAlgorithm` |0asertado |
| Coste fuera del perfil | Mismo caso,600001 | `UnsupportedParameters` |0asertado |
| Sobre mayor de1MiB | `OversizedEnvelopeIsRejectedBeforeDerivation` | `TooLarge` |0asertado |
| Payload vacío o superior al máximo al sellar | `OversizedOrEmptyPayloadIsRejectedBeforeDerivation` | `InvalidRequest` |0asertado |
| Magia/longitudes incorrectas | Caso de cabecera: magia y longitudes de sal/nonce/tag fuera del perfil | `InvalidFormat` |0asertado |
| Codificación/límites de contraseña |11/257puntos de código y sustituto sin pareja; límite astral257 del control independiente | `InvalidRequest`;12/256 tienen controles positivos |0asertado en rechazos instrumentados |
| AAD omitida pese a cabecera válida | Independiente `ValidHeaderWithTagComputedWithoutAadMustNotOpen` | `AuthenticationFailed`, con referencia de formato construida mediante offsets literales |1asertado |
| Representación Unicode diferente | `PasswordIsEncodedWithoutNormalization` | `AuthenticationFailed`; no normalización silenciosa |No instrumentado en ese caso |

Los resultados son de L2d26.10:26casos del autor repetidos por Codex y8controles propios, sin fallos/omisiones. Incluyen positivos de referencia; no se presentan como34negativos únicos ni como nuevas ejecuciones de hoy. El log público del autor permite ligar los casos a sus PASS; los recibos del revisor conservan los contadores y la identidad de fuente.

Los contadores instrumentan la llamada que se comprueba, no la preparación del fixture o de su sobre válido mediante `Lazy`. Cero derivaciones en el rechazo no significa cero derivaciones o cero milisegundos en toda la prueba.

## Coste inferior y amplitud de la batería

El valor fuera de perfil ejecutado es600001. No hay una prueba declarada de cada valor inferior/superior o de todo el espacio uint. La fuente revisada compara desigualdad con600000 antes de `Derive`; el perfil tiene mínimo=máximo. Esta revisión de fuente complementa ese negativo concreto, sin inventar una ejecución de0/599999/uintMax ni ampliar el criterio a fuzzing exhaustivo.

También se probaron longitudes de truncado concretas y retirada de un byte, no todos los prefijos posibles de cualquier entrada. Las categorías del criterio están cubiertas; otro caso sólo se añade si revela un hueco material, no por acumular variantes.

## Efectos de integración y límites

`WindowsMfaKeyRecovery` y sus pruebas conservan identidadL2f. `WrongPasswordOrAlteredEnvelopeFailsWithoutCreatingAnything` comprueba error de autenticación y destino ausente para contraseña incorrecta/ciphertext alterado. Su comentario histórico dice «tag» para `altered[^1]`; la precisiónL2f aclara que es ciphertext. La prueba real de tag usa offset43 en L2d.

El código actual abre/autentica el sobre, analiza el contenido y sólo después llama al writer. El parche de creación/publicación F-04 afecta esa última etapa y no se alcanza en estos fallos. Los archivos/recoveryFiles revisados conservan además sus hashes L2gcorrección; esto no se transforma en un nuevo ensayo de archivos bajo el SID de servicio.

Un fallo de autenticación bien formado conserva su categoría. Formato/versión/algoritmo/contraseña ilegal tienen rechazos previos distintos; no se promete indistinguibilidad universal o igualdad de tiempos. No se afirma borrado físico de toda memoria ni se concede sesión o recuperación operativa por probar un codec.

## Propuesta de cierre

Sólo F-05.03 se acreditará tras dictamen independiente del conjunto. Propuesta **+1/2**,1481/84→1523/84 =**18,13/100 del cierre restante**.39checkpoints cerrados y241sin cierre. F-05.04/.05 y todoF05 permanecen abiertos; D/E sin operaciones y sin nuevo porcentaje global del producto.
