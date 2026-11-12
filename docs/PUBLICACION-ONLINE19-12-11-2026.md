# Publicación del instalador Windows Online19

12 de noviembre de2026 · repositorio privado was-car/RackClick.

La descarga nativa es un activo de Release, separado del ZIP de fuentes. El activo contiene aplicación48, servicio37 sin apphost, interfaz y catálogo revisados, manualEN/DE/ES, cargador y datosDemo50. No contiene runtime.NET/SDK, PostgreSQL, VisualC++ ni Python: el destino los descarga directamente de proveedores oficiales, con TLS normal de Windows, perfiles y hashes/tamaños fijados. Python temporal ensambla el paquete revisado sin compilar RackClick ni instalar herramientas globales.

## Identidad de la entrega

- Transporte19 revisión3: SHA256 `4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf`,12655070bytes,68miembros.
- Core04: `572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5`.
- Wrapper nativo19 reconstruido: `4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd`.
- Bundle48: `098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40`.
- Aplicación manifest: `a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112`; DLL `d9366dbe9be377d4147417fd8c51e40aaa302b82c8d3bd9b830c67d68980b909`.
- Demo50trilingüe03: `d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215`.

## Ensayo ejecutado en B

WindowsServer2025x64noDC nuevo. Adquisición real de los4archivos oficiales; Core/receta/cache/wrapper verificados. Ejecución una vez del brokerNew19oficial tras preparar el paquete; plan producido por el helper nativo del formulario. Es un ensayo automatizado de la preparación y el broker, no una afirmación de haber pulsado todos los botones de laGUI.

Cuenta estándar nueva, claves y certificados nuevos, servicio automático, HTTPS normal/esquema48, frontend exacto deA. Native retorna `setup_ready_reboot_verification_pending`/exit3: preparación válida, no aceptación final.2553comandos cargaron50clientes,17EN/17DE/16ES, con66sitios/88edificios/226salas/180racks/1563equipos/2869grupos/20665puertos/2207conexiones. Nombres y ocho colecciones contrastados porAPI; backup posterior0bajo cuenta estándar.

MFA observado disponible, política globalactiva/gracia45/exención global y activación propia disponibles; factorWascar nuevo ninguno, no modificado. No se copió seguridad deA ni se desactivó MFA. A/D/E conservadas; agente sin operaciones de encendido/apagado/snapshots.

Wascar reinició B. El servicio arrancó automáticamente bajo su cuenta estándar; HTTPS48 y el frontend exacto respondieron. La relectura por API comprobó los 50 nombres y las ocho colecciones con los mismos conteos. MFA sigue disponible y sin cambiar el factor de Wascar.

El primer comprobador automático devolvió `postboot_https_health_failed`, con salida1 a las01:09:23UTC. El proceso actual de la aplicación fue creado a las01:09:34,979UTC; no se reconstruye la historia de posibles procesos anteriores ni se atribuye por ello una causa al fallo de A. El resultado automático se conservó antes de ejecutar el verificador oficial manual, que pasó con `postboot_verified`/salida0. La tarea automática conserva su LastTaskResult1. Este defecto del verificador temprano es una observación explícita de la candidata, no un fallo reinterpretado como éxito.

## Fallos y correcciones conservados

Transporte01 sin gateway se detuvo antes de Python. Transporte02 conInternet encontró issuer ausente en Python/OpenSSL; .NETWindows validó los3proveedores. Transporte03 usa SChannel para adquirirlos y caché cerrada verificada antes de Python, que vuelve a verificar. No se desactivó TLS ni se importaron CA manuales. Stagings y transportes previos se conservan, sin adoptar o sobrescribir una instalación.

20pruebasWindowsPowerShell5.1,9Python y5focosindependientes de la corrección final pasaron; no son una regresión nueva de .NET, cuyo producto permanece exacto. Inventario/hash/licencias del transporte revisados. AvisosMIT yThirdPartyNotices del servicio separados del contrato delruntime; no se afirma habilitación para redistribuirVisualC++: ese ejecutable viene del proveedor al destino.

## Límites

Restore48 y cambio automático de red48 siguen deshabilitados. Demo50 es opcional y debe cargarse sólo una vez sobre el servidor vacío, conHTTPS/CSRF/MFA/permisos y sin reintentos automáticos ante incertidumbre. El ejemplo conserva su fuente43 y cobertura868revisiones/506modelos; catálogo actual884revisiones/877modelos no equivale a884modelos probados en esta base.

La instalación no clonaW02-A: identidadWindows, direcciones, usuarios, contraseñas, certificados y claves son nuevos. La equivalencia es de producto y datos sintéticos. La demostración de10clientes desde fuentes permanece separada, conHTTPloopback yMFA desactivado.

Artefactos/logs privados bajo.localno se versionan; tampoco secretos,DB/dumps,claves/sobres,CAparticular,binlogs o sesiones. Código ydatos publicados no reciben una licencia abierta nueva. Repositorio privado, sin despliegue automático ni aceptación productiva final. Índice26,63/100 del cierre restante sin cambios; no nuevo porcentaje global por empaquetado/publicación.

Condiciones del proveedor .NET: [Microsoft .NET Library](https://dotnet.microsoft.com/en-us/dotnet_library_license.htm). El enlace informativo de gratuidad del manual no sustituye este contrato ni los avisos incluidos en el archivo adquirido. El HTML del activo ensayado se conserva byte a byte.
