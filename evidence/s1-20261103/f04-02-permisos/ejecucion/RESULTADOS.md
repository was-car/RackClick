# Paso 12 · F-04.02 · permisos efectivos en E

03.11.2026. **Cerrado técnicamente con revisión independiente.** Se reutilizaron dos servicios y almacenes existentes en E, sin crear cuentas, claves o instalaciones. D quedó excluida de las ejecuciones en invitado; sus datos/MFA/servicios no se modificaron. Sin commits, push o cambio de binarios del producto.

## Qué se reutilizó

La [preparación anterior](../RESULTADOS.md), [revisión previa de la sonda](../review/DICTAMEN-PREVIO-SONDA.md) y lectura real C10/D11 se conservan. Reader/proveedor/escritor no se editaron ni se compilaron otra vez. Los negativos L2b de DACL nulo, terceros, herencia peligrosa, reparse/redirección y enlaces siguen ligados a su componente por hash; no se alteraron los almacenes reales para reproducirlos.

Wascar encendió E. La identidad física de su invitado se contrastó contra el UUID BIOS del VMX exacto y se distinguió de D; no se confió sólo en el nombre Windows de un clon. Las dos cuentas estándar se identificaron mediante SCM y SID. El proceso se ligó por PID, imagen y fecha de creación antes/después, con suplantación efectiva y restauración comprobadas.

## Medición real

La [matriz fijada](MATRIZ-FIJADA.json), SHA256 de petición `7013bf62823299bd73183aa6cbc2edfafda0b4104b3da790c032b2106c0f6504`, tiene **30 objetivos por actor**: dos padres comunes, doce nodos de almacenes/raíces privadas y dieciséis de management (dos raíces y catorce archivos). Cada cuenta mide los mismos objetos con acceso propio y cruzado.

- **504 aperturas verificadas**, con OPEN_EXISTING y sin leer/escribir contenidos.
- **16 lecturas propias/comunes permitidas**.
- **44 lecturas ajenas o administrativas denegadas**.
- **444 solicitudes de modificación denegadas**: escritura/creación, anexado, atributos, borrado, WRITE_DAC, WRITE_OWNER y DELETE_CHILD donde corresponde.
- Todas las denegaciones son **Win32 5**; ningún resultado por ausencia/compartición se convirtió en PASS. **0 indeterminados y 0 concesiones inesperadas**.
- Salida del hijo **0**, stderr vacío, tarea con resultado **0**, retirada y ausencia confirmadas.

[Salida real íntegra sin secretos](RESULTADO-PERMISOS-REAL.json) · [Consolidación](RESULTADO-CONSOLIDADO.json) · [Salida del hijo](SALIDA-HIJO.json) · [Recibo de tarea](RECIBO-TAREA.json).

## ACL, ancestros e integridad

[Política previa](POLITICA-ACL-PREVIA.json): 30 ACL de objetivos y 362 nodos de staging contrastados. Raíces privadas/management con propietarios de confianza; lector de MFA sin derechos de modificación; management sólo privilegiados. Lectura de Usuarios en los dos padres comunes sin herencia, conforme al instalador. Se midieron derechos efectivos también sobre los padres protegidos, incluido DELETE_CHILD. La sonda verificó tipo, anclaje de ruta, ausencia de reparse y enlaces adicionales en archivos; los ancestros superiores no se trataron como carpetas privadas de MFA.

Runtime de ensayo separado, **339 archivos idénticos por hash al SDK oficial fijado**, versión 10.0.12. Código legible para ambos actores pero no modificable por ellos; petición, scripts de tarea y resultados privados para SYSTEM/Administradores. No se copiaron DLL del producto a las instalaciones. [Pins previos](PINS-PREVIO-ENSAYO.json) y [aptitud independiente antes de ejecutar](review/APTO-PARA-EJECUTAR.md).

La huella nativa de **32 nodos** permaneció idéntica antes/después. Las **30 ACL** consultadas con la misma API PowerShell antes/después también permanecieron idénticas. Entre ambas API, cuatro archivos de management producen hashes de descriptor distintos: se observó orden diferente de SYSTEM/Administradores, con los mismos dos Allow FullControl, máscaras y flags; protección y propietario de confianza coinciden. No se afirma igualdad de esos cuatro descriptores serializados ni una causa universal de las API. La equivalencia de permisos se contrasta por campos y por las aperturas reales.

Los dos servicios conservaron **Running/Auto y PID**. No se operó su ciclo de vida, configuración, base de datos, usuarios, factores, certificados o backups. La única tarea nueva fue la temporal identificada para este ensayo y fue retirada. El código y sus recibos de laboratorio se conservan.

## Incidencias y correcciones del ensayo

1. La primera consulta larga por EncodedCommand agotó la espera de VMware sin aportar recibo. Consultas breves asíncronas confirmaron el canal y la identidad de E; se pasó a scripts verificados en archivo y ejecución no bloqueante. No se atribuye una causa no medida al timeout. No era la sonda y no se presenta como resultado de permisos.
2. El clasificador previo de integridad no rechazaba un vector de ACE vacío en el padre del staging. Un negativo con metadatos sintéticos lo reprodujo; se corrigió para fallar cerrado. Las ACL reales de E no eran vacías y siguieron cumpliendo la política. [Comprobador](CHECK-POLITICA-PREVIA.py), [foco](TEST-POLITICA-DACL.py).
3. El primer recolector de ausencia de tarea admitía indebidamente `0x8004130F`, que significa falta de información de cuenta, **no tarea ausente**. El recibo v1 no registraba el HRESULT, por lo que no bastaba. Se conserva su fuente como referencia, se retiró esa alternativa y se repitió **sólo la consulta de metadatos**, sin recrear tarea o repetir la sonda. V2 observó exactamente **0x80070002 / -2147024894**, archivo no encontrado. [Constantes oficiales de Microsoft](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-error-and-success-constants). El consolidado exige ese valor nativo. No se afirma que E devolviera el código erróneo admitido por v1.

## Revisión y cierre

[Dictamen independiente final](review/DICTAMEN-F0402.md): otro agente contrastó cada apertura contra la matriz, recalculó la huella nativa, verificó recibos, ACL, identidad, servicios y retirada. No ejecutó la VM ni modificó producto. Su [comprobación](review/COMPROBACION-RESULTADO-INDEPENDIENTE.json) y código quedan conservados.

Se acredita **sólo F-04.02, 5/8 de punto**: 323/21 → 2689/168 = **16,01/100 del cierre restante**. Pesos, criterio, baseline y números permanecen; F-04.04/tarea completa no se cierran por arrastre. No es porcentaje global nuevo ni adopción de Wascar.

Límites: es una medición puntual en E con las cuentas identificadas, no aislamiento frente a administrador/SYSTEM comprometido. Se comparan metadatos de MFA, no sus bytes; no se descifran claves ni se prueba un nuevo login/rotación/recuperación/instalador. Política45 y exención global intactas; los resultados QA del usuario se conservan.
