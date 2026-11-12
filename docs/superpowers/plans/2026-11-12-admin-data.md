# Administración de datos e inventario · plan de implementación

> Ejecutar por tandas con archivos asignados y revisión independiente, sin operaciones sobre VM. La autorización de Wascar incluye actualizar GitHub y preparar su siguiente instalación limpia.

**Goal:** cargar los50clientes y exportar/restaurar su inventario desde Administración.
**Architecture:** partial InventoryStore transaccional y endpoints del pipeline actual; panel React reutiliza API/sesión/journal; distribución48 nueva y transporte20.
**Tech Stack:** .NET10.0.401/Npgsql10.0.3, PostgreSQL17.11, React/esbuild0.25.10, Node24.21.0.
**Spec:** `docs/ADMIN-DATOS-COPIAS-INVENTARIO-12-11-2026.md`.

## Global Constraints

Preservar A/B/D/E, cuentas y MFA; sólo inventario vacío. Archivo32MiB/100000filas/500clientes. Autoridad global comprobada en servidor. Sin DDL, nueva biblioteca ni relajación de Restore48. Datos Demo50 ya versionados. No compilar/publicar el árbol concurrente de la raíz.

## Review Focus

Permisos revocados y rutas genéricas de recibos; bloqueo de revisión mientras importación; pérdida de respuesta con replay; claves de propiedades duplicadas y referencias/modelos inválidos; archivo que excede el límite antes de asignación.

### Tarea1 · Servicio y contrato HTTP

- [ ] Añadir pruebas primero: vacío/Demo50, archivo round-trip, seguridad invariable, rechazo de permisos/archivo/capacidad/concurrencia y rollback de auditoría.
- [ ] Ejecutar rojo significativo; implementar partial y recursos Demo50 verificados; endpoints y límites cerrados en Program.
- [ ] Ejecutar verdes PostgreSQL y HTTP con rol restringido; conservar resultados privados y evidencia sanitizada.

Files: `InventoryDataAdministration*.cs`, `Program.cs`, `PostgresStore.cs` (sólo guardia de tipo), csproj (sólo recursos), pruebas nuevas.

### Tarea2 · Panel EN/DE/ES

- [ ] Contrato API y journal, pruebas primero de permisos/recibos/hash/respuesta incierta.
- [ ] `AdminInventoryData.jsx` y acceso desde Administración, con carga50, copia y archivo de restauración/previsualización.
- [ ] Pruebas Node y navegador real contra PG; conservar UI RC9 y nombres.

Files: componente/API/words nuevos; `AdminUsers.jsx` y `AdminSectionNavigation.jsx` para integrar.

### Tarea3 · Entrega

- [ ] BuildRelease único estabilizado y frontend; manifiesto cerrado48 nuevo, operadores actuales, servicio exacto.
- [ ] Transporte20 reproducible desde inputs explícitos; pruebas de integridad y exclusividad, dependencias oficiales descargadas en destino.
- [ ] Revisión independiente, QA/manual/CHANGELOG/CONTINUIDAD; escaneo fuentes/activos sin secretos.
- [ ] Publicar nueva Release con hash y volver a descargar. Conservar19 e instalaciones existentes; entrega de pasos autónomos a Wascar. No cerrar QA nativa sin su ensayo.
