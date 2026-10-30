# Instalador10 — ensayo Windows y MFA

29.10.2026. Candidata de esquema15 para laboratorio. La entrega08 y las instalaciones previas se conservan. La instalación elevada y el reinicio sólo se acreditarán con sus resultados reales.

## 00. Preparar el servidor

Windows Server2025 x64 con escritorio, sin rol de controlador de dominio. Wascar vuelve personalmente al snapshot limpio y avisa cuando Windows esté iniciado. No cambiar la IP de Windows desde RackClick. .NET10.0.12 y PostgreSQL17.11 están incluidos; el asistente instala el redistribuible Visual C++14.51.36247.0 si hace falta. No instalar SDK, Node ni HeidiSQL para usar el producto.

## 01. Abrir el paquete

Compara el SHA256 del ZIP con `SHA256SUMS.txt` entregado por separado. Extrae en una carpeta nueva. Dentro de `RackClick-Servidor-10`, haz doble clic en `00-LIMPIAR-Y-REINSTALAR.cmd` y acepta la elevación. El nombre del CMD procede del envoltorio conservador; no autoriza borrar bases. Revisa el resumen de conservación y pulsa **Conservar anteriores e instalar** sólo si corresponde a este laboratorio.

## 02. Instalar New

En el centro del asistente:

1. Revisa **IP de escucha** y **Nombre DNS o IP para el navegador**: la dirección actual de la VM.
2. Revisa **Puerto HTTPS**5443, **Puerto PostgreSQL local**55441 y la **Red autorizada** real. Los dos puertos deben estar libres.
3. En **Nombre de Systemhaus**, escribe el nombre del laboratorio. En **Administrador de RackClick**, usa la cuenta deseada; la contraseña se genera localmente.
4. En VM limpia deja servicio `RackClick`, cuenta `RackClickSvc` y **Modo: New**. Una prueba paralela necesita nombres y puertos nuevos; no se reutilizan cuentas anteriores.
5. Deja marcada la confianza de CA en este servidor. Abajo a la izquierda, pulsa **Revisar e instalar** y confirma el resumen.
6. Espera al resultado. Si Visual C++ requiere reinicio, reinicia Windows y sigue lo indicado por el asistente. Ante fallo conserva el informe y comunica su código; no repitas sobre el mismo destino.

La instalación genera cuentas Windows y PostgreSQL separadas, claves MFA privadas y un perfil de servicio que habilita el proveedor. Verifica HTTPS, readiness15 y un primer backup antes de `awaiting_reboot`.

## 03. Reiniciar y comprobar

Cuando el asistente diga que falta reiniciar, Wascar reinicia Windows. En el Escritorio abre `RackClick-VERIFICAR-10-<8 caracteres>.cmd`. En el panel pulsa **Verificar instalacion**. El resultado esperado es `postboot_verified`, servicio automático en ejecución y backup programado verificado. No volver a lanzar la instalación para esta comprobación.

## 04. Entrar y probar MFA

1. En el panel inferior pulsa **Acceso privado**. Se abre el archivo local con el usuario y la contraseña de aplicación; no los pegues en el chat.
2. Pulsa **Abrir RackClick** y entra con esa cuenta.
3. Abre **Mi seguridad**. Debe indicar que MFA está disponible y que el administrador global está exento de la obligación automática.
4. Pulsa **Activar MFA**, confirma la contraseña actual y sigue el enrolamiento con un autenticador TOTP. Guarda el secreto únicamente en tu autenticador.
5. Introduce el código de seis cifras. Tras confirmar, debe abrirse la aplicación; al cerrar sesión y volver a entrar, el código debe ser obligatorio.
6. En la administración de usuarios, selecciona una cuenta y abre su sección MFA. Gestionar otra cuenta exige `security.manage` y una sesión que haya completado MFA; un administrador de cliente no obtiene la exención global.

Los usuarios ordinarios disponen de45días: desde creación para cuentas nuevas y desde activación de política para las anteriores. Se muestra el plazo restante. El administrador global de Systemhaus puede desactivar su propio factor con la comprobación correspondiente. Reiniciar o desactivar durante la gracia no reinicia el plazo.

## 05. Restore y recuperación

Restore admite copias nativas compatibles de esquemas13/14/15 en una base nueva. Si contiene cualquier factor MFA, esta candidata se detiene con `recovery_mfa_envelope_required`: todavía falta integrar la importación operativa del sobre de claves. No borrar factores, no cambiar sus claves ni sustituir el backup original. Un JSON RC9 no es un dump PostgreSQL.

El backup SQL no contiene las claves MFA. La custodia externa del sobre y los procedimientos de recuperación completos siguen pendientes para producción. Esta edición es para ensayo; no equivale a adopción final.

## Registro

| Comprobación | Esperado | Resultado / observación de Wascar |
|---|---|---|
| Instalación New | `awaiting_reboot` después de HTTPS y backup | Pendiente |
| Reinicio | `postboot_verified` | Pendiente |
| Mi seguridad | Proveedor MFA disponible | Pendiente |
| Activación | Enrolamiento y confirmación del código | Pendiente |
| Siguiente login | Contraseña y segundo factor | Pendiente |
| Usuarios | Permisos de administración y estados correctos | Pendiente |

El coordinador conserva los hashes y resultados automáticos en `evidence/s1-20261029/installer15-codex/`. Este registro manual no altera resultados anteriores de Wascar.
