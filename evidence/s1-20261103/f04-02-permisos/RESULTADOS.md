# F-04.02 · preparación de la medición efectiva

03.11.2026. **Parcial: no hay resultado de los dos servicios reales.** Sólo D está encendida en el inventario VMware observado. Se pidió a Wascar iniciar E sin revertir ni reinstalar; no se inició ninguna VM desde aquí ni se accedió al invitado D.

## Reutilización

[Investigación previa](INVESTIGACION-PREVIA.md): contraste acotado de fuente y evidencia por agente distinto. Reader `4cc4203cf338f484eb9ddca253a77b491e7f37f75de97efe1cfbdad328f0f884` conserva L2b; provider `c634dd5e8e0272e8abe68842a60ae723bc87c532538fae9a775a10df7a83b3c9` conserva L2h. No se modificaron estos componentes, el escritor del paso 11, el servidor, SQL, frontend o instaladores.

Se reutilizan los 39 negativos históricos del lector y los positivos nativos C10/D11. La salida de Wascar del 28 de octubre sigue siendo lectura real, no aceptación completa: no incluía Judge ni contadores de escritura/WRITE_DAC. Los positivos SQL de E no se convierten en pruebas de archivos MFA. No se repiten suites de producto invariantes.

## Auxiliar preparado

Nuevo `tools/mfa-acl-probe/`, sin paquetes externos o referencia al servidor. Consulta SCM, PID, creación, imagen y cuenta antes/después; comprueba token estándar, suplantación efectiva y restauración. Solicita por separado los derechos mediante OPEN_EXISTING y sólo acepta Win32 5 como denegación. No hay lectura de contenidos, generación de claves, escritura, cambio de ACL, creación de cuentas ni operación sobre servicios.

El hash de contenidos cifrados contemplado en el borrador se retiró antes de ejecutar en VM. Se registran únicamente metadatos/ACL/identidad; no se declara identidad criptográfica de los bytes del almacén.

El auxiliar PowerShell retiene y comprueba DLL/deps/runtimeconfig/solicitud y aísla el entorno del hijo. El runtime debe ser el 10.0.12 oficial, con hash y ACL contrastados por el coordinador; no basta confiar en una ruta. Los dos SID necesitan código/runtime legibles pero no modificables, separados de petición/recibos privados. No se ejecutará SYSTEM desde una carpeta modificable por esos servicios.

[Implementación y pruebas](implementacion/RESULTADOS.md) · [Fuentes y binarios fijados](implementacion/HASHES.json). Los binarios, binlogs y salidas completas permanecen privados; no se publica un paquete instalable.

## Pruebas y revisión

Build Release con SDK 10.0.401: 0 errores/advertencias, restore locked correcto. **15/15 selftests** Windows/TEMP/token propio pasan, también con roll-forward desactivado y runtime exacto. Rechazo de LEAO antes de stdin/SCM/objetivos en CLI y auxiliar; parser PowerShell 5.1 sin errores. No se presenta como verde un primer intento que no compiló.

La [revisión independiente previa](review/DICTAMEN-PREVIO-SONDA.md) distingue aptitud del auxiliar de aceptación del criterio. El revisor ejecutó **15/15 selftests** sobre los pins finales, **9/9 focos propios** y parser/rechazo de host en PowerShell 5.1. Los focos y los resultados efectivamente ejecutados quedan en `review/`; los 15 casos repetidos no se suman como casos únicos nuevos. La matriz concreta todavía no se ha generado con los metadatos de E ni ejecutado bajo sus cuentas reales.

## Pendientes concretos

1. E encendida y Windows listo; ligar el VMX exacto de E y excluir D.
2. Recoger sólo metadatos de sus dos servicios/almacenes; fijar solicitud y código/runtime por hash y contrastar la [matriz completa](MATRIZ-ENSAYO.md).
3. Medición con ambos tokens efectivos: lecturas propias permitidas, escrituras/cambio de ACL/propietario/eliminación denegados, management y lectura cruzada denegados; padres protegidos incluidos.
4. Comparar metadatos, propietarios, herencia, reparse y política del DACL; conservar el resultado real, sea favorable o fallo. Retirar sólo la tarea temporal identificada y registrar su retirada.
5. Dictamen independiente posterior y conciliación del criterio literal. No basta `status=verified` de la sonda para acreditar cobertura completa.

F-04.02 pasa sólo a **en progreso**, **0 puntos**: índice exacto 323/21 = **15,38/100 del cierre restante**, sin nuevo porcentaje global. No se acreditan F-04.04 ni F-04 completo. D, E y sus instalaciones, MFA, datos, servicios, paquetes y resultados QA se conservan; no hubo ejecuciones dentro de invitados, cambios de potencia, snapshots, commits o push.
