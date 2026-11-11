# E13 postboot y Restore14-r2 · resultado del ensayo

03.11.2026, hora de Berlín. Las mediciones conservan sus fechas UTC del02.11. Wascar confirmó el reinicio de **RackClick-W02-E_Limpio**. Sólo se operó E; D conserva su instalación11 y sus50clientes. No hubo snapshots, reinicios Windows, encendidos/apagados, commits o publicación por el agente.

## Resultado observado

- **New13, después del reinicio de Wascar:** el verificador original autenticado termina `postboot_verified`, salida observada0. Boot23:41:19.5Z distinto de22:20:26.5Z; servicio Auto/Running bajo su SID estándar, HTTPS ready43 con TLS normal. [Recibo](postboot-e13-observed.json). No se repitió New.
- **Restore14-r2, una instalación:** UUID57822410-3b69-4542-a829-260152db9f17, cuenta nueva RackClickSvcRc9 y SID distintos del New13, servicio de recuperación admitido por el visor, puertos5444/55442. Broker original `awaiting_reboot`, salida observada3=reportada3. Servicio Auto/Running, cuenta no administradora y HTTPS ready43. [Observación](restore14-observed.json), [plan](restore14-plan.json), [preflight](restore14-preflight.json).
- **Datos:** backup nativo final del laboratorio sintético de LEAO,20clientes «Synthetic SQL1…20» (con espacio antes del número). Se copiaron sólo manifest.json y data.dump. ManifestSHA256 `b22c127b5ea0d6589517ea55f507045d02c6d978a3acd3f99d0e546c97aa5912`. No se copiaron perfiles SQL/DPAPI del origen. SQL y API en E leen los20clientes; sus20nombres coinciden exactamente; login y logout finales pasan. [Origen](restore14-input-receipt.json). Es prueba de migración LEAO→E, no un volcado de D ni Demo50.
- **Privilegios:** consultas reales bajo la cuenta Windows del servicio, usando sus dos identidades SQL. Runtime lee20clientes y no tiene DDL; backup lee20 y no tiene DML/DDL. Manifiesto3, cuatro privados, roles ligados al UUID nuevo y separados. [Sonda saneada](service-probe14-r2-sanitized.json). El backup inicial y la tarea Password/Limited con resultado0 se ejecutaron realmente; dump posterior307531bytes coincide con su manifiesto.
- **Acceso y diagnóstico:** getter instalado14-r2 completo, ficha real nueva de metadatos con DACL privada, sin contraseñas, conexión completa o ciphertext; contenido igual al formateador aprobado. Informe diagnóstico oficial exportado con salida0; sus entradas no contienen las dos contraseñas consultadas en esa operación. No se imprimieron ni copiaron valores. Las fichas/informe privados quedan en E; esta evidencia sólo conserva huellas y booleanos.
- **Reanudación del destino:** un único Stop→Stopped→Start del servicio de recuperación, nueva lectura SQL con su cuenta y HTTPS ready43. Los cinco archivos de material tienen las mismas huellas antes y después. E13 continuó Running. El primer driver informó fallo por comparar una colección PowerShell de forma incorrecta; su resultado se conserva y la conciliación posterior de sólo lectura demuestra igualdad. [Conciliación](resume14-reconciled.json), [error original](resume14-error.json). No se repitió el ciclo ni se fabricó un recibo de salida nativa. El0 del hijo se infiere de la rama que comprobó su salida antes de comparar; se distingue de una observación directa guardada.
- **Persistencia sin SQL en claro:** bajo el SID efectivo se leyeron69archivos seleccionados de configuración privada, logs, control y configuración del servicio;0coincidencias de las contraseñas SQL runtime/backup propias. [Alcance saneado](service-privacy14-r2-sanitized.json). No es un escaneo universal del equipo, historial, dumps o `.local`, ni resuelve el antecedente perdido F01.

## Artefactos y método

Wrapper14-r2 SHA256 `90f9660daf611793a6730c47554cb869cde0d69e96b59f3db53098f28a454f20`; payload `6aff7613db23a5c7ed5d534cbba389fcdfb141f26ec16668b4b1be4a3fc539f8`; bundle `b3f60963b59edddab4ceb51414ced6df8d42afa28210b1ff67701baa4c024f73`. Se reutilizan los paquetes y revisiones sellados en `evidence/s1-20261102/vm12-e/`, sin cambiar sus bytes ni sellos.

Se usaron el broker, layout checker y publicador exacto de planes de la UI del paquete autenticado. **No se declara recorrido manual de todos los controles ni QA de navegador/MFA.** La copia del backup por VMware Tools no es una prueba de exportación GUI. Los arneses en [harness/](harness/) documentan lo ejecutado y sus errores; no son nuevos operadores instalables para el usuario. El puente/credencial de laboratorio, salidas privadas, binarios, dumps y fichas quedan en `.local/` o en E.

Seis componentes de los negativos SQL previos conservan exactamente sus bytes: [contraste](COMPONENTES-REUTILIZADOS.json). Se reutilizan sus rechazos explícitos por contexto incorrecto/material ausente/destino existente; no se corrompe el almacén vivo para repetirlos. No hubo build, cambio de producto, dependencias, migraciones, permisos o parche sobre D/E en esta tanda. Sólo hay arneses y documentación nuevos.

## Incidencias propias conservadas

No hubo una segunda instalación Restore. Los siguientes fallos afectaron a los arneses de observación, después del éxito del broker:

1. Intenté releer la ficha mediante `ReadManagement`, que sólo admite recibos/login. Su rechazo era correcto; se usa lectura ordinaria del archivo propio de metadatos, comprobando DACL y contenido. [Intento1](collector-fixture-error-attempt1.json).
2. Ejecuté un helper SQL destinado a la cuenta estándar desde Administrador; el propietario elevado de su temporal no cumple su política. Se cambió el actor de ensayo a la cuenta real del servicio, sin ampliar ACL/validadores. [Intento2](collector-fixture-error-attempt2.json).
3. El primer arnés de esa cuenta escribió un arreglo de pares de rutas sin agrupar la concatenación. Las consultas pasaron, pero falló su snapshot; se corrigieron sólo los paréntesis. [Registro](service-probe-fixture-error-attempt1.json).
4. PowerShell envolvió la respuesta de Invoke-RestMethod en un solo elemento; falló el contador de clientes pese al SQL20. La asignación separada confirma después20clientes/20nombres. Ese intento pudo dejar una sesión de laboratorio hasta su caducidad; el arnés final hace logout también en su finally. No se afirma cero sesiones en E. [Intento3](collector-fixture-error-attempt3.json).
5. El driver de reanudación usó `PSObject.Properties.Count` sin envolver la colección: informó material distinto. La sonda pura reproduce wrong=false/correct=true; las cinco huellas originales coinciden. Se conserva el fallo y se publica la conciliación de sólo lectura; **no se reescribe como una ejecución limpia**.
6. ReadAllBytes no podía compartir un log que seguía abierto para escritura. La lectura focal final permite compartir lectura/escritura y registra una medición temporal, no una garantía sobre cualquier escritura futura. [Intento](privacy-fixture-error-attempt1.json).

## Estado y límites

La revisión independiente de F-02.02 está en [DICTAMEN-F02-02.md](review/DICTAMEN-F02-02.md); la de reanudación/cierre, en [DICTAMEN-F02-03-04.md](review/DICTAMEN-F02-03-04.md). Ambas son favorables en su criterio literal. El revisor ejecutó sólo contraste de metadatos/código; no se atribuye los ensayos nativos, credenciales o escaneos del coordinador.

[Conciliación del ledger](CONCILIACION-LEDGER.json): únicamente F-02.02/.03/.04 pasan a done. Se añaden15/8=1,875, sin repetir.01:977/84→2269/168=**13,51/100**. Son29checkpoints cerrados/251sin cierre,53resultados/280checkpoints/268números y huella congelada intactos. No es porcentaje global nuevo. Pasos1/3/5/6/7 cerrados;2/4 pendientes; el checkpoint8 de revisión de F-02 también se registra por el cierre efectivamente realizado.

Gitleaks8.30.1 fijado: selección inicial de30archivos nuevos de evidencia/arneses, salida0/sin hallazgos; [medición](SCAN-SANEADO.json). No incluye el historial, los privados ni los snapshots antes de esta tanda y no es una aceptación del antecedenteF01. Las comprobaciones finales de documentos/generadores y el sello se registran aparte.

**No se ha reiniciado Windows después del Restore14-r2:** no hay postboot14 acreditado. Sí hay reanudación del servicio restaurado y postboot real13. Ese pendiente pertenece a la aceptación Windows que corresponda; no se convierte awaiting_reboot3 en éxito completo. Adopción final de Wascar, otros criterios Windows/backup/MFA y F01 no se cierran por arrastre.

URL del New13: `https://192.168.206.134:5443`. URL del Restore14-r2 con los20clientes: `https://192.168.206.134:5444`. E queda encendida y ambos servicios se conservan. La activación de MFA y los datos de D no se modificaron. La incertidumbre F01 sigue pendiente de una decisión expresa del propietario; confirmar la VM/reinicio no la acepta.
