# Matriz F-09.02 · paso30

Sólo este checkpoint; no sustituye el ensayo operativo F-09.04 ni su cierre F-09.05.

| Criterio | Evidencia del lote | Límite |
|---|---|---|
| Preparación expresa de material nuevo | Prepare → Export → Apply → Publish, versión superior al censo, round-trip DPAPI y sobre autenticado | Componentes internos; CLI aún bloqueada |
| Censo y conservación | Anillo/archivos, factores active/pending/disabled, historial y backups; conserva claves legibles y blobs opacos/archivo vacío | Anillo/censo fiable obligatorio; no reconstruye metadata perdida |
| Dependencias de backup | Dump custom PG17 real con factor90; ausencia de clave no declarada bloquea; pérdida90 expresa queda identificada y nueva versión91 | Custodia externa física no probada; sobre nuevo no recupera claves perdidas del backup |
| Retirada segura de factores | Archivo completo cifrado en schema privado, salida de tabla viva y pending/required/revisión en una transacción | No se afirma borrado criptográfico ni eliminación del archivo original |
| Conservación DB | Cuentas/grupos/política/gracia e inventario sintético cliente/rack/equipo; factor legible restante abre; cuenta inactiva continúa inactiva | No es la Demo50 ni todos los recorridos GUI |
| Reenrolamiento obligado | Autenticación de almacén para global y ordinario devuelve enroll sin sesión tras publicar | Fence permanece; no es login HTTP de servidor recuperado |
| Fallos y reentrada | Fallo de SQL hace rollback; cambios de usuario/política/códigos rechazan; commit/publicación interrumpidos lógicamente reentran sin repetir revisión | No Kill, reinicio, corte de alimentación o token de servicio real |
| Vinculación | Negativos reproducidos de SID/versiones/sobre; pin privado inmutable del sobre, binding completo y hashes/identidades del candidato y originales | Amenaza de operador Windows confiable no se convierte en autenticación criptográfica externa |
| Privilegios | Runtime PG no puede leer archivo ni modificar witness aun con DML amplio sobre public; entrada nativa estándar rechazada antes de SCM/SQL | Positivo elevado/SYSTEM y SID real pendientes |
| Fronteras | CLI anterior sin efectos, HTTP sin ruta de emergencia, API restringida, mantenimiento/rotación compatibles con47 | Sin instalación/arranque de47 en D/E |

Consultar `FOCOS.json`, `FUENTES.json`, `CAMBIOS.patch` y `review/DICTAMEN.md` para nombres, pins, ejecución propia del revisor y resultados reales. No contar repeticiones, variantes o pruebas como nuevos puntos.
