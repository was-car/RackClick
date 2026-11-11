# Instalador 08 · candidata interna de ensayo

25.10.2026. **Construida, inspeccionada y reproducida; no instalada ni adoptada.** [Detalle/pins](../../../docs/CANDIDATA-INSTALADOR08-25-10-2026.md), [perfil](../../../docs/INSTALADOR08-PERFIL.json), [coordinación](../../../docs/MENSAJE-PARA-CLAUDE-INSTALADOR08-25-10-2026.md).

Entrega `.local/instalador-08-codex/entrega/`: envoltorio, payload, bundle y auxiliar de cambio de IP, con inventario de fuentes y manifiesto de hashes. El envoltorio es autosuficiente para el recorrido del instalador; los componentes sueltos no requieren instalaciones adicionales por Wascar.

La receta toma S4/S5 y ZIP 07 fijados, extrae la aplicación/operadores/manuales congelados y superpone siete fuentes PowerShell revisadas. El colector oficial vuelve a construir el bundle, con las mismas dependencias/licencias/45 entradas de aplicación. Cambia un operador de los 25 y la metadata del bundle. Las otras actualizaciones y pins se aplican a la copia aislada; 38 archivos de servicio idénticos. No se copia fuente C#/MFA/C2, ni se compila.

## Evidencia

- [FUENTES-08.json](FUENTES-08.json): origen y hashes de 77 fuentes empaquetadoras, overlays y sustituciones de pins.
- [BUILD-08.json](BUILD-08.json): recibo de la primera construcción. Su `bundleRepeated=false` describe aquel momento; aún sólo se habían repetido los tres ZIP externos dentro de esa raíz.
- [REPRODUCIBILIDAD.json](REPRODUCIBILIDAD.json): observación posterior de **dos construcciones completas en raíces independientes**, con los cuatro ZIP idénticos, incluido el bundle. No se reescribe el recibo anterior.
- [CONSTRUIR-08.py](CONSTRUIR-08.py): receta final, con destino nuevo restringido a `.local`, sin borrados, descargas o instalaciones. Tiene entradas locales previas explícitas; no promete aprovisionar un clon vacío.
- [LECTOR-NATIVO.json](LECTOR-NATIVO.json): Windows PowerShell 5.1, `bundle_verified`, salida 0, 1.986 archivos y manifiesto de aplicación e9c58c0c…d74d.
- [HASH-INCORRECTO.json](HASH-INCORRECTO.json): mismo lector sobre bundle 08 con hash 07, rechazo `archive_hash_mismatch`, salida 2. No se extrae ni instala el archivo.
- Autor: `python -B -m unittest tools.tests.test_installer08_candidate -v`, **10 pruebas OK**, 4,328 s, sin omisiones. Primera batería de contenido fue 9 OK; después se añadieron la guarda de rutas y la reproducción completa en segunda raíz.
- [REVISION.md](REVISION.md): inspección independiente de los cuatro ZIP, manifiestos/pins, 45 archivos de aplicación, 38 del servicio, 25 operadores y los siete overlays. Focos propios de rutas y contrato; no repite las pruebas del autor ni ejecuta instalación.
- Escaneo de las fuentes/documentos/recibos nuevos: dos avisos de API key en el inventario de fuentes. Ambos se contrastaron con el SHA256 real del archivo correspondiente y son hashes de archivos, no credenciales. Se conserva el resultado original y la clasificación; no se declara un escaneo global del repositorio ni de binarios.

## Hallazgo de la revisión y corrección

Al añadir `--output-root`, la receta usaba una comprobación léxica que aceptaba `..` hacia fuera del espacio previsto. El revisor lo reprodujo llamando sólo al validador de rutas, sin crear carpetas. Se conservó la versión anterior y se corrigió: rechazo de `..`, comprobación de ancestros sin resolver reparses y comprobación final de la ruta resuelta. Su foco pasó después y la batería del autor lo cubre. Ambas construcciones usaron destinos normales dentro de `.local`; no se produjo escritura exterior ni cambiaron los ZIP por esta corrección. La segunda había empezado antes de corregir la guarda; su ruta era legítima y sus fuentes de empaquetado son las mismas.

## Límites y siguiente paso

No hubo Execute/VerifyOnly, instalación, SQL, servicio, tareas programadas, HTTPS, reinicio ni operación de VM. Windows/VMware quedan a cargo de Wascar. No se cambió el helper W02 de Claude. Falta cerrar REC-02, revisar el ajuste explícito de pins/procedimiento al perfil 08 y ejecutar el ensayo limpio en C.

Etiquetas históricas «05» y reparación de red mantienen sus límites conocidos; cambio de IP sólo inspeccionado, no aplicado. D2/MFA, derechos de redistribución, problemas de la auditoría y unificación de C2 siguen en sus bloques; una nueva edición no los da por cerrados. QA-119/120 continúan planned. ZIP 07 y fuentes originales conservados, sin commits o publicación.

**Delta 0:** cierre del inventario restante 4,79/100; 11/280 subpasos, 1/50 resultados; W-02 0,50/2,50. W-01 ya estaba acreditado y E-01 aún exige la candidata final coordinada; no se puntúa otra vez por reconstruir un paquete.
