# F-06.02 · integración nativa de inventario de backup

09.11.2026 · **En progreso; +0 puntos. D y E conservados sin operaciones.** Continúa la tanda de [componentes revisados](../f06-02-retencion/RESULTADOS.md); no la repite ni sustituye sus resultados.

## Entregado

- CLI local `--mfa-backup-inventory` antes de componer el host. Snapshot readonly RepeatableRead, censo agregado y exportación de snapshot; segundo mensaje liga inventario a hashes de manifiesto/dump/sobre. Rama `verify` sin DB ni claves. Mensajes acotados, campos exactos, Unicode inválido/EOF/cancelación y errores esperables sanitizados.
- Operadores Windows nuevos para producir y consumir el inventario lateral con recibo externo privado. Fuente/dll/dependencias pineadas y retenidas; rutas locales, reparse rechazados, creación exclusiva y parciales conservados. Entorno del hijo sin hooks/profilers/PG heredados. La contraseña del sobre va por stdin, nunca argv; no se copia el sobre al backup.
- Validación de DB/owner/rol por UUID, PG17.11, secuencia SQL1..45, comentario compartido vacío y rol de backup sin DML/DDL/membresías. No se migra ni cambia un permiso desde la CLI. La comprobación de secuencia no equivale a verificar digests de migración.
- El backup histórico conserva sus dos archivos y ocho campos dentro de `database/`. Lateral y recibo tienen formato propio. `catalogComplete=false` y `retirementAuthorized=false` son resultados deliberados, no omisiones que el llamador deba convertir a true.

[Plan e investigación](../../../docs/PLAN-F0602-INTEGRACION-BACKUP.md) · [Manual de desarrollo](../../../docs/BACKUP-MFA-CON-INVENTARIO-DESARROLLO.md) · [Fuentes exactas](FUENTES.json) · [Revisión independiente](REVISION-INDEPENDIENTE.md).

## Ejecutado y resultado

Windows anfitrión, SDK10.0.401/runtime10.0.12, Npgsql10.0.3, PG17.11, esquema45. Fuentes/build en copia aislada `.local`, sin compilar sobre los obj compartidos. Restore locked y build Release con binlogs privados únicos:0errores/0advertencias.

| Verificación final | Resultado | Alcance |
|---|---|---|
| Regresión C# pertinente | 138/138,0omitidas | CLI24, retención51 y controles previos de inicialización/composición del host. Incluye pruebas previas; no se suman como138 funciones nuevas. |
| Python/PowerShell | 13/13 | Tres casos de host/proceso y diez del operador/lector/pines/Framework/reparse. |
| Recorrido PostgreSQL y operadores reales | 8controles correctos | [POSTGRES-NATIVO.json](POSTGRES-NATIVO.json). No usa mocks para pg_dump, CLI o los operadores New/Test. |
| Revisor distinto | Diez PS +cuatro sondas+ tres host | Ejecuciones propias distinguidas de la evidencia PG del coordinador en su dictamen. |

El recorrido PG usa un clúster nuevo loopback y roles/DB sintéticos de nombres nativos. Primero rechaza base con marcador de recuperación, UPDATE de columna en otra tabla y membresía con SET sin INHERIT. Mantiene un snapshot real, añade/commitea después un factor disabled v8 y ejecuta pg_dump con ese snapshot. Restaura en otra DB nueva y contrasta exactamente `1:disabled,1:pending,7:active`; v8 permanece sólo en el origen. Después ejecuta los operadores de backup/verificación completos sobre el estado actual, contrasta las versiones1/7/8 y los pines, rechaza inventario alterado, destino existente y tercer archivo histórico, y vuelve a verificar. Las filas completas de factores se contrastan por huella en lecturas nuevas antes/después del operador, además del recuento4. Se detiene el clúster propio al terminar; se conservan sus archivos privados.

Los ciphertexts de factores son opacos sintéticos para probar censo/dump; no se presentan como autenticadores usados por HTTP. El sobre RCKEY/RCKPAY sí es real, sintético y autenticado mediante el codec aprobado, con claves aleatorias. No se afirma custodia externa real por guardar este fixture en `.local`.

Comandos reproducibles (las huellas se obtienen de la copia aislada y se contrastan con FUENTES/REGRESION):

```powershell
C:/Python312/python.exe -B tools/tests/run_mfa_backup_inventory_native.py --source-root <copia-aislada> --expected-server-sha256 <pin-DLL>
C:/Python312/python.exe -B -m unittest tools.tests.test_mfa_backup_inventory_cli_host tools.tests.test_mfa_backup_inventory_operator
```

El segundo requiere `RACKCLICK_F0602_NATIVE_DLL` apuntando a esa DLL aislada. Los siete casos PG adicionales opt-in del archivo C# (seis normales y uno de marcador) quedan preparados, **no ejecutados** en esta tanda; no se agregan a los resultados. La prueba PG de producción se ejecutó desde el runner Python por procesos reales.

## Rojo, correcciones e intentos conservados

- CLI nueva: pruebas fallaron por ausencia del componente, después24puras correctas. [Registro del implementador](CLI-RESULTADOS.md). No se atribuye ese rojo a un fallo del producto anterior.
- Referencia inicial real: aceptaba los tres negativos de identidad/permisos anteriores; el runner terminó con1. Se corrigieron `shobj_description`, comprobaciones de grants fuera de factores y membresías/CREATE. El mismo recorrido final rechaza los tres antes de una respuesta positiva.
- Junction vacía:1negativo devolvía `accepted`; después se comprueba cada entrada antes de descender. Prueba final correcta, sin seguir el enlace.
- PowerShell5.1: se reprodujo un fallo al construir el proceso porque Framework no tiene `StandardInputEncoding`. Se sustituyó por StreamWriter UTF8 explícito; negativo antes y verde después. El import de prerrequisitos además vaciaba `DotnetPath`; New/Test guardan la ruta antes del import, sin modificar el auxiliar histórico.
- Dos primeros intentos del runner cargaban por autoload un módulo Security del anfitrión PowerShell7; el fixture importa explícitamente el módulo de Windows PowerShell5.1. No fue un fallo del codec o del servicio. Las ejecuciones siguientes distinguieron la colisión de parámetro y la API Framework antes del primer recorrido correcto. Se conserva el error de una sonda privada de diagnóstico mal escapada; no cuenta como ejecución válida del producto.
- Las regresiones previas de115/51 y10PG del componente no se repitieron completas. La regresión138 selecciona los controles afectados por esta nueva integración y contiene51 de retención ya conocidos.

Logs, TRX, binlogs, sobres sintéticos y credenciales nuevas sólo en `.local/f0602-native-b59d6b15/` y laboratorios propios. Este registro no incluye claves, contraseñas, conexiones o dump.

## Límites y contabilidad

Hay caller nativo **de metadatos**, no de retirada. El recibo permite comprobar un backup contra un pin externo; no demuestra que estén registrados todos los backups o que el custodio conserve el sobre. No se expiran backups antiguos ni se inventa una lista completa por defecto. Los pines no sustituyen autoridad y actualidad del catálogo.

Faltan el catálogo autoritativo exhaustivo y la retirada real bajo exclusión/fence/recenso/guard/publicador recuperable del protocolo F-06.01/.03. No se ha implementado rotación, testigo DB, caída/reinicio de Windows, durabilidad frente a corte eléctrico, MFA por HTTP/GUI o lectura bajo el token real del servicio en esta tanda. No se cambia SQL, proveedor/writer, sobre, política45, instalación, cuentas, servicio o QA de D/E; sólo Program incorpora una rama CLI temprana. No hay paquete instalado, commit o push.

F-06.02 permanece `in_progress`, peso5/8 sin acreditar; hitos de F06 siguen pendientes. El índice se mantiene **3319/168 =19,76/100 del cierre restante**, no un porcentaje global de entrega. Siguiente trabajo: integrar catálogo/retirada y recuperación tras fallos, reutilizando esta publicación/consumo de inventarios sin rehacer los codecs ni los ensayos portables anteriores.
