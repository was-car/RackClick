# Paso 2 · F-01.02 en curso, sin crédito

02.11.2026. Encargo de Wascar: continuar el paso 2, conservar D y reutilizar la evidencia. Se preparó la disposición de los hallazgos ya clasificados y se contrastó el antecedente de la auditoría. **No se operó D ni ninguna VM, servicio, base, cuenta, contraseña o factor MFA.**

## Trabajo realizado

- Reutilizada la clasificación revisada de F-01.01, con huella exacta y sin volver a ejecutar Gitleaks o leer valores. 92 históricos y 90 metadatos working relacionados: se registra para cada ocurrencia por qué no procede rotarla; no se suman como secretos distintos.
- Registro propio privado de decisiones ligado por ID y huella a la clasificación previa. Sólo metadatos, sin contraseñas, tokens, valores detectados o comandos de cambio de credenciales.
- Observación `.local` de la auditoría 25.10 conservada como atribución pendiente. La mención de una clave administrativa de laboratorio en chat se consigna como no corroborada por una segunda fuente y sin vincularla a D; ambas observaciones podrían solaparse.
- Inspección limitada de estructura/metadatos del run-1 original: 26 unidades (11 covered, 6 candidate, 9 deferred), 275 ocurrencias de rutas declaradas y ninguna `.local` en ese campo. No hay archivos retenidos en los directorios artifacts/scratch de sus cinco agentes. **Estos datos no son una transcripción y no desmienten el incidente reconocido.** No se abrieron almacenes de credenciales o perfiles de navegador.
- Wascar respondió **«No lo sé»** sobre si aparecieron claves reales o sólo nombres/rutas. Se conserva la respuesta sin atribuir una filtración ni dar por descartada la exposición. No se pide ningún valor ni se interpreta como autorización para cambiar D.
- Tras esa respuesta se intentó localizar el registro: cabeceras de 42 sesiones Codex del 25.10; eventos de herramientas de ese día en el registro Claude del mismo proyecto; metadatos de los padres de las sesiones y eventos de herramientas de un padre disponible. No se encontró un evento correlacionado con el identificador/ruta del run-1 o sus hunters en esa búsqueda acotada. No se examinaron mensajes libres o valores autenticadores, ni se mostraron argumentos/resultados completos. **No es un barrido de todas las conversaciones ni prueba de que no existiera el acceso**; no se amplió a sesiones ajenas. Ver `BUSQUEDA-REGISTRO.json`.

[Disposición saneada](DISPOSICION-SANEADA.json) · [Metadatos de auditoría](AUDITORIA-METADATOS.json) · [Investigación previa y fuentes](INVESTIGACION-PREVIA.md) · [Revisión independiente](REVISION-INDEPENDIENTE.md).

## Decisión y trabajo restante

**No rotar los hallazgos de F-01.01:** los hashes verificados, identificadores y narraciones no son credenciales en esas ocurrencias. No corregir una exposición inexistente en esos casos ni probarlos como contraseñas contra ningún sistema.

**No cerrar F-01.02 por esa condición no activada:** falta delimitar el antecedente `.local`. Una lectura de Git no puede demostrar que otro proceso no mostrara contenido privado. No se cambia el criterio congelado para obtener puntos ni se convierte la incertidumbre en una vulnerabilidad demostrada.

Disposición mínima pendiente, sin valores:

1. Tipo de material que apareció, o evidencia de que sólo se mostraron rutas/nombres y no material autenticador.
2. Instancia/consumidor y alcance del canal/destinatarios, por referencias. No asumir que una clave vieja corresponde a D.
3. Si se identifica una credencial efectivamente afectada, prueba de revocación previa/retirada o tratamiento coordinado y comprobación posterior en el sistema correspondiente. No hay orden de rotación automática ni de reescritura del historial.

Si la aclaración permite resolverlo sin cambios operativos, se registrará así y se revisará antes de acreditar. Si requiere cambios en D, se coordinarán respetando la instrucción vigente de conservarla; no se ejecutan en esta tanda.

## Estado y métrica

F-01.02 pasa sólo a **en progreso**, con evidencia. No se acredita ni se asigna peso nuevo. F-01.01 permanece cerrado y F-01.03/.04 pendientes. **Índice del cierre: 10,38/100**, exacto 218/21, sin incremento. Alcance, pesos, base y los 268 números se conservan.

La hoja maestra mostraba un literal antiguo de 23 acreditados aunque el registro calculaba 24. Se cambió sólo la presentación para derivar los conteos de la métrica existente; no genera un nuevo cierre. Los generadores y el contraste del delta documentan el resultado en `ESTADO.json`.

## Comprobaciones y límites

El auxiliar de disposición sólo leyó el informe de metadatos propio fijado por SHA256 y escribió su nuevo registro privado y resumen público. La revisión independiente verificó cobertura, conteos, huellas, ausencia de valores y tratamiento de incertidumbre. No ejecutó pruebas de producto ni realizó operaciones en sistemas.

Tres pruebas existentes de referencias maestras: PASS. `verificar-estado.py` comprueba pesos/huella/índice iguales, único cambio a en progreso, 268 números conservados, cobertura del registro privado y QA de Wascar con la misma huella. No es una nueva prueba de navegador o del producto. El revisor confirmó también ese delta de estado y la salida focal del generador; no declaró terminado F-01.02.

```powershell
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-02-tratamiento/preparar-disposicion.py
C:/Python312/python.exe -X utf8 -B tools/progress_report.py --check
C:/Python312/python.exe -X utf8 -B tools/build_master_roadmap.py --check
C:/Python312/python.exe -X utf8 -B tools/build_remaining_work_plan.py --check
```

No se repitieron los negativos de F-01.01, pruebas del servidor, PostgreSQL, navegador, paquetes o toda la auditoría. La clasificación anterior, los resultados de Wascar, datos Demo50, catálogo e instalación quedan conservados. Sin cambios en aplicación/paquetes, reglas/hook, supresiones, revocación, historial Git, commits, push o publicación. No se declara el repositorio limpio ni la adopción final.
