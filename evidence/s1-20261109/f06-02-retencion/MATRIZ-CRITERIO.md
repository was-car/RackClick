# Matriz literal · F-06.02

Peso congelado5/8; texto: «Retirar una versión sólo si ningún factor ni backup retenido la necesita; incluir inventario de versiones en backup/sobre».

| Parte | Evidencia de componente | Límite que se conserva |
|---|---|---|
| Factores no omiten estados | Reader real agregado, pending/active/disabled, cero filas explícito, rolSELECT, snapshotreadonly, versión inválida/cancelación rechazados. | No exclusión frente a escritores futuros ni vínculoDB/instalación autenticado por el lector. |
| Referencia impide candidata | EvaluateCandidate bloquea activa, factor, backup, catálogo incompleto, dependencia/ámbito inválidos. | No existe todavía acción de retirada/publicación de anillo vivo que llame esta guarda. |
| Backup identifica versiones | JSONlateral acotado con hashes de inventario/manifiesto/dump/sobre, lista requerida calculada y pin externo. Prueba con dump real quieto y carpeta histórica intacta. | El operador nativo no publica/transporta ese lateral; catálogo autoritativo y snapshot concurrente pendientes. |
| Sobre identifica versiones | Inspector abre/authentica RCKEY/RCKPAY existentes y obtiene anillo/activa completos; disposiciones/limpieza en código. | No nueva prueba de custodia real, DPAPI portable o material del servicio. |
| Integridad/casos inválidos | Pins de referencia externa, JSONduplicado/extra/tipo/rango/UTF8/surrogates, uniónrequired obligatoria e inmutabilidad. | Pines por sí solos no demuestran autenticidad de un inventario autogenerado o vigencia de un snapshot. |

El revisor debe distinguir suficiencia técnica de componentes de cumplimiento operativo del texto. No se reclama que un resultado positivo autorice eliminación. No hay crédito por anticipar el coordinador de F-06.03.
