# Revisión independiente · F-02.01

02.11.2026. Revisor `/root/f01_classification_review`, perfil de seguridad, distinto del implementador. Registro por el coordinador del dictamen devuelto.

**Favorable para desarrollo parcial de F-02.01; sin acreditar puntos.** Falta el positivo bajo SID efectivo del servicio y una instancia real, además del provisionamiento pendiente. Las pruebas con Users SID y confianza de laboratorio no sustituyen ese requisito. No quedan hallazgos de código abiertos tras la corrección indicada abajo.

## Comprobaciones propias del revisor

Lectura de `ProtectForProvisioning`, `Open`, `Entropy`, `ValidateConnection`, `Transform`; `Enabled`, `Resolve`, `Read` y la guardia de mantenimiento. Contraste de fuentes con manifiesto de cuatro SHA256 y diff contra snapshot anterior: `Program.cs` sólo cambia en dos bloques, separación CLI y resolución SQL. La ruta habilitada rechaza texto plano y no regenera archivos. El lector MFA se reutiliza sin editar.

Hallazgo de gravedad baja resuelto: UTF-16 sin pareja antes escapaba como `EncoderFallbackException`; ahora devuelve `sql_secret_connection_invalid`, sin excepción interna. El coordinador añadió negativo y reprodujo fallo antes de corregir. El revisor comprobó la corrección, test y evidencia saneada del rojo/verde, sin ejecutar esa prueba por su cuenta.

| Fuente final | SHA256 verificado |
|---|---|
| WindowsSqlSecret.cs | `fdc6624e1c3719082b7ac8f8470f9896615a9f85a8e850903b8dd8486ceda9df` |
| SqlSecretConnection.cs | `571e251756ca9cfe0a38040c55e1dfefbde2baeecf3ccab09e69469e2c3e6fcd` |
| Program.cs | `e2ee79c718ec1b6198e7a3fac5bc35841c627a8a6c13bb4e72c68fc3c530e028` |
| SqlSecretConnectionTests.cs | `9a21f03bb6e1e49b3add69787df446db34e847d857ae3acf1a77298ce3882c6d` |

Leídos investigación, contrato, ficha y reportes públicos: build final 0 errores/0 advertencias, focal 39/39 y regresión afectada 132/132, sin omisiones. **Son ejecuciones del coordinador; el revisor no ejecutó compilaciones, suites, PostgreSQL ni probes propios.** No abrió los registros privados, credenciales o contenido de D.

Los límites de LocalMachine y la necesidad de ACL están documentados correctamente. Fuente primaria consultada por el revisor: [Microsoft DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata). Protección ligada al equipo; no exclusiva del SID sin la ACL, no portable ni defensa frente a administradores/SYSTEM.

`RuntimeUser` liga el nombre esperado, no demuestra los privilegios de un servicio actual. Falta comprobar la identidad efectiva y completar provisionamiento sin texto claro; no declarar el runtime instalado o los paquetes 11 cifrados.

Sin ediciones, acceso a privados, VM/D, DB existente, autenticación o QA. Compatible con registrar **únicamente F-02.01 pending → in_progress**, crédito 0 e índice 1849/168 = 11,01/100. Los demás checkpoints, pesos, criterios y estados no se cambian ni se acepta el cierre completo de F-02.
