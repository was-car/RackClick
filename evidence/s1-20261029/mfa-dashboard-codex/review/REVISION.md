# Revisión independiente · MFA del dashboard y gracia de 45 días

29.10.2026. Revisor distinto de los autores del backend, frontend y composición. Sólo lectura del producto; las únicas escrituras propias son el foco bajo .local y esta evidencia. Se leyeron AGENTS.md y el briefing vigentes. R0 es histórico; este encargo S1 es una revisión de desarrollo, no adopción ni instalación.

## Dictamen

Favorable **acotado por revisión de fuente** para los componentes descritos, sobre los hashes de FUENTES-REVISADAS.json. No se identificó un P1/P2 de autorización pendiente en esa fuente. El defecto reproducido del aviso de exención/gracia se corrigió antes de este dictamen. Las ejecuciones PostgreSQL, HTTP y navegador del coordinador deben registrarse por separado; este revisor no las ejecutó.

No acredita disponibilidad en QA, instalación Windows, migración de una instancia real, recuperación del último administrador ni producción. Cambios posteriores a los hashes requieren contrastar su diff.

## Contraste de seguridad

- **Autoridad:** rutas nuevas permanecen bajo el middleware de sesión, Origin, CSRF y límites de cuerpo existentes. Mutaciones exigen actor de cabecera igual al de sesión, UUID idempotente, revisión y acciones de lista cerrada. Usuario/ámbito y permisos se consultan en el servidor. Un actor con administración sólo de cliente no obtiene exención global.
- **Exención:** sólo la unión de las dos capacidades globales security.manage y systemhaus.manage, sin customer_id/customer_group_id. No se usan nombres de grupos ni flags enviados por el navegador. El administrador exento puede quitar su factor propio después del plazo; administrar otros mantiene security.manage y sesión MFA completada. La ruta de administración de sí mismo se rechaza y obliga a la ruta personal con contraseña actual.
- **Cambios:** propietario de la cuenta reautentica contraseña; con factor activo necesita sesión MFA. Política, factor, revocación de sesiones/desafíos/códigos, revisión, auditoría y recibo forman una transacción. Los parámetros externos no se interpolan en SQL. El replay comprueba intención y autoridad y no ejecuta otra mutación.
- **Gracia:** SQL015 es aditivo, deja NULL en fechas antiguas y asigna clock_timestamp por defecto sólo a cuentas posteriores. La política persiste activación y 45 días; ON CONFLICT DO NOTHING evita que reiniciar extienda el plazo. El vencimiento se evalúa con reloj PostgreSQL en login y en la validación de sesión, también después de esperar los locks. Sesiones sin segundo factor no pasan tras el vencimiento si el usuario no está exento.
- **Separación del factor:** activar/restablecer exige enrolar en el flujo restringido existente; un desafío no equivale a sesión. Administrador no recibe semilla, URI, ciphertext o QR. DTOs/recibos/auditoría sólo contienen estado público y contadores. Estado de usuario, nombres y mensajes se renderizan con React, sin HTML sin escapar.
- **Frontend:** borrador durable sólo de intención pública, ligado a actor/usuario/acción/revisión/requestId. Password se envía sólo en la petición personal y no entra en el diario. Respuesta de otro actor/objetivo/operación o con efecto incoherente no produce éxito. Una recuperación del recibo no debe expulsar repetidamente una sesión posterior.

La activación de la política se realiza sólo tras composición explícita del proveedor Windows real, antes del listener; la migración por sí sola no la activa y la DI sintética de pruebas no acredita esta rama productiva. El acceso efectivo bajo SID de servicio y el recorrido de instalación siguen necesitando su ensayo propio.

## Hallazgos y correcciones

### P2 de contrato/UX · el aviso ignoraba la exención y el enrolamiento pendiente

La referencia de mfaAccountNotice daba prioridad a deadlineReached y daysRemaining antes de globalAdministratorExempt/enrollmentPending. Un DTO coherente de administrador global exento, factor no configurado y fecha vencida devolvía `deadline`, anunciando una obligación inexistente; durante gracia devolvía cuenta atrás. Un enrolamiento ya exigido durante la gracia también quedaba detrás de la cuenta atrás.

El foco independiente inicial falló con expected=exempt y actual=deadline; había completado cinco comprobaciones, falló la sexta y no alcanzó dos posteriores. Se conserva en FOCOS-INTENTO-1.json; no se presenta como ocho pruebas ejecutadas.

El autor cambió el orden a unavailable → pending → active → exempt → deadline → grace → noPolicy. La repetición independiente confirma exención antes y después de fecha, y enrolamiento pendiente antes de cuenta atrás. **Cerrado en la fuente revisada.** Es un aviso erróneo, no se demostró un bypass del servidor.

### Recuperación de recibo propio · contraste de la corrección del coordinador

El coordinador comunicó el riesgo de interpretar signInRequired histórico como una orden de cerrar también la sesión nueva al recuperar la operación. La fuente revisada distingue respuesta fresca de recuperación/reintento pendiente. El foco independiente confirma que un recibo propio fresco exige reautenticación y el histórico no genera otra expulsión automática. No se atribuye al revisor el descubrimiento original ni un ensayo de navegador de este caso.

### P3 visual comunicado, sin efecto de autoridad

Se comunicó que MfaReminder aún aplicaba ir-warning por deadlineReached sin excluir administrador global exento, aunque el texto ya indicaba exención. La severidad visual debe seguir el aviso efectivo. No bloquea la autorización; si se cambia después de los hashes, contrastar ese diff de presentación.

## Pruebas propias ejecutadas

**12/12 PASS**, Node24.21.0 en Windows, sobre datos sintéticos y funciones puras del adaptador. Salida en FOCOS-INDEPENDIENTES.json:

- Recibo correcto, objetivo sustituido, requestId sustituido y efecto no aplicado.
- Borrador con campo password adicional rechazado.
- Exención global antes/después de fecha y prioridad del enrolamiento pendiente.
- Reautenticación propia fresca frente a recibo histórico.
- Cambio de actor durante lectura y discrepancia ETag/revisión.

Se reutilizó el módulo real del repositorio por import; no se sustituyó la implementación bajo prueba. El foco vive en .local/mfa-dashboard-security-ed67168b803d4e70bdde4750d2148bba/probe.mjs. No se ejecutaron compilación, PostgreSQL, HTTP, Edge, servicios, tareas, lectura de claves, suplantación, ACL ni VM. No hay nuevos secretos o dependencias.

## Archivos y símbolos consultados

- MfaAccountManagement.cs: ReadMfaAccount, ChangeMfaAccount, ReadMfaChangeStatus, RequireMfaManagementActor, MfaSessionVerified, MfaAccountState.
- MfaGraceEnforcement.cs: MfaGraceDueSql, MfaSessionAllowedSql, EnsureMfaGracePolicy, EnforceMfaGrace.
- MfaAccountEndpoints.cs, Program.cs: rutas, cabeceras y middleware autenticado.
- PostgresStore.cs / PostgresStore.Authentication.cs: Session, RequireCurrentSession, AuthenticateCore y la inserción de desafíos/sesiones.
- SchemaMigrations.cs y SQL015; como contexto SQL001/014 y AdminUsers.RequireSecurity, AdminGrantWrites y AdminGroupMembers.
- MfaAccountPanel.jsx, mfa-account.ts, mfa-account-words.ts: scopes, borradores, recibos, avisos, cambios de actor y reautenticación.
- ServerApp.jsx, AdminUsers.jsx y AdminSectionNavigation.jsx: integración y selección compartida.

## Límites

No se inspeccionaron credenciales, transcripciones o claves. No se probaron memoria física, durabilidad de IndexedDB, carreras de base de datos o permisos de Windows. Los fixtures y claves sintéticas usados por otros autores no son evidencia de custodia productiva. La escala de roles se interpreta mediante capacidades globales actuales; no implementa todavía un rediseño general del árbol de administración.

El índice de cierre no cambia por este dictamen. La disponibilidad de QA y cualquier crédito corresponde al coordinador tras el resultado integrado y su evidencia real.

## Adenda final · presentación y criterio F-07.04 actualizado

### Contraste final de fuentes

La única diferencia contra los catorce hashes de la ronda anterior es ServerApp.jsx: `3e24af4222172590874d758238b507b3067a7a20c3a134c13a1be1387c79ea79` pasa a `4f3314633284677532ddcbe829a6daa1e0cb68a4477481c8bcb661cc49712620`.

Se verificó por reconstrucción en memoria que la diferencia consiste exactamente en dos cambios de presentación en Mi seguridad: el selector Language respeta `preferences.disabled` y se muestra UserPreferenceStatus. Al deshacer sólo esos dos fragmentos en memoria, el SHA256 vuelve al anterior. No se cambió producto para comprobarlo. La espera del guardado de preferencias deja de aparentar que un cambio rápido de idioma fue aceptado; la prueba de navegador posterior del coordinador pasó.

MfaAccountPanel.jsx permanece en `60980fe178594daa1286d45fefd4dea85278d753cb5ba91849b7885698228287`; se confirma que el P3 visual ya está corregido: la clase de advertencia depende de notice=deadline/pending, no de la fecha sin considerar la exención. Queda cerrado por fuente. FUENTES-REVISADAS-RONDA1.json conserva el snapshot previo y FUENTES-REVISADAS.json fija el final; los otros trece hashes coinciden.

### Evidencias contrastadas sin repetir sus ejecuciones

El revisor leyó los TRX originales bajo el apuntador privado .local/mfa-dashboard-current.json y contrastó los resultados, sin ejecutar SDK o PostgreSQL:

- quality-final.trx contiene **379 resultados: 378 Passed y un NotExecuted**, la prueba PostgresContainerTests que necesita Docker. El agregado Counters.notExecuted figura cero: se usa el outcome individual para no afirmar 379 aprobadas.
- focus.trx:21 aprobadas; http.trx:3 aprobadas; browser3.trx:1 aprobada. Son ejecuciones del coordinador, no del revisor, y no se suman a Quality como casos adicionales distintos.
- La salida .local/mfa-dashboard-node-final.txt registra101 pruebas Node aprobadas, sin omitidas. El navegador es Edge/Kestrel HTTP loopback, PostgreSQL17.11 con esquema15 y cuenta DML, con proveedor sintético en DI; no prueba servicio Windows, HTTPS productivo ni custodia efectiva.

Además de los doce focos propios ya registrados, el revisor ejecutó **un foco Node independiente** de mfa-api.test.mjs, filtrado por “lost confirmation response”:1 PASS,0 FAIL,0 omitidas. Comprueba que una respuesta de confirmación perdida no se reintenta ni asigna autoridad de sesión. La salida está en FOCO-RESPUESTA-PERDIDA.txt. No equivale a un corte de red físico ni a una repetición de PostgreSQL.

### Criterio de producto F-07.04

Es legítimo actualizar explícitamente la línea base a v2 porque Wascar sustituyó el enrolamiento inmediato de toda cuenta por gracia45, fechas distintas para nuevas/existentes y exención de administrador global. No es una relajación inferida por el desarrollador. La v1 debe conservarse íntegra, junto con la fecha y el motivo del cambio; no se reescriben informes ni resultados anteriores.

**Dictamen favorable al cierre técnico de F-07.04 con su peso existente de0,50**, condicionado a registrar la v2 exactamente con el alcance comunicado por el coordinador:

- Sustituir sólo la cláusula de alta/configure-first-login por la política45 confirmada: nuevas desde creación, existentes desde activación persistida, exención sólo mediante capacidades globales del Systemhaus y rechazo de sesión password-only al vencer.
- Mantener los negativos de código erróneo, caducado y repetido; reintento/respuesta perdida y dos confirmaciones concurrentes. No eliminarlos del texto para obtener el cierre.
- Mantener53 tareas,280 subpasos, pesos y denominador100, y el mismo identificador F-07.04. El crédito es por cumplir su criterio técnico revisado y sus pruebas, no por101/378/83 pruebas, por documentos o por producir un ZIP.

La fuente y los resultados leídos dan cobertura al criterio técnico: los siete Facts de MfaGraceEnforcementTests constan Passed, incluidos persistencia del inicio de política, fecha de nuevas cuentas, cuenta antigua desde rollout, sesión ya abierta, vencimiento durante espera de lock y exención global frente a capacidades de cliente. Los casos actuales de MfaStore/MfaEnrollment/MfaHttp sobre código inválido, caducidad, replay y confirmación concurrente también constan Passed. El foco independiente de respuesta perdida y el recorrido GUI del coordinador complementan esa cobertura con sus límites declarados.

**No se cierran F-07.05, F-04, F-08, F-09, paquete, recuperación operativa, QA de Wascar ni producción.** No se declara que el proveedor sintético pruebe el SID efectivo. La aceptación del servidor y la entrega instalada siguen pendientes. Esta adenda no modifica el ledger ni calcula porcentaje: el coordinador registra el cambio de criterio y el crédito al cerrar el bloque.
