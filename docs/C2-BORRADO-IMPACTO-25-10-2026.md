# C2 · borrado individual y conjunto con impacto exacto

25.10.2026 · I-04.05. Se completa la cobertura técnica de las variantes existentes, reutilizando la DLL5eb1 y el frontend04f4 ya identificados. **No se necesitó cambiar el producto ni reconstruir artefactos.**

## Foco nuevo

La preparación SQL crea jerarquía, racks, Dose/finales y cables ficticios en un PostgreSQL17.11 nuevo. Los borrados se hacen por los controles reales de la GUI:

1. **Dispositivo final conectado:** Eliminar → vista previa. Se contrastan los cinco conjuntos por UUID: ningún rack, un dispositivo, un grupo, un puerto y sólo su cable incidente. Cancelar conserva el proyecto y, medido desde SQL mientras el navegador espera, inventario/cliente/operaciones/auditoría exactos. Reabrir y confirmar produce un solo commit.
2. **Lote mixto Dose + equipo de rack:** selección conservada entre vistas. La vista previa contiene exactamente esos dos dispositivos, dos grupos, cinco puertos y dos cables incidentes. Se muestra el extremo del equipo vecino, pero éste no se elimina. Cancelar conserva selección y estado SQL completo; confirmar después produce un solo commit del lote.
3. **Cable protegido:** un cable no incidente entre dos equipos conservados mantiene UUID, extremos, nota, color, patch y propiedades. Tampoco cambian los puertos ni metadatos no afectados, jerarquía, racks u objetos de otros clientes.

El navegador y el comparador SQL derivan los esperados de identidades y pertenencias originales; no se copia el impacto recibido del servidor como esperado. No se decide por nombre, posición visual o gn.

## Pruebas y resultado

- Ensayo nuevo Windows/Edge/PostgreSQL17.11: **PASS35,891s**. Cuatro barreras permiten a Python medir SQL después de la preparación, de cada Cancelar y del primer commit. Dos borrados confirmados, dos operaciones, una auditoría `inventory.device.delete` y otra `inventory.devices.delete`; revisión+2.
- Lector403 y usuario ajeno404 en preview y commit, tanto individual como conjunto: ocho rechazos sin cambios en inventario, cliente/revisión, operaciones o auditoría.
- Recarga, otra cuenta autorizada y reinicio del proceso servidor conservan exactamente el proyecto restante y el cable protegido. Laboratorios/procesos propios detenidos; fuentes/artefactos sin cambios durante las pruebas.
- Regresión existente de lote ejecutada de nuevo: **PASS27,984s**, con el mismo frontend/DLL. Incluye EN/DE/ES, vista previa/cancelación, lote mixto, selección obsoleta412 sin enviar un subconjunto, respuesta200 perdida y replay idéntico sin segundo commit, avisos/lectores, recarga y reinicio.
- Revisión distinta: tres focos propios en memoria sobre derivación/comparador y recibos; cambios indebidos de vecinos, UUID, metadatos, cables o extremos se rechazan. Confirmada la ausencia de tokens brutos en detalles publicados.

Se reutiliza además el soporte previo de permisos de borrado sin edición y las pruebas de impacto/API existentes; sus informes permanecen históricos y no se presentan como ejecuciones nuevas.

## Límites y siguiente paso

El foco nuevo usa español y controles DOM de navegador real; la regresión cubre los textos de tres idiomas. No se ensayó hardware táctil, Windows reboot, instalador, QA ni VM. Los secretos se generan en el laboratorio; confirmationToken, CSRF y cookies no se publican.

I-04.05 queda completado técnicamente con su peso fijo5/14 tras revisión independiente. **I-04.06/07**, integración en candidata final y aceptación siguen pendientes. No se habilitan casos QA ni cambia la GUI por añadir pruebas. [Evidencia y comandos](../evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md).

Claude inició MFA-L1 según informa Wascar; Codex no modifica sus archivos. C permanece cerrado y apagado según Wascar. Sin commits, push, build, paquete nuevo o adopción.
