# Tanda12 · restauración RC9 para QA · 04.10.2026

Resultado: backup recibido cargado en una base PostgreSQL17 NUEVA, independiente de QA original. Disponible http://127.0.0.1:52346 con INICIAR-QA-RESTAURADO.cmd, guía GUIA-QA-RESTAURADO.html y credenciales propias privadas. Original58822 conserva su snapshot y comandos; no se le ejecutó stop/start ni escrituras en esta tanda. Progreso estimado ~45 %, mismos pesos; no candidata completa ni adopción.

## Cambios y razones

- tools/windows/rc9_restore.py + development/server/tests/test_rc9_restore.py: importación jerárquica atómica por IDs UUID con mapeo privado, valida grupos/tipos/extremos y pertenencia, conserva atributos y propiedades; no usa gn como identidad. Procedencia/auditoría transaccionales; rechazo de destino ocupado. Original exacto archivado privadamente junto al mapeo. Systemhaus se restaura; metadata global no soportada se conserva en el original, sin prometer funciones visibles inexistentes.
- Qa-Local.py/Qa-Accounts.py: perfiles manual y rc9, nueva base y secretos; congela DLL/dist probados; técnicos/lector apuntan a uno de los clientes existentes del backup, sin crear un cliente11. Permisos servidor verificados durante provisión. Repetir --if-needed usa marca coherente sin revalidar permisos vivos.
- Tres CMD nuevos para iniciar/detener/abrir guía restaurada; Python fijado al ejecutable instalado. No dependencia nueva ni cambios .NET/API/frontend en este lote.
- qa_guide.py/catalogo12/HTMLs/test_qa_guide.py: QA11 habilitado solo en copia restaurada, pasos precisos, notas separadas por entorno; export incluye profile e import rechaza otro entorno. Exportaciones antiguas sin profile solo admitidas en manual. Guía se regenera con CMD y catálogo se mantiene por cambio.
- Verify-Restored-QA.py: lectura por API y stop/start SOLO rc9 antes de entregar. No mutaciones de inventario; login sí crea sesiones. No usar durante QA de Wascar porque interrumpe temporalmente esta copia.

## Ejecuciones nuevas Windows

Entorno Windows11 build26300, .NET10.0.401, PostgreSQL17.11, Node24.21.0, Python3.12. DLL9e33077e1a963489d71f7ce934610a0e2d93c9bad8a85ad203dcad7f53a9c9e2; bundlec457e5860274dcf87ec68dbdb1f7fef60b2589adaba20a00f2410157dc05487c. No convertir evidencia histórica en ejecución nueva.

1. Importador:3/3 PostgreSQL + negativo ampliado1/1. Revisar importador/CIERRE.md y postgres-final/result.json. Equivalencia plan→columnas persistidas por ID, campos de puertos/cables API, dos sesiones/escritura, fallo de auditoría rollback, reintento y destino ocupado. Negativos rechazan fuente inválida sin escribir.
2. Revisor independiente distinto:3/3 contra su fixture,17.429s; REVISION.md, hashes y límites allí. P2 guía incorrecta encontrado y corregido. CMD/exportprofile corregidos y reinspeccionados estáticamente. No ejecutó lanzador persistente.
3. C:\Python312\python.exe -B tools/windows/Qa-Local.py start --profile rc9; Qa-Accounts.py --profile rc9 --if-needed: correcta provisión real de cuatro cuentas, ámbito técnico/lector verificado por servidor; contraseñas solo privadas.
4. C:\Python312\python.exe -B tools/windows/Verify-Restored-QA.py --before-handoff --evidence evidence/s1-20261004/rc9-restauracion-12/lanzador: PASS. Lectura10proyectos:10clientes/15sitios/25edificios/68salas/68racks/311equipos/633grupos/5408puertos/623conexiones; mismo recuento tras restart. Puntero y booleano health original conservados; no es comparación íntegra de los datos originales ni identidad de todos los atributos después del restart.
5. python -B -m unittest discover -s tools/tests -p test_qa_guide.py:3/3. Edge nativo tools/tests/browser-qa-guide.mjs:6checks (guardado/recarga/export/import/retirados/inválidos/version/file), guia-edge/result.json. No es QA visual de inventario restaurado ni prueba dinámica crossprofile; aislamiento adicional comprobado por unidad e inspección.

Fallos previos de arnés conservados aquí: primer Verify-Restored-QA falló ModuleNotFoundError pg_support antes de tocar laboratorio; corregido sys.path. Nuevo unittest de contexto falló por fixture fuera de .local/labs y después host ausente; corregido fixture, no relajada validación. Intento token restringido PostgreSQL previo en importador es limitación Windows conocida; ejecución normal nueva indicada en su cierre.

## Límites y próximo bloque

Original SHA256cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0 conservado, fuera de Git. Fuente y mapeo/errores SQL privados .local. No hay ZIP/manifest nuevo ni paquete publicable.

QA visual de Wascar pendiente: comenzar QA11 en navegador/perfil separado; notas Pass/NotPass no adopción automática. Esta herramienta no implementa subir backup desde GUI, restore productivo/pgdump, usuarios anteriores, sesiones anteriores ni todo metadato global RC9. Notificaciones QA10 pendientes; administración/asignaciones/paridad RC9/instalador HTTPS/backup productivo/manual/recuperación/QA final pendientes. Siguiente tanda pequeña: contrato/API de asignaciones de grupos; mantener ambas copias QA congeladas, no reemplazarlas silenciosamente.
