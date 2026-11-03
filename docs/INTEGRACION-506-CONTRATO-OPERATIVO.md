# Integración operativa de los 506 modelos elegidos

01.11.2026 · Propuesta mínima del agente de arquitectura. Responde a la aclaración de
Wascar: los modelos deben estar disponibles para crear inventario y en el paquete.
Un expediente o visor externo no satisface ese resultado. Reutiliza la
[auditoría anterior](CONTRATO-CATALOGO-SELECCION-462.md); no implementa los cambios.

**Sí pueden existir perfiles operativos con cotas desconocidas, después de adaptar
el contrato. Hoy el código los rechaza.** La reserva U documentada permite inventariar
un equipo de rack sin conocer W/H/D; no permite certificar su ajuste físico. La vista
debe decir «Esquema de puertos; cotas/caras no confirmadas» y mantener las acciones reales
sobre los UUID. Esto aporta inventario y cableado tipado; no sustituye la carcasa exacta.

## Bloqueos actuales, con referencias exactas

| Área | Archivo/símbolo o constraint vigente | Efecto |
|---|---|---|
| Cotas | `InventoryHardwareProfiles.cs:13`, record `Profile`: `decimal WidthMm/HeightMm/DepthMm`; `Slot` en línea11 tampoco nullable. | No puede expresar desconocido. Usar 0, 1 o dimensiones de otro SKU falsearía los datos. |
| SQL de catálogo | SQL017 líneas6–16: `mount_kind` sólo shelf/rack/desktop; `rack_units` entero0–60; W/H/D NOT NULL y positivos; desktop=0, los demás>0. SQL018 cambia H/D a numeric, sin quitar NOT NULL. | Ningún perfil sin dimensiones; tampoco logical, rackContainer, pared/DIN/vertical o reserva fraccionaria. |
| Lectura sellada | `ReadHardwareDefinition`, `InventoryHardwareCatalog.cs:29–30`: `GetInt32/GetDecimal` y comparación completa. | Quitar sólo NOT NULL en SQL no basta; fallaría lectura o coherencia con C#. |
| Colocación | Constraint `inventory_device_placement`, SQL017 líneas139–145: raíz rackEquipment U1–1000, hijo montado0U; dose/endDevice en sala requieren profileKey NULL. | Hoy no se puede adjuntar una definición de hardware a un objeto de sala. |
| Trigger | `inventory_validate_mount`, SQL017 líneas157–158, constraint `inventory_hardware_definition`: exige rackEquipment, U idénticas a definición y padre si desktop. `inventory_mount_dimensions` compara cotas en línea170. | Un perfil lógico en sala y un 0U raíz son rechazados. El ajuste desconocido nunca debe pasar por comparación nullable silenciosa. |
| Comando | `CreateHardware`, `InventoryHardwareMounting.cs:14,21,45,57`: claves cerradas, rackId obligatorio, capacidad por RackUnits e INSERT fijo rackEquipment. | No acepta roomId ni crea un rack contenedor. `UpdateHardware` protege identidad y permite sólo nombre/notas/color. |
| API genérica | `Device`, `InventoryDevices.cs:54–64`: prohíbe profileKey por comando genérico; rackEquipment pide U enteras positivas, room/endDevice usa null. `CreateFromCatalog`, líneas43–44, también pide reserva entera para rack. | No hay atajo seguro por device.create o por los presets RC9. |
| Interfaz | `validProject`, `inventory-model.ts:19–24`; `validMounts`, `hardware-mounting.ts:51–59`: rechazan raíz0/null/fraccionaria. `MountedPhysicalRack.jsx:54` crea renglones con `Array.from({length:d.u})`. | Cambiar sólo backend dejaría un snapshot inválido o una altura falsa. |
| Consumidores | `ValidDetailEntity`, `InventoryChangeDetails.cs:168–176`, exige U enteras positivas para equipo rack y hasta96 puertos/grupo. SVG usa `GetInt32(sizeU)`; XLSRC9 usa `GetInt64` y rechaza size<=0 (`InventoryRc9ExcelReports.cs:254–255`). | Admitir U fraccionarias/null en rack requiere una ampliación coordinada, no un cast o redondeo. |
| Tipos y cara | SQL019 líneas3–6: plantillas sólo rj45/sfp/power; SQL017 face sólo front/rear. `InventoryRules.PortTypes` ya tiene sfp28/qsfp/mgmt/console/usb_a/usb_c; SQL002 acepta face=auto y power outlet. | Extender enum de inventario no extiende plantillas. Las caras desconocidas necesitan modo neutro sin inferirlas de tipo. |
| Dibujo | `BatchSocket`, `BatchHardwareFace.jsx:31–35`, dibuja cualquier tipo no power/sfp como RJ45. `MountedPhysicalRack.jsx:24` filtra por `irPortFace`, que es una selección de representación. | El nuevo modo debe evitar ambos comportamientos para conectores/caras no documentados. |
| Materialización | `AddGroup`, `InventoryDevices.cs:99`, limita count1–96. `CreateHardware` pasa grupo tipo/count/prefijo y sólo fija cara/rol/keys después. | SQL permite hasta256 por grupo, pero el comando no. Tampoco conserva por sí solo nombres individuales arbitrarios como wan/HA/serie. |

## Vía mínima recomendada

### 1. Separar cotas, reserva e inventario lógico

Nueva migración posterior a la vigente, sin editar SQL001–028 ni las 406 definiciones.
Convertir W/H/D de `hardware_definition` y `Profile` a nullable y adaptar el nuevo
compilador para conservar esos null; comparar null de forma
exacta en `ReadHardwareDefinition`. Los límites positivos se mantienen cuando existe
un valor. `shelf`, sus slots y `desktop` montado siguen exigiendo todas las cotas para
realizar un ajuste dimensional. `Slot` puede conservar sus `decimal` no null.

- `mount_kind=rack`: U entera positiva respaldada; W/H/D desconocidas permitidas.
  Crear rackEquipment en su rack, reservar esas U y usar esquema. Las cotas no se usan
  para validar ancho/profundidad ni para afirmar montaje físicamente comprobado.
- Nuevo `mount_kind=logical`: `rack_units=0` significa **sin reserva de rack en este
  recorrido**, no tamaño físico del aparato. Crear un objeto lógico en sala con
  `kind=endDevice`, `rack_id=null`, `room_id` autorizado, `size_u=null` y perfil exacto.
  Conservar categoría original (servidor/UPS/switch…), montaje declarado y U nominales
  originales, incluidas0/fracciones, como hechos documentales separados. La UI lo
  identifica como inventario lógico del modelo, sin atribuirle función de terminal final.
- Para ambos, geometría del chasis puede faltar. No transformar dimensiones de pantalla
  en milímetros. En `hardwareFitsShelf` y trigger, desconocido implica ajuste no validable,
  nunca éxito. El perfil lógico no obtiene un slot de bandeja por omitir cotas.

Esta ruta reutiliza los objetos de sala y sus puertos/cables ya proyectados por
`projectToRc9`; exige ampliar el comando de hardware, SQL y selector, no rehacer RC9.
La excepción para hardware en sala debe ser estrecha: definición logical sellada,
sin padre/slot, misma identidad y ámbito; no relajar la regla de los perfiles físicos.

### 2. Crear sólo extremos declarados, con nombres e identidad estables

Ampliar `hardware_group_template` y el compilador para los tipos de inventario ya
implementados y `face=auto`; no cambiar SQL002 por esos tipos. Añadir nombres físicos
por ordinal a la definición compilada y su proyección. Materializar cada extremo con
UUID propio y `hardwareGroupKey/hardwarePortKey`; conservar el nombre del fabricante
en metadato protegido, separado de la etiqueta editable del usuario. Grupo+ordinal
es el vínculo técnico; un texto de puerto nunca identifica el extremo.

La partición por grupos debe respetar el límite real96/32grupos. Si hace falta, dividir
de forma determinista un banco por tipo y trozos de hasta96 conservando sus nombres;
si supera el contrato agregado, ampliar y probar ese límite antes de habilitar el modelo.
No truncar, renumerar en silencio o considerar correcto un INSERT que el helper rechaza.

`Pair` ya admite conexiones entre objetos de sala y equipos de rack dentro del ámbito;
para perfiles compara familias y rol power. Reutilizar transacción, revisión, idempotencia,
reservados, auditoría y confirmación posterior al commit. El modo lógico no rebaja estas reglas.

- RJ45/SFP/SFP28/QSFP/gestión/consola/USB sólo se proyectan mediante una tabla cerrada
  que conserve forma y función documentadas. Consola con boca RJ45 no es Ethernet.
- `other`, radio, virtual, LTE y función desconocida no se convierten a RJ45/SFP.
  Permanecen como componentes declarados sin acción de cableado; se refleja lo pendiente.
- FC/SAS/DC y terminaciones pasivas no soportadas requieren familias/formas y reglas
  operativas concretas. La ausencia de geometría no lo impide; la ausencia del tipo sí.
  No declarar todos los puertos funcionales hasta implementar esos casos necesarios.
- `powerRole=outlet` ya cabe en SQL/inventario; adaptar compilador y dibujo. La pareja
  power/inlet–outlet no demuestra compatibilidad de enchufe, tensión o carga. Para
  conexiones específicas, validar el contrato físico conocido, sin AC↔DC implícito.
- PSU o NIC opcionales no crean extremos instalados. El perfil base puede crear el
  chasis y sus puertos fijos; poblar módulos requiere una configuración explícita
  validada o revisión fija que la describa. Un chasis con cero puertos conocidos es
  creable para inventario, pero no satisface un criterio de cableado completo del modelo.
- Combos conservan exclusión mutua. No crear como independientes dos medios del mismo
  puerto lógico; si todavía no se implementa esa selección/exclusión, queda pendiente.

### 3. Mostrar un esquema operativo honesto

El selector principal incluye las revisiones nuevas; crear abre la operación real y
devuelve los UUID persistidos. Una rama de representación esquemática reutiliza los
botones, estados, tooltips, teclado, contexto y Click-Click. Muestra los nombres físicos
con formas tipadas o un símbolo neutro rotulado; no simula una carcasa exacta.

Puertos sin cara documentada se muestran en «Cara sin confirmar», sin asignación por
`irPortFace`, sin duplicar extremos y con anclas de cable estables. Front/rear sólo
se usan para los extremos con cara conocida. Ausencia de foto o dibujo no desactiva
los puertos tipados; la leyenda EN/DE/ES explica que posiciones, escala y cotas no
están confirmadas. Las carcasas existentes siguen por su rama visual actual.

Actualizar `HardwareCreationFields`, proyección, OpenAPI y vista de sala para enseñar
cotas desconocidas y bloquear ajuste de bandeja cuando corresponda. El perfil no debe
poder cambiarse por una actualización de metadatos ni falsificarse mediante properties.
Proteger también el nuevo nombre físico de puerto en el servidor y adaptar los botones
de sala a las operaciones admitidas para hardware; no dejar un editor genérico de grupos
que sólo termine en rechazo del backend.

### 4. Tratar racks y montajes especiales por su entidad real

| Caso | Utilidad mínima honesta | Qué sigue faltando para representación física completa |
|---|---|---|
| Cuatro racks seleccionados | Modelo de contenedor con capacidad U documentada; alta de `inventory_rack`. | Carcasa/puertas/laterales y dimensiones si no están documentados. |
| Vertical0U | Perfil lógico de sala con puertos, conservando el dato0U y referencia de montaje. | Anclaje lateral al rack, orientación/ocupación lateral, navegación y exportaciones. No usar desktop ni1U. |
| DIN o pared | Inventario lógico en sala con su montaje como dato documentado. | Soporte/panel/carril y posición física; no afirmar ajuste a bandeja. |
| U fraccionaria | Perfil lógico de sala, valor original conservado. | Ocupación fraccionaria del rack en SQL/API/capacidad/GUI/informes. No redondear. |
| Sobremesa sin cotas | Inventario lógico en sala con extremos conocidos. | Montarlo en bandeja exige cotas y soporte válidos; no inventarlos. |

Para los racks, extensión mínima coherente: permitir `mount_kind=rackContainer` en
la misma definición global y añadir `capacity_u` propia; `rack_units=0` queda como
«no es aparato que reserve U». Nuevo `rack.createHardware` materializa `inventory_rack`
desde clave/revisión exactas, con FK/revisión protegida y capacidad validada; no pasa por
`CreateHardware` de equipos. Alternativamente puede existir un registro de modelos de
rack separado, conservando los mismos controles. No sobrecargar rack_units para significar
a la vez capacidad del contenedor y consumo de un aparato.

El alta normal de rack ya existe en `Hierarchy`; reutilizar su ámbito, capacidad y flujo
transaccional. Una etiqueta comercial libre en properties no equivale a un modelo enlazado
y verificado; no usarla para acreditar los cuatro perfiles. Si se exige instalar0U/DIN/
pared/fracciones dentro del rack, el mínimo lógico anterior es insuficiente: hace falta
un contrato de ubicación explícito y adaptar los consumidores indicados, con pruebas propias.

## Inclusión en paquete y condición de cierre

El reparto 44/462 del párrafo siguiente conserva el baseline histórico del conciliador
por nombre/modelo. Para la planificación vigente rige la adenda de mapeos al final.

Los 506 ID seleccionados se resuelven exactamente a 44 revisiones existentes y 462 nuevas
entradas funcionales, incluidas las de racks. Se conservan los otros 362 comerciales y
todos los UUID existentes. El conteo debe distinguir modelos de contenedor de perfiles
de aparato; cambiar de registro no puede dar una falsa coincidencia por nombre.

No basta copiar JSON al instalador: integrar registro C#/frontend, nueva migración y
`SchemaMigrations.LatestVersion`, target/manifiesto de coherencia, verificador frontend,
recursos compilados, selector y alta. El proyecto C# ya copia `database/*.sql`; sus targets
de catálogo y `development/frontend/build.mjs` deben conocer el conjunto nuevo.
El paquete completo debe llevar binarios/GUI/SQL de la misma revisión, fuentes/derechos
permitidos, hashes nuevos y operadores New/Restore compatibles, sin recursos raster privados.

Cierre funcional por ID: selector → alta real en rack/sala/entidadrack apropiada → puertos
declarados e identificación exacta → edición y conexiones admitidas → commit/recarga/otra
sesión/reinicio → permisos/conflicto/idempotencia → consumidores → instalación/restore
del paquete íntegro. Un índice de expedientes no prueba ninguna de esas etapas. La falta
de carcasas exactas sigue registrada aunque el inventario lógico funcione.

## Alcance y evidencia de esta propuesta

Se inspeccionaron 26 archivos y fijaron 119 líneas relevantes en
[FUENTES-CONSULTADAS.json](../evidence/s1-20261101/integracion506/contract/FUENTES-CONSULTADAS.json).
Reutilización y límites: [REVISION.md](../evidence/s1-20261101/integracion506/contract/REVISION.md).
No se ejecutó producto, build, pruebas amplias, DB, VM, instalación o QA; no cambios MFA,
commits o publicación. El documento no declara los 506 operativos ni empaquetados hoy.
Índice restante 9,76/100 sin cambio; no se acredita avance global por esta propuesta.

## Adenda · siete correspondencias SKU aprobadas

01.11.2026. La revisión de QA aprobó [siete mapeos exactos a perfiles existentes](../evidence/s1-20261101/integracion506/review/MAPEOS-7.json)
que el conciliador original no reconocía por nombre/modelo o alias. Su resultado es
`PASS`, con `newProfiles=0`: no son siete altas ni una ampliación funcional. Cada
correspondencia fija selectionId, SKU, clave/revisión y digest de la definición.
HPE no se convierte en un alias global de Aruba; las correspondencias son explícitas.

| Estado del recuento | Seleccionados resueltos | Pendientes de resolver |
|---|---:|---:|
| Baseline histórico por nombre/modelo | 44 | 462 |
| Tras los siete mapeos aprobados a perfiles existentes | **51** | **455** |
| Si el grupo A integra y supera PostgreSQL y revisión independiente sus 17 perfiles nuevos (12 Aruba + 5 Ubiquiti) | **68** | **438** |

El último renglón es una proyección condicionada: no acredita hoy esos 17 perfiles.
Los siete mapeos reutilizan definiciones ya existentes y mantienen sus límites
documentados; no incorporan consolas, interfaces virtuales, PSU opcionales o DC que
aquellas definiciones no materializaban. Tampoco equivalen a instalación del paquete,
prueba de Wascar o aceptación de todas las revisiones físicas.

Por tanto, **no se exige crear 462 definiciones nuevas**. La obligación es resolver
los 506 ID mediante perfiles existentes compatibles y verificados o nuevas definiciones
cuando hagan falta. Otros mapeos legítimos pueden reducir las altas necesarias después
de contrastar SKU/configuración, identidad y límites por ID; nunca mediante semejanza,
alias amplio o selección implícita de latest. Se conservan los 406 perfiles de partida
y sus UUID de instancia. Esta adenda actualiza la interpretación del reparto, conserva
su historia y no modifica producto, ledger ni el índice restante 9,76/100.
