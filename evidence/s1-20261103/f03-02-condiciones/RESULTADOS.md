# Paso9 · F-03.02 · Concreción técnica D2

03.11.2026. Autor: coordinador Codex. Solicitud: continuar F-03.02, conservar D y reutilizar evidencia antes de implementar. El criterio congelado pide **concretar condiciones técnicas**, no desplegar una recuperación o crear otro codec. La tarea F-03 es decisión sin peso; sus pruebas operativas pertenecen a F-04..F-09/R-04.

## Resultado del trabajo

[Contrato técnico](../../../docs/D2-CONDICIONES-TECNICAS-F03-02.md): recuperación restringida con códigos y pérdida total, RCKEYv1 acotado/AAD, protocolo recuperable disco/DB con fases y decisión de commit incierto. Define prioridades de reenrolamiento sobre exención global, autoridad local separada de `--recover-admin`, identidades/AAD, versiones no reutilizadas y límites de Restore. Conserva custodia confirmada y gracia45; no pregunta otra vez por ellas.

La publicación distingue `rotate`, `portable-restore` y `loss-reset`. Pérdida total no exige claves anteriores inexistentes ni declara restaurables sus backupsMFA; conserva material opaco, documenta afectados y fuerza reenrolamiento. Preparación offline, verificación de datos, arranque controlado y recuperación del usuario son fases distintas. Journal/fence/registroDB/publicador/operador de pérdida son contratos pendientes de implementación en sus propietarios; no existen hoy por haberlos definido.

## Investigación previa y reutilización

Leídos Git local y continuidad/hoja/plan/decisiones D2/gracia45, revisiónD2 y fuentes de codec, payload, lector/escritor, exportación/recuperación, host/login/códigos y Restore. El explorador independiente acotó la parte publicación/Restore por lectura, sin modificar producto. Consulta oficial03.11: [.NET10/AES-GCM](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.aesgcm.decrypt?view=net-10.0), [PBKDF2](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.rfc2898derivebytes.pbkdf2?view=net-10.0), [PostgreSQL17/2PC](https://www.postgresql.org/docs/17/two-phase.html). Reutilización de primitivas/componentes existentes; sin biblioteca, versión o configuración nueva.

[CONTRASTE-ENTRADAS.json](CONTRASTE-ENTRADAS.json) conserva hashes de14fuentes de producto y comparación de6componentes con los manifiestos exactos de sus revisionesL2d/f/g: **6/6 idénticos**. Se reutilizan, sin reejecutar ni sumarlas, las pruebas históricas de codec34, recuperación93 y archivos59 dentro de sus alcances. La coincidencia del componente no implica que todo el producto o su integración estén ensayados.

El codec actual mantiene cabecera validada antes de PBKDF2,600000iteraciones fijas, AAD0..42, límites1MiB/contraseña12..256puntos de código y coincidencia con la revisión independiente. El código actual ya devuelve desafío de reenrolamiento sin sesión tras canje de código; falta el operador de pérdida total y su protocolo, no otro login. El exportador actual conserva su límiteABA; el escritor sólo crea almacenes nuevos; Restore nativo aún rechaza factores con `recovery_mfa_envelope_required`.

## Revisión y correcciones

Revisión independiente de seguridad en [REVISION-INDEPENDIENTE.md](REVISION-INDEPENDIENTE.md). Detectó un P2 del primer texto: exigir todas las claves viejas también en pérdida total. Se corrigió con modos excluyentes y cobertura viva posterior, sin cambiar producto. Se añadieron negativos futuros de `disable`/`reset`/activación de política y precisión de Restore sin rotación implícita. No se presenta ese hallazgo documental como fallo o prueba ejecutada de D.

Antes de acreditar se exige dictamen sobre el SHA256 final del contrato. No se acepta una revisión de un borrador anterior como si fuera la versión final.

## Comprobaciones de esta tanda

- Lectura y contraste de criterios/decisiones, fuentes e informes; hashes y enlaces locales del contrato.
- Guardas de planificación: sólo F-03.02 puede cambiar a `done`; F-03.03 y F-04..F-09/R-04 permanecen con su estado; IDs, texto del criterio, pesos, alcance y baselinev3 permanecen intactos.
- Validación/regeneración del informe de progreso, hoja maestra y plan numerado tras el dictamen; número9 conservado, no renumerar.
- Comparación antes/después de las14fuentes de producto; sin código de aplicación, SQL, paquetes, dependencias, GUI o resultadosQA modificados. Único cambio de auxiliar: el render Markdown del plan usa su `vmRule` configurableD45 en vez de la leyenda43 obsoleta; no opera la VM. **0operacionesVM**, cero acceso a claves/credenciales/DB, sin commits ni push.

No se compila ni se ejecutan pruebas PostgreSQL/Windows/crypto nuevas: no hay cambio de producto y el criterio de esta decisión no lo exige. No se presenta el paso como recuperación entre equipos, rotación, aceptación operativa o durabilidad ante corte.

## Métrica y continuación

F-03.02 pesa0: cerrarlo documentalmente tras revisión no añade puntos. Índice exacto conservado2479/168=14,755952…/100, redondeado **14,76/100**; no porcentaje global nuevo. F-03 no queda cerrado entero: sigue F-03.03, número10. Los contratos aquí concretados se implementan/ensayan después en sus pasos sin repetir el proveedor o codec ya revisados.

El estado final del ledger, la huella de alcance y las salidas de generadores se conservan en `CIERRE-VALIDADO.json` al terminar la conciliación.

## Cierre aplicado y contrastado

**F-03.02 done**, tras revisión del contrato SHA256 `b8a601686d9a7c03518f5c3f4084ccd348fcecf393ee41d46fb8c1caec7c0dd3`. [Adenda independiente de planificación](ADENDA-PLANIFICACION.md) confirma sólo ese checkpoint alterado,52otras tareas/279checkpoints idénticos y huella de alcance9ef507b41abc2c8cab58e38bf345c4a4f30dd48a8a156b0d1d4ebd7ea45be974 conservada. Baseline/criterios/pesos intactos;31→32done,249→248sin cierre,0puntos.

Regeneración y los tres `--check` dieron0; salidas propias en [VALIDACIONES.json](VALIDACIONES.json). El9 permanece en268opciones;10/F-03.03 pendiente.14fuentes de aplicación conservan sus hashes,6componentes históricos reutilizados exactos. Ledger finalSHA7951eebfe254558caf6c4871652f610ba582302581e2aff100984800b3621be4. No hay operacionesD/E ni nuevos ensayos de producto. [Estado final](CIERRE-VALIDADO.json).
