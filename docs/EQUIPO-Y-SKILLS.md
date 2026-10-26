# Equipo y capacidades

**Regla compartida desde el 26.10.2026:** antes de implementar, investigar lo existente en RackClick y las soluciones de documentación oficial/proveedores/GitHub. Registrar fuentes y decisión de reutilizar, adaptar o implementar, con esfuerzo proporcional y sin aprobaciones rutinarias nuevas. Se aplica a Codex, Claude y agentes: [procedimiento](INVESTIGAR-ANTES-DE-IMPLEMENTAR.md). No duplica investigaciones vigentes ni autoriza adoptar dependencias automáticamente.

## Activación verificable

El usuario autoriza agentes y skills relevantes para RackClick. Se incluyen perfiles de proyecto en .codex/agents y agentes habilitados con máximo 4 subagentes simultáneos en .codex/config.toml. Trabajar por tandas, no lanzar todos por inercia. Conservar modelo/configuración del padre salvo decisión explícita. No cambiar políticas de seguridad del cliente.

Desde17.10.2026 Wascar prefiere grupos de tres tandas pequeñas independientes, con propiedad separada y cierre conjunto. Mantener alcance acotado y gasto moderado: asignar sólo los perfiles necesarios, revisar por alguien distinto del autor y no duplicar builds o regresiones por cada documento. Primer grupo51: previsualización administrativa, contrato de cierre de auditoría y matriz pendiente de inventario; esto no declara implementadas las funciones que sus planes describen.

La sesión de VS Code debe comprobar que los carga; su disponibilidad depende del cliente, cuenta y versión. Si falta capacidad multiagente, declararlo. No presentar simulación de roles en una sola respuesta como revisión independiente.

| Perfil | Responsabilidad y salida |
|---|---|
| Coordinador principal | PM/PO, orden, decisiones, dependencias, evidencias y aceptación; no se delega la coherencia global |
| product | Paridad RC9, alcance y criterios de aceptación; lista de desviaciones |
| architect | Módulos, contratos, límites y evolución; decisiones justificadas |
| network | Puertos/caras/cables/PoE/AC/Dosen; reglas realistas sin inventar circuitos |
| frontend | Reutilización GUI RC9, adaptador y estados de guardado; cambios asignados después de R0 |
| backend | API/comandos/transacciones y validación; cambios asignados después de R0 |
| database | Esquema, constraints, migraciones y consistencia; pruebas PostgreSQL |
| security | Ámbitos, sesiones, grupos, secretos y amenazas; revisión separada |
| qa | Tests independientes y evidencia negativa/positiva; no editar producto para hacerlo pasar |
| ux | Legibilidad, idiomas, responsive y paridad visual; no rediseñar lo aprobado |
| windows | Instalación/servicio/HTTPS/backup/restore; ensayo desde cero |
| writer | Manual visual, documentación alemana/técnica y registro de decisiones |
| release | Hashes, licencias, contenido, rollback y estado verificable |

R0 contrastado por Wascar el 28.09.2026. S1: un único dueño por conjunto de archivos, tareas paralelas independientes y sin sobrescribir cambios. QA/seguridad no aprueban cambios que hayan implementado. Los perfiles «En R0 solo auditoría» eran condicionales a esa fase ya completada; los encargos S1 de implementación están autorizados. Revisiones devuelven hallazgos reproducibles, no elogios.

## Skills: descubrir antes de usar

Inventariar skills instalados del cliente y leer sus instrucciones. Aplicar los relevantes: desarrollo/debugging .NET y PostgreSQL, pruebas de navegador, revisión de seguridad, accesibilidad, documentación HTML/Word/PDF, Git/release y Windows/PowerShell. Estos son tipos de capacidad, NO nombres de plugins cuya existencia se presupone.

OpenAI Docs es pertinente para configurar Codex, no sustituye documentación oficial de Microsoft/PostgreSQL. Skills de documentos/PDF sirven para los manuales cuando estén disponibles. Un generador de imágenes no sustituye capturas reales de QA. No reconstruir el producto con una herramienta de hosting de sitios ni activar herramientas de marketing/email/calendario ajenas a la tarea.

No se empaquetan skills internos de este chat ni claves/MCP privados. No es posible garantizar desde aquí la activación de todos los skills de otra instalación. Si falta una capacidad, documentar alternativa mediante herramientas normales, o proponer instalación oficial después de R0 sin comprar servicios ni pedir credenciales en el chat.

## Referencias de configuración consultadas el 28.09.2026

- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/build-skills

Los TOML se validan sintácticamente aquí; su carga/ejecución en la extensión local queda por comprobar. No hay agentes locales declarados activos en este paquete.
