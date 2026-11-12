# Descarga e instalación desde GitHub equivalente a W02-A


## Estado vigente: Online19 ensayada en B

La aclaración inicial y su tabla de pendientes se conservan debajo como historia. Online19 revisión3 ya fue preparada y ensayada en B nueva: descargas oficiales con TLS normal de Windows, cuentas y claves nuevas, servicio estándar automático, HTTPS48, carga única de los 50 clientes y backup posterior. Wascar reinició B; servicio y datos persistieron y el verificador oficial manual devolvió `postboot_verified`. El comprobador automático temprano devolvió `postboot_https_health_failed`; ambos resultados se conservan, sin convertir el primero en éxito.

PUB-02 se corrigió en19 con MIT y avisos de terceros del servicio separados del contrato del runtime. Se omitió el apphost sin uso. Wascar no tiene licencia VisualStudio: el ZIP online no aloja VisualC++, runtime/SDK, PostgreSQL o Python; el destino los adquiere directamente de sus proveedores, verificando tamaño y hash. Las entregas18 y anteriores permanecen intactas y no se publican como instaladores completos.

ZIP19 revisión3: `4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf`,12655070bytes/68miembros. Es una candidata de pruebas; Restore48, cambio automático de red48 y aceptación productiva final siguen pendientes. La publicación se cierra con el recibo remoto de la Release, no por este texto. Ver [estado y límites de Online19](PUBLICACION-ONLINE19-12-11-2026.md).

12.11.2026 · Aclaración de Wascar. Este es el objetivo de entrega; la publicación de fuentes `65156d4c5aca4c3842d9aa78bac052f9a5b0c745` todavía no lo satisface.

## Lo que debe recibir quien descargue

En el repositorio privado debe aparecer una descarga de instalación Windows completa, identificada por edición y SHA256, y su manual EN/DE/ES. No debe requerir compilar RackClick ni instalar SDK, Node o Python para usar el producto. La demo de diez clientes desde fuentes queda como opción para desarrolladores, no como recorrido principal de instalación.

Se continúa el instalador nativo existente; no se crea otra aplicación, otro piloto ni una imagen clonada de la VM. El ZIP se entrega como activo de una Release privada, no como archivo Git normal ni como copia de las carpetas privadas del equipo de desarrollo.

## Qué significa «como W02-A»

- Misma aplicación48 e interfaz revisada, vistas de rack y conexiones, catálogo de884 revisiones/877 modelos y EN/DE/ES.
- PostgreSQL privado y cuenta Windows estándar propios, servicio automático, HTTPS con validación normal y acceso administrativo al panel instalado.
- MFA disponible en el dashboard y en el login, con la política vigente de45 días y exención del administrador global. Cada persona debe enrolar su propio autenticador; nunca se copian factores de A.
- Recorrido completo de demostración con50 empresas ficticias:17 nombres ingleses,17 alemanes y16 españoles;66 sitios,88 edificios,226 salas,180 racks,1563 equipos,2869 grupos de puertos,20665 puertos y2207 conexiones.2553 comandos y comparación de las ocho colecciones.
- Backup posterior a la carga, restauración de la lectura tras reinicio y manual que comienza por dónde crear la carpeta y cómo abrir PowerShell.

Direcciones IP, nombre del servidor, UUID, cuentas generadas, contraseñas, certificados y claves deben pertenecer al nuevo servidor. No se copian las credenciales, certificados ni bases privadas de A. La equivalencia es de producto y datos sintéticos; no de identidad de Windows o de seguridad.

Los datos Demo50 permanecen opcionales para quien vaya a usar el servidor con datos propios. Para reproducir W02-A, el manual ofrecerá explícitamente el recorrido completo con los50, sin presentar que se cargaron si el operador aún no lo ejecutó. La fuente Demo50 continúa en43/cobertura868, conservando su destino48 explícito; no acredita todas las884 revisiones en racks.

## Situación comprobada

- Hay una candidata local completa18 de144203012 bytes y73 miembros, SHA256 `512fcaf6aa255e6ff6ae9610daa722f8b9d135972d33d5a249b9d42ad90625ed`. Contiene aplicación, dependencias, asistente, manual y Demo50/cargador.
- A funciona con aplicación48,50 clientes, backup y comprobación oficial manual después del reinicio. Se instaló con17 más finalización acotada revisada; **no es un ensayo completo desde cero de18**.
- La primera verificación automática de HTTPS después del arranque falló. No se convierte en éxito por la verificación manual posterior; queda como observación que debe reproducirse o corregirse en el ensayo nuevo.
- La publicación GitHub actual es de fuentes y datos, sin activo binario de instalación. Los enlaces `.local` de entregas históricas no son descargas del repositorio.
- La medición directa de18 confirma que `service-host-NOTICE.txt` aún atribuye MIT al servicio y remite a `dotnet-LICENSE.txt`, que contiene Microsoft .NET Library. Es la incoherencia PUB-02 ya registrada; falta corregir el empaquetado en una edición nueva.
- El bundle sigue transportando Visual C++ Redistributable. Antes de distribuirlo hay que acreditar las condiciones de Microsoft o preparar una adquisición directa desde Microsoft por el propio instalador. No basta con que GitHub sea privado.

## Comprobaciones para ofrecer la descarga

| Orden | Resultado requerido | Estado12.11 |
|---|---|---|
|1|Fijar este contrato de equivalencia, sin confundirlo con demo10 ni con clonar A.|Registrado por esta aclaración.|
|2|Cerrar referencias/textos de licencias de la entrega y decidir adquisición de VC++; conservar versiones fijadas.|Medición18 y documentación oficial contrastadas; condiciones y dato de Visual Studio pendientes.|
|3|Construir una nueva edición cuando cambie cualquier miembro; manifiestos, hashes, manuales y pruebas negativas coherentes.|18 se conserva intacta. No se etiqueta otra edición antes de construirla.|
|4|Ensayar el ZIP final completo en otra VM Windows Server2025 limpia, sin DC, preservando A/D/E.|Sólo A está encendida; se pidió a Wascar otra VM limpia.|
|5|Comprobar servicio/HTTPS/MFA, cargar50, comparar datos completos y producir backup posterior.|Resultados de A reutilizables como referencia, no como ensayo nuevo del paquete final.|
|6|Wascar reinicia; comprobar arranque automático y datos, con separación del verificador automático y el manual.|Pendiente en la VM nueva.|
|7|Revisión independiente del activo exacto; escaneo; publicar Release privada con ZIP+SHA256+manual y enlace principal enREADME EN/DE/ES.|Pendiente. No anunciar descarga disponible antes de subir y verificar el activo.|

## Investigación y decisiones

Se reutilizan la cadena17/18, sus pruebas48, Demo50trilingüe03, el ensayo de A y `REVISION-PUBLICACION-30-10-2026.md`. No se reimplementa el producto ni se cambian dependencias para cerrar la entrega.

Referencias oficiales consultadas12.11.2026: [redistribución de Visual C++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170) y [Microsoft.Extensions.Hosting.WindowsServices10.0.12](https://www.nuget.org/packages/Microsoft.Extensions.Hosting.WindowsServices/10.0.12). La primera exige revisar la habilitación y términos de redistribución; la segunda identifica MIT para el paquete, sin sustituir el contrato binario del runtime. Se examina el ZIP real, no sólo el código de la rama.

El encendido, snapshots y reinicio manual de la VM siguen a cargo de Wascar. No se opera A/D/E para preparar esta descarga. Restore48 y cambio automático de red48 siguen deshabilitados; no se amplían por anunciar instalación New48. Repositorio privado y sin despliegue automático.

Este trabajo se concilia con la entrega/paquete y sus condiciones existentes; no crea pesos ni acredita por inercia el ledger. Se mantiene **26,63/100 del cierre restante**, sin porcentaje global nuevo.
