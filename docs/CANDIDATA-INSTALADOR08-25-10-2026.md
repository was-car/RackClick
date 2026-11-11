# Instalador 08 · candidata interna reproducida

25.10.2026. **Artefacto y auxiliar W02 con pins 08 revisados. Pendiente de medición/Check/Plan y ensayo limpio en C. No instalar en QA ni en producción.**

Entrega local: `.local/instalador-08-codex/entrega/`. El archivo para iniciar el recorrido completo es `RackClick-Servidor-08.zip`; contiene el payload, que contiene a su vez aplicación, runtime .NET, PostgreSQL privado, prerrequisito Visual C++, operadores y licencias. No necesita una instalación 07 previa. Los otros ZIP son componentes/auxiliares, no pasos adicionales que Wascar deba instalar uno por uno.

## Identidades exactas

| Archivo | SHA256 |
|---|---|
| `RackClick-Servidor-08.zip` | `2855898161ed94ff36fba73b11ac2bb02e9b4d9702e4af6976e946a7307561ae` |
| `RackClick-Servidor-08-payload.zip` | `f1988ba75ef8f278b5d64b81d7a8fb02d99a3be451e8ce70e2f97a4452538da4` |
| `RackClick-Bundle-M3-14-08.zip` | `a26856cb2bf3b9ed76384ebfe40fcc1587075708d3383e6b515246bfebb6da6f` |
| `RackClick-Cambiar-IP-08.zip` | `c070fa06cf40808e0d43197da743bed52c00361ce05f45549ff6498b3a36c6c8` |

`payload.json`: `0d9df32b11a1c39df66cbb444739628eb8f867b06f55d2b3b3e45681ee29baa6`. `PAQUETE.json`: `1f362949398b3da539a171b1150270599fa1761a0c7e1a7649aff31bc68972ac`. [Perfil de la candidata](INSTALADOR08-PERFIL.json).

Se mantienen esquema 14, runtime .NET 10.0.12, PostgreSQL 17.11 y Visual C++ 14.51.36247.0, mínimo 14.44.35211.0. El SDK 10.0.401 sólo se usa como archivo fijado del que el colector extrae el runtime; no se recompiló ni cambió la versión de ninguna dependencia.

## Qué cambia

- Mensaje concreto de nombre de administrador ya existente al restaurar, con los rechazos/tipos revisados.
- Estado postboot registrado separado del resultado histórico. El panel no recupera un 100 antiguo y el informe conserva UUID/fechas/hashes de procedencia.
- Cadena de pins nueva para bundle, payload, envoltorio y auxiliar de red, en copias de fuentes aisladas.

La aplicación procede del bundle 07 congelado y mantiene manifiesto `e9c58c0c…d74d`. Sus 45 entradas de aplicación, incluida la metadata, son idénticas; también los 38 archivos del host de servicio. No se copió `development/server/src`, ni se compiló C#/MFA o frontend, ni se incorporó C2 del árbol compartido. Los siete overlays están fijados por los hashes de sus revisiones anteriores. El bundle sólo cambia `New-RackClickRecoveredInstance.ps1` y `bundle.json` respecto al 07.

## Comprobaciones realizadas

- **Cuatro ZIP idénticos byte a byte desde dos raíces de construcción independientes**, incluido el bundle completo. Los informes de construcción pueden diferir en rutas absolutas; no se exige identidad de esos recibos.
- **10 pruebas de contenido correctas**, sin omisiones: inventarios, hashes, fuentes revisadas, aplicación/servicio congelados, pins, red y reproducción completa.
- Lector nativo Windows: `bundle_verified`, salida 0, **1.986 archivos**. El hash antiguo contra el bundle nuevo se rechaza como `archive_hash_mismatch`, salida 2.
- Revisión independiente de archivos/pins y focos inertes. Detectó un escape de ruta en la opción nueva de la receta; se corrigió antes de publicarla y el foco volvió a pasar. Las construcciones ya realizadas usaron rutas legítimas dentro de `.local`; los ZIP no cambiaron por esta guarda.

[Evidencia y revisión](../evidence/s1-20261025/instalador08-codex/CIERRE.md).

## Reproducir la construcción

En el entorno Windows de desarrollo que conserva las entradas fijadas:

```powershell
C:\Python312\python.exe -B evidence\s1-20261025\instalador08-codex\CONSTRUIR-08.py --output-root .local\instalador-08-repeticion-nueva
```

El destino debe ser nuevo y quedar dentro de `.local`. La receta exige los ZIP 07 y snapshots S4/S5 identificados, los archivos oficiales de dependencias y los siete overlays revisados. No es un aprovisionador de un clon vacío. Esos artefactos previos son entradas de construcción, no dependencias del instalador en el servidor destino. No elimina salidas fallidas ni sobrescribe construcciones anteriores.

## Pendiente antes del ensayo

REC-02 y el cambio del auxiliar a pins 08 están revisados favorablemente: fuente final `f63ad4b4…ab29a6`. [Dictamen y precisiones para C](REVISION-W02-PINS08-CODEX.md). Falta medir el destino, comprobar los bytes tras copiar y pasar Check/Plan antes del Restore coordinado. No mezclar los pins 07 con este ZIP. C manual fue comprobada en el bloque anterior; la IP se vuelve a medir antes del ensayo. Wascar hace instalación del OS, snapshots, encendido y apagado.

Se conservan las etiquetas históricas «05» del verificador de Escritorio y algún mensaje; el procedimiento del ensayo debe identificar el acceso real, no deducir su nombre de «08». La reparación de red histórica, la custodia MFA/D2, redistribución y las candidatas de la auditoría externa siguen con sus límites anteriores. El auxiliar de cambio de IP se verificó por contenido, no aplicándolo a una instalación.

No se ejecutaron instalación, Restore, servicio, HTTPS o reinicio en Windows Server. QA-119/120 siguen planned y los resultados personales permanecen intactos. **Delta 0: cierre restante 4,79/100**, W-02 0,50/2,50; no se acredita de nuevo el empaquetado ya cubierto ni se completa el ensayo por producir ZIP.
