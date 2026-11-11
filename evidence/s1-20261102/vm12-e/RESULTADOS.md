# E · SQL protegido nativo · seguimiento02–03.11.2026

## Resultado y alcance

Wascar preparó y encendió **RackClick-W02-E_Limpio**. Sólo se operó esa VM mediante VMware Tools y PowerShell con las credenciales de laboratorio existentes, sin imprimirlas. D no se operó. No se hicieron snapshots, encendidos, apagados o reinicios desde el agente.

**New13 está instalado en E:** servicio automático bajo su cuenta estándar y SID efectivo, HTTPS43 con validación normal, CA confiable y backups inicial/programado correctos. Falta el reinicio Windows y su verificación. El lector administrativo tenía dos incompatibilidades históricas; ambas se corrigieron, revisaron y probaron mediante lectura completa real contra E13, sin cambiar sus ACL ni su programa instalado. La candidata siguiente es **14-r2**, no el14original.

**Sólo F-02.01/paso5 se acredita ahora.** El dictamen contrasta el criterio literal; no se añade un requisito de Restore/reboot a ese checkpoint. F-02.02/.03/.04 y el cierre completo de F-02 conservan sus pendientes. F-01.02/.04 no se archivan: la respuesta de Wascar confirmó la VM, no aceptó la incertidumbre de exposición.

## Recepción de la VM

[Preflight](preflight.json): Windows Server2025 Datacenter Evaluation,build26100,x64,noDC/sin dominio,elevado,47,32GiB libres,IP192.168.206.134/24,puertos5443/55441 libres y0servicios/cuentas RackClick previos. Se creó únicamente una carpeta privada de ensayo antes de instalar. El bridge restringe las operaciones a la ruta exacta de E; no selecciona D por estar disponible.

## Incidencias y correcciones

1. **Edición12:** el hash externo era correcto, pero VisualC++ se rechazó por un pin de bundle11 conservado en `RackClick.Setup.Prerequisite.ps1`. No se ejecutó el redistribuible ni se crearon cuentas/servicios RackClick. `Prepare-RackClickServer.ps1` conservaba también dos referencias viejas. [Diagnóstico](prerequisite-failure12.json). La revisión anterior omitió el test existente de coherencia de CRT; no era un error del operador.
2. **Pins nativos:** tres literales corregidos, sin relajar hash/firma/versión de Microsoft. El productor ahora rechaza antes de crear archivos si Setup,CRT,verificador Prepare y argumento Prepare no fijan exactamente el mismo bundle. Rojo9pruebas:8fallos; verde inicial9/9. La revisión detectó además que un pin sólo en comentario podía autorizar Setup incoherente; rojo12pruebas/5fallos de caso, corrección y final **13/13pins+7/7edición**. Se conserva un intento fallido por un duplicado en la misma línea y la posterior corrección de reconocimiento de espacios del source real. [Investigación](INVESTIGACION-PINS.md), diffs y rojo/verde en esta carpeta.
3. **Edición13:** reutiliza exactamente C#,bundle y servicehost anteriores; incorpora pins y manual propios. La revisión independiente verificó toda la cadena antes de ensayarla. CRT se instaló de verdad: exit0,ambasDLL14.51.36247.0,`crt_installed_verified`,sin reinicio CRT pendiente. [Medición](prerequisite-success13.json).
4. **ACL del visor:** tras instalar13, Acceso privado rechazaba el ACE de atributos+travesía0xA0 de Administradores que el instalador añade sólo a la raíz. Se reprodujo con el lector real. La corrección acepta ese ACE exacto,no heredable,una vez y sólo sobre el identificador del contenedor raíz ligado a la instancia. Archivos,subcarpetas,otrosSID y máscaras ampliadas siguen rechazados; no se cambiaron ACL de E. **4/4handles propios+138controles del visor**, y29focos independientes. [Investigación](INVESTIGACION-ACL-VISOR.md), [diagnóstico saneado](acl-diagnostic13-sanitized.json) y [revisión](review/REVISION-ACL.md).
5. **Perfil MFA2 del visor:** la lectura14superó ACL y encontró otro rechazo anterior: el perfil de servidor con MFA usa versión2, pero el visor sólo aceptaba1. Se reutiliza `Get-ServerMfaProfile`,puro y existente; la rama2 exige sus14campos y el vínculo MFA con la instalación, sin leer factores/claves. Versión1 se conserva explícitamente. Rojo por `database_access_profile_invalid`, verde final148controles y4handles. MfaRuntime no cambia. [Revisión con29controles propios](review/REVISION-PERFIL-MFA2.md).

El arnés ACL tuvo antes un error de SACL/SeSecurityPrivilege y un primer lanzador de prueba carecía de SystemRoot: no cuentan como rojos de producto. Se corrigió sólo el arnés para modificar DACL de sus fixtures, sin elevarlo. También se corrigió la asignación de ACL de la carpeta privada local usando SID explícito; antes de ese ajuste sólo contenía scripts sin valores y preflight, no contraseñas. Todos los intentos se conservan.

## Prueba nativa observada

[service-observed13.json](service-observed13.json),medida22:56:18Z del02.11:

- Running/Auto, SID del proceso y de la cuenta iguales al recibo; cuenta **no Administrador**.
- HTTPS `https://192.168.206.134:5443`,ready43,validación TLS normal y CA local confiable.
- Backup inicial `backup_complete`; tarea realmente ejecutada con resultado0,Password/Limited,SID igual al servicio.
- Boot actual todavía igual al de instalación: **no hay postboot acreditado**. El broker original terminó `awaiting_reboot`,exit observado3=reportado3,95%. Se preserva el resultado original.

[source-next-actual.json](source-next-actual.json): lectura administrativa completa contra los archivos reales de E13 con los tres sources de la corrección siguiente, verificados por hash dentro del invitado. Manifiesto3,cuatro archivos privados,roles runtime/backup ligados y distintos,sin perfiles owner/cluster. No se imprimieron ni copiaron valores de credenciales. Fue diagnóstico con sources,no instalación14original ni14-r2; el programa13 y sus ACL permanecen intactos.

Se ejecutó el broker original del payload autenticado y el comprobador real de layout. El plan se publicó usando la función exacta extraída del AST de la UI, porque `FunctionsOnly` retorna antes de su definición. No se hizo clic por todos los controles del asistente ni se declara QA manual de navegador/MFA.

## Paquete vigente para continuar

| Pieza | SHA256 |
|---|---|
| Wrapper14-r2,119269930bytes | `90f9660daf611793a6730c47554cb869cde0d69e96b59f3db53098f28a454f20` |
| Payload14-r2,117archivos | `6aff7613db23a5c7ed5d534cbba389fcdfb141f26ec16668b4b1be4a3fc539f8` |
| Bundle SQL r2,idéntico en12/13/14 | `b3f60963b59edddab4ceb51414ced6df8d42afa28210b1ff67701baa4c024f73` |

Los paquetes12/13/14originales se conservan; no se sobrescribieron ni se aplicaron parches sobre sus ZIP. El14original no contiene la corrección del perfil MFA2 y no debe instalarse como candidata final. El14-r2 cambia únicamente visor y payload.json frente al14:115miembros y bundle idénticos. No hubo nueva publicación C#/SQL/dependencias. [Cadena14-r2 revisada](review/REVISION-PAQUETE14-R2.md), [manual](../../../docs/INSTALADOR14-SQL-PROTEGIDO.md).

## Crédito y próximos pasos

[DICTAMEN-F02-01.md](review/DICTAMEN-F02-01.md) acredita el requisito literal de protección y canal mínimo bajo cuenta real. Se suma una sola vez5/8=0,625: **1849/168 → 977/84 =11,63/100**del índice del cierre. No es porcentaje global nuevo. Criterios,53resultados,280checkpoints,pesos y268números se conservan; sólo cambia F-02.01 de en progreso a cerrado.

1. Wascar debe reiniciar E desde Windows,sin revertir snapshots; se le pidió y la respuesta sigue pendiente. No inferir reinicio por tiempo transcurrido ni iniciar otra instalación para verificar.
2. Al volver: comprobar boot nuevo,servicio y ejecutar el verificador original13 una vez. Conservar su resultado y el exit observado.
3. Completar el recorrido14-r2 y Restore a un destino/cuenta/SID nuevos con datos sintéticos y backup verificado. No copiar perfiles DPAPI ni material SQL local del origen. El guard de factores MFA sigue vigente.
4. Acreditar6/7 sólo por sus resultados efectivos y revisión; no por los números de versión o cantidad de pruebas. Conservar D y sus50clientes.
5. F-01 requiere todavía disposición expresa del propietario. No se aceptó el riesgo, no se declaró falso positivo ni se rotó D por esta respuesta.

No hubo commits,push,publicación,limpieza de instalaciones previas,lectura de transcripciones o resultados personales de QA. Los datos/dumps y logs privados permanecen en `.local/`; sólo recibos saneados y sources de prueba aparecen aquí.

## Conciliación e higiene del cierre intermedio

[CHECKS-FINALES.json](CHECKS-FINALES.json) confirma que sólo cambia el estado de F-02.01,con su peso5/8 y criterios intactos. El índice pasa a11,630952380952381;26done/248pending/6in_progress,254sin cierre. Los tres generadores pasan `--check`;53resultados/280checkpoints/268números y frozen_structure_sha256 conservados. Los167casos QA anteriores son idénticos; sólo QA168planned y su revisión se actualizan. Paquetes11,cargador02 y12 mantienen sus bytes. La copia raíz RackClick-Servidor-14.zip coincide con el14-r2 revisado.

Escaneo Gitleaks8.30.1 seleccionado115fuentes/evidencias,con nombres aplanados y procedencia privada: exit1/18coincidencias conservados. Son digests nombrados de archivos,corroborados uno a uno contra bytes actuales,snapshots o fuentes del ZIP14pinado. El test intermedio138se reconstruyó retirando sólo el bloque MFA2 y conservando CRLF,con hash exactamente igual al registrado; no se ejecutó esa reconstrucción. No se decidió por aspecto hexadecimal ni se cambiaron reglas/supresiones. [Medición](SCAN-SANEADO.json) · [18disposiciones](SCAN-DISPOSICIONES.json). No es higiene global ni aceptación del antecedente F01 perdido.

[Revisión independiente del cierre intermedio](review/REVISION-CIERRE-INTERMEDIO.md): favorable a la conciliación y a las18disposiciones individualizadas, sin repetir suites ni operar VM. Verificó por separado el único crédito5/8, los criterios/pesos congelados, los167casos QA intactos, los tres ZIP históricos y las referencias de los18digests. No acepta el antecedente F01 ni acredita postboot/Restore.

El resultado se conserva como **cierre intermedio**: la petición de reinicio de E sigue pendiente y no se ha ejecutado Restore14-r2. El siguiente ensayo debe tener evidencia nueva,sin reescribir los sellos o resultados presentes. `SHA256SUMS-INTERMEDIO.txt` sella los archivos de esta carpeta, excluyéndose a sí mismo.
