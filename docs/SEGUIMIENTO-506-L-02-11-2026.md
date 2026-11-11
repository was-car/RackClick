# Comprobación de continuidad · catálogo L · 02.11.2026

Se retomó el punto pendiente y se conservaron los resultados anteriores. No se repitieron las 995 pruebas de frontend ni las 35 C# ya terminadas. No se accedió a VM, QA, servicios instalados ni datos de Wascar; sin commits ni push.

- Los 62 modelos restantes están definidos:124 caras/1.673 extremos. Existe además una revisión explícita del receptor USP (28 extremos) sin reescribir el switch original. El catálogo de desarrollo tiene868 definiciones/revisiones,862 comerciales correspondientes a861 modelos comerciales distintos. La selección original alcanza506/506 **en autoría de desarrollo**, con355 modelos adicionales aparte. Esto no significa aceptación o instalación de506 modelos.
- Los visores tuvieron revisión independiente de fuentes/identidades,124 caras, selector868 y una muestra visual. [Abrir grupo L](../VER-SELECCION-506-L.html) · [Selector compacto](../VER-SELECTOR-CATALOGO-L.html). Las cotas desconocidas, bases vacías, BOM fijas y referencias de familia siguen indicadas por modelo.
- La prueba completa de upgrade41→43 se detuvo en la migración. Se aisló el error:dos expresiones SQL CASE en condiciones PL/pgSQL necesitaban paréntesis. Tras corregir,042 y043 se ejecutaron correctamente dentro de una transacción de un PostgreSQL17 nuevo y se hizo ROLLBACK deliberado. Esta prueba focal no reemplaza el upgrade completo con preservación de datos.
- Se corrigió el despacho nativo de carcasas, que no incluía las dos revisiones L. El negativo nuevo falla con el despachador anterior y pasa después:12 pruebas focales actuales, incluyendo ambas caras de las63 revisiones. La suite995 anterior se conserva como anterior, no como ejecución nueva sobre este cambio.
- Se regeneraron lock/manifiesto/targets y se reconstruyeron servidor y frontend. Build0 errores/0advertencias. La DLL de pruebas C# mantiene exactamente su hash, por lo que se conserva el resultado35/35 sin repetirlo. Binlogs y diagnósticos completos permanecen privados en.local.

**Pendiente real:** completar el upgrade41→43 con sus805 definiciones/799 instancias anteriores, el ensayo nuevo API/Edge de los62 modelos, el contraste final de las dos correcciones y el paquete de revisión. Después siguen el paquete integral Windows/Restore, QA final y el laboratorio de50 clientes. No copiar DLL/SQL sueltos al servidor. La candidata anterior se conserva; la corregida es de desarrollo.

[Resultados de esta comprobación](../evidence/s1-20261101/integracion506l/comprobacion-20261102/RESULTADOS.json) · [Foco PostgreSQL](../evidence/s1-20261101/integracion506l/comprobacion-20261102/POSTGRESQL-FOCO.json) · [Revisión independiente anterior](../evidence/s1-20261101/integracion506l/review/VISORES-DRAFT.md).

Índice de cierre restante9,76/100, intacto; no es porcentaje global. Autoría del catálogo elegido100%; integración/aceptación completa aún pendiente.

## Adenda · punto1 completado

La comprobación posterior completa el upgrade805/799 y fresh/API/Edge62/124/1673,17+17 conexiones,45rechazos y persistencia. Se conserva arriba el estado previo y sus pendientes históricos; el estado actual, correcciones, atribución de etapas y revisión están en [Integración L](INTEGRACION-506-GRUPO-L.md) y [evidencia final](../evidence/s1-20261102/integracion506l/RESULTADOS.md). VM/QA/instalación intactas; candidata integral/QA pendientes, índice9,76/100 sin cambio.
