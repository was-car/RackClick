# Paso 4 · revisión de cierre de F-01

02.11.2026 · F-01.04.

Se contrastó el criterio completo con las pruebas existentes. **El cierre no puede acreditarse todavía:** falta resolver la observación de exposición que mantiene abierto el paso 2. No significa que haya una credencial activa comprometida ni que D deba reinstalarse.

| Parte del criterio | Resultado |
|---|---|
| Clasificar los hallazgos seleccionados | Verificado en el paso 1: 92 ocurrencias históricas y 90 metadatos relacionados, con solapamiento; no son 182 secretos distintos. |
| Resolver y tratar exposiciones efectivas | Pendiente del paso 2: se desconoce qué mostró la auditoría antigua. La respuesta «No lo sé» se conserva. |
| Registrar falsos positivos sin ocultar coincidencias futuras | Verificado en el paso 3. El registro no es una excepción del escáner. |
| Contrastar las fuentes y paquetes pertinentes | Se reutiliza el escaneo limitado de 118 fuentes congeladas. Los ZIP Windows 11 y cargador 02 conservan sus hashes; Windows 11 vuelve a pasar su verificador de 140 entradas. |

Las reglas, el hook, el escáner y su versión fijada siguen iguales. La prueba sintética del paso 3 se reutiliza; no se repitió. La huella actual de referencias Git difiere de la registrada entonces: queda anotada sin atribuir causa ni afirmar que todo el historial siga idéntico. Los ZIP contrastados conservan sus bytes.

**D queda intacta:** no se accedió a la VM ni a sus claves, cuentas, datos, servicios o MFA. Tampoco se repitieron instalación, carga de clientes o QA.

F-01.04 queda **en progreso**, con la evaluación registrada y sin crédito de cierre. Índice del cierre pendiente: **11,01/100**, sin incremento. No es un nuevo porcentaje global del producto.

Para cerrar F-01 falta evidencia saneada que permita disponer la observación del paso 2: identificar material/instancia/canal y, si corresponde, demostrar retirada y revocación coordinadas. Una inspección negativa de Git no resuelve lo que ocurrió fuera de él. No se pide enviar contraseñas ni volver a contestar la misma pregunta. Este pendiente no impide trabajar en otros pasos independientes del plan.

[Resultado técnico y revisión](../evidence/s1-20261102/f01-04-cierre/RESULTADOS.md) · [Plan numerado](PLAN-PENDIENTES-NUMERADO.md).
