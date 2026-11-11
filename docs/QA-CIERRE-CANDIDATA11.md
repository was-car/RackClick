# QA y cierre · candidata11/esquema43

02.11.2026. [Abrir hoja interactiva](../QA-CIERRE-CANDIDATA11.html). Selección de14casos del catálogo existente: no añade resultados ni pesos al ledger.

ZIP: RackClick-Windows-Completo-11.zip, SHA256 f090b56e13bc3d4670834746cff33a2d01831eae517dbb0343ce760241c567b0. New11 en D ya tiene servicio automático, HTTPS, backup programado y reinicio Windows comprobados como postboot_verified. [Estado y pasos de D](VM11-D-PASOS-QA.md). **Punto6 en curso: no hay aceptación final.**

## Qué hacer

1. Para este ensayo usa D, instalada y reiniciada por Wascar. No vuelvas a instalar ni reviertas el snapshot para hacer QA. Wascar conserva el control del encendido, apagado y snapshots.
2. Abre en D https://192.168.206.133:5443 y el acceso RackClick-VERIFICAR-11-6ca767fa.cmd del Escritorio. Acceso privado muestra las credenciales locales. Conserva el MFA de Wascar. Para instalar tú otra VM limpia sigue [el manual11](INSTALADOR11-WINDOWS43.md), apartados00–03; marca explícitamente la casilla de confianza de CA. No copies DLL/SQL a tu servidor10.
3. D ya tiene50clientes cargados y verificados. No relances el cargador allí. [Corrección02 y límites](CARGADOR-DEMO50-02.md). Para otra instalación43 vacía, usa el ZIP corregido con su SHA externo y sus instrucciones.
4. Abre la hojaHTML y completa por orden. Para permisos/recuperación necesitas cuentas preparadas: si faltan, marcaBloqueado. No arriesgues el último administrador.
5. AnotaPass/NotPass/Bloqueado yobservaciones; pulsaGuardar mis resultadosJSON antes de cerrar. Esta hoja rechaza otras candidatas y conserva casos no incluidos en tu importación. Si cambia un guion conserva notas, pero pide repetirlo.
6. Desde el panel oficial conserva Verificar instalación y el informe sanitizado del Escritorio/RECOPILAR-INFORME.cmd. Devuelve eseZIP ytuJSONmanual; no adjuntes acceso privado,dumps,claves ocódigos. No hace falta otro colector.

| Caso | Prueba | Resultado inicial |
|---|---|---|
| QA-166 | Instalar en VM limpia, acceso privado, HTTPS y reinicio | Sin probar |
| QA-167 | Cargar Demo50 por API en una instalación43 vacía | Sin probar |
| QA-165 | 50 clientes, siete escenarios, perfiles y conexiones | Sin probar |
| QA-133 | Racks primero e información secundaria desplegable | Sin probar |
| QA-136 | Bandeja con firewall, switch y patch panel con ambas caras | Sin probar |
| QA-139 | Aruba Instant On1930 JL682A: cobre, SFP y alimentación | Sin probar |
| QA-141 | Synology RS1221+: dos U, ocho bandejas y conectores traseros | Sin probar |
| QA-142 | DiskStation DS423+: cuatro bahías de sobremesa, soporte alto y dos LAN | Sin probar |
| QA-162 | 62 modelos: armarios, montajes especiales y medios tipados | Sin probar |
| QA-09 | Técnicos y lector con ámbito limitado | Sin probar |
| QA-130 | Exención sólo para el administrador global del Systemhaus | Sin probar |
| QA-163 | Generar códigos privados y recuperar mediante un autenticador nuevo | Sin probar |
| QA-164 | Descargar JSON confirmado del inventario actual de un cliente | Sin probar |
| QA-05 | Cambiar idioma y cerrar sesión | Sin probar |

Los casos condicionales mantienen identidad/texto del catálogo. No se crean cuentasTécnicoA/B/Lector ni se activan casos globales por generar esta hoja. URL,confirmación yresultados son declaración del operador, no medición autenticada.

## Qué impide el cierre global

- QA manual del catálogo, los50clientes y permisos de roles en D; las comprobaciones técnicas no rellenan resultados personales.
- Resultados manuales de Wascar en esta edición; no trasladar PASS anteriores.
- Recuperación con factores MFA: sobre portable/emergencia/rotación no integrados.
- Pendientes del punto3: importación/backup desde dashboard y aceptación administrativa.
- Redistribución de binarios y adopción final de Wascar.


La edición10 conserva sus resultados. Releerhashes/sellos verifica integridad hoy; no vuelve a ejecutar ensayos. Las68pruebas/40focos/50clientes previos no se cuentan otra vez. Catálogo506/506=100% de selección; índice acreditado9,76/100, sin porcentaje global nuevo.

## Reproducir y valorar una copia

    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --write
    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --check
    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --audit
    C:/Python312/python.exe -X utf8 -B tools/qa_candidate11.py --assess 'RUTA/Resultados-QA-RackClick-11-fecha.json'

No cambia producto,DB,VM,servicios,ledger,ZIP ni respuestas personales. --assess mantiene adoption=false incluso con todos losPass y no habilita producción.
