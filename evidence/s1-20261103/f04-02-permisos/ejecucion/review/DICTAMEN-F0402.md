# F-04.02 · dictamen independiente del resultado real

03.11.2026. Revisor: `rackclick_security`, distinto del implementador de la sonda y del coordinador que ejecutó el ensayo. **Favorable al cierre técnico de F-04.02, con el criterio y peso originales.** No hay bloqueante pendiente en ese subpaso. La contabilidad corresponde al coordinador; F-04.04 y la aceptación del resultado F-04 completo no se cierran por arrastre.

La revisión valida metadatos y recibos reales recogidos por el coordinador en E. El revisor no operó VM, SCM, servicios, tareas, cuentas o bases de datos. D quedó excluida; no se actualizó producto, MFA o permisos de ninguna instalación.

## Qué se contrastó

Se conserva el [dictamen previo](APTO-PARA-EJECUTAR.md) y la petición fijada `7013bf62823299bd73183aa6cbc2edfafda0b4104b3da790c032b2106c0f6504`. La matriz liga los dos servicios reales de E13/E14-r2 y sus SID distintos a sus instalaciones y al UUID físico de E, distinto de D. Comprende 30 objetivos por actor: directorios comunes, todos los padres privados, carpetas/archivos MFA y management con sus 14 nodos descubiertos.

Se leyeron y validaron `probe-output.json`, `probe-exit.json`, `task-result.json`, el retorno del lanzador y `post-trial-v2.json`, junto a petición, descubrimiento, metadatos previos y hashes de fuentes/runtime. [Comprobador independiente](Check-ActualMeasurement.py), ejecutado con salida 0; [resultado](COMPROBACION-RESULTADO-INDEPENDIENTE.json). No se aceptó sólo la palabra `verified`.

## Resultado real verificado

- **Dos tokens de servicio estándar**: vínculo SCM/proceso, SID de cuenta, suplantación efectiva y restauración de identidad correctos. Se comparan PID, imagen y fecha de creación en la sonda revisada, no sólo el nombre del servicio.
- **504 aperturas `OPEN_EXISTING`** contrastadas una a una contra la petición: 16 lecturas propias/comunes concedidas, 44 lecturas de otro almacén o management denegadas y 444 solicitudes de derechos de modificación denegadas. Todas las denegaciones devuelven Win32 **5**; no hay concesiones inesperadas ni errores indeterminados.
- Las denegaciones incluyen escritura/anexado o creación, EA/atributos, DELETE, WRITE_DAC y WRITE_OWNER; en carpetas, DELETE_CHILD. No se realizaron esas modificaciones: se solicitaron los derechos al abrir y se cerraron los identificadores sin escribir ni leer contenidos.
- La huella nativa de **32 nodos** permanece igual antes/después. Su SHA se recalculó independientemente a partir del JSON de nodos. Los objetivos y ancestros no presentan reparse; los archivos MFA tienen un único enlace. Los 30 descriptores objetivo se contrastan con la política de propietario, ACE, herencia y límites de lectura. Management no se amplía.
- La consulta posterior con la misma API PowerShell conserva **30/30 hashes de ACL**. Los dos servicios siguen Auto/Running con los mismos PID. No hay operaciones de servicio, cambio de ACL, lectura de contenidos MFA/management, cambio de privilegios o activación de MFA.
- Hijo, tarea y lanzador terminan en 0; stderr vacío. La tarea temporal fue retirada y una consulta posterior confirma su ausencia con el HRESULT exacto de archivo no encontrado.

El código/runtime del ensayo era legible por ambos actores y no modificable por ellos; petición, scripts de tarea y recibos estaban en state privado. Se reutilizan la revisión previa de sus 362 ACL y la identidad de los 339 archivos de runtime con el SDK oficial fijado. No se ha demostrado esa integridad sólo por el nombre del ejecutable.

## Diferencia entre representaciones de ACL, documentada

En `i2.management-node-1` a `i2.management-node-4`, el hash de descriptor de PowerShell no coincide con el de la consulta nativa C#. **No se declara igualdad de esos hashes ni identidad completa entre las dos representaciones.** Se observa orden inverso de dos ACE: SYSTEM/Administradores frente a Administradores/SYSTEM. Son exactamente dos Allow incondicionales con FullControl, flags 0, el mismo multiconjunto de derechos, protección coincidente y propietario de confianza. En ese caso la permutación no amplía acceso.

La huella nativa antes/después sí coincide, y los hashes PowerShell antes/después también coinciden para los 30 objetivos. No se infiere una causa universal de la API ni se oculta la diferencia observada. No se generaliza una comparación sin orden a ACL con Deny, condiciones u otras combinaciones.

## Precisión del recibo de retirada corregida

El primer auxiliar posterior aceptaba tanto `0x80070002` como `0x8004130F` para indicar tarea ausente. Se señaló este hueco de clasificación: Microsoft define el segundo como información de cuenta no establecida, no como ausencia de tarea. [Constantes oficiales de Task Scheduler](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-error-and-success-constants).

Se preservaron el auxiliar y recibo v1. Se corrigió la regla y se repitió **sólo la consulta de metadatos**, sin registrar otra tarea ni repetir la sonda. El recibo v2 observado contiene `taskQueryHResults=[-2147024894]`, hoja `-2147024894` (`0x80070002`) y `taskAbsent=true`. El comprobador independiente exige ese resultado concreto, no el booleano aislado.

## Reutilización y límites

El lector actual conserva el hash revisado L2b y sus negativos históricos de DACL nulo, terceros, herencia, reparse/redirección, hardlinks y sustitución durante lectura. Se reutilizan esos 39 focos y los positivos nativos C10/D11; no se presentan como nuevas ejecuciones. La sonda real de E añade el extremo que faltaba: acceso efectivo bajo dos identidades reales, permisos mínimos y management/padres comprobados.

No se leyó ni descifró el material TOTP en este ensayo, no hubo login MFA nuevo, restauración portable, rotación, reinicio o simulación de cortes. Una huella de metadatos no prueba igualdad byte a byte del contenido. La evidencia corresponde a estas instalaciones y al intervalo medido; no garantiza ausencia de cambios futuros ni resistencia frente a un administrador/SYSTEM comprometido. Esos límites no reducen el criterio congelado ni acreditan otros pasos.

**F-04.02 puede acreditarse con su único peso de 5/8.** El resultado F-04 completo conserva su revisión final F-04.04; no se añade otro crédito por número de aperturas, recibos o pruebas, ni se declara un porcentaje global nuevo.
