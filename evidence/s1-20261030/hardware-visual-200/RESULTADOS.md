# Ampliación de cartera visual a 220 modelos

30.10.2026 · Edición 03 · Encargo Wascar: al menos 200 productos diferentes.

## Resultado

220 claves normalizadas fabricante/modelo,220 conjuntos completos de imágenes diferentes, ningún modelo vacío ni genérico contado como producto. Se conservan35 previos, se añaden20 fotografías oficiales individuales dePaloAlto y165 productos comunitarios elegidos por cuotas.396 contenidos de imagen distintos porSHA256,405 asociaciones/archivos,8 PDF originales y13 siluetas genéricas.28 denominaciones de fabricante de origen; alias no equivalen a empresas distintas.

Cartera:60firewalls/seguridad,76switches,17routers,18NAS,24servidores,9UPS,5paneles,3almacenamientos,2AP,2PDU,2pasivos,1rack y1bandeja. Selección amplia de documentación, no recomendación de compra ni censo reciente del mercado. Revisión/fechas/hardware desconocidos no se deducen del nombre.

## Investigación y reparto

Se reutilizaron la hoja maestra, el alcance de fabricantes, la colección02 y el catálogoNetBox fijado. Investigación previa y fuentes en INVESTIGACION-PREVIA.md. Dos tareas separadas: fotografías oficiales y selección de165 productos; coordinador extrae la selección, preserva base35 y genera visor/paquete. Revisor release distinto de los autores. Sin nuevos paquetes/dependencias instalados.

- Ampliación oficial:20PNG originales/15.566.991bytes, todos distintos de los anteriores. Se rechazaron PA820/5220/5250/5280porque el fabricante enlaza a imágenes de otros modelos. Recursos individuales y variantes señaladas.
- Selección comunitaria:165modelos explícitos/293asociaciones/285SHA en el lote,128confrontalytraseradeclarados.24fabricantes/25grupos, máximo26productos por fabricante. Tres conjuntos de imágenes idénticos sustituidos; prefijoSKU7Z7Xambiguo no se trata como igualdad de productos y se reemplaza SR650V2 porSR645.
- ArchivoNetBox1GB: SHA completo recomputado, CRC/hash/formato/dimensiones de los miembros seleccionados. No se volvió a descargar ni se ejecutó contenido del repositorio. Las293imágenes extraídas siguen community_unverified; no son165fichas verificadas por fabricante.
- Los100activos de base35 y los10SVGanteriores conservan bytes; las ediciones01/02y sus registros se preservan. La primera extracción de selección anterior al cambioLenovo se conserva fuera de la whitelistfinal.

## Verificación ejecutada

Python3.12/Node24.21.0/Edge nativo enWindows. No se ejecutaron suites.NET/PostgreSQL/servicios porque no hay cambio de aplicación, SQL o instaladores.

1. Generador03valida mínimo200,identidades únicas, conjuntos completos no vacíos/distintos, rutas/firmas/hashes y whitelist antes de empaquetar. El modo preview no generaZIP; la salida congelada existente se rechaza sin sobrescribirla.
2. Se conserva02, se prepara preview03 y se congela03. ZIP147.241.660bytes,430entradas, lista exacta de activos/metadatos. Los165 productos se extrajeron tras validar el hash de selección final e5c840373a4f1f4f853b7ec6c4f07fb0842225304c5cc8d8dfd13a578dfed547.
3. **Navegador03: 10 focos PASS.** Tres visores: raíz, carpeta portátil yZIPextraído. Cadauno recorre10páginas/220modelos y decodifica405 asociaciones de imágenes. Páginas de24modelos, máximo70imágenes activas deproductos;0src en tarjetas ocultas.13genéricos cargan. Búsqueda exacta1resultado, filtroSophos8, zoom, filtrodefaltantes,390px sin desbordamiento,0errores y0solicitudesHTTPexternas. Ver NAVEGADOR-03.json. Capturas/perfiles privados, no copiados a evidencia pública.
4. La selección y el recolector verifican metadatos/formatos; no se ha revisado visualmente cada una de las165nuevasfichas. El revisor independiente aporta su muestra y pruebas en REVISION-03.md; la revisión no se sustituye por estas pruebas del coordinador.
5. Hubo un error del auxiliar documental: se reutilizó una copia superficial del diccionario después de quitar la clavepath para el índice público. La generación de lista/CSV falló con KeyError. Se releyó el manifiesto original y se completó la documentación; paquete y producto no cambiaron. No se presenta como fase roja de producto. Detalle en TRAZABILIDAD.json.

Comandos principales:

```powershell
C:/Python312/python.exe -X utf8 -B .local/hardware-visual-200-df324c4b156b49d6918f6a18075c7bbd/extract_selection.py
C:/Python312/python.exe -X utf8 -B .local/hardware-visual-200-df324c4b156b49d6918f6a18075c7bbd/build_library.py --edition 03 --preview-only
C:/Python312/python.exe -X utf8 -B .local/hardware-visual-200-df324c4b156b49d6918f6a18075c7bbd/build_library.py --edition 03
C:/RackClick_SVR/.local/node-v24.21.0-win-x64/node.exe .local/hardware-visual-200-df324c4b156b49d6918f6a18075c7bbd/verify_gallery.mjs
```

## Pins

| Pieza | SHA256 |
|---|---|
| ZIP03 |f8e5f4ea2c36c1d9c1417024ed063b38684f920f82d4edc1eb66c357c45d71f3|
| REFERENCIAS.json |7ffe1075d06c6c5f0b0c48a3983a7d923e260ab871618e784a2db7ff66528568|
| SHA256SUMS.txt |975a50c3f9c5d80b6791f45740ecbbad6bec3fc47702cbc9e816be0d7f9fffde|

## Entrega y límites

Visor VER-CARCASAS-200.html, lista/CSV/índice en docs/CARCASAS-PRINCIPALES/,ZIPprivado en.local/hardware-visual-200-df324c4b156b49d6918f6a18075c7bbd/. El acceso habitual se actualizará tras revisión favorable; no se toca el servidor.

Los recursos de familia/comunidad están etiquetados y los derechos individuales de redistribución siguen pendientes. No se publica fotografía enGitHub. No hay220plantillas instaladas,220dibujos propios ni validación completa de puertos/montaje. Genérica por categoría si definición/cara no fiable; nunca deducir conectores, PoE, U o módulos de una imagen. El contrato y primer perfil StarTech de desarrollo18permanecen intactos.

Siguiente: integrar carcasa específica/genérica por revisión en aplicación, empezando por StarTech y conservando UUID/Click-Click; después validar modelos/variantes, licencias y candidata nativa/QA. La cartera es referencia para ese trabajo.

Se respeta conservar todo:0borrados. Sin aplicación/DB/VM/QA/MFA/instaladores/commits/push. Índice de cierre restante 9,76/100 sin incremento por contar imágenes/productos; no porcentaje global nuevo.


## Dictamen recibido y cierre

Revisor distinto: favorable para consulta privada, sin bloqueantes.9focos propiosPASS:4pins,430ZIPexacto/CRC,220identidades/conjuntos,100activosbase35+10SVGpreservados,165YAML/293imágenes contrastados conZIPNetBoxoriginal y enlaces del visor.10referencias visuales nuevas de distintas marcas/tipos. No repitió las pruebasEdge del coordinador ni valida220especificaciones/licencias. Su primera expectativa de JSONliteral falló por relocalización baseline35/nota deprocedencia esperada; corrigió fixture, no candidata. Ver REVISION-03.md. Capturas originales permanecen privadas.

El acceso habitual VER-CARCASAS-PRINCIPALES.html se actualiza a03tras dictamen; la versión de35se conserva comoVER-CARCASAS-PRINCIPALES-35.html y enZIP02. Se mantienen0borrados y9,76/100sin nuevo crédito.
