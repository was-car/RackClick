# Repetidores de Alemania · cierre del lote de desarrollo

03.11.2026 · Petición de Wascar: incorporar también los repetidores usados en Alemania. Resultado favorable para desarrollo, con revisión independiente. No es adopción, actualización nativa de D ni cierre del paso 9.

## Resultado concreto

Diez modelos, cuatro fabricantes, 20 caras, 13 extremos Ethernet y 10 de alimentación. Seis unidades de enchufe y cuatro de sobremesa, todas en sala sin U/rack/bandeja. FRITZ!Repeater 600 no tiene LAN. Radios no son puertos y los devolo de este lote no se convierten en Powerline. Ubicación `tabletop` y descriptor eléctrico documental `eu-2pin-plug` explícitos; no se deduce un encaje ni se certifica una clavija/diámetro/polaridad.

Definiciones, lock, proyección, migración045 y guardas de build se generan desde autoría validada. Desarrollo: **884 revisiones / 877 modelos comerciales distintos**; se conservan 874 revisiones previas y la selección506. D sigue siendo candidata11/esquema43; en este lote no se accedió a VM, cuentas, claves, servicios nativos ni QA. Los catálogos44/45 siguen sin un instalador completo actualizado.

## Investigación y decisiones

[Investigación previa](INVESTIGACION-PREVIA.md), [investigación del autor](catalogo/INVESTIGACION-Y-DECISION.md), [complemento PDF](INVESTIGACION-COMPLEMENTARIA.md) y [fuentes del revisor](review/FUENTES-Y-ALCANCE.md). Se reutilizan contrato de catálogo, método por familias, buscador, renderer y validadores existentes. Sin nueva dependencia de producto.

No se intercambian los ejes W/D/H de TP-Link. Las tres medidas de devolo permanecen desconocidas por referencias ambiguas/contradictorias. Telekom es el modelo2021, no la segunda generación. Las traseras son agrupaciones operativas de conectores con reserva explícita sobre posiciones inferiores/laterales. Vectores propios, sin fotos/manuales de proveedores en el ZIP.

Skills aplicadas: React best practices y Web Interface Guidelines (Vercel, instrucciones locales), PDF para fuentes y binlog-generation para el build .NET del autor. No se instalaron plugins ni se afirma activar una skill de diseño inexistente.

## Qué se ejecutó

| Responsable | Comprobación | Resultado y evidencia |
|---|---|---|
| Implementador del catálogo | Generador Python, negativos y determinismo | 18/18; [salida](catalogo/PYTHON-18.txt) |
| Implementador del catálogo | Node del catálogo | 7/7; incluido en la regresión179, no se suma como siete pruebas distintas adicionales; [salida](catalogo/NODE-7.txt) |
| Implementador del catálogo | Build Release SDK10.0.401 | 0 errores/advertencias; binlog privado, hashes en [resultado del componente](catalogo/RESULTADOS.md) |
| Implementador del catálogo | PostgreSQL17.11 nuevo, migración44→45 y base nueva45 | PASS; [recibo saneado](catalogo/PG17-RESULTADOS.json) |
| Coordinador | Build frontend `node build.mjs` | PASS; [salida](BUILD-FRONTEND.txt), sin CDN |
| Coordinador | Todos los `hardware*.test.mjs` más búsqueda/tamaño de repetidores | 179/179, 0 omitidas; [salida final](NODE-REGRESION-179.txt) |
| Coordinador | Edge, visor final | 60 casos (10×2×3 anchos), 69 representaciones de extremos, nueve búsquedas y tres idiomas; [mediciones](BROWSER-FINAL.json) |
| Revisor independiente | Contrato, generados, históricos y 12 negativos propios | 874 aserciones, 212 archivos históricos fijados; [contraste](review/CONTRASTE.json) |
| Revisor independiente | Edge desde fuentes, geometría, objetivos, texto no confiable y teclado | 60 casos, 69 objetivos y once consultas; [mediciones](review/UI-FINAL.json) y [dictamen](review/DICTAMEN.md) |

PostgreSQL comprueba dos ejemplares por modelo, 23 extremos por conjunto y 19 conexiones (9 Ethernet y 10 energía). La fuente de energía es sintética, sólo para roles. Recarga, segunda sesión y reinicio de ASP.NET conservan UUID/grupos/ordinales/caras/roles/metadatos. Negativos403/404/422/409 sin cambios de inventario, auditoría, operaciones o revisión. Runtime no tiene DDL ni DML de catálogo. Migración repetida idempotente e historial1..44 intacto. Laboratorio detenido.

El foco Edge usa los componentes reales con fixtures locales; no acredita por sí mismo SQL, arrastre de cable completo ni una instalación Windows. El revisor leyó el recibo PostgreSQL del autor, sin presentarlo como su propia ejecución. No se repiten suites MFA o instaladores ajenos a este cambio.

## Incidencias conservadas y correcciones

- La primera regresión Node desde raíz dio178/179: el test nuevo de manifiesto dependía del cwd. Se corrigió el harness con `import.meta.url`, sin cambiar producto por ese fallo. [Salida inicial](NODE-REGRESION-INTERMEDIA.txt) y salida final separadas.
- La primera galería mostró barra local evitable en un modelo de enchufe: su ancho compacto180 era inferior al mínimo calculado por las bocas. La vista final toma el máximo del ancho compacto y ese mínimo. El revisor retiró el mínimo sólo en una copia de prueba y observó21 barras evitables; no mutó producto.
- Tres rótulos del6000 conservaron su Y antigua al compactar bancos; se recolocaron. **GL-RP-01**: placa rectangular detrás del círculo Telekom. El autor corrigió radio143 en ambas caras y rejillas contenidas; revisión final lo cierra. Cambios visuales sin alterar SQL/C#/DLL ensayados.
- Las coordenadas/artefactos intermedios no sustituyen al pin final. Capturas del coordinador y del revisor tienen esa distinción. El diff de los registros y las referencias anteriores se conservan; no se reconstruye un diff de archivos cuyo original no se capturó.

## Entrega local

- [Abrir HTML](../../../VER-REPETIDORES-ALEMANIA-01.html).
- [ZIP completo](../../../RackClick-Revision-Repetidores-01.zip): **78efa14770d0c5bb7bf5c7c8dc06d9532e2450bab5ce22a389b47cf792e5dc4f**, 1187490 bytes, 14 entradas, CRC válido. [Recibo](ENTREGA.json).
- El visor incluye renderer/catálogo reales, React local y fuentes; no contiene credenciales, DB, radio simulada ni instalador. Abrir desde la carpeta extraída completa. Los botones seleccionan extremos locales; no guardan conexiones.
- Frontend final: app **21d85d7543595d77befce549b98c7f0ebb07d8619648fc9830132f2a04523d04**; CSS **259db36410d51571cc567331bad6852dbbe67871ab64273a992b8affc06c14f7**.
- Manifiesto catálogo: **6349a1370f4ffc6b1ed2ada66816c2a67aa1ad7c4ffad2bf3ec064d599b2dd56**; JSON **6eb2ef2b4945276a10a023a05f33b2aaa1d1d18ecdfdd5cff39867f6dc6cd86d**; DLL de laboratorio **a6046b6a20b176f196c604e38af9eb8bed5132762efd9c5d8b3be00e55edea2b**.

## Escaneo seleccionado y documentación

Gitleaks8.30.1 con herramienta pinada y reglas existentes:123 archivos seleccionados; **salida original1,16 coincidencias generic-api-key**. No se declara escaneo de cero hallazgos. Cada una se contrasta como clave pública exacta de modelo en catálogo generado; [disposición](SCAN-DISPOSICION.json), [selección](SCAN-SELECCION.json), [resumen](SCAN-RESUMEN.json) y revisión independiente en `review-scan/`. No hay supresiones ni modificación del archivo administrativoF01, y no se afirma higiene global de otros archivos/historial.

QA-171 añadido como **planned**, los170 casos anteriores y los resultados personales preservados; guía regenerada. Roadmap/configuración, CONTINUIDAD y CHANGELOG actualizados, sin crear resultados/pesos por modelo. Las verificaciones finales y hashes de fuentes están en `VERIFICACIONES-FINALES.json` y `HASHES-FINALES.json`. Las evidencias históricas selladas y los ZIP anteriores se conservan.

## Pendiente y métrica

Revisión visual de Wascar, transporte en candidata Windows completa45 y ensayo de actualización/Restore antes de modificar D. No copiar DLL/SQL/JS sueltos. No se reabren ni acreditan los506 anteriores, las302 acciones offline o el paso9 por ampliar catálogo.

Índice de cierre congelado: **2479/168 = 14,755952… → 14,76/100**. Cero crédito adicional, sin nuevo porcentaje global ni adopción. Sin commits, push o publicación.
