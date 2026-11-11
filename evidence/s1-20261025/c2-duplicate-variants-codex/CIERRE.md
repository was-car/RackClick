# C2 / I-04.03 — duplicado y confirmación de reserva

25.10.2026. Coordinador/ejecutor Codex. Nuevos escenarios escritos por `rack_variant_tests`, que comprobó sintaxis pero no ejecutó laboratorio. Revisión distinta `rack_choices_review`, sin cambios de producto. No VM, QA, servicios Windows, instalación, paquetes ni commits.

## Alcance y ejecuciones

No hay modificación de producto. Se añaden sólo `browser-duplicate-variants.mjs` y `test_duplicate_variants_gui.py`, reutilizando helpers y fixture existentes. La lógica de duplicado ya existía; se comprueban sus variantes pendientes sin volver a implementarla. [Comportamiento](../../../docs/C2-DUPLICADO-VARIANTES-25-10-2026.md).

| Ensayo | Resultado | Evidencia |
|---|---|---|
| Prueba existente de duplicado, ejecución nueva | PASS 33,469 s | [REGRESION-EXISTENTE.json](REGRESION-EXISTENTE.json), [navegador](NAVEGADOR-EXISTENTE.json) |
| Nuevas variantes sin cables/reserva confirmada | PASS 23,219 s | [EDGE-PG-VARIANTES.json](EDGE-PG-VARIANTES.json), [navegador](NAVEGADOR-VARIANTES.json) |
| Revisor distinto, sensibilidad SQL | 3/3 PASS | [REVISION.md](REVISION.md), [fixture](review-sql-sensitivity.py) |

Ambos ensayos usan Edge en un perfil efímero y PostgreSQL 17.11 nuevo e independiente, con secretos locales nuevos. Los fixtures iniciales son SQL, no altas GUI. Se vuelven a medir los artefactos antes/después y no cambian; cada laboratorio/servidor propio queda detenido.

Prueba existente: un duplicado con cable interno, externo conservado y UUID remapeados. Cuatro negativos API 409 con `reserved_confirmation_required` o `port_blocked`, dos denegaciones de escritura 403 y lecturas fuera de ámbito 404; UUID del origen enviado a otro cliente también 404. `atomic_state` preserva nueve tablas de inventario más cliente, operación y auditoría, sin restos de escritura rechazada. No se presentan los logs históricos de 53 como una ejecución nueva: estos recibos son de la ejecución actual.

Variantes nuevas: dos copias secuenciales del mismo rack, con un puerto reservado en un cable interno y otro reservado suelto de otro grupo que repite `gn=1`. Sin cables no aparece confirmación requerida ni conexión nueva. Con cables, el formulario inválido no genera HTTP de comando y conserva proyecto/revisión/auditoría; la casilla válida confirma sólo el UUID original reservado conectado. Exactamente dos POST/operaciones/commits y revisión +2; ningún tercero por el intento bloqueado.

Nueve tablas reconstruidas desde `before + mappings`: se añaden 2 racks, 4 equipos, 6 grupos, 10 puertos y 1 cable con 2 extremos nuevos. Todo lo anterior, incluido el cable externo, queda exacto; sólo se permite una fecha nueva válida en el cable copiado. No se eligen puertos por `gn`. Otra sesión, recarga y reinicio del proceso servidor preservan los datos y `atomic_state`. No es reinicio Windows ni prueba de drag/táctil/Dosen.

## Revisión y reproducción

El revisor contrastó fuentes, ambas salidas y contrato. Ejecutó tres grupos propios puros: acepta el positivo sin mutar entradas y rechaza cambios de atributos/roles/familia/propiedades, UUID reutilizados y extremos incorrectos. No ejecutó nuestros ensayos Edge/PG y no se le atribuyen. El comparador SQL no toma atributos libres del resultado; sólo el timestamp validado de la conexión nueva. La sensibilidad comprueba que el test detectaría pérdidas.

Comandos nuevos ejecutados desde `C:\RackClick_SVR`:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_duplicate_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/frontend/dist --output C:/RackClick_SVR/.local/c2-duplicate-variants-20261025T195329Z-ae423393/edge-existing
C:/Python312/python.exe -X utf8 -B development/server/tests/test_duplicate_variants_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-rack-variants-20261025T193105Z-3bbe929b/frontend/dist --output C:/RackClick_SVR/.local/c2-duplicate-variants-20261025T195329Z-ae423393/edge-variants
```

[ENTORNO.json](ENTORNO.json) da la raíz exacta utilizada. Para repetir se necesita otra salida nueva, sin sobrescribir resultados. No se incluyen contraseñas, cookies ni cuerpos de login; los detalles de solicitudes/diagnósticos permanecen privados. El artefacto de frontend y la DLL ya existían y no se recompilaron, ni cambiaron dependencias.

Captura inspeccionada por el coordinador: [casilla requerida](duplicate-required-confirmation.png). El revisor no la inspeccionó. Los nombres con `<img>` son datos sintéticos literales, no marcado insertado.

## Cierre

I-04.03 acreditable con peso fijo 5/14 según revisión distinta; sin cambiar alcance ni denominador. QA-122 planned, 121 casos previos y resultados personales conservados; guías regeneradas. I-04.04–07 y la candidata coordinada siguen pendientes. W-02 de Claude no se opera ni se acredita aquí. El cálculo final se registra en CREDITO-I0403.json.

Cálculo final: **5,50/100 del cierre restante (11/2), 13/280 subpasos, 1/50 resultados**. W-02 sigue0,50/2,50; alcance y pesos conservados.
