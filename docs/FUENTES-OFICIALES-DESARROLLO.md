# Fuentes oficiales para desarrollar RackClick

30.10.2026 · Guía compartida para Codex, Claude y colaboradores. Complementa la [regla de investigar antes de implementar](INVESTIGAR-ANTES-DE-IMPLEMENTAR.md) y la [hoja de ruta maestra](HOJA-DE-RUTA-MAESTRA.md). Consultar estas referencias forma parte del trabajo autorizado; encontrarlas no instala ni adopta componentes.

## Qué ofrecen estas fuentes

No existe una base de datos universal que contenga todo JavaScript, SQL, Windows y sus soluciones. Hay referencias de lenguaje, API, frameworks, bibliotecas y ejemplos. La referencia explica el contrato; el ejemplo ayuda a aplicarlo; las pruebas en RackClick demuestran si la adaptación funciona.

JavaScript del lenguaje no incluye por sí mismo el DOM ni todas las API del navegador. SQL tampoco es un dialecto único: PostgreSQL y T-SQL de SQL Server difieren en funciones, tipos, bloqueos y administración. Para nuestra base se consulta PostgreSQL 17; un tutorial de Microsoft sobre SQL Server no sustituye ese manual.

## Dónde buscar según la necesidad

| Necesidad | Fuente primaria | Qué buscar y para qué sirve aquí |
|---|---|---|
| Lenguaje JavaScript | [MDN JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript) | Objetos, arrays, módulos, promesas y errores. Resolver transformaciones de inventario o flujos asíncronos sin añadir una biblioteca por defecto. |
| Navegador, DOM y archivos | [MDN Web APIs](https://developer.mozilla.org/en-US/docs/Web/API) | Fetch, eventos, File/Blob, SVG y compatibilidad. Consultar permisos y soporte real antes de implementar importación, descarga o interacción con racks. |
| Semántica exacta del lenguaje | [Especificación ECMAScript](https://tc39.es/ecma262/) | Aclarar comportamiento del lenguaje. Es una especificación viva: una función descrita allí puede no estar disponible en los navegadores o Node fijados. MDN suele ser más práctico para empezar. |
| Componentes de interfaz | [React Learn](https://react.dev/learn) | Estado, eventos, formularios, listas e identidad de componentes. Adaptar patrones a la GUI RC9 existente, sin cambiar su diseño ni actualizar React por seguir un tutorial reciente. |
| Tipos y contratos de frontend | [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html) | Tipos, narrowing, módulos y funciones. Referencia útil para contratos o lectura de proyectos externos; no implica introducir TypeScript como dependencia del frontend actual. |
| Herramientas de construcción y pruebas | [Node.js Learn](https://nodejs.org/learn/getting-started/introduction-to-nodejs) y [API de Node 24](https://nodejs.org/docs/latest-v24.x/api/) | Archivos, procesos, módulos, asincronía y test runner. Comprobar cada API contra la versión local fijada; la URL latest-v24.x cambia dentro de esa rama. |
| Backend HTTP | [ASP.NET Core 10](https://learn.microsoft.com/en-us/aspnet/core/?view=aspnetcore-10.0) | Minimal APIs, middleware, configuración, cookies, autorización y pruebas de integración. Aprovechar patrones concretos manteniendo el contrato de rutas/DTO y los controles existentes. |
| API de .NET | [Microsoft Learn .NET](https://learn.microsoft.com/en-us/dotnet/) | Buscar la clase o método exactos y seleccionar .NET 10. Contrastar firma, plataforma y excepciones; una página puede mezclar versiones y paquetes preliminares. |
| Operación en PowerShell | [Referencia de directivas de Windows PowerShell 5.1](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1) | Entender ámbitos y precedencia de ejecución de scripts. Para cada cmdlet usar su documentación 5.1: no copiar sintaxis exclusiva de PowerShell 7 en los instaladores. La directiva de ejecución no sustituye autorización, ACL ni verificación de integridad. |
| Windows nativo | [Índice Windows API](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-api-list) | Localizar documentación de procesos, tokens, archivos, ACL y servicios. En P/Invoke comprobar estructura, tamaños, derechos, errores y versiones mínimas en la página de la función concreta. |
| SQL y administración | [Manual PostgreSQL 17](https://www.postgresql.org/docs/17/) | Tipos, constraints, consultas, roles, índices y planes. Es la referencia de nuestra base, evitando copiar SQL de otro motor. |
| Concurrencia y recuperación | [Control de concurrencia PostgreSQL 17](https://www.postgresql.org/docs/17/mvcc.html) y [backup/restore](https://www.postgresql.org/docs/17/backup.html) | Elegir aislamiento y bloqueos; entender dumps, copias físicas y recuperación. Validar después conflictos, rollback y restauración en una base independiente. |
| Acceso .NET a PostgreSQL | [Npgsql: uso básico](https://www.npgsql.org/doc/basic-usage.html) | DataSource, pooling, comandos parametrizados, async y transacciones. Mantener Npgsql directo; no introducir EF Core por seguir un ejemplo que lo utilice. |

Las fuentes en inglés suelen tener la referencia más completa. Se pueden usar traducciones oficiales ES/DE/FR para aprender, contrastando que correspondan al mismo producto y versión. Un buscador, un vídeo o una respuesta de foro orientan hacia estas fuentes; por sí solos no fijan el contrato técnico.

## Ejemplos originales en GitHub

- [dotnet/AspNetCore.Docs](https://github.com/dotnet/AspNetCore.Docs): ejemplos que acompañan a la documentación ASP.NET Core. Su [LICENSE-CODE](https://github.com/dotnet/AspNetCore.Docs/blob/main/LICENSE-CODE) es MIT. Antes de reutilizar un fragmento, localizar su carpeta, versión de framework, dependencias y avisos propios. Los tutoriales que usan EF Core u otra base aportan patrones HTTP, no autorización para sustituir Npgsql/PostgreSQL.
- [dotnet/samples](https://github.com/dotnet/samples): ejemplos oficiales de .NET y C#. Distinguir [LICENSE](https://github.com/dotnet/samples/blob/main/LICENSE) de documentación, CC BY 4.0, y [LICENSE-CODE](https://github.com/dotnet/samples/blob/main/LICENSE-CODE), MIT para código. Revisar además avisos particulares de la carpeta y las dependencias que incorpore.

Un repositorio público no convierte todo su contenido en material libre de condiciones. Código, texto, imágenes, marcas y dependencias pueden tener permisos diferentes. Registrar URL y commit concretos, archivo usado, licencia y atribución exigida antes de copiar; conservar los avisos aplicables. En esta guía sólo se enlazan referencias y se resumen criterios: no se incorpora código externo.

## Cómo aplicar la investigación sin perder tiempo

1. Elegir un resultado de la hoja de ruta y localizar el comportamiento, código y pruebas ya existentes. Reutilizar una investigación anterior si sigue siendo válida.
2. Buscar la API concreta en la documentación oficial y con la versión correcta. Por ejemplo: «PostgreSQL 17 row-level locks», «Npgsql parameters transactions» o «ASP.NET Core 10 integration tests».
3. Si falta un patrón, revisar uno o dos ejemplos originales. Comparar reutilizar lo existente, adaptar el ejemplo o escribir la parte propia. Parar cuando la información permita decidir y probar.
4. Dejar una nota breve en la evidencia: problema, fuentes/fecha/versión o commit, licencia/dependencias, decisión y prueba necesaria. No hacen falta descargas masivas ni un documento nuevo por cada ajuste.
5. Adaptar al contrato de RackClick: autorización y ámbitos en servidor; valores SQL parametrizados; UUID y grupo/tipo para puertos; commit antes de confirmar guardado; conflictos, idempotencia y auditoría. Mantener diseño RC9 e idiomas. Los ejemplos con datos o contraseñas de demostración no se trasladan a configuración real.
6. Ejecutar el negativo afectado y la verificación pertinente, conservar resultado/diff y obtener revisión de otra persona. Una muestra que compila no demuestra persistencia, permisos o concurrencia en nuestro producto.

## Versiones del proyecto y límites

La consulta web no modifica los pins. El [global.json del servidor](../development/server/global.json) fija SDK 10.0.401 con rollForward desactivado; el [proyecto servidor](../development/server/src/RackClick.Server/RackClick.Server.csproj) declara Npgsql 10.0.3 y Otp.NET 1.4.1. El [package.json de frontend](../development/frontend/package.json) fija esbuild 0.25.10. PostgreSQL sigue en la rama 17. Para runtime, Node y artefactos de instalación se contrasta el manifiesto de la candidata concreta antes de construir.

Las páginas vivas pueden mostrar versiones distintas: durante esta consulta React mostraba 19.3, Node latest-v24.x mostraba 24.22.2 y ECMAScript anunciaba la edición viva 2027. Eso no cambia lo instalado ni autoriza actualizaciones. Si una API depende de otra versión, registrar la incompatibilidad y resolverla explícitamente.

Esta entrega es documentación de referencia. No ejecuta ejemplos externos, instala dependencias, altera datos/QA/VM ni acredita funciones del producto. El manual de instalación de RackClick y la selección de archivos para GitHub siguen sus propios procedimientos y evidencias.
