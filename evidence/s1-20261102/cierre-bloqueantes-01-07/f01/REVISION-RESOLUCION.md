# Revisión independiente de la resolución investigada de F-01

02.11.2026 · Revisor: `/root/audit_steps_5_7`, distinto del investigador y del coordinador implementador. Única escritura: este dictamen. No se edita producto, ledger, evidencia anterior ni D.

**Favorable a la investigación adicional y a su delimitación factual. No aprobado el cierre técnico de F-01.02/.04 con el criterio actual.** Sí se puede dar por terminada esta búsqueda concreta y registrar exactamente su resultado. No procede repetirla por inercia, exigir demostrar una ausencia universal ni ordenar rotaciones sin material/consumidor identificados.

## Qué se ha resuelto y qué sigue desconocido

La investigación ya permite clasificar razonablemente el **contexto de la observación**: dos canales de salida dentro del trabajo de auditoría —un resultado temporal y contenido mostrado a otro agente— más un listado de nombres distinto. No son tres credenciales ni tres exposiciones del mismo temporal. Las fuentes públicas no demuestran publicación en GitHub, envío a destinatarios ajenos, uso indebido o una credencial activa de D. Tampoco demuestran que el contenido desconocido fuera inocuo o que sólo contuviera nombres.

Es correcto describirlo como **observación de manejo/salida de datos en el contexto de auditoría, con contenido no recuperado y alcance material indeterminado**. «Brecha pública confirmada» sería una exageración; «no hubo exposición» o «todo estaba autorizado y era de laboratorio» también excedería la prueba disponible.

Los tres canales están correctamente separados en `docs/F01-RESOLUCION-ANTECEDENTE.md`. Los0hallazgos del detector sólo cubren los informes conservados de `run-1`. Los0resultados de la búsqueda por dos IDs exactos y los temporales ausentes explican por qué no hay contenido atribuible; no acreditan ausencia de lectura, ausencia de secretos, caducidad o revocación. La advertencia de que detener un laboratorio no revoca sus credenciales es pertinente.

## Autorizaciones reales de Wascar

El historial de esta conversación contiene autorización expresa para que el equipo use credenciales de VM de prueba: Wascar pide que se le dé la contraseña porque «vas a usar la máquina para pruebas» y señala que los equipos se eliminarán. También autoriza desarrollo, agentes y ensayos. **El uso y la comunicación de credenciales de laboratorio dentro de ese equipo autorizado no constituyen por sí solos una exposición no autorizada que obligue a rotarlas.** No se debe convertir una contraseña legítimamente facilitada para un ensayo en un incidente confirmado sólo por aparecer en ese canal.

Ese permiso no prueba qué contenían las dos salidas del `run-1`, no identifica una clave concreta ni demuestra que todos los archivos de `.local` fueran credenciales de esas VM. «Los equipos se eliminarán» es intención, no recibo de retirada o revocación ya ejecutada. La autorización del ensayo tampoco equivale a consentimiento para publicar secretos en repositorios, informes o destinatarios ajenos. No he visto prueba pública de esa publicación.

Por tanto, el contexto autorizado **reduce lo que puede afirmarse como incidente**, pero no resuelve automáticamente el contenido ausente. No lo trataría como un falso positivo del detector: es otro tipo de observación y debe conservar su incertidumbre.

## Aplicación del criterio congelado

- **F-01.01:** los92hallazgos históricos ya clasificados no se reabren por esta investigación. El antecedente de salida es separado; no se incorporan valores ni se inventa un candidato autenticador.
- **F-01.02:** exige coordinar tratamiento si hay credencial real, corregir exposición y verificar artefactos relevantes. Hoy no existe material autenticador/consumidor identificado que permita escoger una revocación fundada. No hay prueba de revocación, pero tampoco prueba de una credencial real expuesta que deba atribuirse a D. El resultado es indeterminado, no «rotación incumplida de una clave confirmada».
- **F-01.04/F-01 completo:** el cierre conserva la condición de clasificación y resolución verificables de los indeterminados. La nueva investigación documenta el hueco y el canal, pero no contiene aún una disposición explícita del titular de esa incertidumbre. Por ello no acredita por sí sola el cierre técnico con el criterio vigente.

No es necesario ni razonable probar que nunca existió ninguna contraseña en todo el entorno, revisar todas las conversaciones o rotar todos los sistemas. La fuente material relevante sería una salida de herramienta concreta o una referencia saneada al archivo/campo/consumidor implicado; si aparece, se analiza localmente y se actúa sólo donde corresponda. Con los registros hoy disponibles, seguir buscando lo mismo no tiene un objetivo técnico nuevo demostrado.

## Resolución razonable que falta: dato concreto o decisión explícita

Hay dos vías distintas y ambas deben nombrarse correctamente:

1. **Resolución técnica con evidencia:** recuperar legítimamente una de las salidas concretas o su referencia de material/consumidor. Si contiene sólo datos no autenticadores, registrar esa clasificación sin rotar. Si identifica una credencial que salió de su ámbito autorizado, coordinar tratamiento y verificación con ese consumidor; no extenderlo por conjetura a D o a todos los secretos.
2. **Disposición administrativa del antecedente por Wascar:** si el registro no puede recuperarse, Wascar puede aceptar expresamente la incertidumbre residual de esos canales y autorizar archivarla con límites. Esa decisión es verificable como decisión del titular, **no como demostración de ausencia, falso positivo, revocación o corrección técnica**. Puede servir para conciliar el tratamiento de la observación; no produce crédito automático. El coordinador debe explicar y revisar su compatibilidad con el criterio congelado o registrar una conciliación/versionado explícitos antes de cualquier acreditación. Los pesos y la historia se conservan; no se elimina el requisito de tratar futuras credenciales reales confirmadas.

La decisión de la segunda vía debería contener estos cinco elementos, sin pedir contraseñas ni memoria factual imposible:

- Alcance limitado: antecedente del `run-1` del25.10, los dos canales internos de auditoría identificados; no una exención general para `.local`, secretos o publicaciones futuras.
- Reconocimiento de que los contenidos no se recuperaron, no se identificó una credencial/consumidor y no se ha probado ausencia ni revocación.
- Elección explícita de aceptar esa incertidumbre residual y disponer/archivar administrativamente la observación, o mantenerla abierta a la espera de una fuente concreta.
- Conservación de la clasificación indeterminada y de la evidencia; sin allowlists, supresiones del escáner, falsa prueba de retirada ni cambios ciegos sobre D.
- Reapertura y tratamiento coordinado si después aparece una credencial real fuera del ámbito autorizado; la decisión no declara D afectada ni impide intervenirla de forma coordinada si apareciera evidencia.

### Pregunta neutral que puede plantear el coordinador

> La investigación separó dos salidas internas de la auditoría del25deoctubre cuyos contenidos ya no están disponibles. No se ha identificado una credencial concreta ni hay prueba de publicación pública; tampoco podemos demostrar que aquellas salidas no contuvieran secretos. El uso de las credenciales de VM que autorizaste para pruebas se conserva como autorizado. ¿Prefieres mantener este antecedente abierto hasta obtener una fuente concreta, o aceptar expresamente esta incertidumbre limitada y autorizar su archivo administrativo documentado, sin declararlo falso positivo ni rotar D por conjetura? Si luego aparece una credencial fuera de su ámbito autorizado, se coordinará su tratamiento. Esta elección no se registrará como prueba técnica de ausencia o revocación.

No se recomienda volver a preguntar «¿recuerdas si había contraseñas?» ni pedir valores. Tampoco se debe presentar la aceptación de riesgo como condición para continuar con trabajos SQL independientes.

## Comprobaciones ejecutadas y límites

Leí el borrador nuevo, `RESULTADOS.md`, referencias saneadas, los metadatos de salidas ausentes, el resultado de búsqueda de IDs y el escaneo saneado, y contrasté los criterios vigentes y las revisiones históricas de F-01.02/.04. Verifiqué los9SHA256del sello público nuevo:9coinciden. No seguí el puntero al directorio privado ni abrí temporales, salidas originales, credenciales, transcripciones o D. No repetí Gitleaks ni búsquedas de sesiones; no hubo autenticación, rotación, DB, VM, servicios o pruebas operativas por este revisor. Los0hallazgos y contadores de investigación son ejecuciones del investigador, no mías.

**Dictamen final:** la investigación es suficiente para delimitar el antecedente y detener búsquedas repetitivas; no demuestra una exposición pública ni una clave real pendiente de revocar. No basta por sí sola para el cierre técnico congelado. La siguiente acción proporcionada es obtener una fuente material concreta si existe, o una decisión explícita y acotada de Wascar con la conciliación correspondiente, sin inventar rotaciones ni cerrar por silencio. No se cambia el ledger ni se acredita nada con este dictamen.
