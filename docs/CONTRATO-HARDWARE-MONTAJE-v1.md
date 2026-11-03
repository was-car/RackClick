# Hardware y montaje v1 — fundamento del catálogo

Fecha: 30.10.2026. Desarrollo autorizado por Wascar. Este documento define el
contrato del ensayo; no declara instalada ni adoptada la candidata.

## Identidad, plantilla e instancia

- Una plantilla describe un modelo; una instancia representa un objeto físico y
  tiene UUID propio. Sus grupos, puertos y cables también tienen UUID propios.
- El catálogo histórico RC9 de 33 plantillas permanece intacto. El perfil inicial
  `hw-reference-v1` añade cuatro referencias **sintéticas y genéricas**, sin
  atribuirlas a Sophos, Cisco u otro fabricante ni copiar imágenes comerciales.
- La ampliación será fabricante → familia → modelo → variante/SKU → revisión.
  Un puerto de plantilla tiene clave estable; su instancia recibe un UUID nuevo.
  Cambiar una plantilla no modifica equipos ya creados.
- Dimensiones en milímetros, ocupación de rack en U y posición dentro de un
  soporte son conceptos distintos. El esquema nuevo de desarrollo es 16; los
  paquetes instalados con esquema 15 no se cambian automáticamente.

## Montaje y ocupación

- Un equipo raíz reserva `sizeU > 0` del rack. En v1 el orden es el apilado RC9
  existente (`sortOrder`), sin afirmar posiciones U absolutas ni doble ocupación
  frontal/trasera independientes.
- Un equipo sobre bandeja conserva el mismo `rackId`, su propio UUID y puertos.
  `mountParentId` y `mountSlotKey` identifican su soporte y alojamiento; `sizeU=0`
  significa **cero U adicionales**, no altura física nula.
- El padre y el hijo deben pertenecer al mismo Systemhaus, cliente y rack.
  No se admiten ciclos, soportes anidados ni dos objetos en un mismo alojamiento.
  Las relaciones se guardan con constraints en PostgreSQL, no sólo en JSON.
- La bandeja del ensayo reserva 2 U para el conjunto. Su alojamiento `main`
  admite 440 × 60 × 300 mm; el firewall mide 220 × 38 × 200 mm. Son dimensiones
  de referencia del ensayo, no especificaciones de un producto comercial.
- Bandeja 2 U + firewall montado 0 U adicionales + switch 1 U + panel 1 U = 4 U.
  Un rack de 4 U rechaza otra reserva de 1 U. Los movimientos, duplicaciones o
  cambios estructurales no soportados en v1 se rechazan explícitamente; nunca
  se pierde o cambia silenciosamente la relación de montaje.

## Referencias iniciales

| Clave | Montaje | Puertos frontales | Puertos traseros |
|---|---|---|---|
| `shelf-2u` | raíz, 2 U, alojamiento `main` | ninguno | ninguno |
| `desktop-firewall-6` | hijo de bandeja | 6 RJ45 | 1 RJ45 de gestión |
| `switch-24` | raíz, 1 U | 24 RJ45 | 2 SFP |
| `patchpanel-24` | raíz, 1 U | 24 RJ45 | 24 RJ45 |

Los conectores de alimentación no especificados no se ofrecen como puertos
conectables. No se infieren PoE, voltajes, circuitos, ópticas o conectores a partir
del nombre de la referencia. Frontal y trasera son vistas del mismo objeto.

## Puertos y conexiones

- Todos los comandos usan IDs y grupo/tipo. `gn=1` frontal y `gn=1` trasero son
  puertos distintos; el número mostrado nunca decide la identidad.
- En el panel de referencia se declara la correspondencia frontal/trasera 1:1
  por claves de plantilla. Es información de continuidad del modelo; no crea
  cables y no acredita todavía un motor de trazado a través del panel.
- Una conexión externa conserva los UUID de sus dos puertos. Se aplican los
  controles existentes de ámbito, ocupación, estado, tipo y permisos.
- Click-Click sobre los puertos reales abre la operación existente. El éxito
  sólo aparece después de la confirmación del servidor. Recarga y otra sesión
  deben leer el mismo montaje y los mismos extremos.

## API y persistencia

Se reutilizan `/api/v1/customers/{id}/project` y el canal transaccional
`POST /api/v1/customers/{id}/commands`, con revisión, actor, CSRF e idempotencia.

```json
{"type":"device.createHardware","payload":{
  "profileKey":"desktop-firewall-6", "rackId":"<uuid>", "name":"Firewall QA",
  "mountParentId":"<uuid de bandeja>", "mountSlotKey":"main"
}}
```

El snapshot añade `hardwareProfileKey`, `mountParentId` y `mountSlotKey`, nulos
para equipos anteriores. Perfil desconocido, padre inválido, falta de permisos,
conflicto de revisión y alojamiento ocupado son rechazos, sin cambios parciales.

## Ampliación posterior por fabricante

Antes de aceptar un modelo: fuente oficial y fecha; marca/modelo/SKU; dimensiones;
kit de montaje y reserva/holguras; caras y conectores; agrupaciones/combos;
potencia/PoE cuando se conozcan; representación SVG propia o licencia explícita;
pruebas de creación, ocupación, conexiones, recarga y actualización de catálogo.
Los campos desconocidos se marcan desconocidos. Una foto publicada en internet
no constituye permiso de redistribución.

La primera implementación limita expresamente SQL y servidor a estas cuatro
referencias. Añadir fabricantes **no es sólo copiar otro SVG o JSON**: antes se
evolucionará a definiciones versionadas y su validación, con una migración nueva.
No se editará una migración 016 ya aplicada. `hw-reference-v1` se conserva
congelado; el catálogo general resolverá por clave **y revisión**, y conservará
las dimensiones/definición de cada instancia histórica. Módulos, combos,
posiciones U absolutas, peso/carga y holguras de ventilación quedan pendientes.

## Compatibilidad de consumidores en este foco

- En un rack mixto se mantiene el renderer RC9 de los equipos anteriores,
  incluidos sus controles de colapso y orden, decoraciones y puertos. Sólo las
  filas de los nuevos perfiles usan el montaje añadido.
- El presupuesto PoE y la reserva U de los perfiles no son campos editables en
  este editor. Nombre y notas sí se guardan; los estados y etiquetas de puertos
  usan la operación existente. La cara física y las claves de puerto del perfil
  son inmutables. Un cambio estructural exige otro recorrido explícito.
- Las vistas/listas por IDs y el inventario imprimible conservan los objetos.
  La fila imprimible del hijo dice «0 U adicionales; montado sobre» e incluye el
  UUID del soporte y el alojamiento.
- SVG pasivo v1 y XLS/HTML RC9 no tienen relación de montaje: rechazan con
  `report_mounting_unsupported` únicamente el rack que contiene un hijo montado,
  en vez de aplanarlo silenciosamente. Los racks sin hijos siguen exportándose.
  Adaptar estos formatos es un pendiente explícito; no se anuncia paridad total.
- La nueva acción mantiene la auditoría transaccional. El aviso multiusuario
  histórico pide refrescar; no inventa un descriptor de montaje que todavía no
  sabe expresar. La ampliación de su detalle tipado queda pendiente.

El inventario de investigación existente está en
`docs/ALCANCE-CATALOGO-FABRICANTES.md`; disponer de una lista de modelos no
equivale a tener plantillas verificadas e integradas.
