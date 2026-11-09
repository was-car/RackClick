# Bandeja, firewall, switch y patch panel — resultado del bloque

30.10.2026. Implementación de desarrollo y revisión independiente terminadas.
No se modifica la instalación 10, su base, usuarios, MFA, VM ni paquetes históricos.
No se hicieron commits ni push en esta tanda.

## Resultado

El contrato está en [CONTRATO-HARDWARE-MONTAJE-v1.md](CONTRATO-HARDWARE-MONTAJE-v1.md).
Se integraron cuatro referencias genéricas en el producto: bandeja, firewall
autónomo sobre ella, switch y patch panel. El firewall conserva identidad y
puertos propios; la bandeja reserva el espacio del conjunto. No son modelos de
fabricante verificados ni se ha importado el catálogo de investigación completo.

La GUI usa el canal existente de comandos, revisión, recuperación de solicitudes
e idempotencia. El renderer RC9 conserva equipos anteriores en racks mixtos;
sólo delega la fila de cada perfil nuevo. Las caras y las claves de puerto del
perfil son inmutables; nombres, notas, estados y etiquetas admitidos sí se guardan.

## Archivos y cambios

- `development/server/database/016-hardware-mounting.sql`: columnas normalizadas,
  FK compuesta de padre/mismo ámbito/rack, alojamiento exclusivo, checks y trigger
  de soporte. `SchemaMigrations.cs` registra **16** de forma explícita.
- `InventoryHardwareProfiles.cs` y `InventoryHardwareMounting.cs`: referencias
  sintéticas, creación transaccional y edición limitada de metadatos.
- `InventoryDevices.cs`, `InventoryStore.cs`, `InventoryDuplicate.cs`,
  `InventoryImpact.cs`, `InventoryConnections.cs` y `OpenApiInventory.cs`:
  DTO/contrato, capacidad, defensas de ciclo de vida y familia de conectores.
- Frontend: `hardware-reference.json`, `hardware-mounting.ts`,
  `hardware-words.ts`, `HardwareCreationFields.jsx`, `MountedPhysicalRack.jsx`;
  integración en `InventoryPanel.jsx`, `inventory-model.ts`, `OperationDialog.jsx`,
  `server.css` y extracción controlada de `build.mjs`. El ZIP adoptado no cambia.
- Informes: SVG/XLS RC9 rechazan el ámbito montado que no saben expresar;
  `InventoryPrintableReports.cs` identifica U adicionales, padre y alojamiento.
  Los exportadores explican el límite en EN/DE/ES.

## Verificación real

Entorno: Windows, SDK **10.0.401** fijado, .NET **10.0.12**, PostgreSQL **17.11**,
Node **24.21.0**, npm **11.19.0**, esbuild **0.25.10**, Edge **156.0.4314.50**.
Sin versiones ni dependencias nuevas. Restore locked y build Release finales:
**0 errores, 0 advertencias**; binlogs privados bajo `.local/`.

| Prueba | Resultado y alcance |
|---|---|
| Regresión Node | 807/807 PASS; después se añadió el negativo de ordenación de raíces con hijos: foco final 7/7 PASS. No se suman como pruebas distintas. |
| Build frontend | Correcto; 37 comprobaciones del adaptador PASS. |
| `test_hardware_mounting.py` | 21 comprobaciones compuestas PASS en la DLL final: 14 negativos HTTP, 8 restricciones SQL, replay, rollback forzado de auditoría, concurrencia de alojamiento, permisos y migración real 15→16. |
| `test_hardware_mounting_gui.py` | Edge/Kestrel/PG reales: conjunto de 4 objetos, 81 puertos y 3 cables por ambas caras; 4 U; recarga, otra cuenta, lector y persistencia tras reinicio del servidor. Rack mixto adicional: NAS RC9, bandeja y sus controles conservados. 10 comandos confirmados, 83 puertos contando los 2 anteriores. |
| `test_hardware_mounting_consumers.py` | 5 comprobaciones compuestas PASS: cara física inmutable y rechazo sin mutaciones, estado/etiqueta editables, límites SVG/XLS, impresión escapada con padre, exportaciones normales de otro rack. |
| `test_hardware_mounting_delete.py` | Borrado de la unión completa con impacto confirmado; token incorrecto rechazado, otros racks/clientes conservados y persistencia. Resultado final en la evidencia. |
| Revisión independiente | Negativo propio PG17.11: borrar sólo la bandeja con hijo/cable externo devuelve 409; nueve tablas, revisión, operaciones y auditoría intactas. No se atribuye al revisor la ejecución GUI del coordinador. |
| Guías | QA-136 planned; 135 casos previos conservados. Dos HTML regenerados/comprobados y 35 pruebas del generador PASS. |

La migración 15→16 se ensayó en **otra base nueva** con una publicación histórica
15 identificada. Conservó inventario, cuentas, permisos y digests 1–15. No equivale
a actualizar la instalación nativa, ni se ensayó recuperación de sus claves MFA.
Todos los clústeres y servidores de estas pruebas se detuvieron.

## Revisión y límites

[Dictamen independiente](REVISION-HARDWARE-MONTAJE-30-10-2026.md): favorable para
este foco interno. Se corrigieron tres hallazgos antes del cierre: pérdida de
controles RC9 en rack mixto, campo PoE editable que no se enviaba y orden que
intercambiaba una raíz con un hijo invisible. El ensayo final comprueba sus
comportamientos relevantes; las primeras ejecuciones se conservan separadas.

Queda pendiente:

1. Catálogo general versionado por fabricante/modelo/SKU, definiciones revisadas,
   conectores, geometría, montaje, módulos/combos y licencias por modelo. V1 queda
   congelado; no se añaden modelos comerciales sólo editando JSON o SQL016.
2. Mover/reubicar/duplicar ensamblajes mediante un contrato explícito; hoy los
   recorridos no soportados se rechazan, sin perder descendientes ni cables.
3. Trazado interno real del panel, reservas U absolutas, más alojamientos,
   carga/peso, ventilación y conectores eléctricos especificados.
4. Adaptar exportaciones SVG/XLS y detalle tipado de los avisos al montaje.
5. Propagar esquema 16 a distribución, operadores, New/Restore/upgrade y manual;
   ensayo Windows Server completo antes de entregar una candidata nueva a Wascar.

QA manual: [pasos de ubicación y botones](QA-HARDWARE-MONTAJE-WASCAR.md).
La instalación 10 sigue siendo la disponible; **QA-136 no se habilita todavía**.

## Repetición

Con las herramientas fijadas del proyecto ya preparadas, compilar el servidor
actual en un directorio de trabajo independiente y ejecutar el build frontend
existente (`development/frontend/Build-Frontend.ps1`). Añadir `-bl:<ruta privada>`
a cada restore/build de .NET y usar `restore --locked-mode`.

Los ensayos aceptan rutas explícitas, no eligen una instalación existente:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_hardware_mounting.py --dll '<DLL nueva>' --output '<directorio nuevo bajo .local>'
C:/Python312/python.exe -X utf8 -B development/server/tests/test_hardware_mounting_gui.py --dll '<misma DLL>' --frontend '<dist nuevo>' --output '<otro directorio nuevo bajo .local>'
C:/Python312/python.exe -X utf8 -B development/server/tests/test_hardware_mounting_consumers.py --dll '<misma DLL>' --output '<otro directorio nuevo bajo .local>'
C:/Python312/python.exe -X utf8 -B development/server/tests/test_hardware_mounting_delete.py --dll '<misma DLL>' --output '<otro directorio nuevo bajo .local>'
```

`--baseline-dll` añade el ensayo de actualización real desde una DLL 15 preservada;
sin ese argumento no se debe afirmar haber repetido 15→16. El registro de comandos,
huellas y resultados de esta ejecución está en
`evidence/s1-20261030/hardware-mount/RESULTADOS.md`. Logs crudos, claves de los
laboratorios y binlogs no forman parte de la entrega ni del repositorio.

**Seguimiento:** índice de cierre restante **9,76/100**, sin incremento automático.
Se registra avance del nuevo foco C-HW-02/04/05, sin acreditar todo el catálogo ni
convertir pruebas en aceptación. No hay un porcentaje global de producto nuevo.
