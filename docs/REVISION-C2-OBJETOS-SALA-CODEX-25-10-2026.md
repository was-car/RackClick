# Edición de Dosen/finales · revisión de Codex · 25.10.2026

**Foco aceptado técnicamente tras reforzar la prueba.** Una ejecución independiente nueva en Windows, Edge y PostgreSQL17.11 pasa en **27,656 s**. Sin cambios de producto ni acceso a VM/QA.

## Auditoría aclarada

Los cuatro comandos son **cuatro en total**, no cuatro por objeto: dos `device.update` y dos `ports.update`. El desglose medido en la nueva base es:

| Acción | Eventos añadidos |
|---|---:|
| `inventory.device.update` | 2 |
| `inventory.ports.update` | 2 |
| `user.preference.set` | 1 |

El quinto evento corresponde a seleccionar español en la interfaz. No hay un quinto comando ni otra escritura de inventario: se comprobaron cuatro operaciones y cuatro incrementos de revisión.

## Refuerzo realizado sobre las pruebas entregadas

El comparador original excluía todo `properties` y sólo comprobaba dos notas. El revisor independiente demostró seis cambios indebidos de metadatos que la prueba aceptaba. Era una carencia de cobertura, no un fallo demostrado del producto.

Codex conservó los dos archivos originales y reforzó Python y navegador para comparar propiedades completas. La nueva preparación incluye color, un atributo adicional anidado y notas model/IP/firmware no vacías. Sólo pueden cambiar nombre, las notas editadas y el estado del puerto seleccionado; permanecen iguales UUID, sala, grupos, otros atributos/puertos y cables. El comparador contempla la normalización existente de notas conocidas ausentes a texto vacío; no presenta esa normalización como pérdida de metadatos.

El revisor volvió a ejecutar sus sensibilidades: control válido y normalización válida pasan; los seis cambios indebidos ahora se rechazan. No se modificaron frontend de producto, backend, soporte compartido ni artefactos.

## Resultado y límites

- GUI: Dose y dispositivo final editados; cuatro respuestas200 y confirmación de guardado. Un estado de puerto por objeto, sin usar rol eléctrico sobre RJ45.
- Base: nueve tablas comparadas exactamente. Cuatro auditorías de inventario y cuatro operaciones, más la preferencia de idioma explicada.
- Usuario lector403, usuario ajeno404 y nombre vacío422. Los rechazos conservan inventario, cliente/revisión, operaciones y filas de auditoría completos.
- Recarga, segunda cuenta autorizada y lector devuelven el mismo proyecto; persistencia tras reiniciar el proceso servidor. Laboratorio/procesos detenidos y entradas sin cambios al terminar.

Se conserva como evidencia la ejecución de Claude PASS25,968s. La nueva ejecución no se presenta como suya, y sus hashes originales no se sustituyen por los de las pruebas reforzadas.

Sólo español y un puerto/estado por objeto. No acredita todos los roles de energía, campos, plantillas, borrado/impacto, matriz de idiomas ni todo I-06. I-06.02 queda **en curso**, con este foco aceptado; no se añade crédito parcial inventado. Cierre ponderado del pendiente: **5,86/100**, sin cambio; porcentaje global sin recalcular.

[Evidencia y revisión distinta](../evidence/s1-20261025/c2-room-object-codex/CIERRE.md). Claude puede seguir con [MFA-L1](MENSAJE-PARA-CLAUDE-MFA-L1-25-10-2026.md); Codex mantiene borrado e impacto. La VM C sigue cerrada y apagada según Wascar.
