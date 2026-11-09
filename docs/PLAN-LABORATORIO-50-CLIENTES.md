# Laboratorio integral de al menos 50 clientes sintéticos

**Estado vigente ·02.11.2026:** Demo50 preparada y verificada, con revisión independiente. 50clientes,66sitios/88edificios poblados,180racks y868parejas perfil/revisión;21unit/13focosindependientes,PG17.11/Edge/10usuarios ybackuprestaurado a destino nuevo. [Manual y datos](LABORATORIO-50-CLIENTES.md). Los estados de planificación y coberturas siguientes se conservan como historia. Integración opcional en el instalador yQA delpunto5 pendientes.


**Actualización de cobertura · grupo G, 01.11.2026:** 368/506, 138 pendientes; 723 comerciales en desarrollo. Las entradas anteriores son historia. El laboratorio de 50 clientes sigue planificado para después del catálogo completo.


**Actualización de cobertura · grupo F, 01.11.2026:** 318/506, 188 pendientes; 673 comerciales en desarrollo. Las entradas anteriores son historia. El laboratorio de 50 clientes sigue planificado para después del catálogo completo.


**Actualización de cobertura · grupo E, 01.11.2026:** 268/506, 238 pendientes; 623 comerciales en desarrollo. Las entradas anteriores son historia. El laboratorio de 50 clientes sigue planificado para después del catálogo completo.


**Actualización de cobertura · grupo D, 01.11.2026:** selección 218/506, 288 pendientes; catálogo 573 comerciales en desarrollo. Las cifras 68/506 del planteamiento original se conservan como historia. El laboratorio de 50 clientes sigue planificado para después de completar todos los perfiles.

01.11.2026 · Petición de Wascar. **Planificado; base y generador todavía no creados.**

Se ejecutará después de completar e integrar los 506 perfiles elegidos. El objetivo es entregar una base PostgreSQL con al menos 50 clientes distintos, infraestructuras variadas y equipos conectados, acompañada de pruebas que demuestren su funcionamiento. No basta con que los registros existan en la base.

## Alcance y orden

1. Completar los perfiles y sus contratos de conectores, configuración y montaje. El estado actual sigue siendo [68/506 y 438 pendientes](COBERTURA-MODELOS-ELEGIDOS.md); este plan no lo incrementa.
2. Congelar la candidata y el manifiesto de perfiles disponibles. La matriz incluirá los 506 elegidos y los perfiles adicionales disponibles en esa candidata, además de los soportes sintéticos necesarios. No se amplía la lista de fabricantes como parte de este encargo.
3. Crear el generador y aprovisionar una base PostgreSQL 17 nueva e independiente, con cuentas y secretos generados localmente. Conservar los diez clientes originales, el backup aportado y la instalación actual de Wascar.
4. Crear y conectar las infraestructuras mediante los comandos autorizados del servidor. Usar SQL administrativo sólo para inicialización y comprobaciones; no insertar directamente equipos o cables para eludir las validaciones que se quieren probar.
5. Ejecutar las pruebas, corregir fallos, obtener revisión independiente y preparar el conjunto opcional de demostración para el paquete completo. Wascar realizará su QA con una guía por módulos y clientes representativos.

Responsabilidad del conjunto y su medición: **E-06** (demo completa y carga real), relacionado con **E-05** (QA), **C-HW-05** (prueba por perfil), **I-03/I-05/I-06** (conectores, conexiones y objetos de sala) y **R-04** (recuperación). No se crean pesos ni puntos por cada cliente o prueba.

## Distribución inicial de escenarios

| Escenario | Clientes | Diferencias que debe representar |
|---|---:|---|
| Oficinas pequeñas y comercios | 10 | Un sitio, un rack pequeño, firewall sobre bandeja cuando corresponda, switch, patch panel, Dosen y terminales. |
| Empresas medianas | 10 | Varios edificios o plantas, racks de distribución, NAS, servidores, UPS y PDU. |
| Empresas con varias sedes | 8 | Dos o más sitios por cliente, racks separados y enlaces documentados entre ubicaciones del mismo cliente. |
| Centros educativos | 6 | Aulas, salas técnicas, laboratorios, puntos de acceso y reparto de permisos. |
| Entornos industriales | 6 | Armarios y equipos de los tipos realmente soportados; DIN, lateral 0U o fracciones sólo con su contrato implementado. |
| Centros de datos | 6 | Core/acceso, almacenamiento, servidores y alimentación redundante sólo donde esté documentada y soportada. |
| Laboratorios y servicios mixtos | 4 | Diversidad de fabricantes, medios y estados; variantes EN/DE/ES y nombres Unicode sin traducir los nombres del usuario. |
| **Total mínimo** | **50** | Clientes ficticios con jerarquías e inventarios diferentes, no cincuenta copias del mismo proyecto. |

Todos tendrán sitio/edificio/sala/rack cuando su escenario lo requiera. La cantidad total de racks, equipos, puertos y cables se fijará al generar el conjunto desde el catálogo final; no se inventa una cifra ahora. Los modelos se repartirán por categoría y uso, sin instalar un NAS, una PDU o un chasis en una ubicación incompatible sólo para completar la tabla.

## Cobertura obligatoria por perfil

- Al menos una instancia de cada perfil disponible y revisión publicada que forme parte del alcance, ligada a su clave, SKU, configuración y fuente. Las correspondencias de nombres no crean perfiles ni contabilizan instancias nuevas.
- Matriz: perfil/revisión/configuración → cliente/sitio/sala/rack → UUID del equipo → grupos y puertos → conexiones → prueba → resultado y evidencia. Los totales declarados se contrastan contra el inventario persistido y el manifiesto congelado.
- Creación, montaje y ocupación válidos; frontal y trasera conservan los mismos extremos al cambiar de vista. Incluir sobremesa y bandejas, equipos de rack, Dosen y finales, así como los montajes especiales efectivamente implementados.
- Al menos una conexión compatible por familia operativa presente en cada perfil/configuración, con cobertura separada de todas las entradas y salidas de alimentación materializadas. Añadir recorridos Click-Click por GUI, enlaces entre caras, racks y salas del mismo cliente, guardado confirmado, recarga y segunda sesión.
- Puertos sin cable también son casos válidos: libre, reservado, averiado o deshabilitado según contrato. No es necesario ocupar todos para aparentar una infraestructura real.
- Consolas, USB, DC, módulos opcionales y otros elementos declarados inertes no reciben cables ficticios. Un chasis sin extremos operativos se prueba por creación/montaje y ausencia de puertos inventados; su conexión se marca **no aplicable con motivo**, nunca Pass sin ejecutarse. Si el objetivo del perfil exige un módulo aún no implementado, se registra como pendiente y bloquea su cierre.
- Probar rechazos de medios o roles incompatibles, doble ocupación, montaje inválido y cruces entre clientes. La base de demostración queda coherente; los negativos se ejecutan aparte y deben terminar sin cambios persistidos.

Presencia, funcionamiento y revisión visual son estados separados. Ningún porcentaje del catálogo se declara validado porque el mismo generador haya contado sus propias filas. La revisión independiente contrasta los datos esperados y las fuentes físicas, además del resultado del sistema.

## Persistencia, permisos y carga

- Administradores globales, administradores de cliente, técnicos, lectores y cuentas sin acceso, mediante grupos y ámbitos reales. Las contraseñas no se publican; la política MFA vigente de gracia de 45 días y exención global se conserva.
- Lectura y escritura autorizadas por el servidor; aislamiento entre los 50 clientes y un fixture adicional de otro Systemhaus. Un usuario sin ámbito no obtiene datos ni modifica objetos aunque conozca sus UUID.
- Conflictos de edición, reintentos con la misma clave de idempotencia, rollback forzado y auditoría con el actor correcto. Sin éxitos visuales anteriores al commit.
- Reinicio del host y, en el ensayo Windows, reinicio del sistema. Comparar UUID, revisiones, montajes y extremos antes y después. Backup y restauración a otra base nueva, con revocaciones y seguridad según el contrato de recuperación vigente.
- Medir listado de clientes, apertura de proyectos/racks, búsqueda, guardado e informes con el volumen real. Registrar p50/p95, tamaños de respuesta y entorno. Mantener la prueba de diez usuarios simultáneos de E-06: **50 clientes no equivale a 50 sesiones concurrentes**. Los presupuestos de rendimiento se fijarán antes de aceptar las mediciones, con el entorno identificado.
- Recorrer ES/DE/EN y conservar nombres propios y etiquetas. La cobertura automática evita exigir a Wascar que repita manualmente cientos de altas; su guía seleccionará recorridos representativos y permitirá ampliar cada modelo.

## Reproducción y entrega

Reutilizar el inventario de ejemplo y el cargador actuales como referencia, sin multiplicar UUID ni cambiar silenciosamente sus límites. [development/examples/README.md](../development/examples/README.md) describe los diez clientes originales y su carga vacía en esquema 15; **no debe darse por compatible con el catálogo final sin adaptarlo y probarlo**. También se consultará `tools/prepare_rc9_demo_load.py`, que prepara inventario y no es un backup PostgreSQL completo.

El nuevo generador deberá tener semilla/versionado reproducibles para los datos de inventario, manifiesto con hashes y conteos, validación previa e informe de carga. Las claves de cuentas, sesiones y MFA se generan de forma aleatoria y local; nunca se derivan de la semilla de demostración. Una segunda ejecución debe detenerse o devolver el mismo resultado confirmado, sin duplicar ni sobrescribir una base existente. Si falla una carga, no se entrega como lista: se conserva el informe y se recupera mediante el procedimiento definido.

Entregables previstos:

1. Generador, manifiesto e instrucciones repetibles para una base de laboratorio nueva.
2. Inventario sintético portable con al menos 50 clientes y sus conexiones, sin usuarios, sesiones, factores MFA o secretos reales. Carga opcional claramente identificada en el paquete completo; no poblar una instalación de producción de forma implícita.
3. Copia PostgreSQL de laboratorio para recuperación, privada y comprobada en un destino nuevo. Se distingue de la exportación de inventario y se protege conforme al contenido de seguridad que incluya.
4. Matriz de todos los perfiles, resultados automáticos, rechazos y revisión independiente; los casos no ejecutados quedan visibles.
5. Guía QA de Wascar con ubicación, botón, acción y resultado esperado, filtros por cliente/modelo y exportación de Pass/Not Pass/observaciones sin sobrescribir sus notas anteriores.

No se crea ni se modifica una DB por registrar este plan. No se ejecutan ahora instalaciones, cargas o pruebas nuevas de PostgreSQL. Índice de cierre restante **9,76/100**, sin crédito por planificación. La ejecución queda después de completar e integrar los perfiles, como pidió Wascar.
