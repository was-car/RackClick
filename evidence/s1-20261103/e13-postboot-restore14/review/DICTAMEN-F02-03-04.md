# Dictamen independiente · F-02.03 y cierre F-02.04

03.11.2026 · Revisor `/root/audit_steps_5_7`, distinto del implementador y del ejecutor del ensayo. Lectura de código y recibos públicos sanitizados; sin ejecutar arneses operativos, pruebas de producto, escáner o acciones sobre VM.

## Decisión

**F-02.03 y F-02.04 cumplen sus criterios literales.** La reanudación real del servicio recuperado, la identidad/material nuevos en E y la revisión integrada aportan lo que faltaba. Es admisible conciliar el cierre técnico de F-02 sin declarar postboot14, aceptación final o higiene universal del proyecto.

F-02.02 ya tiene dictamen favorable separado. Si aún no se han registrado esos créditos, la propuesta conjunta es **F-02.02 + F-02.03 + F-02.04 = `3 × 5/8 = 15/8` puntos**. Si F-02.02 ya se registró, añadir sólo `2 × 5/8`, sin duplicarlo. F-02.01 conserva su crédito anterior. Los cuatro checkpoints suman el peso congelado de F-02, no puntos nuevos por pruebas o artefactos. No modifico el ledger.

## F-02.03 · criterio literal y contraste

> Ensayar reanudación y Restore en destino nuevo con identidad/roles/claves nuevos; error explícito ante clave ausente/incorrecta.

- **Restore nativo:** origen del backup LEAO, destino Windows E; copia únicamente de dump/manifiesto autenticados. Una instalación14-r2, UUID nuevo `57822410-3b69-4542-a829-260152db9f17`, cuenta/SID reales nuevos, roles SQL ligados al ID nuevo, material creado para el destino y cuatro privados de instancia3. No se copian los perfiles DPAPI/SQL del origen. Esto no se infiere de dos clústeres bajo el mismo usuario: hay otro Windows y una cuenta efectiva distinta.
- **Datos y operación:** runtime y backup consultan20 clientes bajo la cuenta real; API confirma20 nombres exactos, login/logout; runtime sin DDL y backup con SELECT/sin DML o DDL. Servicio estándar Auto/Running, HTTPS ready43 con TLS normal y backup nuevo verificado. No se declara recorrido manual de navegador.
- **Reanudación:** el driver ejecutó un único Stop→Stopped→Start del servicio de recuperación y llegó a salud y sonda SQL posterior. Las cinco huellas de instancia, descriptor runtime, perfil/cipher de backup y cipher runtime son idénticas antes/después; no hubo regeneración para sortear un error. Tras la operación se observan20 clientes y los mismos permisos bajo el SID correcto. E13 continúa funcionando.
- **Material ausente/incorrecto:** se reutilizan los negativos reales PG previos, cuyos seis componentes y arnés conservan sus hashes exactos, incluidos `sql_operator_unprotect_failed` e `instance_sql_ciphertext_missing`. Mis comprobaciones de cadena anteriores enlazan esos operadores y la aplicación SQL con el bundle actual. No es necesario corromper el almacén vivo ni repetir la suite idéntica para demostrar otra vez el rechazo del mismo mecanismo.

### Error del driver y alcance de la conciliación

El driver **terminó con fallo** `resume_material_changed`, conservado en `resume14-error.json`; no se reescribe como una ejecución limpia. El código público permite localizar la causa: compara `PSObject.Properties.Count` sin envolver la colección. La sonda pura registrada reproduce comparación original falsa y comparación de conteos correcta verdadera.

Comprobé que el error registrado es el throw de línea40, posterior a Stop/espera Stopped/Start/readiness y a la condición que rechaza salida nativa no cero, JSON inválido o SID distinto. Por ello el0 del hijo es una **inferencia de la rama alcanzada**, explícitamente declarada; no se fabrica un recibo directo de salida0 que no fue guardado.

La conciliación compara de forma correcta los cinco pares de hashes originales y vuelve a observar el estado, sin repetir Stop/Start. El resultado reconciliado preserva el fallo y su límite de observación. Esta combinación es evidencia suficiente de la reanudación pedida; repetir la operación sólo por el defecto del comparador no aportaría una condición del criterio que siga sin demostrar.

## F-02.04 · cierre literal y revisión integrada

> Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

Cierre de F-02:

> El secreto SQL no queda en claro en el archivo entregado/configuración recuperable; servicio estándar arranca y Restore nuevo funciona mediante procedimiento documentado, sin secretos en logs/paquetes.

| Parte del cierre | Evidencia suficiente dentro de su alcance |
|---|---|
| Configuración SQL protegida | Diseño RCSQL001/DPAPI, descriptor sin conexión en claro, lectura acotada por SID/ACL, configuración excluyente sin fallback en claro y mínimo de cuatro privados. Owner/cluster sólo durante provisionamiento; sus perfiles no se conservan. Fuentes y binarios integrados ya revisados por hash y positivo con cuenta estándar real. |
| Servicio estándar arranca | New13 tiene postboot Windows real, SID correcto no administrador y readiness43/TLS. El recuperado14-r2 tiene arranque y reanudación reales con su propia identidad, sin regenerar material. Son observaciones distintas y se mantienen separadas. |
| Restore nuevo funciona | LEAO→E con sólo datos/manifiesto,20 clientes exactos por SQL/API, identidades/roles/material nuevos, backup del destino, restricciones de permisos y origen conservado. El procedimiento instancia3 y manual14 describen la generación de credenciales locales, mantenimiento mediante destino nuevo y límites MFA. `RESULTADOS.md` registra esta ejecución y sus incidencias. |
| Sin secretos SQL en los entregables/logs revisados | Inventarios y cadena de paquetes revisados, sin transportar privados de instancia; escaneo seleccionado anterior con18 digests dispuestos por bytes, sin supresiones. En el destino, ficha e informe reales no incluyen las contraseñas consultadas. El foco bajo el SID real leyó69 archivos seleccionados de configuración, logs/control y servicio, con0 coincidencias de las contraseñas SQL runtime/backup propias. No se usa esta medición como afirmación universal. |
| Revisión independiente | Este dictamen y los de F-02.01/.02, ACL, perfil MFA2 y paquete14-r2 enlazan el resultado, sus bytes y los límites. No se traslada la revisión íntegra a una decisión pendiente de Wascar que este checkpoint no pide. |

La lectura focal de69 archivos es una medición temporal de los textos seleccionados, usando UTF-8 y compartición lectura/escritura para logs activos. No cubre todos los encodings o representaciones posibles, memoria, DB/dumps, historial, otros secretos, archivos futuros ni todo `.local`. Se conserva el intento previo fallido por compartición; no se cuenta como un escaneo limpio. La conclusión técnica usa conjuntamente esa medición, la construcción/persistencia revisadas y la ausencia de credenciales de instancia en el paquete, sin prometer una prueba negativa universal.

## Contraste propio y atribución

Ejecuté sólo `CONTRASTAR-F02-03-04.py`, salida0/PASS: comprobaciones de metadatos públicos, igualdad de hashes y control de flujo del código. Resultado en `CONTRASTE-F02-03-04.json`; entradas fijadas en `HASHES-F02-03-04.json`.

El contraste liga origen/destino y paquete, compara los cinco hashes con la sonda anterior, exige que el fallo original siga intacto, valida los permisos/SID y ausencia de un segundo Stop/Start/postboot inventado, y recalcula los seis hashes contra las fuentes actuales y las huellas de la ejecución PG anterior. No importa ni ejecuta `bridge`, los arneses de VM, el lector de credenciales o el escáner.

Revisé `resume14-reconciled.json`, `resume14-error.json`, `COMPONENTES-REUTILIZADOS.json`, la sonda real de servicio y privacidad, sus arneses públicos y `RESULTADOS.md`. Las ejecuciones nativas son del coordinador; no se presentan como pruebas mías. No hay valores de credenciales en los recibos examinados.

## Pendientes que no se cierran por arrastre

- **Postboot14-r2 no está demostrado.** El broker conserva salida3/`awaiting_reboot`; el arranque Windows del destino no cambió. F-02 pide que el servicio arranque y la recuperación funcione, no un segundo reinicio Windows como condición literal. El reinicio del recuperado corresponde expresamente a W-03.03 y R-04.04 y a las aceptaciones Windows aplicables; esta evidencia no les concede crédito.
- Recuperación completa de todos los tipos de datos, factores/sobres MFA, frescura y activación de recuperación tienen sus criterios R-04 y demás resultados propios. Restaurar este backup sintético no los acredita todos.
- F01 sigue necesitando su resolución/decisión expresa. Ni los69 archivos ni el paquete nuevo resuelven el antecedente perdido, prueban revocación o aceptan riesgo por el propietario.
- No hay adopción de Wascar, QA manual acreditada, cambios en D o autorización de publicación/despliegue automático por este cierre técnico.

No operé VM, cuentas, servicios, ACL, tareas, certificados, DB o red; no abrí secretos, credenciales, dumps o capturas privadas; no modifiqué código, producto, pesos, resultados QA o ledger. La conciliación documental debe conservar estas distinciones y los fallos originales al registrar el crédito propuesto.
