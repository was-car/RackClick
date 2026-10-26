# Revisión independiente MFA-L2c

**Dictamen: no cerrar todavía L2c. Un P2 de propiedad del staging reproducido en publicación y limpieza.** El recorrido normal funciona, pero un nombre de carpeta no acredita que siga siendo el objeto creado/validado por esta llamada. L2b y los controles anteriores siguen aprobados.

## Qué ejecutó Codex

Investigación antes del auxiliar: entrega/implementación/tests/D2 y documentación oficial de creación/renombrado. Se reutilizan las revisiones anteriores. [Nota previa](../evidence/s1-20261026/mfa-l2c-codex/INVESTIGACION-PREVIA.md).

Se congelaron **285 fuentes**, se contrastaron los **seis hashes** de Claude y se realizó un único build privado SDK **10.0.401**, **0 errores/0 advertencias**. Resultado:

| Grupo | Resultado nuevo de Codex |
|---|---|
| Focos actuales de escritor/proveedor/anillo | **44 PASS**, sin omisiones |
| Tres negativos históricos, mismo código | **3 PASS** |
| Dos negativos propios de ciclo de vida | **2 FAIL** |

21,313 s, cinco binlogs privados. Sin PG, HTTP, cuentas, servicios, VM/QA o claves reales. Las fuentes compartidas/congeladas conservaron sus hashes. La DLL del árbol de trabajo sólo sirve para revisión; no es una distribución o candidata del instalador.

[Resultados y mensajes](../evidence/s1-20261026/mfa-l2c-codex/RESULTADOS-EJECUTADOS.json), [fuentes](../evidence/s1-20261026/mfa-l2c-codex/FUENTES-ENTREGADAS.json), [negativos](../evidence/s1-20261026/mfa-l2c-codex/MfaL2cLifecycleReviewTests.cs), [cierre](../evidence/s1-20261026/mfa-l2c-codex/CIERRE.md). La mutación y los 44 PASS de Claude siguen siendo su evidencia; no se presentan como repetición propia de esa mutación.

## MFA-L2C-01 · P2 · se confunde ruta con propiedad del objeto

`Publish` mueve la ruta del staging, y `Discard`/`RemoveQuietly` borran esa ruta recursivamente, sin comprobar que sea el mismo directorio que se creó y validó.

Los dos negativos usan el punto existente `beforePublish`: renombrar el staging válido a una ubicación reservada del laboratorio y crear **otro directorio** en su ruta anterior con un centinela. Todo sucede dentro de una raíz nueva de fixture, sin datos externos.

1. **Fallo de publicación:** el callback lanza IOException después de la sustitución. El escritor informa `PublishFailed`, pero `Discard` borra el nuevo directorio y su centinela. Mensaje observado: `Cleanup deleted content from a different directory at the old staging path`.
2. **Publicación normal:** el callback termina. `Directory.Move` publica el directorio sustituto y la llamada devuelve normalmente, aunque ese objeto no contiene el almacén validado. El negativo falla con `No exception was thrown`.

Es un problema de robustez/preservación ante concurrencia o intervención durante el ciclo de vida. No demuestra un atacante no confiable, acceso con segundo token o exfiltración. El requisito de no borrar/publicar contenido ajeno a la llamada sigue siendo aplicable al componente de creación.

**Corrección requerida:** acreditar creación exclusiva/identidad de los objetos que pertenecen a la llamada, mantener esa acreditación al publicar y retirar sólo objetos identificados como propios. Ante identidad incierta, preservar el objeto encontrado e informar fallo/residuo. No resolverlo sobrescribiendo, buscando y borrando por prefijo o reparando silenciosamente un almacén existente.

`CreateOwnFolder` tiene además el patrón `Exists` → `CreateDirectory` → marcar como propio/cambiar ACL. [Microsoft documenta que CreateDirectory también devuelve éxito si ya existía](https://learn.microsoft.com/en-us/dotnet/api/system.io.directory.createdirectory?view=net-10.0). La carrera de creación es un riesgo de la misma regla de propiedad identificado por fuente; **no se reprodujo independientemente**. Corregir la atribución de propiedad sin asumir que esa llamada creó el objeto.

## Decisiones y alcance que se conservan

- DPAPI duplicado es aceptable en este componente aislado; no abrir un refactor compartido sólo para consolidar firmas. Generación, protección y borrado normal de la clave en memoria no presentan otro bloqueo material en la lectura revisada.
- `Directory.Move` sigue rechazando destinos existentes en los casos probados. [Su contrato](https://learn.microsoft.com/en-us/dotnet/api/system.io.directory.move?view=net-10.0) no basta para atribuirle garantías adicionales de atomicidad/durabilidad; esas limitaciones y el corte de proceso siguen declarados, sin nuevos fallos inventados.
- Se acepta no fijar la clase de error del caso de creador sin derechos mientras se comprueban las salidas efectivas. No se cambia la cuenta real, propietario productivo o privilegios para hacer pasar fixtures.
- Las tres adendas L2b se conservan. No se aplican etiquetas de integridad ni se cambia el servicio a SYSTEM.
- El subrevisor `mfa_l2_windows_review`, distinto del implementador, inspeccionó el escritor y tests completos y fuentes oficiales; confirmó el foco de propiedad por fuente. No compiló ni ejecutó pruebas: las reproducciones anteriores corresponden a Codex.

No se cierra custodia completa ni se conecta el proveedor. Sin código de producto editado por el revisor, dependencias, SQL, instaladores, VM/QA, commits/push o adopción. **Cierre pendiente 7,63/100**, sin crédito nuevo ni porcentaje global recalculado.
