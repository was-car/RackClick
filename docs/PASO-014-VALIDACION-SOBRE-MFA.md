# Paso 14 · validación del sobre portable MFA

03.11.2026 · **F-05.01 completado con revisión independiente favorable.** D se conserva sin operaciones.

RCKEYv1 ya está implementado. Se reutilizan el codec, el contenido portable y sus pruebas/revisiones anteriores; no se crea otro formato ni se cambian dependencias.

## Qué cubre este paso

- Magia, versión, algoritmos y longitudes exactas, con rechazo antes de PBKDF2.
- Tamaño de sobre60bytes..1MiB; enteros big-endian y perfil fijo600000iteraciones (mínimo=máximo).
- Contraseña12..256puntos de códigoUnicode, UTF-8 estricto, sin normalización automática.
- Cabecera de metadatos0..42 autenticada como AAD. La etiqueta se verifica mediante GCM; no forma parte de su propia AAD.
- Salida canónica del contenido; entrada JSON válida conforme al parser. No se afirma rechazo de todas las variantes de formato JSON ni equivalencia de contraseñas escritas con distinta composiciónUnicode.

Codec, payload, sus pruebas y parser de anillo conservan los hashes revisados. Se contrastaron25referencias públicas y las ejecuciones históricas L2d/L2e, incluidos los controles independientes de offsets/AAD. **No se presentan como pruebas nuevas de esta tanda.**

Esto valida el formato y su frontera criptográfica; no acredita todavía recuperación del servidor en otro Windows, costes en cualquier equipo o aceptación final. Los pasos15–18 conservan sus criterios.

[Resultado y límites](../evidence/s1-20261103/f05-01-sobre/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261103/f05-01-sobre/review/DICTAMEN-F0501.md) · [Matriz del criterio](../evidence/s1-20261103/f05-01-sobre/MATRIZ-CRITERIO.md).

Se acredita únicamente **1/2 punto**. El índice de cierre restante sube de **16,63 a17,13/100** (exacto1439/84), sin cambiar pesos ni números. F-05 completo sigue abierto; no es un nuevo porcentaje global ni aceptación de producción.

No necesitas ejecutar nada ni proporcionar sobres, contraseñas o códigos. El siguiente paso numerado es el **15/F-05.02**, contraste de la medición de coste PBKDF2 existente en Windows.
