# Paso 2 · tratamiento de credenciales

02.11.2026 · F-01.02 **en progreso**, sin crédito nuevo.

Para los hallazgos clasificados del paso 1 **no corresponde rotar nada**: son hashes de archivos, identificadores de carpetas/diarios y narraciones técnicas. Quedó registrada la decisión por cada ocurrencia, reutilizando las pruebas existentes.

Hay un antecedente distinto sin aclarar: la auditoría del 25.10 reconoció haber mostrado contenido de `.local`, sin delimitar qué material apareció. No está demostrada una credencial activa expuesta ni que afecte a D, pero tampoco se puede descartarlo con el barrido de Git, que excluye esa carpeta.

Para cerrar el paso falta conocer, **sin comunicar ninguna clave**, si aparecieron contraseñas/tokens reales o sólo nombres/rutas; y, si hubo material autenticador, a qué instancia pertenecía y qué tratamiento recibió. No se rotarán credenciales a ciegas ni se ejecutarán cambios en D desde esta observación.

Wascar ha indicado que no lo sabe. La búsqueda acotada en metadatos y eventos de herramientas no localizó el registro de la ejecución original; eso no prueba que no hubiera exposición. La incertidumbre queda documentada, sin volver a pedir contraseñas ni marcar este punto como terminado.

**D está conservada; no se cambió su contraseña, MFA, datos, servicio o configuración.** El índice del cierre sigue en **10,38/100**. Los pasos y pesos mantienen sus números.

[Resultado y límites](../evidence/s1-20261102/f01-02-tratamiento/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261102/f01-02-tratamiento/REVISION-INDEPENDIENTE.md) · [Plan numerado](PLAN-PENDIENTES-NUMERADO.md).
