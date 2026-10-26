# RackClick — instrucciones de continuidad

Comunícate con Wascar en español claro. Este proyecto continúa trabajo existente; no comenzar otro piloto ni rediseñar la GUI aprobada.

## Estado vigente: R0 contrastado, S1 autorizado

Wascar confirmó el 28.09.2026 el contraste del ZIP recepcion-20260928-091834 por el chat de continuidad. Continúa S1 bajo la autorización de desarrollo ya concedida: herramientas oficiales, laboratorio PostgreSQL nuevo, correcciones/pruebas e integración progresiva RC9. No solicitar otra aprobación de arranque. Adopción del servidor pendiente de QA final de Wascar. Lee docs/BRIEFING-MAESTRO.md, docs/CONTINUIDAD-CODEX.md y docs/S1-FUNDAMENTO.md. Los informes R0 y su protocolo son históricos; el límite de solo lectura ya no rige S1.

## Lectura inicial obligatoria
1. `docs/CONTINUIDAD-CODEX.md` — decisiones y próximo trabajo.
2. `docs/INICIO-IMPLEMENTACION-S1.md` — resultados y límites reales.
3. `docs/CONTRATO-SERVIDOR-v0.1.md` — alcance completo.
4. `docs/MAPA-RC9-R3.md` y `docs/ACEPTACION.md` — código y aceptación.
5. `development/server/README.md`, código y evidencia antes de modificarlo.

No se presupone acceso al chat anterior. Este archivo orienta; los documentos, código y pruebas dan el detalle. Si falta una decisión, registra la incertidumbre; no la inventes.

## Reglas del producto

### Reglas de código y seguridad (revisión 4, 21.10.2026)
- Mantener Npgsql directo y migraciones SQL; no introducir EF Core. Todos los valores externos se pasan como parámetros SQL; identificadores dinámicos sólo desde listas internas cerradas.
- Tratar nombres, etiquetas y descripciones como datos no confiables también en SVG, DOM e informes. No insertar HTML sin saneado ni sustituir el escape de React.
- Crear un token nuevo en cada login. MFA deberá consumir un desafío separado y emitir sesión/CSRF nuevos sólo después del segundo factor; un desafío no concede acceso a la API.
- La cuenta PostgreSQL de ejecución no es superusuario ni propietaria y carece de DDL; migración/inicialización usan identidad separada. Mantener revocación y ámbitos en el servidor.
- Nunca versionar secretos, dumps de memoria ni binlogs de compilación. Diagnósticos privados bajo `.local/`; escanear historial y cambios antes de incorporar archivos. No reemplazar controles existentes sólo para añadir una biblioteca.
- MFA aún no está disponible. Wascar confirma el21.10.2026 que será obligatorio para todos antes de producción. Completar diseño, integración, recuperación y pruebas antes de anunciarlo o habilitarlo en QA. Estado: `docs/IMPLEMENTACION-REV4.md`.

- RC9 offline adoptada es la referencia funcional y visual. No modificar el archivo adoptado. Extraer su ZIP de referencia a un directorio de trabajo separado cuando proceda.
- Conservar Click-Click, aspecto aprobado, frontal/trasera, estados/PoE, tooltips, informes e idiomas EN/DE/ES. Conservar nombres escritos por el usuario sin traducirlos.
- Servidor: ASP.NET Core/.NET 10 y PostgreSQL 17; Windows primero. No sustituir por otro piloto SQLite. La GUI está integrada y probada para login, Systemhaus y clientes; jerarquía/inventario continúan según evidencia de cada bloque.
- Jerarquía: Systemhaus configurable → clientes → sitios → edificios → salas → racks → equipos → puertos/conexiones; Dosen y dispositivos finales según contrato.
- Ámbitos de clientes y autorización se comprueban en lectura Y escritura del servidor. Permisos mediante grupos de usuarios, grupos de clientes y capacidades; no confiar en controles ocultos de la UI.
- Guardado confirmado después del commit; conflictos e idempotencia explícitos; auditoría. No perder datos ni declarar éxitos sin persistencia.
- Lotes de puertos por IDs y grupo/tipo explícitos; gn no es una identidad inequívoca. Concretar y probar Dosen/dispositivos finales sin inventar circuitos físicos.
- Entrega para Wascar: candidata COMPLETA, instalación limpia, comprobación de dependencias, base/cuentas/claves nuevas, panel administrativo, backup/restore, manual y evidencias. Los bloques S1–S4 son internos, no instaladores parciales.
- El reinicio de laboratorio solo afecta a la instancia identificada; no borrar servicios/bases ajenos. No es necesario migrar las contraseñas/datos R3 para avanzar.
- No publicar en web/GitHub ni incluir datos reales/secretos en paquetes de desarrollo.
- Nada se adopta por el desarrollador: QA y confirmación final de Wascar. Fundamento con revisión independiente registrada; cada bloque posterior requiere su propia revisión por alguien distinto del implementador, indicando qué ejecutó realmente.

## Método y continuidad
Antes de editar, inspeccionar el estado Git local; no sobrescribir trabajo ajeno. Si no hay Git, después de R0 preparar control de versiones local sin publicar ni incorporar secretos.
**Investigar antes de implementar (regla de Wascar, 26.10.2026):** Codex, Claude y agentes deben revisar primero lo existente en RackClick y consultar documentación oficial, proveedores y repositorios originales de GitHub pertinentes. Evaluar reutilización/adaptación, compatibilidad, licencia, mantenimiento, seguridad y dependencias; dejar una nota breve con fuentes/versiones y decisión en la evidencia del lote antes de cambiar código. Investigación proporcional: reutilizar consultas previas válidas y detenerse cuando permitan decidir y probar; no abrir búsquedas interminables ni exigir siempre una biblioteca externa. No instalar, copiar o cambiar versiones automáticamente. Esto no requiere otra aprobación para trabajo ya autorizado. Procedimiento compartido: [docs/INVESTIGAR-ANTES-DE-IMPLEMENTAR.md](docs/INVESTIGAR-ANTES-DE-IMPLEMENTAR.md).
Investigar → decidir reutilización/adaptación → implementar o corregir → ejecutar pruebas relevantes → conservar salida y diff → revisión independiente → QA de Wascar.
Al terminar cada bloque, actualizar `docs/CONTINUIDAD-CODEX.md`, `CHANGELOG.md`, evidencias y pruebas pendientes. Registrar qué archivo cambió, por qué, prueba/comando, entorno, resultado y próximo paso. Recalcular SHA256SUMS al empaquetar; no presentar el manifiesto anterior como vigente después de editar.
No declarar pruebas PostgreSQL/Windows por haber compilado en Linux. No afirmar que agentes siguen trabajando después de finalizar una sesión.

**QA manual detallada (04.10.2026):** actualizar docs/QA-CASOS-WASCAR.json con pasos de ubicación/botón/campo, resultado esperado y disponibilidad real después de cada cambio visible; regenerar GUIA-QA-WASCAR.html con `C:/Python312/python.exe -B tools/windows/qa_guide.py` antes del cierre. INICIAR-QA/ABRIR-GUIA-QA regeneran automáticamente desde ese catálogo y el snapshot real. Nunca sobrescribir resultados/observaciones de Wascar: se guardan en su navegador y se exportan/importan como copia JSON. No habilitar casos solo porque el código de desarrollo existe. Cuentas de QA con roles/ámbitos distintos y contraseñas privadas locales; restauración del backup aportado siempre a laboratorio/base nuevos. Avisos multiusuario autorizados como requisito nuevo, pendientes según docs/QA-COLABORACION-Y-RESTAURACION.md.

## Desarrollo después del contraste R0
Leer los documentos, localizar el proyecto y comprobar Git, SDK fijado en global.json, PostgreSQL y herramientas frontend requeridas por el código. Instalar solo lo que falte por canales oficiales y con los permisos del entorno. Registrar todo para el futuro instalador. Primera prioridad: ejecutar pruebas PostgreSQL reales antes de afirmar persistencia o concurrencia verificadas.

## Delegación autorizada

Wascar pide agentes especializados. Descubre y usa los perfiles pertinentes de .codex/agents; lee docs/EQUIPO-Y-SKILLS.md. No declares activos agentes/skills no detectados. Trabaja por tandas y separa revisión de implementación.

**Preferencia vigente de gasto moderado (28.09.2026):** Wascar pidió continuar sin agotar sus créditos. Priorizar trabajo del coordinador en tandas pequeñas y verificables; evitar activar un equipo completo en paralelo. Reservar una revisión independiente acotada para cambios listos. Probar primero los fallos afectados y hacer una sola regresión pertinente al estabilizar el código. Entregar un resultado breve por tanda antes de ampliar alcance; no dar estimaciones de créditos sin datos de facturación.

**Agrupación solicitada por Wascar (17.10.2026):** avanzar en grupos de tres tandas pequeñas cuando sus tareas sean independientes. Asignar archivos y resultados separados, coordinar las dependencias y entregar un cierre conjunto con el resultado real de cada tanda. La preferencia de gasto moderado y la revisión independiente se mantienen; agrupar tres tareas no obliga a ejecutar tres suites completas ni a abrir tres cambios sobre el mismo archivo.

**Seguimiento solicitado por Wascar (28.09.2026):** incluir siempre en cada cierre el porcentaje aproximado de la entrega completa, qué avanzó y qué falta. Usar docs/PROGRESO-GLOBAL.md como criterio vigente; distinguir estimación de alcance de pruebas/aceptación. No incrementar el porcentaje por inercia ni confundirlo con créditos consumidos.
