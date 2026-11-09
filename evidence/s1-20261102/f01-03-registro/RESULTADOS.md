# Paso 3 · F-01.03: registro contextual terminado

02.11.2026, anfitrión Windows, Python 3.12 y Gitleaks 8.30.1 ya fijado. Wascar pidió continuar F-01.03 reutilizando evidencia y conservando D. **No se operaron D, ninguna VM, servicios, bases, datos, contraseñas o factores MFA.**

## Entrega

- [Criterio reutilizable](../../../docs/CRITERIO-FALSOS-POSITIVOS-SECRETOS.md): tres criterios específicos, condición de revisión de contexto nuevo y límites de divulgación.
- Registro privado propio de ocurrencias, señalado por `.local/security/f01-03-current.json`: 92 históricos más 90 metadatos working corroborados, sin valores detectados. No son 182 secretos distintos.
- [Resumen saneado](REGISTRO-SANEADO.json): criterios, recuentos y huellas, sin rutas/commits de hallazgos o valores.
- [Revisión independiente favorable](REVISION-INDEPENDIENTE.md).

| Criterio | Prueba reutilizada de F-01.01 | Históricos | Working relacionado |
|---|---|---:|---:|
| FP-01 · Digest | Bytes de 16 fuentes versionadas y uso de integridad | 80 | 80 |
| FP-02 · Identificador | Vínculo al nombre de carpeta/diario y uso no autenticador | 3 | 3 |
| FP-03 · Narración | Tres frases técnicas y sus copias de parche en sus versiones | 9 | 7 |

Cada entrada vincula caso, regla, ruta, commits, líneas/columnas disponibles, blob y contexto de campo, con criterio y referencia de prueba/revisión. La huella se calcula sólo sobre metadatos, nunca sobre el valor sospechoso. El rol working está rotulado como corroboración; no representa un snapshot original recuperado.

## Lo que permanece activo

El registro **no es una allowlist**, no se importa desde el escáner y no modifica su resultado. No se añaden supresiones por directorio, archivo, regla, HEX/UUID, comentarios, baseline o ignorados. `.gitleaks.toml`, hook, escáner, lock y referencias Git conservan sus huellas.

Un contexto diferente no hereda la decisión. El registro antiguo sigue describiendo su ocurrencia histórica; una fuente nueva requiere otro contraste. Las observaciones desconocidas de F-01.02 no se registran como falsos positivos. No se reescribe historial, se hace force-push, se elimina evidencia o se rota una credencial.

## Investigación y verificación

[Investigación previa](INVESTIGACION-PREVIA.md): reutilización de Gitleaks y fuentes oficiales ya contrastadas, sin librerías o instalaciones nuevas. No se repitieron barridos globales, clasificación de blobs, análisis de chats o pruebas del producto.

```powershell
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-03-registro/crear-registro.py
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-03-registro/verificar-registro.py
```

[Verificación del coordinador](VERIFICACION.json), PASS:

- Los 182 registros coinciden con la clasificación pinada y sus vínculos son únicos. Alterar cada uno de los 11 campos de identidad o quitar un campo invalida el vínculo. No se modifica ningún archivo fuente para estos negativos.
- **Un focal existente** `test_staged_content_blocks_even_when_working_copy_clean`, con Gitleaks real en un repositorio sintético temporal: clave falsa staged con comentario `gitleaks:allow` → salida 10; working limpio → salida 0. El registro documental no rebaja el escáner. No es un barrido del proyecto.
- La ruta absoluta del fixture se verifica dentro de `.local/security-test-fixtures` antes de la limpieza; el Git sintético pertenece sólo a ese fixture. No hubo commits, staging o configuración de hooks del proyecto principal.
- Cuatro archivos del escáner y referencias Git antes/después iguales; catálogo QA de Wascar con la misma huella. No se importan resultados personales o casos QA nuevos.

El revisor contrastó cobertura, huellas y 2.002 cambios de contexto en memoria; reutilizó la revisión anterior de prueba/procedencia. No repitió el focal Gitleaks, leyó su resultado. Ejecuciones separadas y límites en el dictamen.

## Cierre y continuidad

Se acredita sólo **F-01.03 = 5/8 = 0,625 puntos**: índice del cierre **218/21 → 1849/168**, redondeado **10,38 → 11,01/100**. Alcance, pesos, base y denominador conservados. La acreditación y comprobación del delta quedan en `ACREDITACION.json`; ledger anterior/configuraciones/plan previo en `sources/`.

F-01.01 y F-01.03 quedan done. **F-01.02 sigue in_progress**, con la respuesta de Wascar «No lo sé» y atribución pendiente; **F-01.04 sigue pending**. No se declara F-01 completo ni higiene global. Los 268 números se conservan; 25 checkpoints acreditados y 255 sin cierre. No es porcentaje global nuevo del producto ni aceptación de Wascar.

Se actualizan la ficha del paso, continuidad, CHANGELOG, progreso y salidas del plan. Los generadores se comprueban con `--check`. Sin cambios en aplicación, paquetes, D/VM/SCM/DB/MFA, reglas, dependencias o QA manual, ni commits/push/publicación del proyecto.

[Verificación del cierre](VERIFICACION-CIERRE.json) comprueba el delta único y el HTML/JSON actual: paso 3 cerrado, 2 en progreso, 4 pendiente, números estables y dos botones ya acreditados desactivados. Es contraste estructural del documento, sin ejecutar navegador, escáner o producto otra vez. El revisor confirmó también el crédito/delta de estado.
