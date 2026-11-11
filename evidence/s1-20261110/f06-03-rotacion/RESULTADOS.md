# F-06.03 · rotación y recuperación ante caídas

10.11.2026 · F-06.03 cerrado técnicamente, con revisión independiente favorable. D/E conservadas sin operaciones; ninguna instalación, publicación, cuenta o servicio instalado utilizado. No hay commits ni push.

## Implementación y reutilización

Se reutilizan protocolo F-06.01, catálogo/retirada/admisión F-06.02, DPAPI del escritor aprobado, proveedor, AES-GCM/AAD, RCKEY y SQL directo. La ampliación interna prepara una versión nueva sin reutilizar números, publica material y anillo aditivo, exige sobre autenticado antes de permitir dependencias DB, recifra todos los estados y publica el anillo final. El testigo de autoridad local se confirma en la misma transacción que los factores y la revocación/consumo de sesiones/desafíos afectados.

SQL046 es aditivo;001–045 se conservan. Ninguna dependencia, csproj, lock o política MFA cambia. El rol de ejecución de laboratorio sólo lee el testigo; propietario/mantenimiento escribe. Los instaladores anteriores siguen fijados a su esquema y no se actualizan con esta tanda.

Se publica un recibo legible por el servicio antes de liberar el fence. El guard contrasta su binding/testigo, activa, hash del archivo DPAPI y autenticación/versiones de factores. Rechaza base anterior, testigo ausente y factor antiguo aún auténtico. Un journal local ya completado sin su testigo DB no vuelve a ejecutar el commit: queda para un procedimiento Restore explícito.

El coordinador no expone rotación por HTTP/CLI pública. Su resultado interno `verified` es conciliación offline; no significa que se haya iniciado un servicio o completado el `verified` operativo de D2.

## Entorno y pines finales

Windows anfitrión; SDK10.0.401/runtime10.0.12, Npgsql10.0.3, PostgreSQL17.11; bases/clústeres nuevos. Fuente congelada bajo `.local/f0603-rotation-c32a5e0b/freeze`, binlogs únicos y logs privados. No se compiló sobre obj compartidos.

- Servidor: `610b3841446046ae2d5a17488376e57ef5bcfbd8652ffba6ceb3eacfad7f4685`.
- Pruebas: `0f28a021bb698b87b8402258078eee89c61f024528624da1992e5c7f7499ac76`.
- Build final:0 errores/0 advertencias.
- Regresión pertinente final:360/360,0 fallos/0 omitidas; incluye12 del adaptador,30 del publicador,4 del recibo, contratos y regresión F-06.02/host/escritor. No se presenta como regresión de todo RackClick.
- Tres negativos PG/publicación pasan sobre esos binarios: pérdida de backend después de data_verified y antes de liberar fence, y colisión ajena del recibo. Conservan fence/objeto ajeno y concilian después con intervención del fixture.
- Matriz final:15/15 cortes reales,15 reaperturas correctas y2 Restores correctos, sin omitidas, registrados en [MATRIZ-CAIDAS.json](MATRIZ-CAIDAS.json). Cada terminación intencional devuelve1; los verificadores de recuperación devuelven0. No son quince fallos del producto ni quince funcionalidades nuevas.
- Operadores/arnés Python:14/14 PASS sobre la DLL final, sin omisiones. Los rechazos de la CLI existente no ejecutan mantenimiento elevado ni acceden a servicios instalados.

`tools/tests/run_mfa_rotation.py` exige fuente aislada y ambos pines. Cada ejecución comprueba los binarios antes/después. El trabajador publica un marcador con flush y el padre termina únicamente el árbol de su propio Popen; nunca usa un PID de entrada como destino. No es una excepción simulada: mueren procesos, se liberan handles y la conexión SQL queda cortada.

## Comprobaciones

Se comparan los hashes de los secretos descifrados, los metadatos completos de factores y las filas de usuarios/política/códigos/Systemhaus. Versiones1/7 anteriores permanecen legibles e idénticas en disco; tras rotación la activa es8. Sesiones/desafíos afectados revocados/consumidos, antirreplay y estados conservados. Una segunda reanudación no vuelve a cifrar ni añade un testigo.

Restore usa pg_dump custom y pg_restore --single-transaction en otro clúster nuevo, con la identidad nativa explícita y material/journal propios aún conservados en este equipo. No adapta identidades ni prueba portabilidad DPAPI. La base origen se compara y conserva; la copia anterior al commit se concilia en destino y el origen ahora antiguo se rechaza por guard y coordinador. El posterior al commit continúa hacia delante.

## Rojos e intentos preservados

- Contratos iniciales:3/3 fallaron por componentes/migración ausentes. Antes hubo errores de invocación (`--locked-mode` en test), inputs del catálogo no copiados y un using Xunit omitido; esos intentos no cuentan como rojos funcionales.
- Primera prueba de proceso falló al preparar otra tienda profundamente anidada (Win323). Se sustituyó por una ampliación de15 líneas del escritor que reutiliza su DPAPI/formato en memoria; no se cambia el escritor nativo general ni se afirma resolver rutas largas de todo el producto.
- Primer arnés omitió owner.pgpass; se corrigió sólo el entorno. La primera ejecución Python no tenía el pin de DLL por variable: se conservan los errores y se repite con la entrada explícita.
- Regresión inicial360:344PASS/16FAIL por longitud del fixture histórico F-06.02. Se acortó únicamente la raíz del arnés. Segunda:355PASS/5FAIL por dos clases que compartían la misma DB en paralelo. Se añadió la colección serializada existente a la clase nueva; ninguna aserción histórica ni control de producto se relajó. Regresión final360PASS.
- La revisión detectó guard insuficiente para DB anterior/testigo perdido/factor viejo, posible reemplazo de un recibo ajeno y liberación de fence después de perder la conexión. Guard, identidad previa/publicada y revalidación de admisión se corrigieron; sus negativos se ejecutan con PG/ACL/objetos reales.
- Negativo adicional de operación local completada con DB anterior: rojo real `No exception was thrown` en fuente525ed…; la corrección añade un rechazo antes de volver a recifrar. El original y la prueba fallida se conservan privados. La reanudación del commit incierto se sigue decidiendo por el testigo, no por la fase del journal.
- Un trabajador que se auto-terminaba hacía esperar a VSTest antes de devolver. El arnés final termina su árbol propio tras el marcador; no se atribuye aquella espera al producto.

## Límites y aceptación

La custodia externa del ensayo es un archivo cifrado privado fuera del árbol de la instancia, en el mismo equipo de laboratorio: no acredita custodia de Wascar fuera del servidor ni almacenamiento físico independiente. Las claves/contraseñas/sobres/dumps/binlogs nunca se incorporan a esta evidencia. La puesta a cero es la del código y componentes existentes, no borrado universal de memoria.

No se hizo apagón, reinicio de Windows, ensayo elevado con SID efectivo de un servicio instalado, arranque/HTTPS/login de una instalación real o instalación limpia46. Las pruebas usan confianza y cuenta Windows de laboratorio. Flush/relectura y kills de proceso no prueban persistencia ante pérdida eléctrica. La rotación pública continúa sin habilitarse hasta completar esas condiciones.

No se declara terminado F-06.04, R-04, la integración de candidata, QA o adopción. La política y los datos de D/E permanecen intactos. [Revisión independiente](REVISION.md), [pines](FUENTES.json), [regresión](POSTGRES-REGRESION.json), [negativos](NEGATIVOS.json) y [diff respecto a la fuente anterior conservada](CAMBIOS.patch).

[Plan e investigación](../../../docs/PLAN-F0603-ROTACION-Y-CAIDAS.md) · [Ficha del paso](../../../docs/PASO-021-CAIDAS-ROTACION-MFA.md).


## Conciliación

Sólo F-06.03: +5/8.428/21→3529/168=21,005952…/100 del cierre restante,21,01 redondeado. Sin incremento por cantidad de pruebas, sin nuevos puntos/pesos ni cierre de hitos operativos F06. El porcentaje global del producto no se recalcula.
