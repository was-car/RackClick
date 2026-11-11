# Paso 21 · caídas durante la rotación MFA

10.11.2026 · F-06.03. Cerrado técnicamente con revisión independiente favorable. Se conserva D y también E: no se han usado VM, servicios, cuentas o bases instaladas.

## Qué añade

El coordinador interno reutiliza F-06.02 y el cifrado existente. Prepara una clave nueva, conserva las anteriores y publica primero un anillo que todavía usa la activa anterior. Sólo después de autenticar el sobre de recuperación externo recifra los mismos secretos TOTP en una transacción PostgreSQL, revoca las sesiones y desafíos afectados e inserta un testigo local en esa misma transacción.

El testigo permite distinguir un commit efectuado de una transacción abortada cuando desaparece el proceso. La recuperación posterior al commit continúa hacia delante; no vuelve a cifrar las filas ni reconstruye el resultado a partir del exit de consola. El guard de arranque contrasta un marcador de disco, el testigo, la versión activa y los factores. Una base antigua o incompleta queda bloqueada.

Se conserva la gracia de 45 días, la exención global, las identidades, estados pending/active/disabled, antirreplay, códigos de recuperación y autenticadores del usuario. La rotación no elimina ninguna clave anterior y no autoriza retirar versiones que necesitan los backups. El catálogo sigue limitado a todas las raíces retenidas declaradas y contrastadas por el operador.

## Prueba prevista y alcance

El arnés crea clústeres PostgreSQL17.11 y bases nuevas con esquema46. Detiene únicamente el árbol del proceso de pruebas que él mismo lanzó, cuando el trabajador ha publicado el marcador del punto de corte. No toma un PID de un servicio o de un archivo como objetivo del comando de terminación.

Se ensayan cortes antes y después de publicar la clave, los anillos aditivo/final y el recibo de arranque, además del commit, la verificación y la liberación del fence. En dos estados se obtiene un dump custom real y se restaura en otro clúster nuevo antes de conciliar; la base de origen se conserva. Se comprueban reapertura, secretos, metadatos, revocación, idempotencia, versiones antiguas y acceso SQL de ejecución sin escritura sobre el testigo.

La [evidencia del lote](../evidence/s1-20261110/f06-03-rotacion/RESULTADOS.md) registra pines, resultados finales, intentos fallidos y dictamen. El [plan y fuentes](PLAN-F0603-ROTACION-Y-CAIDAS.md) documentan la reutilización y las responsabilidades. Las pruebas anteriores se reutilizan para sus componentes, sin atribuirlas a este ensayo.

## Qué puedes hacer en D

Continuar utilizándola tal como está. **Este lote no entrega un botón, comando público de rotación ni instalador nuevo.** No hay que copiar DLL, SQL o archivos de claves a D; la candidata instalada conserva su versión. La migración046 sólo se ha aplicado a bases nuevas de laboratorio, sin editar001–045.

El resultado interno `verified` acredita conciliación offline y material/DB comprobados; no acredita los pasos `service_resumed`/`verified` del recorrido operativo completo de D2. Quedan pendientes candidata completa, permisos del instalador46, ensayo elevado con SID efectivo, custodia externa real, arranque/HTTPS/login de la instalación objetivo y QA/adopción. Los cortes de proceso no equivalen a pérdida eléctrica ni acreditan durabilidad universal del almacenamiento.

El cierre integral F-06.04 y la integración operativa R-04 siguen siendo pasos separados. Se acredita únicamente +5/8: el índice del cierre restante pasa de20,38 a21,01/100. No es un porcentaje global nuevo ni aceptación operativa.
