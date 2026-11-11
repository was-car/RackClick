# Pruebas de Wascar — MFA en la VM C

**Esta guía sirve para acceder y probar la instalación actual de C.** Para instalar tú mismo en otro Windows limpio, guarda el [manual autónomo de instalación desde cero](PASOS-COMPLETOS-INSTALADOR10-WASCAR.md). Incluye carpetas, apertura de PowerShell, comandos, formulario, reinicio, primer login y MFA, sin depender de los accesos creados durante el ensayo.

29.10.2026. Instalador10, esquema15. Instalación, servicio automático, HTTPS, backup y reinicio verificados por Codex. Enrolamiento y segundo login probados por API con el proveedor Windows real, también después del reinicio. **Wascar comunica que probó MFA en su cuenta administrativa y que funciona satisfactoriamente.** Se registra su observación sin atribuirle cada caso detallado ni rellenar sus casillas. Los casos restantes conservan su estado.

Esta es una instalación nueva de laboratorio. Después del ensayo inicial se cargaron los clientes y el inventario del Full Backup original, por petición de Wascar, conservando su cuenta y MFA. Sigue la [guía de datos originales](QA-DATOS-ORIGINALES-MFA10-WASCAR.md) para verlos; las otras VM se conservan.

## 1. Abrir el acceso

1. Dentro de la VM **RackClick-W02-C-Manual**, busca en el Escritorio **RackClick-VERIFICAR-10-883e2f83.cmd** y ábrelo. Acepta el aviso de permisos de Windows.
2. En la parte inferior del panel pulsa **Acceso privado**. Se abrirá un archivo local con `username` y `password`.
3. El usuario de aplicación es **Wascar**. Usa la contraseña de ese archivo: es distinta de la contraseña de Windows. Consúltala localmente; no la pegues en el chat ni en tus observaciones.
4. En el mismo panel pulsa **Abrir RackClick**. También puedes abrir Microsoft Edge dentro de la VM y escribir **https://192.168.206.131:5443**. En el Escritorio está el acceso **Abrir-RackClick-MFA10.url**.
5. Inicia sesión. El certificado está confiado dentro de esta VM. El acceso desde otro equipo necesita su propia confianza de CA; para esta prueba usa el navegador del servidor.

## 2. Ver tu estado

1. Si la interfaz aparece en otro idioma, selecciona **Español** en el selector de idioma de la parte superior derecha. Espera a la confirmación del guardado.
2. En la barra lateral izquierda, baja hasta la zona de tu nombre de usuario. Pulsa **Mi seguridad**, situada antes de **Cerrar sesión**.
3. En el panel central debes ver tu cuenta, el estado del factor y el aviso de exención del administrador global. MFA debe estar disponible y el botón **Activar MFA** habilitado.

Codex no activó el factor de Wascar durante el ensayo inicial; después Wascar lo activó y probó satisfactoriamente. Conserva ese autenticador: no repitas el enrolamiento de una cuenta que ya lo tiene activo. Las cuentas sintéticas `QA-MFA10` y `QA-MFA10B` pertenecen al ensayo automático y tienen estados distintos; no necesitas utilizarlas para tu prueba.

## 3. Activar tu autenticador

1. En el panel central pulsa **Activar MFA**.
2. En el formulario que aparece debajo escribe **Tu contraseña actual**, la contraseña de aplicación que consultaste en Acceso privado.
3. Marca **Entiendo el efecto sobre esta cuenta y sus sesiones** y pulsa **Confirmar cambio**. Espera la confirmación del servidor.
4. Si vuelve al inicio de sesión, entra otra vez con Wascar y la misma contraseña. Si muestra **Iniciar sesión de nuevo**, pulsa ese botón.
5. Aparecerá la configuración del autenticador con un QR y una clave manual. Añádela a tu autenticador TOTP en el teléfono. Conserva ese registro en tu autenticador; no incluyas QR ni clave en informes o capturas compartidas.
6. Introduce los seis dígitos actuales y pulsa **Confirmar autenticador e iniciar sesión**.
7. Al entrar, vuelve a **Mi seguridad**: debe indicar factor activo y sesión verificada con MFA.

## 4. Comprobar un nuevo login

1. En la parte inferior de la barra lateral izquierda pulsa **Cerrar sesión**.
2. Vuelve a entrar con usuario y contraseña. Ahora debe aparecer el campo de código del autenticador.
3. Usa un código nuevo del teléfono, diferente del que acabas de confirmar, y pulsa **Verificar e iniciar sesión**.
4. Comprueba que entras y que **Mi seguridad** conserva el factor activo. Actualiza la página y vuelve a comprobarlo.

## 5. Ver la administración de usuarios

1. Con una sesión que haya completado MFA, abre **Usuarios** desde la barra lateral izquierda.
2. En la navegación de administración busca **Métodos de autenticación**. Selecciona primero el usuario objetivo en **Usuario seleccionado**.
3. Revisa que el panel central identifique exactamente a ese usuario antes de cambiar nada. El administrador necesita `security.manage` y una sesión MFA para administrar a otra cuenta.
4. Para tu propia cuenta utiliza **Mi seguridad**. La sección de otro usuario no debe permitir saltarse esta separación.
5. Como administrador global de Systemhaus puedes desactivar tu propio factor con las comprobaciones correspondientes. Los usuarios ordinarios, técnicos y administradores de clientes tienen45días; desactivar durante la gracia no reinicia su fecha límite. Para este primer QA basta comprobar activación y segundo login; no hace falta desactivar tu factor.

## Registro de tus resultados

Escribe **Pass**, **Not Pass** o **No probado** y una observación concreta. Puedes devolver este archivo editado. No se sobrescriben tus resultados anteriores.

| ID | Prueba | Resultado de Wascar | Observación |
|---|---|---|---|
| MFA10-01 | Abrir panel y consultar acceso privado | No probado | |
| MFA10-02 | Login de Wascar y disponibilidad de Mi seguridad | No probado | |
| MFA10-03 | QR/clave manual y confirmación del autenticador | No probado | |
| MFA10-04 | Nuevo login con contraseña y código nuevo | No probado | |
| MFA10-05 | Estado persistente después de recargar | No probado | |
| MFA10-06 | Usuario seleccionado y Métodos de autenticación | No probado | |

Si una prueba falla, anota el paso, el texto del error y la hora aproximada. Conserva el estado para revisarlo: el snapshot **HTTPS/MFA 00** sigue disponible, pero revertirlo retiraría esta instalación de ensayo. La recuperación portable de claves y el procedimiento de emergencia completo siguen pendientes para producción.
