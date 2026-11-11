# Revisión independiente de la edición 07 · 25.10.2026

**W-01 cerrado: parada D14-07 y validación del generador conformes en el alcance revisado.** La edición07 queda identificada para ensayo en otra VM Windows Server limpia; no es una aprobación para instalar en la QA actual ni una adopción del producto.

## Comprobaciones nuevas de Codex

- **14/14 pruebas afectadas**, sin omisiones: candidata07 y negativos de edición. No se repitieron las95 completas de Claude.
- **Carrera reproducida en WinPS5.1** mediante escritor/lector AST exactos y helper real: original29c expone el archivo final y devuelve `stop_request_invalid`; corregidof084 sólo expone el temporal mientras escribe, acepta la orden tras publicar y rechaza contenido malformado. Sin temporales restantes.
- **Cadena de entrega6/6**, snapshotsS4/S5 de708 archivos cada uno, y7 hashes históricos de la06 conformes. ZIPs:bundle1986, payload114, envoltorio5 e IP65. Inventarios completos, hashes/tamaños correctos, sin rutas inseguras, duplicados case-insensitive ni symlinks.
- **45 archivos de aplicación idénticos a candidata03**,25 operadores idénticos entre bundle/payload/S4. Runtimef084 idéntico en fuente compartida, snapshot y payload. Los10 hashes de fuentes/pruebas del apartado5 de Claude coinciden.
- Revisor distinto: **17 negativos adicionales** de empaquetadores y foco de dos publicaciones solapadas. El segundo escritor puede ganar sin sobrescritura; identidad coincidente aceptada, identidad ajena rechazada, ACL privada y sin temporales. Comparación AST/tokens conserva la propuesta atómica revisada, salvo normalización CR. [Ejecución exacta y límites](../evidence/s1-20261025/instalador14-07-codex/REVISION-FUENTES.md).

La guardia valida formato de edición y coherencia del hash con las fuentes. El negativo histórico rechaza bundle05 frente a fuentes actuales; no es un catálogo general que prohíba todos los números históricos si se aporta un bundle actual. No se afirma reproducibilidad de05 desde fuentes nuevas.

## Ensayo de Claude revisado; no repetido aquí

Se revisaron el observador y `LIFECYCLE-RESULT.json`:dos arranques/paradas normales, HTTPS/login/escritura/backup, Stop repetido, persistencia y limpieza;83,02s. Usa recibos sintéticos explícitos y una interfaz VMware. **Codex no ejecutó un nuevo ciclo PostgreSQL/runtime en esta tanda.** El ensayo offline privado New/Restore anterior corresponde al mismo bundle6d5a, cuyos bytes no cambian; se conserva su atribución original.

No acredita SCM, cuenta real del servicio, reinicio Windows, instalación limpia, HTTPMFA ni drenaje HTTP universal. `applicationHttpDrain=false` permanece explícito.

## Artefactos revisados

| Pieza | SHA256 |
|---|---|
| Bundle14-07 reutilizado | `6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8` |
| Payload07 | `71469d1e084fe1927eadfc2122540868c1db8bf9ac1d22f8819574e4afef8d37` |
| payload.json07 | `25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7` |
| Envoltorio07 | `3ca223230fc5ea1ab1e2ce7e40c9b7ca222ef65e4735412cb3fdb7cfd19ddca1` |
| CMDIP07 | `b36fd6d394f090d4fcbc16fa7c278132486a58ed8c774199b5001ea0030703bd` |
| Runtime corregido | `f08466f2a7633074131ad0a261bdb98f83f5a292e5a8a366c04e76cd6cfca2ed` |

La edición06 y bundle14-07 no se modifican. Reparación de red y `prepare_server_step2.py` históricos05 quedan fuera de07: no necesitan modernizarse para acreditar esta corrección ni deben ofrecerse como herramientas07.

Quedan referencias editoriales06 en nombres/comentarios del test07; corregirlas cuando se trabaje en ese archivo, sin regenerar paquetes sólo por ello. No alteran los pins07 ni las14 pruebas ejecutadas. Los fallos tardíos del empaquetador pueden dejar un payload interno: la garantía de ausencia de salidas corresponde a entradas inválidas, no a toda posible interrupción.

## Crédito y siguiente paso

Los cinco subpasos de **W-01** reciben evidencia y revisión independiente: **2,50/100 puntos del cierre restante**,1/50 resultados ponderados. Denominador, alcance y pesos conservados. No es2,50% del producto; el78anterior sigue retirado.

Siguiente: **W-02**, instalación limpia en otra VM no controladora de dominio; después cuenta/SCM/HTTPS/backup/reinicio de W-03/W-04/R. Preparar un recorrido reproducible New y Restore con evidencia del equipo real. Mantener QA actual intacta. MFA completo, custodiaD2, redistribución, aprovisionamiento limpio y adopción siguen pendientes.

[Evidencia y comandos](../evidence/s1-20261025/instalador14-07-codex/CIERRE.md), [mensaje listo para Claude](MENSAJE-PARA-CLAUDE-INSTALADOR07-25-10-2026.md). Sin cambios de código de producto, builds, servicios, cuentas, firewall, confianza, bases existentes, QA/VM, commits o push por Codex.
