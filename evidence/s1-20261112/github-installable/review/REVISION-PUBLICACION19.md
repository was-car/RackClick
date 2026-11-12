# Revisión independiente de publicación · Online19

12.11.2026 · Revisión de release separada de implementación y seguridad. Worktree `.local/github-installable-20261112/worktree`, base `65156d4c5aca4c3842d9aa78bac052f9a5b0c745`. Escritura pública limitada a este informe; probes propios en `.local/github-installable-20261112/review-publication19/`.

## Dictamen

**Favorable técnicamente al activo Online19 revisión3 y a las fuentes revisadas.** La publicación privada queda condicionada a conciliar la documentación vigente con los recibos posteriores al reinicio de B y a completar el escaneo, manifiestos, índice y contraste remoto finales. No quedan hallazgos funcionales nuevos en el alcance revisado. No se autoriza publicar otro ZIP, incorporar el bundle nativo reconstruido ni ampliar el producto por este dictamen.

### Adenda final del gate · 12.11.2026

**Gate favorable: las condiciones documentales y de clasificación indicadas abajo están satisfechas.** Revisé las cabeceras vigentes del contrato W02-A y de `THIRD-PARTY-NOTICES.md`, la nota de publicación con postboot manual0/automático1, README EN/DE/ES y la nueva guía `INSTALACION19-PASO-A-PASO.md`. Separan Online19 de los paquetes offline históricos, adquisición del proveedor de redistribución propia y prueba del broker de inspección del resumenGUI. Incluyen el contrato normativo .NET y la observación automática en los tres idiomas. El enlace nuevo de la nota de continuidad, inicialmente relativo a `docs/docs`, fue comunicado y corregido por el coordinador antes del gate final. Los estados pendientes de la tabla inicial de este informe se conservan como historia de revisión.

Sin ejecutar nuevamente Gitleaks, suites ni VM, ejecuté `review-publication19/check_final_gate.py`: **44 archivos de fuentes/documentación escaneados, reporte con0 hallazgos**, cero duplicados, diferencias frente a sus hashes, rutas inseguras o modificaciones de producto. El activo mantiene su SHA256 `4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf`.

Para el activo con profundidad3 contrasté **1737 coincidencias / 1737 clasificadas / 0 sin resolver**, sin fallos de clasificación en mi sonda:1592 ocurrencias Demo50,144 identificadores de catálogo en el frontend fijado y1checksum de archivo. No se declara un escaneo vacío. Las comprobaciones usan bytes publicados de651, catálogo validado y archivos reales del ZIP; no una excepción general de regla, directorio o formato.

Las tres ocurrencias residuales quedan aprobadas individualmente:

- Dos copias de `demo50-replay.json`, una exterior y otra dentro del Core/DemoZIP: bytes idénticos aGit651 y SHA256 `44f7fca5dd78b10de1a5efbb51f34cff488974ed264bfcf9ea72059b1194216d`, línea1/columna28642, regla `generic-api-key`. El comando33 del cliente47 contiene un identificador de perfil real de19 caracteres; el escáner captura sus primeros18 y omite el sufijo final. Comprobé la concatenación exacta, pertenencia al catálogo validado y la misma identidad en el equipo esperado29. Es un identificador de catálogo, no material autenticador; la clasificación no se extiende a otro valor o ubicación.
- `application/manifest.json`, SHA256 `a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112`, línea79/columna18: el valor coincide con la entrada del manifest **y con el SHA256 calculado de `server/database/046-mfa-key-rotation.sql` dentro del activo**. No se clasificó como checksum sólo por tener formaHEX.

Resultado privado: `review-publication19/final-gate-results.json`. No se modifican reglas del escáner ni producto. Sólo resta al coordinador sellar esta adenda en los manifiestos/evidencias, comprobar bytes del índice y publicar/verificar el commit y los activos exactos en el repositorio privado, conservando rollback y las limitaciones declaradas. No se requiere otro ensayo funcional para esta adenda.

La relectura final de B ya acredita funcionamiento después del reinicio mediante el comprobador oficial manual y los datos conservados. **La primera tarea automática de comprobación falló y sigue siendo una observación operativa abierta**; no debe declararse pasada. Esta distinción debe aparecer en EN/DE/ES y en la Release. La entrega continúa como candidata de pruebas, sin adopción productiva.

## Identidad comprobada directamente

| Pieza | Resultado propio |
|---|---|
| `RackClick-Windows-Online-19.zip` | **12655070 bytes / 68 miembros**, SHA256 `4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf` |
| Sumas exteriores | 67 registros; inventario cerrado, sin faltas ni hashes incorrectos |
| Core04 | 197 miembros, inventario `FILES.json` cerrado y todos sus tamaños/hashes correctos; SHA256 `572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5` |
| Aplicación | 79 archivos, manifest `a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112`; contenidos correctos frente al manifest |
| Servicio | 37 archivos exactamente iguales a los de18 al excluir `RackClick.WindowsService.exe`; no se recompiló ni se sustituyó la DLL |
| Demo50 | 62 archivos exteriores idénticos a la entrega trilingüe03; archivo interior fijado a `d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215` |

La apertura de ZIPs no encontró nombres duplicados ni rutas inseguras en estos inventarios. El transporte no contiene SDK/runtime.NET, PostgreSQL, CRT, Python ejecutable/DLL ni el apphost omitido. **Sí contiene bibliotecas de terceros redistribuidas con sus avisos**: no se presenta como código exclusivamente propio.

## Fuentes y diff

Ejecuté `C:/Python312/python.exe -B .local/github-installable-20261112/review-publication19/probe_selection.py`. Comparación mediante `git cat-file --batch` contra los blobs de651 y contra `BASELINE-SOURCES.json`: **426/426 archivos de producto idénticos**, cero añadidos, eliminados o modificados en frontend/src, servidor/src y SQL. No hay compilación ni una nueva verificación .NET implícita en ese resultado. El catálogo contenido en esas fuentes permanece igual.

El diff de los productores nativos agrega la edición19 a las ramas existentes, conserva las anteriores y exige37 archivos de servicio sin apphost. La rama19 añade los textos MIT/ThirdPartyNotices con pins cerrados y corrige su NOTICE. El ensamblador reconstruye el bundle48 y exige su digest exacto, después el wrapper19 fijado a `4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd`; no compila RackClick. Los cambios nuevos de transporte son Python/PowerShell, receta, avisos y documentación; no cambios C#/JS/SQL.

Revisé `collect/package` del productor, `verify_core/require_new_work/acquire/assemble` y el cierre diagnóstico del CLI, más las ramas nativas de empaquetado. El código actual sólo escribe su diagnóstico si `_owned_work` identifica la raíz creada por ese intento: la observación histórica del CLI ajeno no se presenta como vigente sin esa corrección.

## Avisos y condiciones de distribución

**PUB-02 está corregido para19**, sin reescribir los ZIP17/18 históricos. El activo lleva:

- MIT del servicio: 1115 bytes, SHA256 `ae48df11a335dc1a615f4f938b69cba73bcf4485c4f97af49b38efb0f216353b`.
- ThirdPartyNotices de sus30 paquetes10.0.12: 78041 bytes, SHA256 `6d15e10a101c6bfff2ab4429ed061bf76c456fc4b23ad6b03e0d0f8377148a21`.
- Npgsql903 bytes, Otp.NET1070 bytes y los cinco avisos originales de React/ReactDOM/fuentes del frontend, con los hashes ya contrastados.

La rama19 del NOTICE distingue esos paquetes MIT del contrato binario del runtime Windows y explica la ejecución de la DLL mediante `dotnet.exe` adquirido. La receta declara cuatro adquisiciones directas y fijadas: Python embebido3.12.3, SDK10.0.401 usado sólo como origen del runtime10.0.12, PostgreSQL17.11-4 y CRT14.51.36247.0. No se publicó una copia de estos cuatro archivos dentro del activo; no se presupone que Wascar tenga licencia de Visual Studio. El wrapper/bundle ensamblado en destino y sus cachés deben permanecer fuera de los activos GitHub.

Se reutiliza la [revisión concreta de condiciones](CONDICIONES-DISTRIBUCION.md): los términos del proveedor siguen aplicándose a su adquisición/uso. No se afirma que MIT cubra todo el runtime ni que las condiciones de redistribuir el ZIP18 hayan quedado cerradas por esta alternativa.

## Documentación, traducciones y enlaces

Ejecuté `check_links.py`: **10 documentos / 71 enlaces**, cero enlaces relativos ausentes, anclas HTML inexistentes o URL externas con sintaxis inválida. No comprobé la disponibilidad del futuro activo remoto: el enlace a `windows-online19-schema48` sólo debe anunciarse como disponible tras subir y verificar la Release privada.

README EN/DE/ES y las guías separan instalación nativa con MFA de demo10 en loopback/MFA desactivado. El manual exterior incluye la ruta accesible del cargador desde la carpeta extraída; el manual nativo interior utiliza su ruta privada `work/demo03`. Ambas rutas corresponden a sus respectivos contextos. Los idiomas conservan pasos de adquisición, New, acceso privado, carga explícita de50, backup, reinicio y comprobación; no prometen cuentas/factores copiados de A. La prueba de B no acredita haber pulsado todos los botones del asistente: se ensayaron preparación y broker oficial.

| Gravedad | Observación | Estado al revisar |
|---|---|---|
| Media documental | README.es conservaba una frase general de recuperación/emergencia/rotación pendientes, incoherente con los componentes internos ya implementados. | Retirada por el coordinador y comprobada; EN/DE/ES conservan los límites operativos. |
| Baja | Párrafo roadmap EN duplicado. | Retirado y comprobado. |
| Baja | El HTML03 enlaza `.NET/platform/free` como información de términos, sin ser el contrato Windows transportado. | Mantener el HTML03 exacto; el coordinador añadirá el enlace normativo `.NET Library` en README/nota Release/fuentes. No se confunde con MIT. |
| Media documental | El contrato inicial aún describe VM nueva y PUB-02 pendientes; `THIRD-PARTY-NOTICES.md` conserva el contexto de publicación de fuentes sin nuevo instalador. | Antes de publicar, añadir estado vigente19/B y distinguir el activo Online19 de los ZIP nativos históricos excluidos. No requiere cambiar el activo03 ni producto. |
| Media documental | La nota de publicación aún decía reinicio de B pendiente al preparar su primera versión. | Conciliar con los recibos finales descritos abajo, preservando también el fallo automático. |

## B: evidencia del coordinador leída, no ejecutada por el revisor

Leí `readiness-b.json`, `demo50-status-b.json`, `post-demo-backup-b.json`, `mfa-status-b.json` y los cuatro recibos postboot privados. Corresponden a una misma instalación nueva. Acreditan preparación03 y brokerNew19 una vez; la salida nativa inicial3/valid:true/awaiting_reboot no era éxito final. Servicio estándar/Auto, HTTPS48 y frontend SHA256 `21d85d7543595d77befce549b98c7f0ebb07d8619648fc9830132f2a04523d04`; carga50 verificada mediante2553 comandos y backup posterior con resultado de tarea0 bajo cuenta estándar.

Después del reinicio efectuado por Wascar:

- `postboot-first-automatic.json`: fallo `postboot_https_health_failed`, exit1, a01:09:23UTC; original conservado. La observación de proceso posterior se registra aparte y no prueba una causa universal para otros fallos.
- `postboot-manual-result.json`: comprobador oficial manual exit0, `postboot_verified`, rebootVerified:true a01:11UTC; sin reinstalación ni reescritura del primer resultado.
- `postboot-final-b.json`: `postboot_demo50_verified`, 50 nombres y distribución17EN/17DE/16ES, y las ocho colecciones completas:66 sitios,88 edificios,226 salas,180 racks,1563 equipos,2869 grupos,20665 puertos,2207 conexiones. HTTPS48, servicioSTD/Auto y frontend exacto conservados. Registra MFA disponible, política global activa, gracia45/exención global y factor nuevoNONE sin cambios.

No repetí un enrolamiento/TOTP ni operé B o A/D/E. Disponibilidad y política MFA no se convierten en un nuevo ensayo completo de todos sus recorridos. Restore48, cambio automático de red48, QA/adopción y corrección de la comprobación automática temprana conservan sus pendientes.

## Pruebas reutilizadas y límites

Leí [REVISION-ONLINE19.md](REVISION-ONLINE19.md) y su probe `security-review/schannel03-02/review-transport03.json`: activo03 exacto,67 hashes, pins, caché cerrada, receta, hosts y rechazo antes de Python. Se reutilizan sus resultados:20 Windows PowerShell5.1 y9Python comunicados por implementación/coordinación, y5 focos independientes de seguridad más su probe. **No repetí esas suites ni las sumé como casos distintos.** Los fallos previos de red/issuer/arnés están preservados y no se sustituyen por un relato íntegramente verde.

Mis ejecuciones fueron sólo probes de inventario/hashes/blobs/enlaces y `git -c core.whitespace=cr-at-eol diff --check` (exit0). No ejecuté instalador, descargas, servicios, API/MFA, compilaciones, suites de producto, escáner de secretos, staging, commits, Release ni push. El escaneo definitivo corresponde al coordinador sobre la selección final, incluyendo avisos/docs/evidencias sanitizadas y el activo exacto; no basta el escaneo focal de15 fuentes.

Antes de publicar: conciliar las notas indicadas, incorporar este informe, fijar selección/manifiestos, completar clasificación de secretos y contrastar que índice/activo remoto coincidan con los bytes aprobados, manteniendo repositorio privado y punto de retorno. Una corrección de contenido del ZIP requiere otro digest y revisión de su delta; las notas complementarias no deben reescribir el HTML03 congelado.

**Métrica:**26,63/100 del cierre restante, sin incremento por transporte, publicación o número de pruebas; no es un porcentaje global nuevo del producto.

## Archivos y símbolos consultados

`AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, estado Git del worktree; `BASELINE-SOURCES.json`; README EN/DE/ES, tres guías de fuentes, contrato W02-A, `PUBLICACION-ONLINE19-12-11-2026.md`, ambos HTML19, `THIRD-PARTY-NOTICES.md`; `online-installer19.sources.json`; `build_online_installer19.collect/package/members`, `assemble.verify_core/acquire/assemble`, plantilla `Install-RackClickOnline.ps1` y confirmaciónADQUIRIR, productores nativos `build/clean_build`; avisos MIT/TPN y locks; ZIP03/Core04/Demo03; pruebas online19 leídas, revisión/probe de seguridad, recibos privados de B y resultados históricos de esta tanda. No se editaron los archivos implementados por otros.
