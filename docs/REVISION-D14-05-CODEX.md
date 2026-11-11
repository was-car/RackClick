# Dictamen independiente D14-05 y corrección D14-06

25.10.2026. D14-05 y candidata03: implementación de Claude. Revisión y ensayos de Codex; revisiones focales separadas por `bundle02_native_review` y `d05_source_provenance`. D14-06: corrección del operador por Codex coordinador y revisión por agente distinto. Sin commits, QA, VM o bases existentes.

## Dictamen y decisión de candidata

**D14-05 cerrado en su alcance de invalidación persistente, rollback y auditoría.** Se registra en `DISTRIBUCION14-PERFIL.json` la candidata03 limpia, manifiesto **`e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d`**, DLL **`19c94d4e104ef117f4c7788a0a0d4fbe1f846656c4e00d2dc854c2e80bd7f78c`**. Es desarrollo interno; no aprobación de instalación o adopción ni acreditación de MFA completo por HTTP.

La revisión detectó **D14-06, P2**, en el operador nuevo. Queda corregido y cubierto por focos nuevos en esta misma tanda. Se conserva el bundle05 original y se genera **bundle14-06**, con la misma aplicación03 y sólo ese operador modificado. Los bundles01–05 y los informes de Claude se conservan.

## Procedencia: qué se puede sostener

El revisor de fuentes comparó95 entradas de producto de B con el manifiesto histórico M3 de `m3-correcciones-codex/source-manifest.json`. No faltan ni sobran entradas de producto. Sólo difieren `MfaStore.cs` —exactamente el pin final M3 documentado— y `RecoveryAdministrator.cs` —invalidación y contador D14-05—. Frente al árbol actual, B difiere exactamente en los cinco archivos C2 señalados. Los tests se compararon por separado; tres pruebas Python C2 siguen en B, sin entrar en el producto publicado.

**Se acredita identidad de fuente, no reconstrucción binaria bit a bit de M3.** Tampoco se demuestra criptográficamente la correspondencia completa fuente→DLL ni que el crecimiento del PDB se deba exclusivamente a rutas. El PDB diferente/rutas de la copia quedan declarados; no se presentan como la misma publicación anterior. [Dictamen de procedencia con hashes](../evidence/s1-20261025/distribucion14-d05-codex/PROCEDENCIA-FUENTES.md).

**Decisión C2:** conservar sus cambios y sus revisiones independientes de API/validación/PostgreSQL. La frase «C2 sin revisar» del informe de Claude es demasiado amplia. Excluir C2 de esta candidata enfocada en M3+D14-05 es correcto; su integración en GUI/distribución requiere una candidata posterior coordinada y pins propios. No se revierte su trabajo ni se modifica silenciosamente la candidata03 para incluirlo.

## Pruebas ejecutadas por Codex

Windows local, PostgreSQL17.11, runtime .NET10.0.12 del SDK fijado10.0.401. Copias aisladas de operadores, publicación y tests; clúster y destinos nuevos, secretos locales y procesos en Job propio. **No se compiló producto ni se repitió la suite completa de61/62 o Python65 del autor.**

| Ejecución propia | Resultado |
|---|---|
| Dos `RecoveryChallengeTests` precompilados Debug de B, con conexión al clúster nuevo | **2/2 PASS, 0 omitidas**. Consumo enroll/verify/sesiones y fallo forzado de auditoría con rollback. XML identifica los dos nombres. No se confunde ese binario Debug con la candidata Release. |
| Release03, Restore13→14 | PASS: historial1..14, usuario original conservado, sesiones0, auditoría de recuperación, runtime lee MFA y tiene autorización DML de sesión (`UPDATE WHERE false`), CREATE denegado42501. |
| Release03, Restore14→14 | PASS: dos desafíos sintéticos enroll/verify consumidos, cero abiertos/sesiones y auditoría `revokedChallenges=2`. No se emitieron ni canjearon desafíos por HTTP. |
| Operador de Claude anterior al fix, Restore13→13 | **Regresión reproducida:** CLI confirma commit y luego `verify_postgres_command_failed`, exit1; sin manifiesto final y PostgreSQL nuevo parado. No es rollback del commit ya realizado ni daño a la base de origen. |
| Operador corregido, Restore13→13 | PASS: historial13, tabla MFA ausente, sesiones0, auditoría y manifiesto válidos. |
| Operador corregido, Restore14→14 con03 | PASS: consumidos2, abiertos0, sesiones0 y contador2. |
| Operador corregido, destino14 con M3 antigua `2ec91056…` y backup con pendientes | **Rechazo esperado** `verify_recovery_not_finalized`; demuestra que no se relajó la comprobación de14. Destino nuevo conservado sin manifiesto final. |

Los ensayos sólo modifican sus bases nuevas. Los estados de fallo se conservan; PostgreSQL propio quedó parado. El `productEdits:0` de los JSON describe al observador, no a la tanda completa: **Codex sí corrigió un archivo de producto**, el operador. Los resultados de Claude permanecen separados. [Replay D14-05](../evidence/s1-20261025/distribucion14-d05-codex/REPLAY-D14-05.json), [focos D14-06](../evidence/s1-20261025/distribucion14-d05-codex/REPLAY-D14-06.json), [pruebas con nombres](../evidence/s1-20261025/distribucion14-d05-codex/PRUEBAS-RECUPERACION.json).

## Corrección D14-06 y paquete nuevo

`New-RackClickRecoveredInstance.ps1` consultaba `app_mfa_challenge` incluso para9–13, que no tienen014. Ahora inicializa el resultado a cero y consulta obligatoriamente cuando **`stageSchema>=14`**. No cambia la revocación de sesiones, marcador, auditoría, permisos o identidades. Se ejecutó13→13;9–12 sólo tienen revisión estática de esa condición. [Diff](../evidence/s1-20261025/distribucion14-d05-codex/D14-06.patch), [revisión distinta del fix](../evidence/s1-20261025/distribucion14-d05-codex/REVISION-D14-06.md).

| Artefacto interno | SHA256 |
|---|---|
| Operador corregido | `4e10b2791ca6721c1b0dec2cb54b12d420d89d647c78eb3adf8e94ff8cfde5cd` |
| `RackClick-Bundle-M3-14-06.zip` | `75b898859dcf9163411ee49ff9c5dcadb8ad5c52d3adfbf434eed9ff0a10f6f9` |
| Manifiesto del bundle06 | `20b55172e0431c2537283e4706febddf71a2f45ded96e3a9ef94a672070b5ad8` |

BundleId06: `4b9d20b6-512c-58db-872a-30453770dec3`. Se verificaron1985 registros/1986 entradas,25 operadores actuales y lector embebido `bundle_verified`. **La única carga distinta frente a05 es `operators/New-RackClickRecoveredInstance.ps1`**;42 archivos de aplicación y sus metadatos permanecen idénticos. Se usaron archivos oficiales en caché, comprobados por sus locks; no se cambiaron versiones ni se descargaron dependencias nuevas.

New y Restore del instalador embebido06 siguen rechazando14 con `preflight_schema14_install_not_propagated`, exit2, sin crear destinos de instalación. **06 no es un ZIP para instalar en la VM.** El bundle05 queda superado por06 por D14-06, aunque su aplicación03 es válida. La candidata02 y el bundle04 se rechazan de forma nativa por sus pins excluidos; se conservan como evidencia. La M3 antigua se mantiene como referencia histórica y no debe restaurar backups con desafíos MFA pendientes. [Integridad05](../evidence/s1-20261025/distribucion14-d05-codex/BUNDLE05.json), [integridad06](../evidence/s1-20261025/distribucion14-d05-codex/BUNDLE06.json), [rechazos nativos](../evidence/s1-20261025/distribucion14-d05-codex/NATIVO05.json), [guardas06](../evidence/s1-20261025/distribucion14-d05-codex/GUARDAS06.json).

## Repetición y continuidad

Observadores publicados en la evidencia: `replay_d05.py` y `replay_legacy_fix.py`. El primero corre las dos pruebas precompiladas, los restores03 y reproduce el defecto del operador anterior; el segundo comprueba el fix con tres destinos nuevos. **Exit0 significa observaciones completadas**, incluyendo defectos/rechazos esperados según el escenario; no aprobación de entrega. Comandos y precondiciones en [el cierre](../evidence/s1-20261025/distribucion14-d05-codex/CIERRE.md). Requieren artefactos/herramientas explícitos: no son autosuficientes desde un clon limpio.

Se conserva también el rechazo de un auxiliar de Restore invocado sin argumentos suficientes y el intento de empaquetar desde una copia que no coincidía con `candidateDirectory` del manifiesto. Se corrigieron las entradas, sin modificar manifests ni producto para eludir validaciones. Son fallos de preparación, no nuevas regresiones del producto.

Próximo orden:

1. Claude puede continuar desde **aplicación03/e9 y operadores06/4e10**, conservando la aplicación pinada; evitar publicar desde el árbol compartido que contiene C2.
2. Completar pruebas HTTP con proveedor de claves de laboratorio controlado. Esto no decide ni adopta la custodia D2 definitiva de producción, que sigue pendiente de Wascar.
3. Alinear una candidata interna completa de instalador/wrapper/CMD y ejecutar instalación limpia, runtime del servicio, HTTPS/backup/Restore y reinicio en Windows Server. Mantener06 bloqueado hasta disponer de esa vía de ensayo.
4. Aprovisionamiento reproducible desde fuentes/artefactos pinados, revisión de redistribución, integración funcional pendiente y QA/adopción final. No repetir suites completas por inercia.

No se altera el servidor existente ni la disponibilidad visible de QA. Catálogo, guías y observaciones de Wascar conservados. **Avance global aproximado:78 %, sin incremento automático.**
