# F-07 · matriz del criterio de cierre

11.11.2026. Criterio: «Usuario nuevo completa primer factor y obtiene única sesión nueva sólo al confirmar; desafío/enrolamiento incompleto no acceden a /me, clientes ni mutaciones; negativos concurrentes y revisión independiente».

Rige la decisión posterior de45días/exención global: «usuario nuevo» no obliga a bloquear inmediatamente todas las altas. El escenario de obligación prueba cuentas cuyo plazo ya venció; la activación voluntaria y exención conservan sus pruebas específicas.

| Criterio | Evidencia ejecutada/reutilizada | Límite |
|---|---|---|
| Password válido → desafío enroll, sin sesión | L1ronda2 F0701 y nuevos2casos de [HTTP-ENROLAMIENTO.json](HTTP-ENROLAMIENTO.json) | Nueva cuenta desde creación y existente desde activación;45días no alterados |
| QR/secreto personal y factor pending | [GUI27.10](../../s1-20261027/mfa-gui-codex/RESULTADO-NAVEGADOR.json), [punto3](../../s1-20261102/punto3/MFA-EDGE.json), fuentes actuales contrastadas y70Node | UI ya existente; no navegador nuevo ni secreto en evidencia |
| /me, clientes y mutaciones prohibidos antes de confirmar | Nueva matriz3etapas×4rutas×2cookies en cada caso, DB invariable | Son24rechazos por caso, no24funciones; no se deduce autorización de controles ocultos |
| Token de desafío renombrado Session no autoriza | Misma matriz con ambas representaciones de cookie | TestServer ignora transporte real; envía cookies manualmente para probar servidor |
| Primer TOTP válido y única sesión/CSRF nuevos | Dos confirmaciones simultáneas:200/401;1filaMFA, hashes/novedad y transacción observada en SQL | DPAPI real con identidad de laboratorio; no token de servicio instalado |
| Confirmación incompleta/inválida o repetida sin autoridad | Matriz pending/código incorrecto y replay; [regresión36](REGRESION-NUCLEO.json) | Los rechazos y reintentos no abren otra sesión |
| Caducidad/revocación/rollback concurrentes |36casos actuales de Enrollment/HTTP/Grace reutilizan tests históricos: espera de política, revocación durante confirmar, auditoría fallida, locks y finalidades | No se declara toda la suite RackClick ni otra auditoría integral |
| Gracia45/exención y fecha persistida | [Decisión](../../../docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md), [dashboard29.10](../../s1-20261029/mfa-dashboard-codex/RESULTADOS.md), regresiónGrace actual | No desactivar MFA personal ni alterar fechas instaladas para probarlo |
| Proveedor/DB de ejecución reales | Nuevoscasos Windows/DPAPI1retirada/7activa, current_user observado, DDL42501, SQL46 | HTTP de memoria; identidad Windows del laboratorio |
| Evidencia instalada ya existente | [C10](../../s1-20261029/installer10-vm-codex/RESULTADOS.md), [D11 positivo sintético](../../s1-20261102/demo50-auth-diagnostic/NATIVE-MFA-CARGADOR-02.json) | C10 aporta enroll/login/postboot; D11verify/TLS. No convertir smoke inicial fallido aPASS ni duplicar recibos |
| Revisión distinta del conjunto | `review/DICTAMEN.md`, con su propia ejecución y pines | Crédito1/2 sólo tras dictamen; integración/aceptación no se adoptan por el desarrollador |

La evidencia compuesta cierra el criterio técnico, sin sumar otra vez F0701–04 ni usar cantidades de tests como puntos. Candidata objetivo, QA y adopción conservan hitos y responsables separados.
