# Grupo62 · tres tandas cerradas y revisadas

17.10.2026. Base f264e5f2d25459cdc2f939a9508b349d6e3534af. S1 autorizado; sin instalaciones, cambios de versiones/SQL001–007, publicación o adopción. Los tres autores tienen archivos separados y la revisión la ejecutó rackclick_qa, distinto de los implementadores.

## Resultado concreto

1. **62-A — previews protegidos:** rack.delete, device.delete, device.editPortGroups y devices.delete comparten ReadCommitted, bloqueo cliente→actor/sesión y revalidación de sesión/read/capacidad tras esperas y antes de devolver el impacto. DTO, rutas, token y ejecución conservados. Se corrige el P2 heredado de las tres familias anteriores; no se declara seguridad universal ni serialización de revocaciones posteriores a la última consulta. [Contrato](../../../docs/API-PREVIEWS-AUTORIZACION-S1.md).
2. **62-B — traslado entre salas:** Mover de tomas/finales muestra nombre literal, sala actual/ruta/UUID; destino empieza vacío, excluye sala actual y clientes ajenos. Sin destino no envía; tras412 refresca sala/opciones desde snapshot vigente conservando borrador. Identidad/grupos/puertos/cables exactos; cambian únicamente room_id y sort_order documental MAX+1. Dos cables en puertos distintos de Dose no suponen circuito interno. GUI RC9, CSS, Click-Click y rama de racks conservados. [QA33](../../../docs/GUI-TRASLADO-SALA-S1.md).
3. **62-C — transición aprobada61→62:** registro/pin cerrado y entrypoint con guardia de transición. Motor, defaults anteriores y esquema7 conservados; no se reconstruye base ni se cambia puntero/URL/cuentas. [Procedimiento](../../../docs/ACTUALIZACION-ARTEFACTOS7-62-S1.md).

## Pruebas Windows nuevas y revisión distinta

| Responsable | Ejecución y resultado real |
|---|---|
| Backend | Un build Windows correcto; cinco focos propios finales combinados: tres válidos pg01 + sesiones pg02 + estabilidad con writerAPI pg03. Pg02 31,045s/pg03 26,575s de pruebas. Dos regresiones correctas: token individual heredado y lote/execute/concurrencia/replay. Misma DLL desde el build. |
| Frontend | Un build; native-v2 PASS24,969s; regresión entre racks PASS21,625s. Dos actores, recarga, reinicio ASP.NET, negativos403/404/422, dos412, sin destino/no-op cero peticiones, nueve tablas exactas salvo sala/orden. Capturas390px EN/DE/ES inspeccionadas. |
| Windows | Siete contratos prepin PASS1,028s. Único nativo final PASS73,418s en una fuente61 sintética nueva/versionada: lock rechaza, PG externo se conserva, update/filas/historia/OID/exactos3campos/privados/puntero, escritura y reinicio sólo en fixture. No repetir transiciones históricas. |
| Revisor distinto | Preview inicial2/2 PASS50,093s total; después sólo estabilidad corregida writerAPI1/1 PASS26,667s. GUI PASS24,031s. Un nativo Windows PASS75,406s. Guía24/24 PASS. Artefactos/entradas intactos y procesos de fixtures detenidos. [Informe](revision/REVISION.md). |
| Coordinador | Foco de gate QA33 1/1 PASS; generación y check de ambas guías4/4. Sin builds ni repetición de nativos del equipo. Revisión de compatibilidad estática, no reejecución global de módulos anteriores. |

**Intentos preservados:** pg01 terminó successful:false con cuatro subcasos FAIL al intentar revocar después del SHARE de sesión; era espera correcta del DELETE, no fallo del producto. El reportador heredado no enumera addSubTestFAIL en cases, pero tests.log conserva los cuatro fallos: no se convierte en suite PASS. Pg02 corrige sólo cuándo revoca el fixture. La primera estabilidad usó SQL en sentido inverso; pg03 y repetición independiente usan escritor API real en ambos sentidos. Frontend native-v1 falló por tupla4/3 antes de INSERT/navegador; native-v2 corrige únicamente el arnés. No hubo rebuild de producto por estos ajustes. Rutas/logs y hashes en cierres [backend](backend/CIERRE.md), [frontend](frontend/CIERRE.md) y [Windows](windows/receipt-final.json). Los logs de grupos anteriores son históricos.

## Copia de QA y guía de Wascar

CANDIDATA62.json congelada: SHA ba9654b0228f4278b157f3ac568d46595ffb5d8b98a27a47ff78564f71def3e9. Distribuciones completas16/18; DLL78fcf05c…5c27, JS468fa553…c726, CSS50dd8567…7ec3 sin cambios. SQL001–007 idénticos61. El manifiesto de build conserva su cronología; los ajustes posteriores fueron sólo de pruebas/documentos.

Tras GO técnico, único operador revisado SHAca06c3cd932b922d764f98f323915c917815d39b35cfcf9fe3d0c7b1ea403102: CLI0/wrapper0,35,175s y16/16comprobaciones [OPERACION-REAL.json](OPERACION-REAL.json). Misma base/roles/configuración salvo artifactDirectory,dllSha256,bundleSha256; puntero yURL http://127.0.0.1:52346 conservados, pareja61 retenida y nueva62 completa. Comparados36archivos originales y8privados por hash. Cero login/DML técnicos de aplicación, cero migraciones/restore; sólo helper con lecturas de control y arranque/parada de procesos propios. APP/PG quedaron apagados.

Una observación pasiva independiente posterior27/27 correcta, sin SQL/HTTP/auth/start/stop; [post62-passive.json](revision/post62-passive.json). Esa observación compara metadatos/artefactos y estado; no repite snapshot SQL ni se atribuye las36/8comparaciones del coordinador.

INICIAR-QA-RESTAURADO.cmd conserva cuentas privadas/URL. GUIA-QA-RESTAURADO.html ofrece33casos incluido QA33; guía original8disponibles yQA33pendiente. Los32objetos de casos anteriores son idénticos, código de notas/importación/exportación conservado; no se leyó ni sobrescribió ningún resultado personal. QA33 prepara datos nuevos y asignación explícita del cliente al grupo de clientes para TécnicoB/Lector. Disponible no significa Pass de Wascar.

## Seguimiento y próxima terna propuesta

**58/100 provisional**, mismos pesos20/25/15/15/15/10 y aportes18/18/14/4/3/1; administración14/15. Corrección de seguridad, refinamiento y evidencia de movimiento ya existente y adaptación de motor ya contado no añaden automáticamente otro punto. No porcentaje de créditos ni de aceptación.

Siguiente foco propuesto: concretar compensación colaborativa condicionada (sin restaurar snapshots ciegos), completar casos de Dosen/conectores/presupuesto sin inventar circuitos y avanzar panel administrativo guiado conforme al árbol solicitado. Orden sujeto a contratos y dependencias; no se declara implementado. Siguen pendientes informes/plantillas/exportes y paridad completa, instalador limpio/servicio/HTTPS, backup/recuperación en otro equipo, manual/paquete reproducible y QA/adopción final de Wascar. No candidata de servidor final ni R3 adoptado.

Fuentes finales/diff comprimido/verificación/SHA256SUMS se cierran en este mismo directorio. El manifiesto de recepción y evidencias anteriores permanecen históricos; aquí no se produce un ZIP de instalación final.
