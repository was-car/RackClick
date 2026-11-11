# F-04.02 · dictamen previo de la sonda

03.11.2026. Revisor `rackclick_security`, distinto del implementador. **Favorable para preparar y realizar la medición acotada en E con la matriz y las condiciones descritas abajo. No es aceptación de una medición real ni cierre de F-04.02.** D no se ha consultado ni operado durante esta revisión.

## Archivos y versiones revisados

`tools/mfa-acl-probe/Program.cs`, `Native.cs`, `SelfTest.cs`, `RackClick.MfaAclProbe.csproj`, `packages.lock.json` e `Invoke-MfaAclProbe.ps1`. Se contrastaron además `WindowsMfaKeyFileReader`, `MfaKeyStoreInitCommand`, `RackClick.Setup.Security.ps1` (`New-SetupManagementDirectory`, directorios comunes y `New-SetupInstanceParent`), la revisión L2b y el resultado histórico de lectura del 28.10.

Las huellas finales y los binarios autorizados están copiados en [FUENTES-REVISADAS.json](FUENTES-REVISADAS.json). DLL: `70255530b65ece553c298d27b68d3391ae45816df35972afe57fef22c6182572`; runtimeconfig definitivo: `f173c9b0e8afdb290f78340d46dea63517542f89947431c936f76fd5ecd77181`, que pide exactamente 10.0.12 con roll-forward desactivado. No aceptar el runtimeconfig inicial que pedía 10.0.0.

## Observaciones de revisión resueltas antes de la VM

- **Lectura innecesaria de contenido:** el borrador calculaba hashes leyendo los archivos de clave cifrada y el anillo. Se retiró antes de la medición; el snapshot final contiene sólo identidad, tipo, tamaño, última escritura y descriptor/ACE. No permite afirmar igualdad byte a byte del contenido. No se descifra ninguna clave.
- **Continuidad de proceso:** se añadió `GetProcessTimes` sobre los identificadores de proceso. El vínculo final contrasta SCM/PID, cuenta/SID, imagen y fecha de creación, evitando aceptar sólo la coincidencia numérica del PID.
- **Runtime exacto:** el runtimeconfig 10.0.0 no era compatible con exigir roll-forward `Disable` en un equipo con 10.0.12. La edición definitiva fija 10.0.12; se verificó de nuevo el arranque del SelfTest con ese entorno.

Estas observaciones se identificaron por revisión de fuente, no por ensayos fallidos sobre servicios reales.

## Propiedades revisadas

La ruta de medición exige Windows, excluye LEAO antes de leer stdin o consultar SCM y requiere ejecutor SYSTEM. La entrada es acotada y rechaza campos extra/duplicados, dos actores con el mismo SID/servicio y rutas fuera del alcance. La instalación D identificada queda excluida. El coordinador debe revisar adicionalmente la petición completa; el parser no demuestra por sí solo cobertura de todos los objetivos.

Cada actor se liga al servicio y al token estándar efectivo. `RunImpersonated` comprueba la identidad dentro de las aperturas; la identidad vuelve al ejecutor después. Las aperturas usan `OPEN_EXISTING`, comparten lectura/escritura/borrado para no confundir una retención con una ACL y no leen/escriben datos. Sólo error 5 acredita una denegación. Hay siete derechos de modificación por archivo; las carpetas añaden DELETE_CHILD. Con la lectura, son ocho aperturas por archivo y nueve por carpeta, no nueve derechos de modificación.

El wrapper verifica y retiene DLL, deps, runtimeconfig y petición; aísla las variables de diagnóstico/profiler y configuración sólo del hijo, no usa shell, no muestra stderr interno y comprueba la correspondencia entre estado y salida. No crea tareas ni cambia servicios por sí mismo.

## Pruebas ejecutadas por este revisor

Windows, SDK 10.0.401. Sin VM, SCM real, cuentas nuevas, servicios, base de datos ni elevación de LEAO.

- **SelfTest final 15/15 PASS**, exit 0, stderr vacío, sobre la DLL autorizada y con runtime 10.0.12/roll-forward `Disable`, diagnósticos desactivados y entorno aislado como el wrapper. Son fixtures TEMP, no tokens de servicio reales.
- **9/9 focos propios PASS**, en copia separada, compilada con advertencias como errores, sin dependencias nuevas. [Código de revisión](ProbeReviewChecks.cs): error 5 frente a errores 0/2/3/32/1314; sello de creación del proceso sobre identificador real; actores/SID distintos; nombres de servicio insensibles a mayúsculas; rechazo de rutas ajenas; concesión de escritura detectada en fixture permisivo; sharing violation 32 y archivo inexistente 2 nunca tomados por denegación; bytes sintéticos conservados.
- `--measure` en LEAO devuelve `host_excluded`, exit 1, antes de stdin/SCM/objetivos.
- Wrapper en Windows PowerShell **5.1.26100.9711**, parser sin errores; rechazo temprano `host_excluded`, exit 1, con rutas de prueba inexistentes. No se lanzó su hijo.
- Restore locked-mode y compilación propia terminan en 0, sin errores ni advertencias. Binlogs privados únicos; resultados sanitizados en [RESULTADOS-PREVIO.json](RESULTADOS-PREVIO.json).

## Condiciones para ejecutar y aceptar después

1. E identificada y encendida por Wascar, con dos servicios estándar distintos y los objetivos existentes. Mantener D excluida y sin cambios.
2. Matriz y hash de petición revisados: almacenes propios, acceso cruzado, management y sus archivos administrativos seleccionados, y **cada padre protegido** con aperturas efectivas de modificación/DELETE_CHILD. Los padres agregados sólo al snapshot no cuentan como aperturas medidas.
3. Runtime oficial existente contrastado por ruta, hash y protección; el wrapper sólo comprueba reparse de ese ejecutable, no su hash. Script, petición y programa bajo staging privado SYSTEM/Administradores desde su creación antes de cualquier tarea SYSTEM. La tarea temporal y su retirada las coordina el operador, fuera de este componente.
4. Recoger salida completa y salida del padre/tarea. Verificar restauración de identidad, continuidad SCM/proceso, ausencia de resultados indeterminados y metadatos iguales antes/después.
5. Conciliar propietario, ACE, herencia y reparse de cada nivel. `verified` de la sonda combina sus aperturas y la huella; los campos `OwnerFixedTrust`, `ProtectedDacl` y ACE capturados **no son un validador automático de todo el contrato**. Hace falta ese contraste independiente de la matriz real, con las reglas distintas de ancestros del sistema y raíces privadas.

No se ha ejecutado el positivo SYSTEM con servicios reales ni se ha medido E. No se acredita lectura cruzada, denegación real de WRITE_DAC, management o padres con los tokens de E por estos SelfTests. El checkpoint sigue pendiente hasta esa evidencia y su revisión. Esta revisión previa no añade puntos ni porcentaje global nuevo.

## Adenda · legibilidad del código e integridad del estado

La condición 3 se precisa para la ejecución con dos tokens de servicio: **el programa y el runtime pueden y deben ser legibles/ejecutables por ambos actores**, por ejemplo mediante Usuarios (BU) con lectura/ejecución. Sus propietarios y permisos de modificación permanecen reservados a SYSTEM/Administradores; los actores no pueden escribir, reemplazar, borrar ni cambiar su ACL. Los hashes y la protección de las rutas siguen siendo obligatorios. No se exige confidencialidad del código.

El script de la tarea, la petición y las salidas/recibos quedan en un subdirectorio privado accesible sólo por SYSTEM/Administradores. Esta separación evita impedir una carga de ensamblado bajo impersonación sin abrir el estado administrativo. Sustituye únicamente la formulación anterior que agrupaba el programa con los archivos privados. No amplía el acceso al almacén MFA o a management, no cambia la matriz de aperturas y no añade pruebas ni aceptación de la VM, que sigue pendiente.
