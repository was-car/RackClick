# Instalación11 en D y verificación posterior al reinicio

02.11.2026. New11/esquema43 instalado en RackClick-W02-D. Se conserva el clon base de Wascar y no se opera otra VM. No hay commits, push, adopción ni cambios en el ZIP11.

## Resultado comprobado

- ZIP fijo `f090b56e13bc3d4670834746cff33a2d01831eae517dbb0343ce760241c567b0`, verificado en el invitado. Windows Server2025 Datacenter Evaluation,26100, noDC/no dominio, elevado, sin RackClick previo. IP192.168.206.133/24.
- Instalador original ejecutado una sola vez: `awaiting_reboot`, valid/installedReady=true, exit3,95%. Se conserva el resultado original; el guion no guardó por separado el exit observado de ese proceso.
- Medición preboot: servicio Running/Auto bajo cuenta estándar con SID correcto y sin pertenencia a Administradores; HTTPS con validación TLS normal ready43; CA local confiable; firewall5443 limitado a IP/subred del plan; MFA store creado; backup inicial y tarea programada realmente ejecutados, resultado0/Password/Limited.
- Wascar reinició Windows. Boot de instalación10:33:17.5Z; boot nuevo10:47:45.5Z. Verificador ORIGINAL ejecutado una vez a10:48:24Z: **postboot_verified**, valid/success/rebootVerified=true, exit observado=reportado0. Eso acredita100% de instalación técnica en este ensayo, no100% del proyecto.
- Wascar confirmó que él activó MFA en su cuenta. Un login HTTPS de comprobación devuelve202/purpose=verify. Se conserva su factor; no se leen su secreto ni códigos. No se declara por ello una prueba completa de todos los recorridos MFA.

## Incidencias conservadas y límites

- Dos fallos del guion, separados de la instalación: función no exportada antes de instalar; launcher no definido después del resultado correcto. El primero se corrigió extrayendo la función original del AST, como en el ensayo10. Después se creó el acceso del Escritorio con la función original verificada. No se repite instalación ni se modifica producto.
- La primera recogida del SID no resolvió .\RackClickSvc; se ajustó sólo el comprobador a Get-LocalUser. Los recibos de error quedan privados, no se cambió cuenta o ACL.
- El smoke esperaba contraseña→200 antes de crear QA-MFA11. Recibió202 porque Wascar ya había activado MFA. Se conserva `mfa-smoke-sanitized.json` como intento fallido del arnés, con sólo dos controles previos. Una consulta separada confirmó purpose=verify; Wascar confirmó la causa. **No se creó esa cuenta ni se ejecutaron enrolamiento, códigos o recuperación automáticos.**
- El formulario nace con confianza de CA desmarcada; el plan del ensayo la fija en true. Se documenta «marca la casilla» para una instalación manual futura, sin regenerar ZIP11.
- No se ha cargado Demo50 en D, hecho Restore allí ni probado todo el asistente mediante clics. El cargador se deja preparado y pide contraseña/TOTP localmente. Restores con factores siguen bloqueados por el sobre portable no integrado; emergencia/rotación, importación/backup desde dashboard y redistribución continúan abiertos.
- `RECEPCION.json` y `RESULTADOS-PREBOOT.md` son observaciones anteriores conservadas. Para el estado final rigen `postboot-observed.json` y esta adenda; no se reescriben los originales.

## Entrega para QA

En el Escritorio de D están RackClick.url, el acceso original RackClick-VERIFICAR-11-6ca767fa.cmd, Cargar 50 clientes.lnk, QA-CIERRE-CANDIDATA11.html y PASOS-QA11.txt. La creación está medida en desktop-ready.json. URL: https://192.168.206.133:5443. El panel Acceso privado conserva las credenciales locales.

Se actualizó sólo el texto QA-166 y el estado/protocolo documental del generador de la hoja11; siguen167 casos/14 seleccionados, sin rellenar resultados personales ni habilitar el snapshot genérico del laboratorio. Guía regenerada. Siete pruebas unitarias PASS; --check y --audit PASS. El audit contrasta hashes/sellos históricos, no reejecuta sus pruebas. No se repite Edge ni la regresión del punto5 por este texto. Comandos/resultados: VALIDACIONES-GUIA.json. Las referencias de fuentes actuales se fijan por hash en REFERENCIAS-FUENTES.json.

La revisión independiente está en review/: lectura de recibos/contratos y comprobaciones propias locales, sin otra ejecución en VM ni lectura de credenciales por el revisor. No convertir su revisión de recibos en una segunda ejecución del instalador.

## Métrica

Instalación técnica de D:100%. Catálogo seleccionado:506/506. Índice acreditado de cierre pendiente:9,76/100, sin cambio. W-02.01 y W-02.02 ya estaban acreditados por el ensayo10: repetirlos en11 refuerza la candidata, no suma puntos otra vez. Siguen la matriz de hosts/rechazos y la QA final. Ledger congelado SHA256 `f2653b6a3fac5bbae3f2dd613f92c66a4004b8ce8192e6eb1b06f4493783fa3d` intacto.
