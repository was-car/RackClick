# Revisión independiente — I-04.05 impacto y cancelación de borrados

25.10.2026. Revisor distinto de los autores del producto y de los tests. Único archivo escrito: este informe. Git inspeccionado antes; cambios ajenos conservados. Sin modificar producto/tests, ejecutar Edge/PostgreSQL, construir, instalar ni acceder a laboratorios privados, credenciales, VM, MFA o QA de Wascar.

## Dictamen

**Conforme acreditar I-04.05 (`5/14`), sin hallazgos bloqueantes nuevos.** Texto exacto leído: «Borrado individual/conjunto con objetos de sala y cables incidentes: commit único, impacto/cancelación exactos.» El foco nuevo cubre un End conectado individual y Dose+B en lote, con cuatro previews y cuatro barreras SQL; la regresión pertinente conserva los casos previos. No acredita candidata final/QA ni I-04 completo; no modifica métricas ni afirma porcentaje global.

## Fuentes y contrato comprobados

- `test_delete_impact_variants_gui.py`: `deleted_inventory` deriva los puertos desde `before.inventory_port.device_id` y los cables incidentes desde los extremos originales. Elimina objetos/grupos/puertos propios y ambos extremos de cada cable incidente; mantiene todos los demás atributos/filas de las nueve tablas. La comparación final real es `canonical(after) == canonical(final_expected)`, sin construir el esperado a partir de `after`.
- `browser-delete-impact-variants.mjs`: `deletionImpact`, `removedProject`, `preview`, `barrier`, `cancel`, `committed`. Calcula los cinco conjuntos desde propiedad de grupos/puertos y extremos del snapshot inicial; compara todos los UUID del DOM, sin duplicados. Usa controles ofrecidos, selección explícita `[Dose,B]`, cancela y reabre previews; los vecinos/puertos y cable no incidente se conservan.
- `InventoryImpact.cs`: `ImpactFor`, `ImpactToken`, `RequireImpact`, `PreviewImpact`, `DeleteInventory`. El impacto es unión de conexiones con al menos un extremo en los puertos afectados. La confirmación queda ligada a actor/cliente/revisión/tipo/payload/impacto; preview y ejecución comprueban autorización vigente. La ejecución retira conexiones y entidades dentro de la transacción existente.
- `OperationDialog.jsx`: `submit` obtiene preview antes de preparar la escritura con token; el token no es un campo del formulario. `impact-model.ts`, `impactSections`: los UUID son autoritativos y los nombres son texto. `delete-batch.ts`, `prepareDeleteBatch`: selección explícita de 1–64 UUID, sin reducir silenciosamente un lote obsoleto.
- Contexto acotado: `test_room_device_move_gui.fixture`, `test_delete_batch_gui.py`, `docs/C2-PERMISOS-BORRADO-25-10-2026.md` y revisión previa de permisos. Sus resultados históricos no se presentan como ejecución nueva del revisor.

## Barreras, errores y sanitización

El navegador escribe un marcador y espera respuesta antes de continuar. Python espera JSON completo (tolera existencia del archivo antes de acabar `writeFile`), compara `atomic_state` y sólo después publica `valid=true` mediante archivo temporal+replace. Un error del checkpoint publica `valid=false` y se propaga; marcador faltante/incompleto o finalización prematura del navegador también falla. El resultado final exige proceso de navegador exitoso, entradas intactas y laboratorio/servidores detenidos. No se infiere cancelación segura de una espera visual solamente.

`ready` fija el estado completo, auditorías/operaciones/revisión iniciales; `single-cancel` debe ser idéntico; `after-single` exige el estado SQL esperado y exactamente una operación/auditoría/revisión nueva; `batch-cancel` debe ser idéntico a ese estado post-single. La comparación final exige las dos únicas auditorías previstas y dos operaciones en total respecto a la base. `atomic_state` incluye las nueve tablas, customer/revisión, operation y audit_event.

El observador elimina `payload.confirmationToken` antes de conservar escrituras; guarda sólo `hasConfirmationToken: boolean` y ETag/revisión. No conserva cabeceras completas, cookies ni CSRF. Los requests de preview se guardan antes de incorporar la confirmación, no contienen el token de respuesta.

## Pruebas propias realmente ejecutadas

**Python 3.12 existente, Windows PowerShell; scripts en memoria enviados por stdin a `C:/Python312/python.exe -B -`.** No se importan dependencias del runner: se extraen por AST `deleted_inventory` y el assert final real del comparador.

**Tres grupos de sensibilidad: 3/3 PASS, exit 0, 0,005 s.** Matriz artificial propia de nueve tablas con jerarquía, vecinos, cable protegido, cable ajeno adicional y metadatos:

1. Controles positivos individual y conjunto, esperados por listas explícitas independientes de identidades del fixture. Cable incidente exacto y equivalencia de borrar por etapas; el puerto del vecino sobrevive desconectado; `before` no se modifica.
2. El comparador rechaza cambios en nota del cable protegido, propiedades del cable ajeno, metadatos del equipo vecino y label de su puerto.
3. Rechaza borrar cable no incidente y sus extremos, borrar un puerto vecino, conservar un extremo huérfano o cambiar un UUID superviviente.

**Control propio adicional de `DETALLES-BORRADO.json`: PASS, exit 0.** Recorrido recursivo: cero claves brutas `confirmationToken/csrf/cookie/cookies/password/headers/authorization`; exactamente dos `hasConfirmationToken` booleanos verdaderos. Comprueba barreras POST `[0,0,1,1]`, revisión `[1,1,2,2]`, cuatro previews de tamaños `[0,1,1,1,1]`/`[0,2,2,5,2]` en orden rack/device/group/port/connection, y cable protegido excluido de todos.

Una lectura inicial paralela no llegó a arrancar por fallo local de PowerShell 7 al cargar ApplicationInsights. Se repitió sólo esa lectura con Windows PowerShell existente, sin instalación/configuración ni fallo de test de producto. No se ejecutaron pruebas de navegador/DB, capturas, teclado/lector de pantalla o suites generales por el revisor.

## Recibos finales contrastados; ejecuciones del coordinador

- `EDGE-PG.json`: **PASS 35,891 s**, PostgreSQL 17.11, browser exit 0. Las cuatro barreras son válidas; borrado y cancelaciones exactos, cable protegido y ambos extremos conservados, **dos commits**. Individual y lote reciben 403 en preview+commit para lector y 404 para ajeno: ocho rechazos sin cambiar `atomic_state`. Dos cuentas leen el estado/ETag exacto tras reinicio; `inputsUnchanged/labStopped/serversStopped=true`.
- `EDGE-BROWSER.json`: Edge `156.0.4314.42`, tres focos PASS, `jsExceptions=[]`. Individual End conectado y lote mixto Dose+B; selección retenida al cancelar y vaciada sólo tras confirmación; originales/vecinos/cable no incidente intactos; dos POST con revisiones exactas, recarga y segundo actor.
- `DETALLES-BORRADO.json`: cuatro previews/barreras y confirmaciones sanitizadas contrastadas también con el control propio anterior. La cancelación individual conserva revisión 1/0 POST; tras el único individual y la cancelación de lote sigue revisión 2/1 POST.
- `REGRESION-LOTE.json`/`REGRESION-BROWSER.json`: **PASS 27,984 s**, PG17.11, mismo frontend y DLL que el foco nuevo (hashes comparados). Incluye EN/DE/ES, preview/cancelación, lote mixto, selección obsoleta/412 con rechazo entero, respuesta 200 perdida y replay exacto sin segundo commit, aislamiento, recarga y reinicio. Nueve tablas verificadas, entradas intactas y procesos detenidos. No repetida por el revisor.

## Identidad y límites

| Archivo / artefacto | SHA256 |
| --- | --- |
| test_delete_impact_variants_gui.py | `bc516d4da0530a27caf65f5af4ee04f23484bd2f191e8cf9839fc4e7a9cf5e0a` |
| browser-delete-impact-variants.mjs | `e9b8cea0d8415d74345103733c15ee66e3ca30c0f6b0cd2c9eb9fc458b28b7af` |
| frontend congelado del recibo | `04f4ef02c15ed46f57756e43d3949222d9f8d9f11961765acafe57eec3c81101` |
| DLL congelada del recibo | `5eb1abcf9d2f91d293bae8f1b01e94f0352ca254c0387aaa45de1c35b2a97585` |

El foco nuevo usa español y un lote pequeño; los tres idiomas y otros negativos proceden de la regresión nueva pertinente, sin atribución retrospectiva. No se acredita matriz exhaustiva de 64 objetos, todas las topologías, hardware táctil, reboot Windows, candidata final, QA/adopción ni accesibilidad/paridad completa. La revisión no implementa cambios funcionales; documenta cobertura técnica del criterio existente.
