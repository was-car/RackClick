# F-04 · matriz de cierre técnico

03.11.2026. Criterio congelado: «Servicio real lee/descifra y verifica factores; otra cuenta no lee, servicio no escribe ni modifica ACL, management no se amplía; negativos y revisión independiente registrados». F-04.04 añade la revisión del conjunto; no exige volver a ejecutar cada prueba ni modifica ese criterio.

## Cobertura por obligación

| Obligación | Evidencia reutilizada y contraste actual | Resultado y límite |
|---|---|---|
| Custodia definida antes de componer el proveedor | Decisión25.10, F-03.02/.03 y política29.10. Se conserva el almacén fuera de PostgreSQL/management y la confianza SYSTEM/Administradores | Decisión confirmada, no nueva aprobación ni aislamiento frente al administrador o servicio comprometido |
| Almacén seguro desde creación y publicación inicial completa | F-04.01: writer `76e6dfc3…`, descriptor pasado a Win32 desde creación exclusiva, publicación completa y preservación posterior. Rojo5/3controles, verde8 y regresión195; revisión independiente16.NET/8Python | Fuente actual coincide con la revisada. No afirma durabilidad ante corte, transacción disco/DB ni que D tenga esta corrección |
| Servicio estándar real lee y descifra | C10: init elevado, proveedor Windows en servicio estándar. D11 refuerza SID real/arranque; no se convierte la sonda SQL de E en prueba de descifrado | Se reutilizan ejecuciones nativas existentes; no se abre material privado ni se lee una clave en esta tanda |
| Verificación real del segundo factor | C10: confirmación y nuevo login verify por HTTPS con proveedor real; repetición posterior al reinicio. EnsayoB conserva401 posterior y no se cuenta como flujo completo; ensayoC y postboot son los positivos | Wascar comunicó satisfacción con MFA administrativo, sin atribuirle toda la QA manual o una aceptación de producción |
| Otra cuenta estándar no lee el almacén | F-04.02: dos tokens de servicios distintos de E; matriz30objetivos por actor. Lecturas propias/comunes16permitidas y ajenas/management44denegadas con error5 | Incluye acceso cruzado de ambas instalaciones; SYSTEM sólo obtiene/suplanta el token, no se presenta como lector efectivo |
| Servicio no escribe ni cambia permisos | F-04.02:444solicitudes de derechos de modificación denegadas con error5, incluidas WRITE_DAC/WRITE_OWNER/DELETE y derechos de directorio | Aperturas OPEN_EXISTING sin modificación efectiva; cero concesiones inesperadas o errores inconcluyentes |
| Management y padres no se amplían; herencia/reparse controlados | Dos management y14archivos, padres comunes/privados, propietario/DACL y rutas contrastados;32metadatos nativos y30ACL PowerShell sin cambios | Cuatro hashes entre APIs difieren por orden observado de Allow; permisos equivalentes y comparación antes/después por cada API. No se afirma igualdad entre sus serializaciones |
| Clave/versión/almacén ausente no regeneran ni abren sesión alternativa | F-04.03:39resultados históricos del host Passed, negativos de arranque sin listener y pérdida de activa durante ejecución con503/sin sesión/factor/consumo | Composición, proveedor, lector, anillo y dos archivos de pruebas conservan hashes. La fuente del host no crea el almacén al arrancar |
| Correspondencia de fuente y evidencia | `CONCILIAR-EVIDENCIA.py`:99referencias, sellos anteriores30/54verificados antes de editar planes,7recibos de F-04.03 y writer revisado. `CONTRASTE-NUCLEO.json` añade identidad de MfaStore, Enrollment, cipher y login frente a la copia compiladaC10. Se conserva diff de Program | Program cambió por SQL protegido, recuperación por código y mapping de exportaciónJSON. Segmento de composición/resolución MFA idéntico; Program actual coincide con manifiesto45. No se atribuye a toda la DLL actual el ensayo históricoC10 |
| Revisión independiente del conjunto | `review/DICTAMEN-F0404.md`, revisor distinto del implementador; debe contrastar esta matriz y los límites antes del crédito | Pendiente de dictamen final al redactar la matriz; el ledger no se modifica antes de recibirlo |

## Hitos: cierre técnico y entrega

Propuesta para conciliar los hitos descriptivos sin cambiar sus pesos ni el criterio:

- `definition_confirmed`: cumplido por decisión y condiciones técnicas ya confirmadas.
- `implementation_complete`: cumplido para el proveedor/almacén/validación de F-04 en fuentes; no engloba recuperación portable/rotación.
- `technical_tests_same_scope`: cumplido por las pruebas afectadas de creación, los positivos nativos reales, negativos del host y matriz efectiva de E. Es evidencia compuesta de alcances trazados, no ensayo de un único instalador nuevo.
- `independent_review_same_scope`: sólo cumplido cuando se emita el dictamen del conjunto.
- `integrated_current_candidate`: **pendiente**. La corrección del writer03.11 no se ha incorporado/ensayado en una candidata completa nueva. La integración previa del proveedor C10/D11 sigue siendo válida para su tramo.
- `target_acceptance`: **pendiente** como aceptación final de la entrega. La confirmación de custodia y la observación administrativa de Wascar no se convierten en un PASS de todos los casos manuales.

El cierre técnico de F-04.04 no altera los hitos pendientes de distribución/aceptación ni acredita W/R/E por arrastre. No se renueva la instalación de D para hacer coincidir artificialmente todos los ensayos históricos con un mismo binario.

## Lo que este resultado no cierra

F-05 recuperación portable, F-06 rotación/coherencia disco-DB, F-08 códigos y F-09 emergencia conservan sus propios criterios; tener rutas/componentes parciales no los acredita. También conservan sus criterios la candidata completa Windows, New/Restore, backups con MFA y QA final. Gracia45/exención global, ámbitos y fechas no se cambian. No se reclasifica un login autorizado por gracia como verificación MFA.

## Métrica propuesta

Sólo F-04.04 pasa de pending a done tras revisión favorable, **5/8 =0,625 puntos**. De2689/168 a1397/84 =**16,63/100** del cierre restante. Los tres subpasos anteriores conservan su crédito; no sumar39/195/504pruebas como tareas. F-04 quedaría cerrado técnicamente, con integración final y aceptación todavía explícitas en sus hitos. Pesos, criterios,53resultados/280checkpoints/268números y huella congelada sin cambios.
