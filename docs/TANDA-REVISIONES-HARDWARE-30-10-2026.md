# Revisiones de hardware — resultado

30.10.2026. Primer tramo del catálogo versionado, implementado y probado.
Se conserva el esquema16, el JSON de las cuatro referencias v1 y la instalación10.
No hay modelos comerciales nuevos, dependencias nuevas, commits o push.

## Qué cambia

- Cada búsqueda usa **clave y revisión exactas**. Dos revisiones sintéticas de
  una clave conviven sin sobrescribirse; duplicar una pareja se rechaza.
- El registro toma copias independientes y protege también listas anidadas.
  No se puede cambiar una definición aceptada modificando el objeto de entrada.
- Las creaciones nuevas envían `profileVersion`, visible en el formulario. Las
  solicitudes anteriores que lo omiten siguen ligadas a v1, nunca a «latest».
- Se aprovecha la revisión que ya se guardaba en las propiedades del equipo.
  La lectura conserva sus dimensiones y sus puertos reales.
- Una revisión no disponible produce una vista genérica con advertencia; no
  reutiliza el dibujo de otra versión ni oculta los equipos montados. Una bandeja
  con revisión desconocida no se ofrece para montajes nuevos y el servidor lo
  rechaza también.

[Contrato](CONTRATO-REVISIONES-HARDWARE-v1.md).
[Revisión independiente](REVISION-REVISIONES-HARDWARE-30-10-2026.md).

## Evidencia

Entorno Windows, SDK10.0.401 fijado, runtime10.0.12, PostgreSQL17.11,
Node24.21.0/esbuild0.25.10 y Edge156.0.4314.50. Sin cambio de versiones.

| Verificación | Resultado |
|---|---|
| Restore locked y build Release | 0 errores y 0 advertencias. Binlogs privados. |
| Prueba del fallo anterior | La misma consulta de revisión inexistente falla en el código anterior y pasa tras la corrección. Se conserva la salida previa. |
| Node | 814/814 PASS; incluye los 13 focos de montaje/revisiones. |
| .NET | 4/4 pruebas nuevas de registro/revisiones PASS. Se compiló el proyecto de calidad; no se afirma haber ejecutado toda su suite. |
| HTTP/PostgreSQL real | 5 comprobaciones compuestas PASS: versión explícita/replay, omisión histórica, ocho revisiones inválidas sin mutación, cuatro rechazos por revisión de padre desconocida/malformada y metadato de versión protegido. Persistencia tras reinicio. |
| Edge/PostgreSQL real | Revisión visible/enviada por GUI; instancias previas con revisión ausente del catálogo mantienen montaje, puertos y cable; no se suponen dimensiones de alojamiento v1. Recarga, otra cuenta y reinicio conservan el resultado. |
| Regresión de montaje | El conjunto anterior de81puertos/3cables y el rack mixto RC9 vuelven a pasar; 10comandos confirmados, recarga/otra cuenta/lector/reinicio. |
| Revisor independiente | Pruebas Node propias y negativos HTTP/PG propios, separados de la ejecución del coordinador. Alcance exacto en su dictamen. |
| Guía manual | QA137 planned;136casos anteriores conservados. Dos HTML regenerados,35pruebas del generador PASS. |

Las revisiones no disponibles del recorrido Edge se introducen mediante edición
del propietario de **su nueva base de fixture**. La API no permite crear esas
versiones ni alterar la revisión de una instancia. No son modelos publicados.
La prueba de coexistencia de dos revisiones es sintética, en el registro; el
producto sigue ofreciendo sólo las cuatro referencias v1.

## Código

- Backend: `InventoryHardwareProfiles.cs`, `InventoryHardwareMounting.cs`,
  `OpenApiInventory.cs`; prueba nueva `HardwareRevisionTests.cs`.
- Frontend: `hardware-registry.ts`, `hardware-mounting.ts`, proyección en
  `inventory-model.ts`, componentes de creación/representación y textos. No se
  modifica el ZIP RC9 adoptado ni la geometría del JSON v1.
- Nuevos ensayos: `test_hardware_revisions.py`,
  `test_hardware_revisions_gui.py`, `browser-hardware-revisions.mjs`,
  `hardware-revisions.test.mjs`; el foco de montaje conserva sus aserciones y
  ahora espera la revisión explícita del nuevo cuerpo de comando.

Huellas, comandos y salidas sanitizadas:
`evidence/s1-20261030/hardware-revisions/RESULTADOS.md`.

## Pendiente

El catálogo general de definiciones en PostgreSQL, modelos/SKU verificados,
módulos/combos, imágenes/licencias y publicación del catálogo siguen pendientes.
SQL016 aún contiene la limitación del primer ensayo; no se declara que baste
con añadir un JSON para registrar cualquier producto comercial.

También siguen pendientes los consumidores de montaje SVG/XLS/avisos, la
distribución/operadores16 y una candidata completa para QA136/137. Tu servidor y
su MFA permanecen intactos. [Guía QA preparada](QA-REVISIONES-HARDWARE-WASCAR.md).

**Índice de cierre restante:9,76/100, sin incremento automático.** Este avance
parcial no cierra todo C-HW-02/C-HW-06 ni modifica la métrica global del producto.
