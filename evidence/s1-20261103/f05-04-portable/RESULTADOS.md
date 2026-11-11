# Paso17 · F-05.04 · recuperación portable entre Windows

03.11.2026. Coordinador Codex; implementación acotada `rackclick_backend`; revisión independiente `rackclick_security`. Se reutilizan los componentes revisados. **F-05.04 completado técnicamente** con [dictamen final favorable](review/DICTAMEN-F0504.md). No implica adopción ni cierre de F-05 completa.

## Qué se comprobó realmente

- Origen **Windows LEAO** y destino **Windows Server E**, UUID físicos distintos comprobados privadamente y VMX de E fijado. D no recibió comandos de invitado, cambios de potencia, instalación, DB, cuentas o MFA.
- Dos claves completamente sintéticas: **1 retirada y 7 activa**. Dos factores cifrados con los IDs originales de Systemhaus/usuario/versión como AAD. La identidad de instalación del anillo se adapta explícitamente; no se modifica la AAD de los factores.
- Exportación RCKEY real desde el origen y recuperación con DPAPI LocalMachine del destino mediante los componentes aprobados, conservando todas las versiones/estados requeridos. El ejecutable Release referencia la DLL **Debug** F-04.01 aprobada, no la DLL de D ni una nueva candidata completa. [Manifiesto de siete archivos](implementacion/MANIFIESTO-TOOL.json).
- Un **dump PostgreSQL17.11 custom real de2076bytes** contiene una sola tabla con dos ciphertext y sus IDs/versiones/estados. Se inspeccionó y comparó con el fixture. No contiene claves, sobre, contraseña ni columnas de TOTP en claro. Es un fixture SQL mínimo, **no backup de aplicación**, y no se restaura/serve una DB en E. [Alcance e identidad](ORIGEN-Y-ALCANCE.json).
- Bajo el **token real de la cuenta estándar del servicio de E**: SCM, imagen, PID y hora de inicio ligados; SID/token e identidad suplantada verificados, identidad del ejecutor restaurada. Ambos factores descifran con el contexto original; seis contextos AAD incorrectos se rechazan. Seis objetivos permiten cero escrituras y cero WRITE_DAC: **12 denegaciones**, sin inconcluyentes. No se presenta como repetición de toda la matriz F-04.02.

## Siete resultados del destino

Los [recibos originales de hijos](ejecucion/) tienen exit/código/fecha y salidas sanitizadas; no se deducen del exit del padre.

| Caso | Resultado |
|---|---|
| Adaptación no autorizada | `adaptation_required`; namespace `instances` ausente |
| Contraseña errónea | `envelope_rejected`; namespace ausente |
| Sobre auténtico con sólo versión7 | `material_required_version_missing`; namespace ausente, antes del writer |
| Origen diferente al fixture fijado | `fixture_origin_mismatch`; namespace ausente; prueba de vínculo, no otro negativo del codec |
| Importación válida | exit0; adaptación explícita, dos factores verificados después de publicar |
| Uso bajo token estándar | exit0; activa7/retirada1, dos factores, seis AAD rechazadas y versión8 inexistente rechazada; huella bytes/DACL sin cambio |
| Importación duplicada | `destination_exists`; bytes/DACL del almacén conservados |

[Resultado del job](ejecucion/trial-exit.json): `portable_cross_windows_verified`, exit0 de la [tarea](ejecucion/task-result.json). Los archivos de código y339archivos del runtime se comprobaron por hash/longitud y permanecieron retenidos sin compartir escritura/borrado durante los hijos. No hubo rebuild o cambio de producto después de fijar los pins.

## Custodia y comprobación posterior

- Sobre, dump y contraseña son artefactos distintos. En el host la contraseña sintética se conserva bajo **DPAPI CurrentUser**, en carpeta privada separada de la exportación y del dump. Nunca se pasó por argv, entorno, transcripción, binlog, recibo o ZIP.
- Para alimentar stdin hubo una **entrada privada transitoria en claro en disco**, creada en carpeta protegida con DACL Admin/SYSTEM. Su retirada se comprobó en ambos intentos. No se afirma borrado físico de disco/memoria ni custodia externa productiva.
- Las **dos copias temporales del sobre en E se retiraron**, por hash y ACL comprobados, después de completar el ensayo. Los originales sintéticos permanecen privados en LEAO; los nuevos blobs reprotegidos de E permanecen en su namespace offline. No se adoptaron ni se activaron para el host instalado.
- [Postflight](ejecucion/POSTFLIGHT.json): ambas tareas temporales ausentes por consulta COM con leafHRESULT `0x80070002`; entrada privada ausente; los dos servicios de E mantienen Auto/Running, PID, hora de inicio e imagen. El primer recibo de postflight etiquetaba la línea SCM completa como imagen; el contraste detectó la diferencia de representación y un suplemento de sólo lectura comprobó la imagen real. Se conservaron ambos originales privados, sin reconstruir recibos.
- No se leen ni cambian los almacenes MFA **instalados** de E. La afirmación de no escritura en ellos deriva del alcance del código fijado y de sus rutas nuevas; no se afirma un hash de sus claves existentes. Los procesos/servicios sí se contrastaron antes/después.

## Intento fallido conservado y corrección del harness

La primera ronda no alcanzó el hijo ni la importación: `H` resolvía al alias PowerShell `Get-History` antes que a la función homónima y dio `ParameterBindingException`. La tarea quedó retirada y el JSON privado con contraseña quedó como residuo declarado. El retiro posterior comprobó hash/ACL, tarea ausente, namespace ausente y servicios previos iguales. [Originales](harness/round1/).

Se reprodujo el mismo fallo localmente y se cambió exclusivamente a `HashFilePortable`; [control rojo/verde](harness/CONTROLES-ALIAS.json). Se prepararon tarea nueva y recibos `r2-` exclusivos, manteniendo fuente/sobre/dump idénticos y el namespace todavía vacío. [Revisión previa2](review/APTO-PARA-ENSAYO-R2.md). No hubo repetición ciega, limpieza de datos de producto ni cambio del codec. La primera revisión estática no detectó el conflicto de alias; este límite queda visible.

## Investigación, pruebas y límites

[Investigación y decisión](INVESTIGACION-Y-DECISION.md), [implementación y build](implementacion/RESULTADOS.md), [diez controles locales](implementacion/CONTROLES-LEAO-REPRODUCIBLES.json), tres controles DACL nuevos y parser PS5.1. Los controles repetidos no se suman como casos nuevos. Build del harness0errores/advertencias; binlogs privados. No se repite la suite criptográfica/HTTP/GUI: sus componentes no cambiaron.

Los comandos ejecutados por el coordinador son los drivers `harness/Create-Source.py`, `Create-FixtureDump.py` y `Coordinate-E.py prepare/run/collect`, ligados a un contexto privado único; no son instrucciones para ejecutar en una instalación de usuario. Los `.ps1` de staging/tarea/job/postflight quedan como fuente de la medición, no como operador distribuible.

## Registro del cierre

Se cambió únicamente el estado de **F-05.04**, pending→done, manteniendo su criterio/peso1/2. Índice1523/84→**1565/84=18,63/100** del cierre restante;40done/238pending/2in_progress. Otros52resultados, checkpoints de F05, hitos completos, pesos, huella congelada, baselinev3 y268números permanecen iguales. [Comprobación](VERIFICACION-CIERRE.json). No se calcula un porcentaje global nuevo del producto.

Plan/registro/changelog/continuidad actualizados y tres generadores en modo write/check correctos. La primera captura de stdout esperaba UTF8 frente a la página Windows y perdió dos salidas aunque los seis procesos terminaron0; se conserva esa captura y se repitieron únicamente los tres checks con UTF8 explícito. No se repitió ninguna prueba de producto por este detalle de registro.

**Fuera de este resultado:** Restore de DB completa, login/TOTP/HTTP después de Restore, journal/fence/marcadorDB de D2, integración en instalador/candidata completa, recuperación de datos reales, rotación, emergencia, durabilidad ante corte y aceptación de Wascar. Las guardias existentes de Restore se conservan. Sólo F-05.04 es candidato a crédito1/2; F-05.05, hitos completos F-05 y R-04 mantienen sus criterios pendientes. Sin commits, push, publicación o cambios de GUI/resultadosQA.
