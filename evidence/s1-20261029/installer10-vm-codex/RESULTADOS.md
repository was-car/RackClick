# Instalación10 y MFA real en Windows Server — resultado

29.10.2026. Operador de ensayo: Codex. Revisión de código, cadena y criterios: agente distinto `installer15_review`. Wascar creó el snapshot y reinició Windows; Codex no creó, revirtió, encendió ni apagó VM. No se tocaron A, B, RackClickSRV ni otras instalaciones.

## Resultado comprobado

- VM C: Windows Server2025 Standard Evaluation, independiente y no DC. Antes del ensayo: cero servicios/cuentas/carpetas de instalación RackClick y puertos5443/55441 libres. Snapshot manual **HTTPS/MFA 00**, UID4, padreUID2, conservado.
- Candidata10: wrapper `8c74b3b52d8b65f22473408ea9e23820898de9005628d6a0b14d3894cbd89e4c`; payload `990b97c0fc52176c02c1cb2023d46a8516ecc34c20fdfd8c59fb9688f247e85d`; bundle15 conservado `29927a6581fb1229163b75af66dd8d0924be0199b239052a164da096f0aef9ce`. Aplicación43archivos/operadores25 idénticos a candidata revisada; no nueva compilación del árbol compartido.
- `INICIAR.ps1 -VerifyOnly` real valida y extrae. Instalación ejecutada por el operador oficial elevado con el plan creado mediante la función pura `New-SetupUiPrivatePlan` extraída del GUI verificado. **Ensayo headless: no se acreditan clics del formulario ni ejecución de Namespacecleanup.**
- Visual C++14.40 incompatible detectado; paquete oficial14.51.36247.0 verificado e instalado, nativeExit0 y ambas DLL correctas. No se observó3010. Se transportan runtime10.0.12 y PostgreSQL17.11; no se instala SDK, Node ni Python. El comando Python disponible es un alias WindowsApps, no evidencia de un intérprete instalado.
- Creadas base y cuentas nuevas; servicio `RackClick` con cuenta estándar `RackClickSvc10`. Init elevado del almacén: `setup_mfa_store_created`, exit0, residue none. Proveedor real Windows DPAPI; sin proveedor sintético en el servicio.
- Instalador: `setup_ready_reboot_verification_pending`, valid true, salida observada/reportada3,95%. HTTPS y primer backup verificados; tarea diaria ejecutada y validada. `success=false` en ese recibo original corresponde a su estado previo al reinicio y no se reescribe como éxito histórico.
- Wascar reinició Windows. Servicio **Running/Auto**, HTTPS `/health/ready` **ready/esquema15**, validación normal de CA/nombre. Comprobación oficial posterior: **postboot_verified**, exit0, mismo UUID y arranque. Primer chequeo de inicio se adelantó al readiness y falló a21,767s del arranque; se conserva. El posterior éxito se obtuvo invocando la verificación oficial cuando el servicio estaba listo: **no se afirma éxito automático inicial**.
- MFA real por HTTPS: administrador global exento y proveedor disponible; usuario ordinario nuevo con45días; activación, desafío, secreto TOTP, confirmación y sesión MFA. Nuevo login exige segundo factor y lo verifica; sesión de prueba cerrada. Repetido tras reinicio: password202 → verify200 → estado MFA200 → logout204. Factor y almacén persistentes, sin omitir TLS ni cambiar reloj.

URL del laboratorio: **https://192.168.206.131:5443**. Desktop: `RackClick-VERIFICAR-10-883e2f83.cmd`, `Abrir-RackClick-MFA10.url` y `GUIA-QA-MFA10.txt`. El usuario de aplicación Wascar conserva su contraseña generada en Acceso privado y no fue enrolado ni modificado por el ensayo. Dos cuentas sintéticas fueron creadas para pruebas; el QA visual de Wascar se registra aparte en [QA-MFA10-WASCAR.md](../../../docs/QA-MFA10-WASCAR.md).

## Incidencias y originales conservados

1. El primer envío usó mal la posición de `-noWait` de vmrun. Se comprobó que sólo existían archivos copiados, sin proceso de ensayo ni servicio, y se lanzó correctamente. No se repitió una instalación desconocida.
2. Intento09: el driver creó un directorio de informe con DACL heredada; CRT lo rechazó como `crt_report_acl_invalid` antes de instalar dependencias o crear cuentas. Se corrigió el driver usando la función exacta del GUI, sin relajar ACL del producto.
3. Al revisar esa rama se encontró un pin histórico de bundle en `RackClick.Setup.Prerequisite.ps1`. El negativo de coherencia falló antes del cambio y pasó después; **sólo cambió ese pin**. Nueva edición10, ZIP09 intacto y marcado como superado. [Revisión CRT y cadena10](../installer15-review/ADENDA-CRT10.md).
4. La primera fórmula TOTP del cliente de ensayo no superó el vector público RFC6238 por tipos de desplazamiento de PowerShell. Se corrigió y validó antes de enviar códigos al servidor. No se cambió código del producto.
5. Primer cliente HTTP perdió la cookie del desafío por el tratamiento de Path de CookieContainer de .NET Framework; intentoA falla401 al iniciar enrolamiento. El intentoB confirma enrolamiento, pero falla401 en el siguiente login al conservar la cookie anterior. Se conservan ambos resultados parciales. La adaptaciónC copia exactamente la cookie del servidor con su Path/Secure/HttpOnly, sin omitir Origin/CSRF/TLS, y pasa. No se presenta B como PASS ni C como prueba de navegador.
6. Se conservan el primer postboot fallido y el recibo oficial posterior. No se reconstruyen recibos, no se repite instalación y no se convierte el fallo a22s en un supuesto timeout.

Los originales y scripts de ensayo están privados bajo el `work` de `.local/installer15-current.json`, subdirectorios `vm09` y `vm10`. El repositorio sólo recibe resultados saneados. Contraseñas, cookies, semillas y archivos de acceso privados no se incorporan ni se imprimen. Los pequeños errores sintácticos de scripts de transporte previos a su ejecución no son fallos del producto.

## Revisión y crédito

- [F-04.03](../installer15-review/DICTAMEN-F04-03.md): wiring real tras D2, positivos del servicio y39 negativos/controles actuales de host conciliados por identidad de fuente, sin presentarlos como una nueva ejecución. **+5/8**. No cierra F-04 completo: otros tokens, WRITE_DAC, todo el criterio ACL y recuperación siguen separados.
- [W-02.02](../installer15-review/DICTAMEN-W02-02-POSTBOOT.md): New completo, dependencias y reinicio observado. **+1/2**. No cierra matriz Windows11/DC/puertos, UX del asistente ni W-02 completo.
- Línea basev2 conservada; sólo esos dos subpasos cambian a done. **Índice de cierre del trabajo restante9,76/100**, antes8,63; +1,125. No es porcentaje global de producto. `ACREDITACION.json` conserva hashes y cálculo.

## Límites y siguiente paso

Wascar puede probar ahora la GUI/MFA de esta VM. La nueva instalación no contiene los clientes ficticios del Full Backup. Restore con factores todavía requiere integrar el sobre portable y se bloquea explícitamente. Custodia externa operativa, recuperación de último administrador y aceptación productiva siguen pendientes. No se afirma recuperación completa ni adopción.

Entrega para nuevas instalaciones de ensayo: `.local/entregas/servidor10/`, con ZIP, mantenimientoIP10 y sumas propias. No utilizar IP09 con10. El mantenimientoIP10 se verifica por bytes/pins, pero no se cambió la red de la VM. Sin commits ni push.
