# Paso 32 · pérdida de claves y recuperación MFA

11.11.2026 · **F-09.04 cerrado técnicamente**, con revisión independiente favorable. D se conserva. E conserva sus instalaciones anteriores y recibe únicamente un laboratorio separado.

Se ensayó la pérdida de todo el material del anillo del laboratorio: su única clavev1, sin copiarla antes de retirarla. Se conservaron anillo, catálogo e identidades fiables. El arranque normal se detuvo con `mfa_keystore_version_missing`, sin listener HTTPS.

La CLI local ejecutó cinco fases explícitas: preparar, exportar el material nuevo a un sobre privado, aplicar la transición SQL, publicar y completar. Mantenimiento bajo SYSTEM real, servidor bajo cuenta Windows estándar. Ninguna fase del CLI concedió sesión ni afirmó que el servicio ya estuviera recuperado.

Después arrancó el servidor con clavev2. El ensayo comprobó HTTPS/pin/nombre, rechazo de la sesión anterior y de solicitudes antiguas, revocación SQL y conservación del cliente/rack/equipo sintéticos. La contraseña sólo permitió enrolamiento restringido: **el acceso volvió después del TOTP nuevo**, con sesión y CSRF nuevos.

## Cambios

- Finalización y recibo de arranque ligados al testigo SQL, instalación y material publicado; retirada del fence propio por identidad sólo tras verificarlo todo.
- Migración48: vista pública no actualizable con metadatos mínimos, sin acceso runtime al archivo privado de factores ni DDL.
- Guarda de arranque que contrasta pérdida/rotación y rechaza incoherencias antes del listener.
- `--mfa-emergency-recovery`: autoridad Windows anterior a stdin, JSON cerrado/acotado, confirmaciones explícitas y sobre fuera de instancia/backups. Sin ruta web alternativa ni sesión desde la CLI.

Regresión pertinente: **378/378 PASS**, sin omitidas. Repetición independiente de componentes: **40/40 PASS**. El ensayo Windows real se distingue de esas pruebas; se conservan también sus intentos fallidos. El cliente HTTP final es Administrador Windows con contraseña/TOTP de aplicación; el mantenimiento es SYSTEM y el servidor sigue siendo estándar.

Se detuvieron sólo los dos servicios del ensayo y quedaron cero tareas temporales propias. Los dos servicios anteriores de E conservan sus procesos Running. No se apagaron VM ni se cambiaron snapshots.

**No es un instalador48 ni una actualización de D.** F-09.05, integración/operadores/manual de entrega, mantenimiento positivo Admin sin SYSTEM, custodia física externa, segunda pérdida independiente, retirada posterior sin nueva rotación y aceptación final siguen pendientes. No se ensayaron pérdida de todos los metadatos, namespace nuevo, apagón o reinicio Windows.

[Resultados](../evidence/s1-20261111/f09-04-ensayo-perdida/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f09-04-ensayo-perdida/MATRIZ-CRITERIO.md) · [recibos](../evidence/s1-20261111/f09-04-ensayo-perdida/NATIVO.json) · [dictamen](../evidence/s1-20261111/f09-04-ensayo-perdida/review/DICTAMEN.md).

Sólo F-09.04 acredita **1/2 punto**: **26,13→26,63/100 del cierre restante**. No es un porcentaje global nuevo del producto. Siguiente: **33 / F-09.05**.
