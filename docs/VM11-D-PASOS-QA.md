# RackClick11 en D: qué hacer ahora

02.11.2026. La instalación técnica New está comprobada al 100% tras el reinicio: `postboot_verified`, servicio automático, HTTPS y backup programado. Esto no es aceptación final del producto ni resultado manual de Wascar.

1. En VMware selecciona **RackClick-W02-D**. No necesitas reinstalar, crear carpetas ni abrir PowerShell para entrar.
2. En el Escritorio abre **RackClick.url**, o abre Edge y escribe **https://192.168.206.133:5443**. Esa dirección corresponde a la red actual de D.
3. Para consultar la contraseña nueva, abre **RackClick-VERIFICAR-11-6ca767fa.cmd** en el Escritorio, acepta el aviso de administrador y pulsa **Acceso privado** en la parte inferior del panel. El usuario de aplicación es **Wascar**. No compartas ese archivo ni su contraseña.
4. Inicia sesión según el estado de MFA que tú elegiste. Wascar lo activó y después lo desactivó para probar el cargador; Codex conserva esa elección. Puedes volver a configurarlo desde Mi seguridad. El cargador02 ya superó una verificación MFA nativa con otra cuenta sintética, sin cambiar tu factor.
5. Los **50 clientes ya están cargados y verificados**. Pulsa F5 y, en la barra izquierda, abre Todos los clientes. Hay180 racks,1.563 equipos/objetos,20.665 puertos y2.207 conexiones. No vuelvas a ejecutar Cargar50 sobre D: exige servidor vacío. Se retiró el cliente manual anterior porque autorizaste limpiar los datos de prueba. [Corrección y entrega02](CARGADOR-DEMO50-02.md).
6. Abre **QA-CIERRE-CANDIDATA11.html** del Escritorio. En la parte superior escribe la URL de D y confirma que pruebas la candidata11. Despliega cada caso: contiene los botones/campos y el resultado esperado. Marca Pass, Not Pass o Bloqueado según lo que hayas probado; las pruebas técnicas no rellenan tus respuestas.
7. Al terminar pulsa **Guardar mis resultados JSON** en la parte superior y entrega ese archivo. Las observaciones no deben contener contraseñas, códigos o QR. Los casos de lector/técnico requieren esas cuentas: si faltan, marca Bloqueado y se preparan aparte.

Los datos no incluyen usuarios ni factores. La carga usa comandos de la API; la limpieza local del cliente anterior fue una operación autorizada distinta, con transacción y revisión. La cuenta QA-MFA11 se creó sólo para verificar el flujo MFA del cargador y no tiene permisos globales.

Para una instalación futura desde cero, el manual completo sigue en [INSTALADOR11-WINDOWS43.md](INSTALADOR11-WINDOWS43.md) y dentro del ZIP. Adenda al paso02.7: **marca** la casilla de confianza de CA; no presupongas que viene marcada. El ZIP11 permanece intacto.

Pendientes separados: QA manual, carga de datos en D, recuperación portable/emergencia/rotación MFA, importación y backup desde el dashboard, y condiciones de redistribución. Catálogo seleccionado506/506; índice acreditado de cierre pendiente9,76/100, sin nuevo porcentaje global.
