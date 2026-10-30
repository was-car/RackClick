# Revisión independiente MFA-L2d · RCKEY v1

**Dictamen favorable para el codec aislado en memoria.** No se identificó un defecto material. No es exportación del almacén, recuperación completa o habilitación MFA.

## Ejecución nueva de Codex

Se congelaron **119 archivos** de los proyectos pertinentes y se contrastaron **10 hashes**: codec/tests nuevos y ocho archivos previamente aprobados. Restore locked/build Release SDK **10.0.401**, **0 errores y 0 advertencias**.

| Grupo | Resultado |
|---|---|
| Pruebas de Claude, repetidas por Codex | **26 PASS** |
| Controles propios adicionales | **8 PASS** |

**34 PASS, cero fallos y omisiones; 18,484 s** para restore/build y ambos grupos. Cuatro binlogs, logs y TRX privados. Fuentes compartidas/congeladas y ocho documentos protegidos conservan sus hashes. [Resultados](../evidence/s1-20261026/mfa-l2d-codex/RESULTADOS-EJECUTADOS.json), [fuentes](../evidence/s1-20261026/mfa-l2d-codex/FUENTES-ENTREGADAS.json), [cierre](../evidence/s1-20261026/mfa-l2d-codex/CIERRE.md).

Los ocho casos propios contrastan el formato con una implementación de referencia que usa directamente primitivas .NET y offsets literales, sin usar el codec para construir o abrir los datos de referencia:

- Referencia abre `Seal`; `Open` abre el sobre de referencia con cabecera como AAD.
- Cabecera válida y tag calculado **sin AAD**: `Open` lo rechaza tras una derivación. Junto con el caso positivo anterior contrasta la vinculación exacta de la cabecera.
- Un byte añadido o un segundo sobre concatenado: autenticación rechazada.
- Contraseñas de12/256 puntos de código astrales aceptadas, 257 rechazados sin derivar; no se confunden con número de unidades UTF-16.

Se usa el mismo motor criptográfico .NET: **no** es otro backend, plataforma o vector público de conformidad. No se repitieron las mutaciones de Claude ni la regresión completa. [Pruebas propias](../evidence/s1-20261026/mfa-l2d-codex/MfaL2dIndependentReviewTests.cs).

## Decisiones aceptadas

Perfil v1 fijo600000, salida32, sal16/nonce12/tag16; metadatos validados antes de PBKDF2 y AAD completa salvo tag; ciphertext hasta el final con mínimo1 byte y límite total1MiB. La ausencia de campo de longitud no permite aceptar contenido añadido en los casos ejecutados. Puntos de código y UTF-8 estricto sin normalización son coherentes con el contrato documentado.

`mfa_l2_windows_review`, distinto del autor, revisó código/tests, D2 e investigación/XML oficial y no halló defecto material. No compiló ni ejecutó: las cifras anteriores corresponden al coordinador. [Subrevisión](../evidence/s1-20261026/mfa-l2d-codex/SUBREVISION-FUENTE.md).

Precisión de errores: contraseña incorrecta y contenido autenticado alterado son indistinguibles **con cabecera y contraseña bien formadas**. Formato, versión o longitud de contraseña inválidos conservan errores previos distintos por diseño; no afirmar indistinguibilidad universal. Sin cambio de código requerido por esta redacción.

## Límites conservados

Contraseña string no borrable; no inspección física de memoria, segundo equipo o exportación real. El código borra buffers en los recorridos revisados; no se afirma ausencia absoluta de copias ante cualquier fallo de recursos. La cuenta de runas recorre la cadena completa, sin vector remoto/coste material demostrado aquí. No se extrapola la medición local de57–62ms de Claude a otros equipos.

Adendas de L2c presentes, sin reabrir ese componente. Sin cambios de producto por Codex, dependencias, SQL, arranque, cuentas/servicios, PostgreSQL/HTTP, instaladores, VM/QA, commits/push o GitHub. [Siguiente lote L2e](MENSAJE-PARA-CLAUDE-MFA-L2D-REVISADO-26-10-2026.md). **Índice del cierre pendiente7,63/100**, sin crédito nuevo ni porcentaje global recalculado; MFA aún no disponible.
