# Errores de proyectos temporales en VS Code

21.10.2026. Corrección de desarrollo en LEAO; no modifica el servidor ni los datos.

## Qué estaba ocurriendo

La captura muestra ocho diagnósticos asociados a una solución sintética de C# Dev Kit en `workspaceStorage`. La inspección de sus referencias confirmó cuatro proyectos de un snapshot del escáner, bajo `.local/security/PRIVADOS.local/.../tracked-*`, además de proyectos reales. El snapshot ya no contiene esos proyectos, pero la solución del editor conservaba las referencias.

El `TargetFramework` real se define en `development/server/Directory.Build.props`, como `net10.0`. Una copia de `.csproj` sin ese contexto puede producir NETSDK1013; una referencia al archivo ya retirado produce MSB3202/MSB4025. Se reprodujo NETSDK1013 con una copia aislada del proyecto de dominio, sin modificar el original.

Había además un problema distinto: el ejecutable global `C:\Program Files\dotnet\dotnet.exe` sólo encontraba SDK10.0.402, mientras el proyecto fija10.0.401. Antes del arreglo, `--version` desde `development/server` fallaba. El SDK401 ya estaba instalado localmente.

## Corrección aplicada

- `.vscode/settings.json` selecciona `development/server/RackClick.sln` como solución predeterminada. Añade exclusiones de archivos, búsqueda y observación para `.local` y `.artifacts`. Las exclusiones son complementarias; no se presume que eliminen por sí solas proyectos cargados en memoria.
- Nuevo `global.json` en la raíz y rutas relativas `sdk.paths` en los dos existentes (`development/server` y `development/windows-service`) permiten encontrar `.local/dotnet-10.0.401`. `$host$` permite usar una instalación del mismo SDK en otro equipo o CI. Se conservan versión10.0.401, `rollForward:disable` y `allowPrerelease:false`.
- No se eliminan informes, backups, fixtures ni `workspaceStorage`. No se cambia el runtime interno de las extensiones ni se actualizan SDK/paquetes para ocultar el error.

Microsoft documenta [rutas de búsqueda de SDK relativas a global.json](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json#paths), disponibles en .NET10. La solución predeterminada corresponde al [gestor de proyectos de C#](https://code.visualstudio.com/docs/csharp/project-management).

## Qué hacer ahora en el editor

1. En VS Code, termina o guarda la edición que tengas pendiente.
2. Pulsa **Ctrl+Shift+P**, escribe **Developer: Reload Window** y pulsa Enter. No hace falta reiniciar Windows ni el servidor.
3. Espera a que C# termine de cargar y vuelve a la pestaña **Problems** de la parte inferior.
4. Si aún aparece la solución sintética: pulsa **Ctrl+Shift+P**, ejecuta **.NET: Open Solution** y elige `development/server/RackClick.sln`. Después ejecuta **.NET: Restart Language Server** desde la misma paleta.
5. Si persiste algún error, comprueba su ruta completa. Los proyectos reales deben estar bajo `development/server/src` o `development/server/tests`, no en `.local`. Conserva el mensaje nuevo para corregir su causa; no borres configuraciones ni suprimas diagnósticos del compilador.

La solución real contiene los tres proyectos originales. El proyecto adicional `RackClick.Quality.Tests` continúa fuera de ella y se ejecuta por su ruta explícita; esta corrección no cambia ese alcance.

## Verificación y límites

Windows/LEAO: once comprobaciones correctas, incluidas dos negativas esperadas; restore locked y compilación Release correctos, sin avisos ni errores. Evaluación nativa de los cuatro `.csproj` reales: `net10.0`. Se comprobó también que, sin SDK401 local y con402 en el host, falle en lugar de cambiar de versión. Siete binlogs conservados en privado bajo `.local`, sin distribuir variables de entorno ni archivos importados.

Revisión independiente: con variables de SDK/MSBuild realmente eliminadas y sin rutas `.local` en PATH, el host global selecciona401 en las tres ubicaciones y evalúa los cuatro proyectos correctamente. No se ha medido el contador de Problems después de recargar la ventana de Wascar; no se afirma que la interfaz ya muestre cero.

[Evidencia y comandos ejecutados](../evidence/s1-20261021/consola-vscode/CIERRE.md). Avance global aproximado78%, sin aumento por este arreglo de herramientas. MFA para todos y los demás trabajos pendientes conservan su estado.
