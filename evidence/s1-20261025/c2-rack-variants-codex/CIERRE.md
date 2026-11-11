# C2 / I-04.02 — destinos, capacidad y metadatos de rack

25.10.2026. Implementador de producto y ejecutor: Codex. Autor de dos nuevos escenarios: agente `rack_variant_tests`; sólo comprobó sintaxis, no ejecutó laboratorio. Revisión independiente de producto/presentación: `rack_choices_review`, sin editar producto. No se opera VM, QA, servicios Windows ni bases existentes.

[Comportamiento corregido y límites](../../../docs/C2-NOMBRES-DESTINOS-RACK-25-10-2026.md). Producto: `InventoryPanel.jsx`, presentación de `Fields` en `OperationDialog.jsx` y módulo `inventory-choice-labels.ts`. No cambian cuerpos de comandos/guardas ni autorización del servidor; no hay nuevo guardado o DTO. CSS idéntico a la referencia previa.

## Ejecuciones nuevas, separadas de las históricas

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Edge/PG con frontend anterior | FAIL 26,61 s; nombre literal `room` traducido en opciones | [ORIGINAL.json](ORIGINAL.json), [diagnóstico](ORIGINAL-DIAGNOSTICO.json) |
| Edge/PG con frontend corregido | PASS 22,00 s, PostgreSQL 17.11 | [EDGE-PG.json](EDGE-PG.json), [navegador](NAVEGADOR.json) |
| Regresión de permisos/recuperación, frontend corregido | PASS 20,95 s | [REGRESION-EDICION.json](REGRESION-EDICION.json) |
| Node pertinente | 47/47 PASS, sin omisiones | [NODE.txt](NODE.txt) |
| Revisor distinto, casos propios de presentación | 7/7 PASS; original reproduce traducción/homónimos/títulos | [REVISION.md](REVISION.md), [fixture](review-fields.test.mjs) |

Los escenarios usan Edge real sin perfil del usuario y un PostgreSQL nuevo con secretos generados localmente. La jerarquía inicial es fixture SQL, no un alta GUI acreditada. El preset `sw8p` sí se crea y edita por GUI contra el catálogo real del servidor.

Nueve tablas completas comparadas, con identidad, atributos y extremos: sólo la reasignación/tamaño/ubicación del rack y la adición real del preset cambian. Reducción por debajo de ocupación rechazada sin revisión/filas alteradas. Cambio/cancelación de diálogo de mover no escribe. Metadatos de catálogo conservados al editar cinco notas/U/presupuesto; 10 puertos y dos grupos exactos. Recarga y segunda sesión coinciden; tras reiniciar el proceso servidor, ambas cuentas leen proyecto/ETag y SQL exactos. No es un reinicio Windows.

La regresión conserva permisos, recuperación con bytes/actor/clave/ETag originales y nueve tablas iniciales exactas. Ambos laboratorios terminaron con `labStopped`, `serversStopped` e `inputsUnchanged` verdaderos. El informe `productModified=false` del runner significa que la ejecución no modifica fuentes: la corrección se había compilado antes del ensayo.

## Identidad y reproducción

[FUENTES.json](FUENTES.json) fija los cambios y artefactos. Las copias originales de los dos componentes coinciden con los hashes registrados en la evidencia del build anterior C8; no se construye un rojo con una dependencia ausente. Un build frontend correcto nuevo, fuente coincidente con la copia privada, reutiliza Node 24.21.0/esbuild 0.25.10 y la referencia RC9 verificada. DLL anterior C2 reutilizada, sin compilar .NET ni tocar MFA. [Intento inicial de build con cwd erróneo](BUILD-INTENTO-1.json), conservado; no produjo una candidata válida.

Desde `C:\RackClick_SVR`, comandos de los tres ensayos:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_rack_variants_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-delete-permission-20261025T135722Z-e69491f3/frontend/dist --output C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/edge-original
C:/Python312/python.exe -X utf8 -B development/server/tests/test_rack_variants_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/frontend/dist --output C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/edge-final
C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/frontend/dist --output C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/edge-regression-edit --scenario write-permission
```

Las salidas deben ser nuevas para repetir, nunca sobrescribir las anteriores. Diagnósticos privados permanecen bajo `.local`; las copias públicas omiten configuraciones/secretos y no incluyen cuerpos de login ni claves. [Escaneo focal](ESCANEO.json): seis archivos de fuente/prueba modificados, Gitleaks sin hallazgos. Una copia inicial de recibos buscó `result.json` en vez del nombre real `fixture.json`; se corrigió la copia de evidencia, sin repetir o cambiar el ensayo.

Capturas inspeccionadas por el coordinador: [rack y sala](rack-edit-repeated-paths.png), [mover](rack-move-literal-options.png). Son datos sintéticos; nombres literales/UUID visibles caben en el diálogo. El revisor no afirma haber inspeccionado esas capturas ni ejecutado Edge/PG. No hay aceptación de accesibilidad completa/responsive ni de toda la GUI.

## Crédito y continuidad

El texto fijado de I-04.02 pide focos, no toda la matriz de presets. Con la revisión distinta y el ensayo exacto se acredita sólo ese subpaso, **5/14 puntos**, sin cambiar pesos, denominador ni alcance. I-04.03–07 permanecen pendientes; no se acredita candidata final, permisos generales, drag/táctil o adopción por este foco.

QA-121 planned; se conservan los 120 casos previos y resultados personales y se regeneran las guías. Sin integración/selección QA, paquetes, instalación, commits ni publicación. El trabajo W-02 de Claude no se toca ni se acredita aquí. Resultado del cálculo posterior registrado en CREDITO-I0402.json.

Cálculo verificado con `tools/progress_report.py --check`: **5,14/100 del cierre restante (36/7), 12/280 subpasos, 1/50 resultados**. W-02 permanece 0,50/2,50. No es porcentaje global del producto.
