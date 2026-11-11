# F-05 · matriz del cierre técnico

03.11.2026. Se conserva literalmente el criterio del ledger: «Restore nuevo verifica factores usando clave recuperada; sin material/contraseña correctos falla explícitamente, sin emitir sesión insegura; negativos y revisión independiente». No se sustituye por un número de pruebas ni por el estado de una VM.

| Checkpoint | Evidencia reutilizada o nueva | Alcance comprobado |
|---|---|---|
| F-05.01 | [Matriz previa](../f05-01-sobre/MATRIZ-CRITERIO.md) y dictamen | Cabecera/límites/codificación/AAD del codec RCKEYv1 fijado. Sin nuevo codec |
| F-05.02 | [Medición/decisión conciliadas](../f05-02-coste/RESULTADOS.md) | Perfil600000 conservado;57–62ms son casos Windows completos históricos, no benchmark KDF universal |
| F-05.03 | [Negativos conciliados](../f05-03-negativos/MATRIZ-NEGATIVOS.md) | Contraseña, alteración, truncado, extra, versión/algoritmos y coste/tamaño. No se repite la suite por inercia |
| F-05.04 | [Portabilidad real revisada](../f05-04-portable/RESULTADOS.md) | LEAO→WindowsServerE, adaptación explícita, factores/AAD1y7 y token estándar real. No se repite otroWindows en este lote |
| F-05.05 | [Corrida nueva](COORDINACION-PG-R3.json), [fuente/pins](implementacion/HARNESS-FREEZE6-PREVIO-PG.json), [implementación](implementacion/RESULTADOS.md) | DB de aplicación45 dump/restore real, todas las filas públicas iguales antes de recuperación administrativa; proveedor Windows sobre claves importadas; endpoints Program, TOTP conservado y autoridad nueva; negativos sin nueva sesión |

## Nuevos ocho casos ejecutados

- Restore custom PostgreSQL real a DB/roles nuevos:45migraciones y todo el contenido de tablas públicas coinciden antes de los cambios administrativos intencionales. Se comprueban inventario, rol noowner/nosuper/sinDDL y siete catálogos globales sólo lectura. La igualdad de filas no se presenta como comparación de archivos del cluster, roles globales o assets externos.
- `RecoveryAdministrator.Run` real revoca las dos sesiones y consume los dos desafíos del backup; se comprueban por SQL y por rechazo de cookies/desafío en API. Los factores/IDs/ciphertext/versiones se conservan. El administrador de recuperación adicional no es el usuario con cuyo factor se hace el positivo.
- Dos casos de login, uno por versión1retirada/7activa: contraseña→desafío sin sesión/API→TOTP válido→sesión/CSRF→`/me` e inventario autorizado. CSRF incorrecto rechaza, correcto cierra sesión; la cookie cerrada no sirve. Otra petición con desafío nuevo y el mismo TOTP ya usado se rechaza sin nueva sesión.
- TOTP incorrecto:401 y cero sesiones nuevas.
- Contraseña incorrecta del sobre: rechazo antes de crear almacén/host.
- Sobre auténtico sin la versión retirada requerida: rechazo antes de crear almacén/host.
- Ciphertext de un usuario asociado al ID del otro: fallo de autenticación AAD antes de crear almacén/host.

Son siete métodos y ocho casos, no ocho métodos. Los tres últimos gates son supervisión del **fixture** con componentes reales, no un operador productivo ni una guardia nueva en el instalador. El positivo sí utiliza `Program` y el proveedor Windows reales; la única sustitución de identidad/confianza y de dirección de cliente es la del laboratorio declarada. El rate limit del producto permanece activo.

## Límite del cierre técnico

[Umbral independiente](review/UMBRAL-F0505.md). Se prueba integración de componentes sobre una DB restaurada en laboratorio, sin listener HTTP de red, instalación o adopción de DB/material. La identidad Windows LAB no repite la del servicio real ya medida en F-05.04.

El coordinador operativo D2, consistencia de exportación concurrente, fence/journal/marcadorDB y caídas, CLI/instalador New/Restore, HTTPS/servicio/reinicio/cutover y aceptación conservan sus criterios F-06/F-09/R-04 y los hitos pendientes. Un resultado técnico de .05 no les asigna crédito ni convierte la entrega en adoptada.
