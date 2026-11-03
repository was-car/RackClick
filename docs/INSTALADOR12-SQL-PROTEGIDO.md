# RackClick · instalación de ensayo12 · SQL protegido

Candidata local para una VM Windows Server2025 independiente. Conserva D y sus datos. El servicio, HTTPS, MFA/gracia45 y catálogo actuales se mantienen; cambia la protección SQL. Las pruebas de laboratorio no sustituyen el ensayo real del paquete12.

## 00 · Preparar Windows

1. Usa Windows Server2025 x64 con experiencia de escritorio y sin rol de controlador de dominio. Para el laboratorio:2vCPU,8GiB de RAM y60GiB de disco, como orientación. Los clientes trabajan en el navegador.
2. En VMware conserva un snapshot limpio. No borres ni reviertas D. El encendido, apagado y los snapshots los gestiona Wascar.
3. Instala VMware Tools y reinicia si lo solicita. En Windows deja operativa la tarjeta de red. No crees cuentas RackClick ni instales PostgreSQL global, SDK, Node, Python o HeidiSQL: el ZIP incluye sus dependencias de ejecución y crea sus cuentas.

## 01 · Copiar y verificar

1. En Explorador abre Este equipo → Disco local(C:) → Nuevo → Carpeta. Crea C:\RackClick-Instalar12.
2. Copia allí RackClick-Servidor-12.zip y su archivo .sha256. Conserva además el SHA256 entregado por el coordinador separado del ZIP.
3. Abre Inicio, escribe Windows PowerShell, haz clic derecho y elige Ejecutar como administrador. Acepta el aviso de Windows.
4. Ejecuta el siguiente bloque. Compara el resultado exactamente con el SHA256 de la entrega. Si no coincide, no extraigas ni ejecutes.

```powershell
Get-FileHash -LiteralPath 'C:\RackClick-Instalar12\RackClick-Servidor-12.zip' -Algorithm SHA256
```

## 02 · Extraer en una carpeta nueva

1. En esa misma PowerShell ejecuta:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $zipRackClick = 'C:\RackClick-Instalar12\RackClick-Servidor-12.zip'
    $destinoRackClick = 'C:\RackClick-Instalar12\Extraido12'
    if (Test-Path -LiteralPath $destinoRackClick) {
        throw 'La carpeta ya existe. Conserva su contenido y utiliza otra carpeta nueva.'
    }
    Expand-Archive -LiteralPath $zipRackClick -DestinationPath $destinoRackClick
}
```

2. Abre C:\RackClick-Instalar12\Extraido12\RackClick-Servidor-12 en Explorador. No cambies ni mezcles archivos de otras ediciones.

## 03 · Instalar New en la VM limpia

1. Haz doble clic en 00-LIMPIAR-Y-REINSTALAR.cmd. En una VM limpia no hay instalaciones anteriores que retirar. No lo ejecutes en D. Acepta elevación y revisa la propuesta antes de confirmar cualquier retirada.
2. En el asistente comprueba IP de escucha y nombre/IP del navegador. Deben coincidir con la red actual de esta VM o su DNS. RackClick no cambia la IP/DNS de Windows.
3. Comprueba HTTPS5443, PostgreSQL local55441 y subred autorizada. Si están ocupados, conserva el resultado y coordina otros puertos; no detengas servicios ajenos.
4. Escribe nombre del Systemhaus y usuario administrador de aplicación. Para New deja vacíos backup y su hash. En una VM limpia conserva servicio RackClick y cuenta RackClickSvc; el instalador genera su contraseña localmente. No envíes contraseñas por chat.
5. Mantén activada la confianza de CA en este servidor para validar HTTPS. Pulsa Revisar e instalar, contrasta el resumen y confirma el plan correcto.
6. Espera al resultado. Si VisualC++ exige reiniciar, conserva el informe y reinicia Windows antes de reintentar desde el asistente. No elimines archivos/cuentas para forzar el intento.
7. Cuando indique preparada con HTTPS y backup comprobados, el resultado es awaiting_reboot. No equivale todavía a la comprobación posterior al arranque.

## 04 · Reinicio y acceso

1. Reinicia Windows desde Inicio → Encendido → Reiniciar, sin revertir snapshots.
2. En el Escritorio abre RackClick-VERIFICAR-12-xxxxxxxx.cmd y pulsa Verificar instalacion. Debe terminar en postboot_verified con servicio automático, HTTPS y backup comprobados. Si falta ese acceso, conserva el informe y detente; no repitas una instalación para verificar.
3. Pulsa Acceso privado. El operador elevado puede consultar usuario/contraseña web y conexión SQL runtime con máscara inicial. La ficha que se guarda no contiene contraseñas; no adjuntes capturas con secretos revelados.
4. Pulsa Abrir RackClick, inicia sesión y comprueba el dashboard. MFA conserva45días de gracia y la exención global confirmada. En otros equipos importa sólo la CA pública, nunca su clave privada, y usa la URL HTTPS del servidor.

## 05 · Backup y Restore

1. El backup programado se ejecuta con la cuenta estándar prevista y otro rol SQL de sólo lectura. Verifica que existe una copia completa, su manifest.json y data.dump. Conserva su hash en un medio confiable y copia el backup fuera del disco de la VM; contiene datos de seguridad y no es una demo pública.
2. Para Restore usa otra VM o instancia nueva con cuenta/servicio/puertos nuevos y disponibles. Selecciona modo Restore, carpeta nativa del backup y SHA256 de manifest.json. Un JSON RC9 o de inventario no sirve en esos campos.
3. El destino crea UUID, roles, contraseñas y material DPAPI nuevos. No copies runtime.json, perfiles cifrados, contraseñas SQL o archivos DPAPI del origen.
4. Tras el Restore repite el reinicio y Verificar instalacion. Comprueba los datos esperados y que backup nuevo funciona. El origen se conserva; no se sobrescribe ninguna base existente.
5. Límite conservado: si el backup contiene factores MFA, se exige su procedimiento de custodia/recuperación, aún separado del ensayo SQL. No borres factores ni generes una clave nueva para saltar recovery_mfa_envelope_required.

## 06 · Mantenimiento y datos de prueba

La instancia3 no guarda contraseñas SQL owner/cluster. El mantenimiento con DDL se realiza mediante Restore a instancia nueva con una candidata compatible; no mediante --migrate sobre la instancia en marcha. El rol SQL de backup no puede modificar datos ni crear tablas.

La carga Demo50 es opcional y separada. Usa el paquete de datos validado que facilite el coordinador únicamente en una instalación vacía y autorizada; no se ejecuta automáticamente, no incorpora usuarios/factores y no debe repetirse sobre D. Este envoltorio no promete incluir los auxiliares de cambio de IP de otra edición: se deben preparar contra los pins12 antes de usarlos.

## 07 · Si hay un fallo

No repitas ni borres a ciegas. Conserva el mensaje, el informe sanitizado y la fase. El asistente exporta un ZIP al Escritorio; RECOPILAR-INFORME.cmd genera otra copia cuando proceda. No adjuntes archivos de management/private, contraseñas, claves, dumps, capturas de Acceso privado revelado ni binlogs.

El ensayo final de servicio/backup/Restore y reinicio se registra con los hashes exactos del paquete12. No hay adopción automática ni publicación pública. D y las entregas anteriores se conservan.
