# Paso 20 · inventario y conservación de versiones MFA

09.11.2026 · **F-06.02 cerrado técnicamente, con revisión independiente y crédito5/8.** D y E se conservan sin operaciones. No necesitas ejecutar comandos o proporcionar secretos. Los tramos iniciales siguientes conservan su estado histórico; el cierre vigente está al final.

## Qué está implementado

- Un lector agregado de PostgreSQL que incluye factores `pending`, `active` y `disabled`, con todos los usuarios de la DB. Exige transacción read-only y RepeatableRead/Serializable; no lee el secreto TOTP ni su ciphertext. No supone que un GUID de entrada autentique la conexión.
- Inspección autenticada del sobre RCKEY/RCKPAY existente: devuelve instalación, versiones, activa y SHA256, sin devolver claves. Su anillo ya incluye el inventario completo dentro del contenido cifrado; no se cambia ese formato.
- Inventario lateral de backup ligado por hashes al manifiestoSQL, dump y sobre, más un pin propio procedente de un registro privado independiente. Incluye las versiones de factores y la activa del sobre como requeridas, incluso con cero factores. Es externo a la carpeta histórica de dos archivos, que mantiene sus ocho campos cerrados.
- Una guarda de candidata sin referencias: activa, factor de cualquier estado, backup retenido, dependencia ausente, catálogo incompleto, ámbito ajeno o entrada inválida impiden el resultado positivo. Lista vacía no significa catálogo completo por defecto. Parser y modelos son acotados, de campos exactos y colecciones copiadas.

[Contrato, investigación y límites](CONTRATO-INVENTARIO-RETENCION-MFA-v1.md).

## Qué significa el resultado

`CandidateUnreferenced` sólo describe el inventario suministrado. **No es permiso para borrar una clave ni prueba de que el inventario siga vigente.** No hay un comando de retirada o publicador del anillo instalado. F-06.03 debe aportar coordinador, exclusión/fence, recenso, registro de backups fiable y publicación recuperable para ejecutar una retirada real. Un backup antiguo sin inventario verificado bloquea la decisión; no se inventa una lista vacía.

En la primera tanda no se modificaron Program, endpoints, SQL, proveedor/writer, perfil del sobre, manifiesto histórico, instaladores o D. Las claves activas y versiones necesarias para backups siguen conservadas. La continuación siguiente sí integra una CLI temprana en Program.

## Evidencia de esta tanda

Pruebas de componente y sobre real sintético en memoria; lector real con PostgreSQL17.11 y roles nuevos sólo SELECT; inventario lateral generado contra un dump real de un laboratorio quieto, sin escritores concurrentes. La comprobación nativa del backup acepta los dos archivos y sigue rechazando un tercero. No demuestra un snapshot concurrente dump/DB/disco, custodia externa real, borrado de almacén vivo o caída de Windows.

[Resultado y contabilidad](../evidence/s1-20261109/f06-02-retencion/RESULTADOS.md) · [Dictamen independiente](../evidence/s1-20261109/f06-02-retencion/review/DICTAMEN-F0602.md). La revisión confirma los componentes y sus pruebas, pero exige la acción nativa de retirada y la publicación/consumo del inventario confiable para cerrar el texto literal. Se conserva el peso5/8 sin acreditarlo; el índice sigue en **19,76/100 del cierre restante**.

## Continuación nativa · 09.11.2026

- CLI local `--mfa-backup-inventory` antes de construir el host: snapshot PostgreSQL read-only y verificación del inventario contra pines externos, sin listener o composición de claves del servicio.
- Operadores Windows nuevos para crear y verificar un backup con inventario lateral. Conservan el formato SQL cerrado en `database/`, publican un recibo privado separado y mantienen `catalogComplete=false`/`retirementAuthorized=false`.
- Identidad de DB/owner/rol por UUID, permisos de backup cerrados, protocolo acotado y diagnósticos sanitizados. Herramienta y dependencias pineadas/retendidas durante el hijo; se rechazan reparse, contenido alterado y destinos existentes.
- Dump e inventario comparten snapshot exportado. La prueba actual sí incluye un escritor que confirma después del snapshot y una restauración a otra DB sintética: estados/recuentos/versiones del dump coinciden con el censo anterior. Se contrastan además las filas completas de factores del origen antes/después del operador.

[Manual técnico](BACKUP-MFA-CON-INVENTARIO-DESARROLLO.md) · [Resultado nativo y revisión](../evidence/s1-20261109/f06-02-nativo/RESULTADOS.md). Se reutilizan los componentes ya probados;138casos de regresión pertinente y13Python, sin omitidas, más8controles nativos PG17.11. No se atribuyen ejecuciones HTTP/GUI/TOTP, DPAPI, token real, Windows Server, cortes o retirada de claves a este recorrido de metadatos. D/E no se operaron ni se actualizó un instalador.

Continúa pendiente integrar la retirada con el coordinador/fence/guard/publicador de F-06.03, cerrar el catálogo autoritativo de **todos** los backups y probar su aplicación real ante dependencias/cortes. Los backups históricos sin inventario no se convierten en catálogo vacío ni expiran. Después se vuelve a evaluar F-06.02; permanece en progreso, +0, con el índice **19,76/100 del cierre restante**.

## Cierre técnico posterior · catálogo y retirada

Ese pendiente técnico ya está implementado: catálogo privado con declaración de todas las raíces retenidas, recibos/pines y escaneo exacto; nuevos, desconocidos, legacy o alterados bloquean. Coordinador offline con exclusión local/PG, ACCESS EXCLUSIVE y recenso, autenticación de factores, fence/journal, publicación verificada y resume idempotente. La versión deja de entregarse por GetKey; el archivo DPAPI se conserva. No es rotación/recifrado o destrucción criptográfica.

**297/297** en la regresión pertinente final, **8** controles de backup nativo y **18** Python/PowerShell; revisor distinto ejecutó153focales correctos (sin sumarlos como funciones nuevas). [Evidencia y límites](../evidence/s1-20261109/f06-02-retirada/RESULTADOS.md) · [Dictamen final](../evidence/s1-20261109/f06-02-retirada/REVISION.md) · [Manual](MANTENIMIENTO-CATALOGO-Y-RETIRADA-MFA.md).

Sólo F-06.02 pasa a `done`,+5/8; índice **20,38/100 del cierre restante** (428/21). Se conservan pesos, criterio, estructura y todos los hitos operativos pendientes de F06. No se descubre una raíz externa omitida por el operador; no se permite ignorar un backup desconocido para retirar.

Quedan aparte el positivo CLI elevado/SCM contra servicio instalado y cuenta efectiva, paquete/QA/adopción y F-06.03/F-06.04: rotación, testigo DB y caídas reales. Los cortes actuales son excepciones de ensayo; no acreditan todos los cortes de proceso/alimentación. No se desplegó ni modificó D/E.
