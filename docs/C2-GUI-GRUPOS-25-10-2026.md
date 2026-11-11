# C2 · Deshacer estructural de grupos en la GUI

25.10.2026 · Codex. Implementación y revisión focal terminadas sobre I-01.01/02/04; Claude mantiene W-02/instalación. Sin commits, despliegues ni cambios en QA/VM. La candidata07 y sus fuentes congeladas se conservan.

Propiedad: `development/frontend/src/inventory-compensation.ts`, `inventory-api.ts`, `InventoryPanel.jsx`, `inventory-words.ts`; nuevos `inventory-group-compensation-words.ts` y `InventoryGroupCompensationScope.jsx`. Pruebas nuevas de candidato/adaptador y navegador, runner PostgreSQL de laboratorio, corrección de diagnóstico del test anterior y documentación/evidencia propias. Catálogo QA sólo con guiones planificados y guías regeneradas; sin habilitar disponibilidad. Backend/MFA, migraciones e instaladores intactos.

Objetivo: ofrecer revisión/confirmación de crecimiento y reducción puros a partir de una operación propia confirmada y vistas de servidor de revisiones adyacentes. El navegador describe IDs y alcance, pero sólo envía `operations.compensate` con `operationId`; la evidencia inversa y la autorización siguen en el servidor. No aceptar cambios mixtos ni inventar un historial al recargar.

Se conservan las barreras de actor/cliente/revisión/permisos, el journal original y las rutas de consulta/reintento/cancelación. El alcance estructural usa UUID y conjuntos separados de grupos/puertos/conexiones; no fabrica `changedIds` ni un detalle histórico que la API marca `notAvailable`.

## Comportamiento desarrollado

- Tras confirmar `device.editPortGroups`, la GUI relee y compara vistas de servidor adyacentes del mismo usuario/cliente/revisión. Sólo propone altas o bajas puras; renombres, reordenamientos, cambios mixtos, no-op y límites incompatibles no se ofrecen. Un número de puerto repetido en otro grupo no sustituye UUID.
- La revisión muestra grupos, puertos y cables por UUID, distingue retirar de restaurar y exige una casilla explícita. Cancelar permite revisar de nuevo el mismo alcance si sigue vigente. Se conserva el diseño del diálogo RC9; no hay otro sistema de navegación.
- La petición inversa envía únicamente `operationId`. El navegador no manda valores anteriores ni evidencia inversa. El servidor sigue comprobando permisos, revisión, evidencia completa y estado actual; no se garantiza éxito por la presencia del botón.
- La respuesta confirmada debe corresponder a variante, recurso y conjuntos revisados. No se interpreta una restauración como `changedIds`. Contexto histórico no disponible se muestra expresamente.
- Ante respuesta perdida se conserva solicitud original en el journal. Tras recargar puede recuperarse esa operación exacta, pero no se inventa un candidato nuevo si falta la vista anterior. Las expectativas adicionales son efímeras; no se añaden snapshots ni secretos al journal.

## Verificación real

- **27/27 Node24.21.0**:11casos nuevos y16regresiones, sin omisiones. Límite256/257, grupos, IDs, revisiones, cambios mixtos, respuesta inválida, replay/cancelación y textos EN/DE/ES.
- **Edge156/PostgreSQL17.11**, laboratorio nuevo: ampliación→Deshacer, casilla obligatoria, Cancelar/reabrir, eliminación de grupo/cable→Deshacer, pérdida real de respuesta HTTP200, recarga y replay exacto. Otra sesión ve la restauración y Lector no obtiene Deshacer. Nueve tablas SQL exactamente restauradas, incluidas fechas y ambos extremos; persistencia tras reiniciar proceso del servidor.22,27s, procesos y clúster detenidos.
- Regresión focal anterior de atributos: primer intento falla por índice fijo de hooks en el observador (`false !== null`), sin defecto de producto acreditado. Se corrigió sólo el diagnóstico para identificar forma y comprobar positivamente el candidato visible. Repetición focal PASS21,30s: cancelación, commit remoto invalidante, recarga vigente, persistencia y ámbito404. Primer resultado conservado.
- Revisor distinto: **5/5 negativos propios**, sin omisiones; duplicados por caja, cable ajeno a reducción, reconexión mixta y respuesta/cancelación de ámbito inválido. Adenda estática favorable al arreglo del observador. No se atribuye las pruebas de Edge/PostgreSQL del coordinador.

DLL de desarrollo reutilizada `5eb1abcf9d2f91d293bae8f1b01e94f0352ca254c0387aaa45de1c35b2a97585`, frontend privado `33cfa38f6da3ff7390d162737e5ec8c3b3c39cbb372aace2a0a771076309cf20`; CSS conservado `50dd856718dd01b3e3356a9a08005df880c859a2652b68a670c167fa75567ec3`. No compilación .NET ni sustitución de versión/dependencia. Esbuild0.25.10 y referencia RC9 verificada por el build.

[Resultados, comandos, screenshots y revisión](../evidence/s1-20261025/c2-gui-grupos-codex/CIERRE.md).

## QA, crédito y pendientes

QA112/113 añaden pasos por ubicación/campo/botón, como **planned**. Los111 casos anteriores, sus hashes/disponibilidad y metadatos permanecen iguales; guías original/restaurada regeneradas sin tocar resultados de Wascar. La cabecera enlaza al plan de cierre y ya no presenta78como cifra vigente.

Se acreditan **I-01.01/02/04**,15/14puntos adicionales. Total del pendiente: **25/7 =3,57/100puntos**,8/280subpasos. Permanece1/50resultados completos: I-01 aún está parcial. Baseline/alcance/pesos intactos; no es porcentaje global del producto.

Pendientes I-01.03/05/06/07: cubrir todos los controles/invalidez de recuperación, integrar y probar una candidata coordinada con MFA/instalación, habilitar sólo allí el QA real y registrar aceptación/cierre. El ensayo usa DLLC2 previa y PostgreSQL aislado, no la candidata07, VM, servicioWindows o un despliegue. Cambios mixtos/Redo y modelo físico permanecen en sus tareas propias; no se recorta su alcance.
