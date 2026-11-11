# Tanda moderada 04 — impacto de eliminación y reconexión

28.09.2026. Base Git `e1d6b66`. Desarrollo autorizado; no candidata completa ni adopción.

## Resultado y corrección

**Seis comprobaciones correctas en Edge/PostgreSQL**, más **28/28 pruebas de adaptador** y compilación frontend:

1. Reconexión conserva UUID del cable y extremo elegido; cambia únicamente el otro extremo y la revisión. Otro cable permanece idéntico, al igual que racks, equipos, grupos y puertos.
2. La vista previa de eliminar un equipo contiene exactamente los IDs de equipo, grupo, puertos y cable afectados. Consultarla y cancelarla conserva el snapshot completo del inventario.
3. Otra sesión crea un sitio después de la vista previa. Confirmar con la revisión antigua devuelve **412**, conserva todos los datos y bloquea confirmar hasta recargar explícitamente.
4. Recargar exige nueva vista previa y genera otra confirmación. Eliminar afecta solo a los objetos previstos; se compara el resto de cada colección completa, incluido el cambio de la otra sesión.
5. Eliminar el rack restante aplica su impacto exacto y conserva otro rack con sus equipos, puertos y cable.
6. Recargar y consultar desde la segunda sesión obtiene el mismo snapshot persistido.

El primer recorrido pasó funcionalmente, pero su captura reveló una deficiencia de presentación: la vista previa mostraba `deviceIds`, `groupIds` y UUID. **Se corrigió para mostrar rótulos traducidos y nombres/rutas de racks, equipos, grupos, puertos y extremos de cables**, con los detalles abiertos para revisión. Los IDs del servidor siguen siendo la autoridad, se conservan como atributos del elemento y están disponibles como título. No se infieren identidades por nombres ni por `gn`; no cambian token, permisos, contrato ni operación enviada.

La prueba final compara tanto los IDs exactos como nombres visibles de los equipos, puertos y extremos. [Captura final](run2/exact-impact-windows.png); [captura anterior conservada](run1/exact-impact-windows.png).

## Archivos

- `development/frontend/src/impact-model.ts`: etiquetas de impacto sobre el snapshot de la revisión confirmada; conserva cada ID recibido.
- `development/frontend/src/OperationDialog.jsx`: presentación legible usando las traducciones EN/DE/ES existentes, sin alterar el protocolo de commit.
- `development/frontend/tests/browser-impact.mjs`: escenario repetible con escrituras desde GUI, dos sesiones y comparación completa del inventario afectado/no afectado.
- `tools/windows/Verify-Windows.py`: incorpora el nuevo escenario en el ámbito inventory; sintaxis comprobada, verificador completo no reejecutado.
- Documentos de continuidad, aceptación, registro, README y changelog actualizados.

## Repetición y entorno

Windows 11 `10.0.26200`, Edge `154.0.4258.37`, Node `24.21.0`, PostgreSQL `17.11`. Cada ensayo usa instancia/base y secretos de laboratorio nuevos, con cierre registrado. Dos contextos de cookies del mismo administrador. No se modificaron bases existentes ni la RC9 adoptada.

Desde `C:\RackClick_SVR`, herramientas y dependencias locales ya preparadas:

```powershell
powershell -NoProfile -File development/frontend/Build-Frontend.ps1 -SkipRestore
C:/Python312/python.exe development/server/tests/run_frontend_smoke.py --scenario browser-impact.mjs --output evidence/nueva-prueba-impacto --timeout 180
```

El directorio de salida debe ser nuevo. La preparación inicial está documentada en `Initialize-Toolchain.ps1` y build sin `-SkipRestore`.

| Evidencia | Estado y versión |
|---|---|
| `run1/` | PASS inicial, antes de corregir las etiquetas |
| `revision-browser/` | Reproducción independiente inicial, conservada como tal |
| `build.log` | Primera compilación de la corrección y 28/28 adaptador |
| `build-final.log` | Compilación final tras ajustar el rótulo de rack; 28/28 adaptador |
| `run2/` | PASS final, seis comprobaciones sobre el bundle corregido |
| `revision-final/`, `REVISION.md` | Revisión y reproducción final independientes, alcance propio |

Los logs de build/redirección PowerShell son UTF-16LE. Cada `fixture.json` registra hashes de DLL, escenario y todos los archivos dist antes/después, salida de proceso y `labStopped`. El bundle final cambia; no se le atribuyen automáticamente las ejecuciones iniciales ni las tandas anteriores. La DLL backend sigue siendo `7a5fb79c41f755b69360e0317ab5cc7a402f62eb496b64981138a1530d682f4d`.

Bundle final `app.js`: `d644b6fa7ed6fd3e63fb68d131bc4facfe758ec9d13629048d051e6ad5fa07a5`. Las dos ejecuciones del coordinador y las dos del revisor terminaron con proceso 0, hashes de entrada estables y laboratorio detenido, cada una con su versión y base propias. La repetición final se justifica por la corrección posterior a la primera captura.

## Límites y siguiente trabajo

El 412 acredita rechazo de revisión antigua, no un ensayo aislado de token antiguo enviado con revisión actual. Conservar el snapshot no demuestra ausencia de toda escritura interna: esta prueba no consulta auditoría directamente. La eliminación del rack ensayado sucede después de borrar su equipo conectado; la eliminación de cables se comprueba en el caso de equipo, no como cable conectado a un rack eliminado. No cubre eliminación parcial de grupos, todos los conectores, PoE/AC, otros usuarios/permisos, reinicio del servidor/Windows ni paridad visual completa. Se usan traducciones existentes; la prueba de navegador se ejecuta en inglés y no certifica todas las pantallas en los tres idiomas.

Siguiente tanda acotada: edición parcial de grupos y comportamiento PoE/AC en GUI; después continúan administración de usuarios/grupos, paridad RC9 pendiente e instalación/recuperación/manual completos. No hay adopción del servidor: el QA final corresponde a Wascar.
