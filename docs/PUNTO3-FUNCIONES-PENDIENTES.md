# Punto 3 · cierre de funciones pendientes

02.11.2026. Continúa los puntos 1 y 2, sin repetir el catálogo ni sustituir la candidata43 congelada. Esta tanda integra **dos recorridos completos en desarrollo**: códigos de recuperación MFA propios y exportación JSON del inventario actual de un cliente. No declara terminado todo el punto 3.

[Resultados y pruebas](../evidence/s1-20261102/punto3/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261102/punto3/review/REVISION.md) · [Decisión MFA vigente](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md).

## Qué funciona en esta tanda

| Recorrido | Comportamiento comprobado | Disponibilidad |
|---|---|---|
| Códigos MFA propios | Diez códigos aleatorios, generación con contraseña actual y sesión MFA completada; valores sólo en la primera respuesta y recibos sin códigos | Desarrollo con PostgreSQL 17.11 y Edge; no instalado en QA |
| Pérdida del autenticador | Contraseña, desafío de verificación y código guardado producen únicamente un desafío de enrolamiento nuevo; se revocan sesiones y todos los códigos anteriores | Sin acceso API hasta confirmar un autenticador nuevo |
| Inventario JSON por cliente | Instantánea de ocho colecciones, UUID, montajes y metadatos; confirmación del servidor, revisión, recibo y SHA256 antes de descargar | Requiere `inventory.read` y `reports.export` en el ámbito actual |

El catálogo sigue en esquema43, con las 506 identidades seleccionadas. No hay migración SQL ni dependencia nueva. Se reutiliza la tabla de códigos de recuperación de SQL014. Las cuentas y sus factores no salen en el JSON de inventario. Las notas y propiedades introducidas por personas sí salen: hay que revisarlas antes de compartirlo.

## Pasos para Wascar cuando se entregue la candidata completa

Estos pasos corresponden a QA-163 y QA-164, **todavía planificados para el servidor instalado**. No copies DLL o SQL ni apliques el ZIP de revisión del punto2 a una instalación existente.

### Generar y usar códigos MFA

1. Entra con tu cuenta y completa su MFA. En la barra lateral izquierda, abajo, debajo de tu nombre, pulsa **Mi seguridad**.
2. En el panel central despliega **Códigos de recuperación**. Escribe **Contraseña actual**, marca que generar códigos reemplaza los anteriores y pulsa **Generar diez códigos de recuperación**.
3. Espera **El servidor confirmó la generación**. Guarda los diez valores fuera del servidor mediante **Descargar mis códigos** o en tu medio privado de custodia. No los incluyas en capturas ni resultados de QA. Pulsa **Ya los guardé; ocultar códigos**. No se pueden volver a consultar; generar otro conjunto invalida el anterior.
4. Para la prueba, conserva tu autenticador anterior y usa una cuenta de laboratorio. Abre una ventana privada del navegador e inicia sesión con la misma cuenta. En la pantalla que pide el código del autenticador pulsa **Perdí mi autenticador**.
5. Introduce un código guardado y pulsa **Recuperar y configurar un autenticador nuevo**. Debe aparecer la configuración de un nuevo autenticador, sin dashboard ni acceso normal. Las sesiones antiguas dejan de servir.
6. Configura ese autenticador y confirma su código actual. Sólo entonces debe abrirse la aplicación. En **Mi seguridad → Códigos de recuperación** deben quedar cero códigos antiguos sin usar. Genera expresamente un conjunto nuevo y guárdalo.
7. Si se pierde la respuesta al generar, usa **Comprobar solicitud original**. Un recibo confirma el resultado, pero no vuelve a mostrar valores. No se genera otro conjunto automáticamente. El registro local conserva sólo identificadores de intención.

La política de 45 días y la exención del administrador global siguen vigentes. El administrador no puede ver ni generar los códigos de otra persona. El canje retira todo el conjunto antiguo, aunque se presente un solo código. La generación es una acción expresa después del enrolamiento; no se garantiza todavía que todos los administradores hayan guardado códigos.

### Exportar el inventario del cliente

1. Abre un cliente desde la barra lateral izquierda y entra en su vista de infraestructura/racks. En la barra superior del inventario pulsa el acceso a **Información e informes**; también puedes bajar a esa sección, situada después de los racks.
2. Pulsa **JSON de inventario**. Lee la advertencia sobre notas y metadatos y marca la casilla de aceptación del contenido.
3. Pulsa **Preparar JSON actual** y espera **Exportación confirmada por el servidor**. Antes de esa confirmación no debe habilitarse la descarga.
4. Pulsa **Descargar JSON confirmado**. Se vuelve a consultar el recibo con tus permisos actuales. En **Integridad y datos de origen** se muestran revisión y SHA256. El archivo tiene nombre basado en el UUID del cliente y la revisión.
5. Comprueba que conserva sitios, edificios, salas, racks, equipos, grupos de puertos, puertos y conexiones. Exportar no modifica ese inventario. Una cuenta sin `reports.export` no debe ver el control ni obtener el archivo por API.
6. Si el resultado es incierto, conserva la vista y pulsa **Consultar exportación original**. El reintento usa la misma solicitud. Cambiar de cliente, desmontar la vista o recargar pierde esta referencia local; el recibo permanece en el servidor. Esta limitación no se presenta como recuperación persistente de intención.

Formato `RackClickInventory-v1`, un cliente completo, hasta 4 MiB y 100.000 registros, sin truncamiento. No es el Full Backup original RC9, ni una copia PostgreSQL, ni existe todavía un botón de importar este formato. El límite de archivo no constituye un límite de memoria de la consulta que construye la instantánea.

## Pendientes del punto 3, sin añadir resultados al ledger

| Área | Lo que queda por hacer | Trazabilidad existente |
|---|---|---|
| Recuperación MFA operativa | Recuperación portable y emergencia local cuando no arranca el proveedor; rotación/rewrap, procedimiento del último administrador y ensayo bajo la identidad efectiva del servicio | F-05 a F-09, R-03/R-04 |
| Custodia de códigos | Completar la política operativa y el manual para que los administradores guarden material; no confundir generación disponible con custodia aceptada | F-07/F-10 |
| Administración | Conciliar permisos/global/cliente/técnico, reautenticación, último administrador y observaciones visuales con la matriz final de aceptación | A-02, F-10, REQ-UX-02/08 |
| Intercambio JSON | Importación del formato actual, compatibilidad con el JSON original, previsualización/merge, validación y destino seguro; recuperar intención después de navegación/recarga | P-01/P-03, R-04, REQ-UX-05 |
| Backup desde dashboard | Exportar/restaurar copia PostgreSQL con integridad, destino nuevo, progreso y custodia de seguridad/MFA separados | R-01/R-03/R-04, REQ-UX-05 |
| Entrega | Integrar lo revisado en una candidata nueva; punto5: operadores43, permisos SELECT-only del catálogo, New/Restore, servicio/HTTPS/backup/reinicio Windows y QA de Wascar | W-02/W-03, E-04/E-05 |

El laboratorio de 50 clientes sigue como el punto siguiente propio. La candidata de aplicación43 del punto2 y su ZIP permanecen intactos; estos cambios son una revisión posterior de desarrollo, no una actualización automática de la VM.

**Seguimiento:** selección del catálogo 506/506 (100% de ese conjunto); índice acreditado del cierre pendiente 9,76/100, conservado. No se calcula un porcentaje global nuevo ni se acredita aceptación por contar pruebas o botones.
