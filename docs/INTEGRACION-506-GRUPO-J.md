# Grupo J · dos familias: paneles pasivos y AP PoE

01.11.2026. **Trece configuraciones, 26 caras y 538 extremos.** [Abrir modelos](../VER-SELECCION-506-J.html) · [Selector compacto](../VER-SELECTOR-CATALOGO-J.html) · [Método reutilizable](METODO-CATALOGO-POR-FAMILIAS.md) · [Familias pendientes](FAMILIAS-CATALOGO-PENDIENTES.md).

Desarrollo 39: **752 definiciones/747 comerciales**. Selección original **392/506 (77,47 %), 114 pendientes**; 355 comerciales adicionales separados. Cada configuración usa la revisión `selected506j-20261101-v1`. La instalación nativa MFA y sus datos se conservan.

## Revisión visual paso a paso

1. Extrae el ZIP en carpeta nueva. Abre **VER-SELECCION-506-J.html** con **PERFILES-SELECCION-506-J** al lado, usando Edge o Chrome.
2. Arriba a la izquierda busca Panduit, Ubiquiti, MikroTik, Grandstream o el SKU. Pulsa un resultado. En el centro revisa ambas caras y despliega **Alcance y límites de las fuentes de este modelo**. El enlace **HTML individual de este modelo** abre sólo ese equipo.
3. Panduit: el chasis base se vende vacío. Aquí se elige explícitamente **N×CC688BL** (24/48/72 según SKU), con bocas RJ45 hembra en ambas caras. No son terminaciones IDC. Los dos extremos tienen identidades distintas y una continuidad declarada por ordinal; el trazado automático sigue pendiente.
4. AP: identifica las bocas Ethernet reales, de alimentación PoE descriptiva. Los radios, antenas lógicas y las entradas DC no soportadas permanecen inertes. La configuración de laboratorio va sobre bandeja; no acredita instalación en techo, pared o mástil.
5. Pulsa una boca y un extremo de prueba RJ45 para comprobar el anclaje del cable al desplazar las caras. El visor sólo demuestra conexiones locales; no crea cable interno por declarar continuidad ni escribe en la API.
6. Bajo las caras, en **Tu revisión de este modelo**, marca Pass/Not Pass/No probado y escribe observaciones. En la izquierda pulsa **Exportar mis resultados JSON**. Guarda `RackClick-Revision-Visual-506J.json` separado de los lotes anteriores. **Importar en casillas vacías** conserva tus notas existentes.
7. Abre **VER-SELECTOR-CATALOGO-J.html** con **PREVIEW-SELECTOR-CATALOGO-J** al lado. En **Perfil de referencia** busca fabricante/SKU o sofos; usa flechas/Enter y Escape. La lista mantiene desplazamiento interno. **Revisar selección** muestra un comando sin guardar inventario.

## Configuraciones y límites

| Fabricante | Modelo | SKU base/configuración | Ocupación | Extremos |
|---|---|---|---|---|
| Ubiquiti | U7 Pro XGS | U7-Pro-XGS | 0 U | 1 rj45 |
| MikroTik | cAP XL ac | RBcAPGi-5acD2nD-XL | 0 U | 2 rj45 |
| Panduit | Mini-Com High Density Patch Panel (48 Port, 1RU) | CPP48HDEWBL | 1 U | 48 rj45 + 48 rj45 |
| Panduit | Mini-Com Flush Mount Patch Panel (48 Port, 2RU) | CPP48FMWBLY | 2 U | 48 rj45 + 48 rj45 |
| Ubiquiti | U7 Pro XG | U7-Pro-XG | 0 U | 1 rj45 |
| Panduit | Mini-Com Flush Mount Patch Panel (24 Port, 1RU) | CPP24FMWBLY | 1 U | 24 rj45 + 24 rj45 |
| Grandstream | GWN7660E | GWN7660E | 0 U | 1 rj45 |
| MikroTik | cAP ax | cAPGi-5HaxD2HaxD | 0 U | 2 rj45 |
| Panduit | Mini-Com Flush Mount Angled Patch Panel (24 Port, 1RU) | CPPA24FMWBLY | 1 U | 24 rj45 + 24 rj45 |
| Panduit | Mini-Com Flush Mount Angled Patch Panel (48 Port, 2RU) | CPPA48FMWBLY | 2 U | 48 rj45 + 48 rj45 |
| Panduit | Mini-Com Flush Mount Angled Patch Panel (72 Port, 2RU) | CPPA72FMWBLY | 2 U | 72 rj45 + 72 rj45 |
| MikroTik | cAP ac | RBcAPGi-5acD2nD | 0 U | 2 rj45 |
| Ubiquiti | U7 Pro Max | U7-Pro-Max | 0 U | 1 rj45 |

Los seis paneles representan 264 acopladores CC688BL y 528 extremos RJ45; los siete AP suman diez Ethernet reales y ninguna boca WLAN/AC. Los módulos elegidos no se atribuyen al embalaje de fábrica. La profundidad de cada panel cargado es una envolvente conservadora declarada (profundidad del chasis más 27,62 mm del acoplador, redondeada hacia arriba), no una medición certificada; excluye clavijas, cables y radios de curvatura. Las reservas de ensamblaje/revisión quedan visibles.

En los AP circulares, diámetro es anchura/profundidad y grosor es altura en su orientación sobre bandeja. Todos los cuerpos caben en 440×60×300 mm; esto no certifica ventilación, antenas ni cableado instalado. PoE es información del modelo, no negociación ni simulación de consumo. Cualquier reserva de referencia trasera se conserva. Las imágenes se consultan como referencia; se muestran vectores propios interactivos, sin fotos operativas.

## Integración probada

Un build aislado con SDK 10.0.401, cero errores/advertencias, **20 C# focales y 967 Node en 78 archivos**. Focos del compilador incluidos en la regresión Node, sin doble suma. PostgreSQL 17.11 migra **38→39** conservando 739 definiciones/734 instancias previas, soportes, UUID, auditoría, operaciones e historial; repetir migración no cambia datos.

En otra base nueva: dos instancias por modelo, 538 extremos en las primeras instancias, **18 cables API** (12 rj45, 6 rj45-rear) y **dos Click-Click reales** (panel y AP). Se conserva la declaración `sameOrdinal`/`tracingImplemented=false` de cada panel, sin fabricar cables internos. La ocupación repetida de la bandeja se rechaza. Un equipo sintético de referencia aporta controles negativos RJ45↔SFP/AC, sin inventar puertos en los nuevos modelos. También pasan replay, conflicto 412, revisión 422, rollback, lector 403, catálogo sólo SELECT y runtime sin DDL.

Edge inspecciona las 26 caras y todos los extremos de la primera instancia; comprueba UUID, objetivos ≥24 px, creación desde selector 752, móvil 390 px, recarga, otra sesión y persistencia tras reiniciar el proceso. No es reinicio Windows ni ensayo de instalador. [Evidencia y revisión independiente](../evidence/s1-20261101/integracion506j/RESULTADOS.md). La compactación visual final de los AP se volvió a comprobar con otra base nueva; los bytes de C#/SQL no cambiaron y se reutiliza explícitamente la prueba anterior de migración, sin anunciar que se repitió.

## Reserva del formulario antes de adopción

La galería y este manual explican base + N×CC688BL y el cálculo conservador de profundidad. El formulario actual de creación todavía muestra las dimensiones y continuidad sin exponer ese BOM ni distinguir cotas base de envolvente. La revisión independiente lo registra como límite UX de gravedad media: debe corregirse antes de la adopción final. No se considera aceptado ese flujo productivo por haber pasado las pruebas de datos.

## Disponibilidad

**QA-160 planificada.** Los HTML son revisables ahora; la instalación nativa no se actualizó. Para probar guardado en tu servidor, esperar la candidata completa identificada; no copiar DLL/SQL sueltos. Faltan 114 modelos y contratos especializados, paquete Windows/Restore y QA final. Después se prepara el laboratorio de al menos 50 clientes. **Índice del cierre restante 9,76/100 sin cambio; no es porcentaje global.**
