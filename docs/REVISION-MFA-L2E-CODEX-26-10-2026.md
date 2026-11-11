# Revisión independiente MFA-L2e · contenido portable

**Dictamen favorable para el componente en memoria.** Asociación versión/clave, identidad explícita, análisis acotado y propiedad de buffers conformes en el alcance revisado. No es recuperación de disco ni habilitación MFA.

## Ejecución nueva de Codex

**121 archivos congelados, 12 hashes contrastados** de la entrega y componentes previos. Restore locked/build Release SDK **10.0.401**, **0 errores/0 advertencias**.

| Grupo | Resultado |
|---|---|
| Focos de Claude repetidos por Codex | **28 PASS** |
| Controles independientes adicionales | **8 PASS** |

**36 PASS, sin fallos u omisiones; 19,344s** para restore/build y ambos grupos. Los controles propios verifican formato construido a mano en ambos sentidos con versiones no contiguas7/999999, copias de claves sin alias con el input, borrado de ambas vistas al desechar, doble Dispose/getters rechazados, todos los prefijos truncados y rechazo de versiones0/uintMax y metadatos desconocidos/repetidos/fecha inválida por el parser aprobado.

Fuentes compartidas/congeladas y ocho documentos protegidos sin cambios. Cuatro binlogs, logs y TRX privados. [Resultados](../evidence/s1-20261026/mfa-l2e-codex/RESULTADOS-EJECUTADOS.json), [fuentes](../evidence/s1-20261026/mfa-l2e-codex/FUENTES-ENTREGADAS.json), [pruebas propias](../evidence/s1-20261026/mfa-l2e-codex/MfaL2eIndependentReviewTests.cs), [cierre](../evidence/s1-20261026/mfa-l2e-codex/CIERRE.md).

Subrevisor `mfa_l2_windows_review`, distinto del autor, confirmó por fuente pertenencia/count/orden, límites y limpieza normal/parcial. No compiló ni ejecutó; las cifras anteriores son del coordinador. La limpieza tras error parcial sigue acreditada por fuente, **no por observación directa de esos buffers**. Mutaciones y118ms de Claude conservan su autoría; no se repitieron ni extrapolan a otros equipos.

## Precisiones sin bloqueo de código

- El cálculo de la cota estructural es **11+65536+1+64×37=67.916 bytes**, no67.240. No hay constante funcional errónea que obligue a cambiar el código. La salida canónica normalmente es menor.
- `Serialize` normaliza el JSON del anillo. `Deserialize` acepta las variantes JSON válidas del parser aprobado; **no exige igualdad byte a byte con CanonicalRingJson**. Se acepta este contrato de entrada: mantiene semántica/identidad y rechazos de campos ilegales, orden de claves y fin exacto. No anunciar que rechaza toda representación JSON no canónica ni endurecer el parser aprobado por una frase documental.
- Se acepta duplicación de escritura de metadatos y del límite del codec en este componente aislado; no abrir ahora un refactor compartido sólo para consolidar constantes.

Permanecen los límites declarados de memoria/runtime, string de contraseña y limpieza parcial sin sonda de memoria. Sin archivos reales, exportación/importación, PostgreSQL/HTTP, servicio/SID, instalador, VM/QA, producto editado por Codex, commits/push o cambios de GitHub.

[Siguiente lote L2f](MENSAJE-PARA-CLAUDE-MFA-L2E-REVISADO-26-10-2026.md): primera exportación y recuperación integradas en un almacén nuevo de laboratorio. **Índice del cierre pendiente7,63/100**, sin crédito nuevo por el componente ni porcentaje global recalculado. MFA aún no disponible.
