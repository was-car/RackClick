# W02-C manual · Windows comprobado antes del ensayo

25.10.2026. Wascar terminó la instalación manual de Windows. Codex identificó exclusivamente `RackClick-W02-C-Manual` y ejecutó una inspección por VMware Tools con la credencial desechable autorizada. No se instaló RackClick ni se ejecutó Restore.

- **Sistema real:** Microsoft Windows Server 2025 Standard Evaluation, 64 bits, versión 10.0.26100/build 26100 comunicado por CIM. Equipo `WIN-O8PBF3UU7T7`, servidor independiente (DomainRole 2), sin AD DS. El build no incluye aquí una revisión UBR medida.
- **Acceso:** autenticación correcta con la cuenta de laboratorio y token administrativo. Usuario/SID y contraseña quedan en archivos privados, fuera de esta evidencia. La inspección sólo creó un JSON de diagnóstico nuevo en Windows Temp.
- **Red:** VMware Tools activo; VMnet1 por VMX. IPv4 medida `192.168.206.131/24`, subred `192.168.206.0/24`. No se cambió la configuración de red. Volver a comprobar la dirección antes de ejecutar un ensayo posterior.
- **Estado previo:** no se encontraron servicios RackClick/PostgreSQL ni las tres rutas de aplicación examinadas. Ningún listener en los seis puertos seleccionados. `dotnet`, Node/npm y psql no aparecen en Get-Command; `python.exe` aparece como alias WindowsApps, sin ejecución ni prueba de un runtime Python instalado. No es un inventario forense completo de programas.
- **Recursos:** cuatro CPU, memoria configurada 6.120 MB y disco NVMe; volumen C NTFS con unos 67 GiB libres al medir. No trasladar a esta VM los 6.144 MB de la C automática fallida.
- **Snapshot:** la llamada única de Codex a `vmrun snapshot` y su posterior `listSnapshots` terminaron con salida 0. [Recibo final](SNAPSHOT.json), 16:23:58 UTC. El log confirma terminación del UID 1, `W02-C-Windows-limpio-20261025T161843Z`. Es un snapshot con la VM encendida; tardó unos cinco minutos en guardar su memoria. **La revisión posterior detectó UID 1 y UID 2 con el mismo nombre, actual UID 2.** El segundo comenzó con nombre inicial `Snapshot 1`; su origen y el cambio de nombre no están acreditados. No se afirma que UID 2 haya terminado. [Inventario y extracto del log](SNAPSHOT-INVENTARIO.json). No se borró ni renombró ninguno. Antes de cualquier reversión hay que resolver la selección inequívoca; no revertir sólo por nombre. No se ha probado revertirlos.

[Medición sanitizada](ESTADO-VM.json), [preparación de hoja](PREPARACION.json), [revisión distinta](REVISION.md). El hash del recibo privado permite contrastar la medición sin publicar nombres de cuentas locales. El revisor cotejó sus campos con los originales; no ejecutó inspección en el invitado ni instalación.

La hoja de Restore tiene UUID nuevo, las direcciones reales y los nombres nuevos del borrador de Claude. Sigue siendo **preparación sin validar**: no se ejecutaron Check, Plan ni Execute, y la copia no se ha trasladado al invitado. Se volvió a medir el manifiesto de la copia exportada `e6559c36-11f7-43ef-a92d-18b6327392f0`; coincide con `af6a82d20417368ccc003a58bb28af437778edf89eeb95d538240a5e6fd0adda`. No se volvió a comprobar el dump ni a restaurarlo.

La revisión del auxiliar R3 sigue abierta: el SHA del ejecutor permanece `67079bebcc1d8dc20575d881a2115dbae0e5fa6e344c8f6f9463b1c2f6ea4897`. Tener Windows listo no elimina esos hallazgos. Próximo paso: revisar las correcciones de R3, fijar candidata coherente y preparar Check/Plan; Execute sigue pendiente. Paquetes 07 y A/B/QA conservados; sólo se actuó sobre C manual.

No hubo servicios/cuentas/red modificados por Codex, instalación del producto, commits o publicación. **Delta 0:** cierre restante 4,79/100; 11/280 subpasos, 1/50 resultados; W-02 0,50/2,50. Preparar otra VM no añade crédito al criterio de entorno ya acreditado.

## Aclaración posterior de Wascar

Wascar confirma que creó un snapshot manual mientras esperaba. Este testimonio explica la presencia de otra operación; la asociación exacta de su clic con UID 2 es una correlación temporal, no una comprobación independiente. Se conserva el inventario medido y sus límites.

Preferencia expresa: Wascar realiza las tareas sencillas de VMware y Windows (instalación del OS, snapshots, encendido/apagado). Codex indica los pasos necesarios y concentra su trabajo en código, paquetes, pruebas y análisis. No repetir esas operaciones automáticamente ni crear otro snapshot.
