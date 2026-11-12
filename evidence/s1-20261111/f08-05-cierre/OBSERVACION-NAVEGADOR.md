# Observación de automatización del navegador, sin corrección atribuida

Se preparó el frontend actual en copia privada: build0, 18 archivos, esbuild0.25.10 existente, sin instalar dependencias. Las DLL servidor/pruebas son las finales de F0804. El primer lanzamiento seleccionó los dos casos opcionales existentes:

- Dashboard: PASS, ocho comprobaciones, incluidos aviso de gracia y textos EN/DE/ES, activación propia, activación/reset de otra cuenta y siguiente login con TOTP.
- Recuperación: FAIL en la etapa amplia `generate_codes`, después del primer enrolamiento y sin excepciones de runtime observadas. El código de salida de la invocación fue1. No se registra como2/2PASS.

Una ejecución aislada posterior de recuperación pasó con el **guion original idéntico**, cuatro comprobaciones: enrolamiento inicial, diez códigos privados, retirada de la sesión anterior sin acceso API y acceso sólo tras confirmar el factor nuevo. No constituye una corrección por sí sola.

## Diagnóstico acotado y conservado

Se usaron después copias privadas del guion con instrumentación limitada: etiquetas de etapa, método GET/POST, categorías de ruta, estados HTTP y booleanos de controles. Nunca se imprimieron valores de códigos, contraseña, semillas, cookies, DOM o cuerpos HTTP.

Cinco invocaciones instrumentadas dieron, en orden, FAIL/PASS/FAIL/PASS/PASS. Con la medición disponible, el botón estaba habilitado después de marcar la casilla; se descarta atribuir el fallo a un botón deshabilitado. Una corrida fallida observó GET200/POST200 de códigos. La etiqueta `generate_codes` comprende también aserciones de lectura, unicidad, formato, almacenamiento y ocultación: no demuestra que fallara el servidor al generar. Las etiquetas más finas añadidas en las dos últimas ejecuciones no volvieron a fallar. **La causa exacta no queda acreditada.**

No se modificaron el guion compartido, React, API ni almacén. Los guiones diagnósticos privados no se fijaron por hash al inicio de cada invocación; no se presentan como una regresión certificada de un cambio. Los resultados y sus TRX están preservados por invocación; [NAVEGADOR-INTENTOS.json](NAVEGADOR-INTENTOS.json) conserva los siete lanzamientos completos, sin sumar repeticiones como cobertura distinta.

## Límite de la conclusión

Hay positivos de los dos escenarios sobre el mismo build de aplicación, y un fallo intermitente del recorrido automatizado de recuperación aún sin explicación demostrada. No se clasifica como defecto exclusivamente del guion ni como falso positivo. No se declara una batería de navegador totalmente verde ni se reescribe la omisión del paso27.

Las doce pruebas PG/HTTP del criterio de seguridad y las seis del revisor se distinguen de esta observación. El dictamen independiente la mantiene abierta, de severidad media, sin bloqueo del criterio técnico literal; la integración en candidata Windows y la aceptación de la GUI/custodia instalada permanecen pendientes. Antes de usarse como compuerta automatizada de entrega, el recorrido deberá diagnosticar sus aserciones por etapa sin volcar valores secretos y resolver la intermitencia con un negativo pertinente, sin reintentar hasta ocultar el fallo. No requiere tocar D ni repetir su instalación.
