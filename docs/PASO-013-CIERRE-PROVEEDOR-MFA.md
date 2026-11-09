# Paso 13 · cierre técnico del proveedor MFA Windows

03.11.2026 · **F-04.04 completado con revisión independiente favorable.** F-04 queda cerrado técnicamente; D se conserva sin operaciones.

El criterio de este resultado es que el servicio real lea y descifre sus claves, verifique factores MFA y no pueda escribirlas ni cambiar sus permisos; otra cuenta estándar no debe leerlas y management debe permanecer cerrado. El conjunto debe tener negativos y revisión independiente registrados.

## Evidencia que se conserva

1. **Creación y publicación del almacén:** paso11/F-04.01, descriptor protegido desde la creación nativa y preservación del conjunto completo ante fallo posterior a publicar. Pruebas y revisión Windows ya ejecutadas; no se repiten.
2. **Permisos efectivos:** paso12/F-04.02, dos cuentas reales de servicio de E;504 comprobaciones correctas sobre padres, almacenes propios/ajenos y management. Sin cambios en objetivos o servicios.
3. **Uso del proveedor real:** F-04.03, instalaciónC10 y refuerzoD11, enrolamiento y nuevo login con segundo factor por HTTPS, también después del reinicio. Negativos históricos de clave/versión/almacén ausente, sin regeneración ni sesión alternativa.
4. **Correspondencia con las fuentes actuales:** composición Windows, lector, proveedor, anillo, enrolamiento, verificación y cifrado conservan la identidad de fuente contrastada. Los cambios posteriores de Program se identifican por diff; su segmento de composición MFA permanece idéntico. El writer corregido coincide con la fuente revisada del paso11.

Esta tanda concilia documentos, hashes y resultados existentes. **No es una nueva ejecución de esas pruebas**, ni afirma que todos los ensayos se realizaran con una única DLL o un instalador nuevo.

## Límites que conservan su propio paso

- La incorporación del writer corregido a una candidata completa y su ensayo Windows siguen pendientes. D conserva su instalación.
- Recuperación portable, rotación/coherencia disco-DB, códigos y emergencia mantienen sus criterios posteriores.
- La custodia y gracia45/exención global ya están decididas; no se vuelven a solicitar ni se cambian.
- La observación favorable de Wascar sobre su MFA administrativo no sustituye la aceptación final de toda la entrega.

[Resultados y límites](../evidence/s1-20261103/f04-04-cierre/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261103/f04-04-cierre/review/DICTAMEN-F0404.md) · [Matriz de cierre](../evidence/s1-20261103/f04-04-cierre/MATRIZ-CIERRE.md).

Se acredita sólo **5/8 =0,625 puntos**. El índice de cierre restante pasa de **16,01 a16,63/100** (exacto1397/84). Pesos y números se conservan. No es un nuevo porcentaje global del producto ni una aceptación de la entrega completa.

No necesitas ejecutar nada en D ni volver a instalar para esta conciliación. El siguiente paso numerado es el **14/F-05.01**, contraste de la validación del sobre de recuperación MFA existente.
