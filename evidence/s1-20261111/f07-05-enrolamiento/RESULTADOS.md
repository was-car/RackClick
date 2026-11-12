# F-07.05 · enrolamiento restringido y sesión confirmada

11.11.2026. Cierre técnico con dictamen independiente favorable. Sin operaciones en D/E, VM, servicios, cuentas o bases instaladas; sin commits, push, instalaciones o publicación.

## Investigación y elección

Se reutilizaron F0701–04, L1ronda2, GUI27.10, dashboard45, C10 y D11 antes de añadir pruebas. La revisión previa detectó que el rechazo histórico del desafío sólo comprobaba /me y logout, sin la matriz completa de clientes/mutaciones y etapas. No se identificó un defecto de producto. Se añade cobertura de la brecha sobre fuentes actuales; no un login nuevo.

Se consultaron [ASP.NET Core10 integración](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0) y [PostgreSQL17 locks](https://www.postgresql.org/docs/17/explicit-locking.html),11.11.2026. Se reutiliza WebApplicationFactory y las dependencias fijadas, sin copiar código externo o cambiar versiones. La skill React se utilizó para contrastar el componente existente; no se cambian diseño, estilos o interacciones aprobadas.

## Ejecuciones nuevas del coordinador

Windows; SDK10.0.401/runtime10.0.12, PostgreSQL17.11. Fuentes aisladas `.local/f0705-33db9a25/freeze`; salidas originales y binlogs únicos privados.

| Comprobación | Resultado |
|---|---|
| Restore locked y build Release final | exit0,0 errores/advertencias C# |
| Nueva cuenta con gracia vencida desde creación |1PASS,0 omitidas; DB46 nueva, DPAPI real y rol runtime restringido |
| Cuenta existente sin fecha histórica, gracia desde activación vencida |1PASS,0 omitidas; otra DB46 nueva con el mismo alcance |
| Núcleo de enrolamiento/HTTP/gracia45 existente |36PASS,0FAIL,0 omitidas sobre los binarios finales |
| Frontend API MFA, textos, QR y administración propia |70Node PASS,0FAIL,0 omitidas; copia aislada y esbuild existente0.25.10 |

Pines finales:

- Servidor: `1a6cb30d7a74efa7760c6ea88c46adfac4674c84071b9f88ea023ac2117aef06`.
- Pruebas: `801d965a11d73165764aa579fd75c6c7ea163cc0cd53ccb9bcd1d9c061e3c8ec`.

Las dos nuevas invocaciones son escenarios completos del mismo trabajador, no48funciones por contar peticiones. Los36casos son regresión pertinente, no toda la suite RackClick. Las70Node no son tests PostgreSQL ni navegador. Node avisa del tipo de módulo implícito ya existente en package.json; no se modificó ese archivo ni se ocultó el aviso.

Comandos: `C:/Python312/python.exe -B tools/tests/run_mfa_enrollment_closure.py --source-root <freeze> --expected-server-sha256 <pin servidor> --expected-tests-sha256 <pin pruebas> --mode closure`, y la misma invocación con `--mode regression`. Node24.21.0: `--test` con `mfa-api.test.mjs`, `mfa-words.test.mjs`, `mfa-qr.test.mjs` y `mfa-account.test.mjs`. No se descargan dependencias.

## Comprobaciones integradas

- Contraseña incorrecta:401, sin cookie, desafío o sesión. Las cuentas positivas se rigen por gracia45 real, no por una fila de mfa_required impuesta artificialmente.
- Tres etapas sin autoridad: desafío, pending y TOTP inválido. En cada una, GET/me, GET/customers, POST/customers y POST/me/preferences con cookie de desafío y con el token renombrado como Session:401, sin cookie de sesión ni cambio en usuarios, factores, desafíos, sesiones, clientes, preferencias o auditoría durante esas peticiones.
- Dos confirmaciones concurrentes: una200 y una401; exactamente un factor activo y una sesión verificada. Token/CSRF distintos del desafío, hashes persistidos, atributos Secure/HttpOnly/SameSite/Path y acceso posterior a /me/clientes.
- Testigo SQL propio del fixture registra current_user y txid, sin secretos: activación de factor, consumo de desafío e inserción de sesión comparten la transacción que crea esa única sesión. Todas sus escrituras HTTP observadas proceden del rol runtime; crear una tabla con ese rol devuelve42501.
- Repetir confirmación no emite sesión ni aumenta su número. No se presenta esto como simulación de pérdida de red; el adaptador de frontend conserva su prueba específica de respuesta incierta sin reintento automático.

## Reutilización trazada

Las227fuentes/archivos de producto se conservan respecto a F0604. Ninguna migración, dependencia, Program, proveedor, algoritmo o flujo de usuario cambia. Sólo se añaden prueba y runner. La DLL tiene su propio hash por reconstrucción en otra ruta; no se afirma identidad binaria con candidatos antiguos.

El núcleo de autenticación/enrolamiento coincide con C10 según el contraste F0404. La política y sus pruebas mantienen los hashes del29.10. La pantalla actual ya incluye recuperación, por lo que su pin no coincide con el27.10: se contrasta con `punto3/review/COMPARACION-FUENTES-FINAL.json` y su `MFA-EDGE.json`, además de Node actual. No se presenta un manifiesto antiguo como vigente.

Se reutilizan las pruebas históricas de GUI EN/DE/ES, C10 HTTPS/enrolamiento/postboot, y el positivo sintético posterior de D11. El smoke inicial D11 falló al encontrar el MFA personal activado; se conserva como fallo y no se cuenta como ese positivo. Los recibos duplicados de D11 no son dos ejecuciones.

## Fallos de preparación preservados

1. El primer runner omitió owner.pgpass: la comprobación SQL de bootstrap no pudo autenticar. Se corrigió sólo el entorno del laboratorio.
2. El siguiente intento llegó a la prueba pero su comparación de preferencias ordenaba por user_id; la columna real es owner_id. Se corrigió sólo el fixture y se recompiló. El servidor conserva su hash; ambos binarios de pruebas y logs se conservan privados.
3. El primer Node aislado pasó14casos pero dos módulos no pudieron cargar esbuild, omitido al copiar node_modules. Se copiaron los dos paquetes existentes necesarios, sin instalación ni cambio de versión. La repetición completa pasó70casos.

Ninguno de estos intentos es fase roja de un defecto de producto. La cobertura nueva pasó tras corregir la preparación; los resultados finales y sus hashes se registran aparte de los intentos fallidos.

## Límites y continuidad

HTTP en memoria, cuenta/confianza Windows de laboratorio: no nuevo ensayo de TLS, navegador, servicio instalado o token efectivo. Los36fixtures históricos usan su propio esquema y rol de laboratorio; sólo los2casos nuevos prueban juntos DB46 completa, rol restringido y proveedor Windows. No se atribuye ese alcance a todos los36.

No se cambia la gracia45 ni la exención global; tampoco el MFA personal o las fechas de D/E. El testigo f0705_writes y sus permisos existen únicamente en las bases nuevas de prueba. No se amplían permisos del producto ni se incorporan sus datos al servidor.

La integración de candidata46 y aceptación instalada/productiva permanecen pendientes. Este cierre de enrolamiento no cierra custodia externa, rotación operativa, códigos completos ni recuperación de emergencia.


## Dictamen y conciliación

[Revisión distinta](review/DICTAMEN.md) con dos casos propios PASS y mismos pines. Sólo F-07.05 suma1/2:1817/84→1859/84=22,130952…/100del cierre restante. No se vuelven a puntuar F0701–04; no porcentaje global nuevo, instalación o adopción. Implementación/pruebas/revisión técnicas quedan conciliadas, integración y aceptación pendientes.


## Escaneo final

Gitleaks8.30.1, reglas intactas: una detección genérica en la línea30 del dictamen, correspondiente a una descripción de estados de versiones, no una credencial o clave. Se contrasta el archivo íntegro por SHA256, la regla/línea/match exactos y la generación aleatoria del material del fixture. [Clasificación independiente](review/CLASIFICACION-ESCANEO.md), con original intacto y sin supresiones. Se conserva el recuento bruto1 y0sin clasificar; no se afirma un escaneo bruto de cero ni ausencia universal de secretos.
