# Registro de falsos positivos de secretos

02.11.2026 · F-01.03. Registro documental, **no lista de exclusión del escáner**.

## Criterios específicos

| Criterio | Qué permite registrar la decisión | Qué no basta |
|---|---|---|
| FP-01 · Digest de un archivo | Igualdad SHA256 con los bytes de la fuente versionada referenciada y uso comprobado como control de integridad. | Tener 64 caracteres HEX, llamarse hash o aparecer en un manifiesto. |
| FP-02 · Identificador sin función de autenticación | Vínculo con el nombre de carpeta/diario y comprobación del uso del símbolo en el contexto revisado. | Tener forma UUID, ser aleatorio o llamarse token. |
| FP-03 · Narración técnica | Frase y copia de parche contrastadas en su blob/versionado exactos; no asignan material autenticador. | Ser Markdown, estar bajo tests/evidence o contener palabras que parezcan técnicas. |

El registro reutiliza los casos revisados de F-01.01: **92 históricos (80/3/9)** y **90 metadatos working relacionados (80/3/7)**. Son ocurrencias solapadas, no 182 secretos distintos. No se amplía a las demás categorías del barrido o a otros archivos.

## Vínculo de cada decisión

Cada registro privado conserva ID de caso, regla, ruta, commit de detección y versión fuente, líneas/columnas disponibles, contexto de campo, SHA256 del blob, criterio, referencia de prueba y revisión. Su huella de contexto se calcula sólo sobre esos metadatos; **no sobre el valor sospechoso**. Las corroboraciones working están rotuladas como tales, sin afirmar que se reconstruyó el snapshot original.

Una decisión vale para esa ocurrencia. Una regla, ruta, línea, campo, commit o blob diferente requiere contraste nuevo. Que se conserve la forma HEX/UUID o el nombre de archivo no transfiere el dictamen. Si falta evidencia, permanece indeterminado. Los cambios de fuente no borran el dictamen histórico de su versión anterior.

Las observaciones no delimitadas de F-01.02 **no entran como falsos positivos**. Su ausencia de confirmación no demuestra que no hubiera material autenticador.

## Comportamiento del escáner

- No se modifica `.gitleaks.toml`, el hook, la versión fijada, el escáner ni su archivo de ignorados.
- No se añaden allowlists por directorio/archivo/regla, comentarios `gitleaks:allow`, baselines, exclusiones por entropía o supresiones globales.
- El escáner no importa este registro y sigue informando coincidencias. Una decisión documental no convierte una salida con hallazgos en un barrido limpio.
- No se reescribe el historial, se hace force-push ni se eliminan pruebas. Cualquier tratamiento histórico futuro requiere decisión expresa y coordinación; no está autorizado por registrar un falso positivo.
- No se rotan contraseñas, claves MFA o cuentas a partir de estos registros. El tratamiento de una credencial efectivamente afectada corresponde al paso 2, aún abierto.

## Conservación y actualización

Detalles únicamente en el registro privado propio señalado por `.local/security/f01-03-current.json`, excluido de Git. El resumen público ofrece recuentos, criterios y huellas de evidencia, sin valores ni rutas/commits de hallazgos. No hay API, comando de cambio de credenciales o integración productiva.

Para incorporar otro caso: fijar origen y contexto exacto, obtener prueba de uso/procedencia, mantener fuera cualquier valor, revisar por otra persona y versionar la decisión. No extender silenciosamente las 92/90 ocurrencias ni alterar los pesos del plan.

[Resultado y comprobaciones](../evidence/s1-20261102/f01-03-registro/RESULTADOS.md) · [Paso 1](PASO-001-CLASIFICACION-SECRETOS.md) · [Paso 2 pendiente](PASO-002-TRATAMIENTO-CREDENCIALES.md).
