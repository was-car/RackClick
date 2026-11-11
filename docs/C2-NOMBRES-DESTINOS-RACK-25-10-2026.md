# C2 · nombres literales y destinos distinguibles por UUID

25.10.2026. Foco I-04.02 en laboratorio, separado del ensayo W-02 de Claude. No se incorpora al instalador 08 ni se selecciona en el QA actual.

## Corrección

Los selectores de sede, edificio, sala y rack guardaban el UUID correcto, pero algunos mostraban únicamente el nombre o la ruta. Dos destinos homónimos resultaban indistinguibles. Además, `Fields` buscaba cualquier etiqueta en el diccionario: un nombre escrito como `room` se mostraba como «Sala» en español.

Ahora las opciones de entidad mantienen **nombre literal · UUID completo** y tienen un título con esos datos, también en el selector cerrado. Las opciones internas, como «Sin asignar», «Sí/No» y estados de patch, mantienen sus traducciones. Una propiedad heredada como `constructor` no puede convertirse en una etiqueta React.

Cambios: módulo `inventory-choice-labels.ts`; cuatro productores de opciones en `InventoryPanel.jsx` (padres de jerarquía, sala de rack, destino de plantilla compartida y movimiento de equipo); presentación de `Fields` en `OperationDialog.jsx`. No cambian comandos, revisión, permisos, journal ni API/backend. React sigue tratando los nombres como texto y atributos; CSS, Click-Click y RC9 conservados.

## Tres focos comprobados

1. **Homónimos:** dos sedes/edificios/salas con la misma ruta y dos racks llamados literalmente `room`; sus opciones y títulos conservan nombre y UUID distintos. Revisados EN/DE/ES mediante pruebas de presentación y el flujo real español en Edge.
2. **Rack y ocupación:** reasignación por UUID, ubicación Unicode/HTML literal y reducción exactamente a 2 U ocupadas. Reducir a 1 U devuelve 409: conserva borrador, proyecto completo y revisión; cancelar no escribe. Se preservan equipos, grupos, puertos y cables.
3. **Equipo de catálogo:** creación real del preset `sw8p` por GUI, con UUID nuevos; edición de nombre, 2 U, presupuesto cero y cinco notas desde el control RC9. Se conservan preset/catálogo/icono/color y propiedades no editadas, clase/destino y grupos/puertos/cables. Tooltip literal, recarga, otra sesión y lectura tras reiniciar el proceso servidor coinciden.

El preset probado tiene 8 puertos RJ45 PoE y 2 SFP; no se afirma haber probado los 33 presets ni circuitos físicos. Las nueve tablas de inventario se comparan íntegramente: sólo cambian el rack previsto y las filas añadidas por el preset. Auditoría: tres commits válidos; la reducción rechazada y mover/cancelar no producen mutación ni auditoría de commit.

## Resultado y límites

- Frontend anterior: **FAIL 26,61 s**, nombre `room` traducido; fallo real de presentación, no importación ausente.
- Frontend corregido, Edge/PostgreSQL **17.11**: **PASS 22,00 s**; SQL exacto y persistencia después de reiniciar el proceso servidor.
- Regresión de permisos/recuperación, mismo frontend: **PASS 20,95 s**; nueve tablas originales exactas.
- Node pertinente: **47/47 PASS**. Revisor distinto: **7/7 casos propios**, renderizado de `Fields` y productores reales, incluyendo callback/required/disabled; reproducción válida del original.

Artefacto frontend privado `app.js` SHA256 `c357d44775a145cf48a293732cc4456e9f6f86858c92d03fe23926bc0fd0990e`; CSS idéntico `50dd8567…7ec3`. DLL C2 reutilizada `5eb1abcf…7585`; no compilación .NET, cambio de versiones ni código MFA. Una ejecución inicial del build se lanzó con un directorio incorrecto, se conservó como fallo del comando y se repitió correctamente en la copia privada.

[Evidencia, fuentes y revisión](../evidence/s1-20261025/c2-rack-variants-codex/CIERRE.md). I-04.02 acreditable técnicamente con revisión distinta; I-04.03–07, candidata coordinada y QA/adopción siguen pendientes. QA-121 queda **planned**, sin habilitar por existir este build de laboratorio y sin tocar resultados personales.
