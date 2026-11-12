# Instalador online19 equivalente a W02-A

> Ejecución autorizada por Wascar: continuar en esta sesión, reutilizando el instalador existente; revisión independiente al estabilizar. No crear commits ni publicar binarios de terceros por inercia.

**Objetivo:** descarga privada desde GitHub que instale aplicación48/HTTPS/servicio/MFA y permita cargar los50 clientes, sin compilación ni herramientas instaladas manualmente.

**Arquitectura:** transportar aplicación propia, dependencias de paquetes redistribuibles con sus avisos y fuentes del ensamblador. El destino adquiere directamente Python embebido3.12.3 temporal, SDK10.0.401 como archivo fuente de runtime10.0.12, PostgreSQL17.11-4 y VC++14.51 desde proveedores oficiales, con pins. Se reutilizan los productores deterministas revisados para reconstruir el bundle48 exacto y un wrapper19 nuevo; no se compila producto ni se instala SDK/Python/Node enWindows.

**Tecnologías:** PowerShell5.1, Python3.12.3/zlib1.3.1, productores ZIP existentes, aplicación y servicio ya revisados. **Contrato:** [equivalenciaW02-A](../../ENTREGA-GITHUB-EQUIVALENTE-W02A.md).

## Restricciones

- Sólo VM B: WindowsServer2025 noDC, nueva y sin RackClick. A/D/E intactas; encendido/snapshots/reinicio a cargo de Wascar.
- Wascar no tiene licencia VisualStudio: no subir CRT al Release. Tampoco se alojan copias del runtime, PostgreSQL o Python.
- No nuevas versiones: preservar DLLaplicación48, appmanifest `a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112`, bundle `098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40`, servicioDLL `130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61` y Demo50 `d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215`.
- El servicio usa `dotnet.exe …WindowsService.dll`: omitir en19 su apphost.EXE no utilizado; conservar37 archivos restantes y pins.01–18 históricos intactos.
- Corregir PUB02: MIT1115B y TPN78041B exactos del servicio separados del contrato del runtime. Conservar Npgsql/licenciaPostgreSQL, OtpMIT y avisosReact/fuentes.
- Descargas HTTPS con host cerrado, tamaño/hash, sin salto a latest ni reintento automático de instalación. Fallar antes de instalar si cualquier pin no coincide.
- Workspace nuevo y privado desde creación; no sobrescribir ni limpiar instalaciones existentes. Credenciales sólo en el mecanismo privado nativo.
- MFA/gracia45/exención global, SQL mínimo, guardiasRestore48 yred48 se conservan. Métrica26,63 sin cambio por empaquetar.

## Foco de revisión

1. Descarga alterada, redirección ajena, caída/offline: ningún ejecutable sin verificar.
2. ZIP con ruta insegura, duplicados, reparse o extras: rechazo; no escritura fuera del workspace.
3. Coincidencia de todas las fuentes/datos con A; ninguna dependencia restringida dentro del activoGitHub.
4. Inicio sin privilegio/DC/servidor existente: rechazo antes de crear instalación o pedir secretos.
5. Verificador de arranque automático y manual separados; no convertir fallos previos en éxitos.

## Tarea1 · Transporte verificable y montaje determinista

Crear `tools/build_online_installer19.py`, `tools/online-install/assemble.py`, `tools/tests/test_online_installer19.py` y lock `development/online-installer19.sources.json`. Adaptar productores para19 en sus ramas cerradas y avisos completos, sin ampliar esquemas. Entradas: wrapper18 validado, app79, Demo03, productores/fuentes pinados y archivos oficiales de caché para ensayos. Salida: core propio con inventario, dependencias conURL/tamaño/digest y montaje exclusivo.37archivos servicio, sin apphost.

- [x] Rojo de nuevos tests: falta módulo/API; luego negativos de pin/ZIP/rutas/extras, sin output.
- [x] Implementar `collect(...)`, `verify_core(root)` y `assemble(root, work, dependencies)`; no instalar.
- [x] Reconstruir con Pythonembed oficial; bundle098 exacto y wrapper19 determinista en dos montajes; DLL/GUI/Demo conservadas.

## Tarea2 · Entrada Windows y paquete descargable

Crear `tools/windows/online-install/Install-RackClickOnline.ps1`, CMD y manual. Check sólo lectura. Install valida Windows/noDC/nuevacarpeta, confirma adquisición directa, crea staging privado exclusivo, descarga/verifica Python, ejecuta montaje con entorno hijo aislado, comprueba wrapper esperado y delega en INICIAR nativo. Pin del core y del wrapper generado en el lanzador; SHA externo del ZIP completo. Sin tokensGitHub en el servidor: el operador descarga el ZIP autenticado desde navegador.

- [x] Tests WinPS5.1: parser/ASCII oBOM, rechazo previo a escritura, ZIP/tamaño/hash, host, entorno y lanzamiento condicionado.
- [x] Negativos de origen alterado y archivos extras; preservar copia/fallos sin reintentos de instalación.
- [x] Construir activo y escanear inventario completo; revisión independiente antes de ejecutar Install en B.

## Tarea3 · Ensayo B y entrega GitHub

- [x] Validar B porVMX/UUID/OS/Tools/limpieza; sin restaurar snapshots automáticamente.
- [ ] Ejecutar el activo exacto una vez, con adquisición real, instalación nativa, cuentas nuevas, HTTPS/MFA y backup. No finalizadores ocultos para declarar coldNew exitoso.
- [ ] Cargar50 una vez; verificar8colecciones/nombres/2553comandos y backup posterior.
- [ ] Pedir a Wascar reinicio de B; verificar servicio y persistencia, conservando ambos resultados de postboot.
- [ ] Revisión independiente del paquete y recibos, licencias/acquisición/ausencia de terceros restringidos, escaneo; publicar Release privada de prueba con ZIP/SHA/manual EN/DE/ES y enlaces principales enREADME. Sin adopción productiva ni despliegue automático.
- [ ] Actualizar continuidad/changelog/evidencias/QA real y recibo remoto; conservar fallos y punto de retorno.

12.11 · Transporte03 revisado `4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf`; Prepare03realB completado0, wrapper19exacto4bb169ad. DependenciasadquiridasporHTTPSnormalWindows; Pythonrecibecachéprivada completa yrevalida. New19brokeroficialejecutado unavez, preparandoPG. No requierecompilarproducto. Fallos01sinInternet/02OpenSSLpreservados, no instalacionessobrepuestas. B usa178.125, A/D/Eintactos. ReinicioWascar aún pendiente.
