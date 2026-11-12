# Publicación Windows Online20 · datos desde Administración

12.11.2026 · aplicación48, panel de inventario nuevo y candidato de pruebas.

Release prevista/verificada al cerrar: [windows-online20-schema48-admin-data](https://github.com/was-car/RackClick/releases/tag/windows-online20-schema48-admin-data). Descarga pública, sinGitHubCLI ni autenticación. La visibilidad pública ya existía al observar el repositorio; esta tanda no cambia su visibilidad. La edición19 permanece.

- Outer público `RackClick-Windows-Online-20.zip`:11.555.659bytes/63archivos, SHA256 `2644dc115ed03086a5a1d60b5e6418989350ebaf08942e8c07d81a5bdda813fb`.
- Aplicación: manifiesto `f7b971f31dd5f424dbce35c9c18a4c6c75c8968f31d10c5df8bbfe215e5b8a53`,76archivos/35.919.405bytes; DLL768df75e yfrontend03537b7f. SQL001–048 ylocks intactos.
- Native20 ybundle sólo privados: reconstruidos con dependencias oficiales, no se alojan como activos. Core sólo propio/avisos, sin runtime.NET/SDK,PG,CRT niPython.

Desde Administración → Datos y copias de inventario: cargar50clientes sobre vacío, crear/descargar copia global y previsualizar/restaurar esa copia sobre otro vacío. Una transacción, UUID/montajes/puertos/cables preservados; cuentas/MFA/permisos no se importan. Solicitudes propias recuperables y cancelación expresa; no retryautomático. Enlaces ypasos [manual EN/DE/ES](INSTALACION20-PASO-A-PASO.md).

Backend18/18 actuales yrevisiónPG independiente; regresión868PASS/107SKIP se ejecutó antes de la corrección focal de dos fuentes nuevas. Ocho casos F0505 se excluyeron expresamente porque sufixture histórico se fija a esquema45; no se presentan como verdes de48. La aserción antigua PhysicalMedia45 se alineó a48, que ya eraLatestVersion enHEAD. Node411/411, Edge de integración yrevisión de contextos/journal, GUI real de carga/descarga yrestauración en segundo laboratorio. [Evidencia integrada](../evidence/s1-20261112/admin-data/RESULTADOS-GUI.md), [backend](../evidence/s1-20261112/admin-data/RESULTADOS-BACKEND.md), [paquete](../evidence/s1-20261112/admin-data/RESULTADOS-PAQUETE20.md), revisiones en su carpeta review.

La copia JSON es sólo inventario: excluye cuentas, contraseñas, grupos/permisos, factores/claves/sobresMFA, preferencias, plantillas privadas/compartidas, auditoría completa yWindows. Incluye notas/metadatos de usuarios: revisar antes de compartir. BackupPostgreSQL yrecuperación de seguridad tienen otro procedimiento. Restore48 completo yred48 permanecen bloqueados.

No New20 nativo ni reinicioWindows ensayados en esta tanda. El usuario hará la instalación nueva desdeGitHub; no se atribuye a20 elensayo deB19. No hay despliegue automático ni adopción. A/B/D/E conservadas. Índice26,63/100 delcierre restante invariable; no nueva cifra global porpublicar.
