# MFA-L1 · ronda 2 · dictamen independiente de Codex

25.10.2026. **Conforme al cierre técnico acotado del backend L1**, sobre los ocho hashes de la entrega de Claude. Las cuatro causas P2 anteriores están corregidas. MFA completo, F-07/F-12, custodia operativa, recuperación, interfaz y candidata final siguen pendientes. No habilitar ni anunciar MFA en QA.

## Ejecución independiente

Se congelaron110 archivos en una copia privada, sin construir una distribución desde el árbol compartido. Los ocho hashes entregados coinciden y ninguna de esas110 fuentes cambió durante la revisión. Restore con lock y SDK10.0.401 fijado correcto; compilación Release sin errores ni advertencias. Binlogs y diagnósticos completos privados en `.local`.

- **88 pruebas originales PASS**,0 fallos originales,1 omitida por Docker. Incluye18 de enrolamiento,9 HTTP y la regresión histórica. No se atribuyen a Codex las fases rojas ejecutadas por Claude.
- **Un foco independiente adicional PASS**, PostgreSQL17.11: enrolar→confirmar→API→nuevo login verify→API, con identidad de ejecución distinta del propietario, sin superusuario/CREATEDB/CREATEROLE/CREATE. Un intento DDL recibe42501. Un testigo SQL observa las cinco escrituras confirmadas del flujo bajo ese rol; no deduce la identidad sólo de la conexión configurada.
- Cookie de desafío y sesiones con Secure/HttpOnly/SameSite/Path/MaxAge; eliminación del desafío por su Path, tokens/CSRF nuevos, hashes y vida≤5min en DB, cero sesión antes de confirmar y dos sesiones MFA tras los dos logins. Esto comprueba cabeceras de TestServer, **no navegador, TCP ni TLS**.
- CLI con bootstrap real:14 migraciones registradas, `--migrate` exitoso e inmutable; segundo bootstrap y modos incompatibles rechazados. Base vacía rechazada sin inicializar; recover-admin sin usuario rechaza antes del host. Origen deliberadamente inválido no afecta estas ramas. No es una nueva prueba13→14 ni de recuperación completa.

## Seguridad y observaciones

Revisor distinto contrastó código, pruebas y recibos; ejecutó tres focos de fuente/16 aserciones, sin atribuirse C#/PG/HTTP. Auditoría mínima en la misma transacción, con rollback forzado aprobado en la suite. [Dictamen de seguridad](../evidence/s1-20261025/mfa-l1-ronda2-codex/REVISION-SEGURIDAD.md).

`CompleteVerify` **no actualiza la política después del reloj**. Su FOR SHARE no introduce el upgrade que causaba el fallo del enrolamiento; no se justifica cambiarlo por analogía. Sus pruebas históricas de caducidad tras bloqueos pasan.

Dos intentos del auxiliar propio se conservan: uno esperaba un código de recuperación inexistente y paró antes de las pruebas; el otro aprobó la suite original y el flujo adicional, pero su observador de conexiones no confirmó la identidad al terminar. Se corrigieron sólo los observadores/expectativas de pruebas. La repetición final ejecutó únicamente el foco adicional, sin repetir las88 pruebas. DLL de producto idéntica en ambas ejecuciones.

Mejora P3 restante: el fixture de Claude debe restaurar las variables de entorno en finally aunque falle Dispose. Los atributos de cookies ya están cubiertos por el foco independiente; conviene trasladar esas aserciones al conjunto permanente. Ninguna de estas observaciones demuestra un bloqueo de producto.

## Conciliación

Se acreditan únicamente **F-07.01 y F-07.03**, pesos fijos0,50+0,50: desafío restringido y confirmación transaccional. F-07.02/04/05 y F-12 no se declaran completos. Cierre del plan pendiente **6,63→7,63/100 (641/84)**,19/280subpasos; no es porcentaje global del producto. Sin cambio de pesos o alcance.

[Evidencia y reproducción](../evidence/s1-20261025/mfa-l1-ronda2-codex/CIERRE.md). Sin cambios de producto por Codex, commits/push, paquetes, VM, QA o activación del proveedor normal. [Mensaje para Claude](MENSAJE-PARA-CLAUDE-MFA-L1-RONDA2-REVISADO-25-10-2026.md).
