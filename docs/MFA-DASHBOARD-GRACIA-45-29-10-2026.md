# MFA en el dashboard · 29.10.2026

**Implementado y probado en desarrollo. La VM instalada todavía no se ha actualizado.**

## Lo que tendrás en la interfaz

- En el menú lateral izquierdo: **Mi seguridad**, cerca del usuario y de Cerrar sesión. Permite consultar estado y fecha límite, activar MFA, desactivarlo cuando la política lo permita y restablecer el autenticador propio.
- Bajo la ruta de navegación: aviso con los días restantes y **Gestionar mi MFA**. Se actualiza desde el servidor al entrar, al recuperar el foco y cada minuto; el navegador no decide la autorización.
- En **Usuarios → Usuario seleccionado → Métodos de autenticación**: estado y acciones del destino. El administrador no ve su QR ni su clave. Las acciones sobre otros exigen permiso global `security.manage` y una sesión con MFA completado; la cuenta propia se gestiona por Mi seguridad y contraseña actual.
- Una operación sólo se presenta como guardada tras confirmar el servidor. Una respuesta incierta conserva la solicitud, sin contraseña; permite consultar el resultado original. Recuperar un recibo antiguo después de volver a entrar no causa un bucle de cierre de sesión.

Se mantienen RC9, Click-Click y EN/DE/ES. Se toma la organización de métodos personales y administrativos de Entra, sin conectar RackClick a Microsoft Entra/Active Directory ni copiar su diseño.

## Política confirmada por Wascar

**45 días** para usuarios, técnicos y administradores de clientes. Nuevas cuentas desde creación; existentes desde activación persistida de la política. Activar voluntariamente obliga a completar el factor antes del siguiente acceso. Desactivar durante la gracia no mueve la fecha límite. Al vencer, el servidor rechaza contraseña sola y sesiones anteriores sin MFA.

El administrador global del Systemhaus está exento y puede desactivar su propio factor también después del plazo. La exención se comprueba con capacidades globales `systemhaus.manage` y `security.manage`; el nombre de un usuario o grupo no concede ese rol. La administración de un cliente no lo hereda.

La base anterior no guardaba fecha de creación de cuenta: la nueva **SQL015 aditiva** registra las futuras y conserva NULL para las antiguas. La migración no activa la política. El arranque con proveedor Windows real validado registra la activación una vez; reiniciar no reinicia los 45 días.

## Verificación real

- Compilación SDK10.0.401, dependencias fijadas: cero errores y advertencias.
- Regresión del proyecto de calidad, excluidos los dos escenarios Browser separados: **378 PASS, 0 fallos, 1 omitida por Docker**. Incluye gestión, vencimiento, permisos, CSRF/Origin, conflictos, idempotencia y rollback con PostgreSQL17.11 nuevo.
- **1 recorrido Edge/Kestrel/PostgreSQL PASS**, ocho etapas: aviso35 días, exención/idiomas, activación propia y QR, recibo histórico, activación por administrador y revocación, enrolamiento del destino, restablecimiento y siguiente login TOTP. Cero excepciones JavaScript.
- **101 pruebas Node PASS**, incluidas las48 nuevas;35 pruebas de la guía QA PASS.
- Revisión independiente favorable acotada,12 focos propios y un foco adicional de respuesta perdida. El revisor no ejecutó PostgreSQL o la VM.

El navegador usa HTTP loopback y un proveedor sintético registrado sólo en el host de prueba; PostgreSQL usa rol DML sin DDL. No equivale a la prueba HTTPS con el proveedor real y la cuenta del servicio en tu VM.

## QA y siguientes pasos

Los casos **QA-127 a QA-131** contienen ubicaciones, botones, acciones y resultados. La [guía QA](../GUIA-QA-WASCAR.html) los mantiene bloqueados/no disponibles hasta recibir una candidata instalada adecuada. No se alteraron tus resultados anteriores.

Falta integrar y comprobar la distribución/instalador de esquema15, custodia real, recuperación del último administrador y ensayo de la candidata completa antes de habilitarlo en QA. Los paquetes históricos de esquema14 siguen intactos: no copiar DLLs o SQL sueltos sobre la instalación existente.

Tus observaciones de racks primero e información secundaria plegable, y la reorganización general de usuarios/grupos, están [registradas](OBSERVACIONES-DASHBOARD-WASCAR-29-10-2026.md); no se presentan como implementadas en esta tanda.

[Evidencia, intentos y límites](../evidence/s1-20261029/mfa-dashboard-codex/RESULTADOS.md). El cierre técnico de F-07.04 se registra bajo una línea base v2 explícita por tu nueva política, sin cambiar pesos ni denominador. F-07.05 y la entrega completa siguen pendientes.

**Índice de cierre del trabajo restante:8,63/100**, antes8,13;21/280 subpasos. No es el porcentaje global del producto. [Cambio explicado](../evidence/s1-20261029/mfa-dashboard-codex/REBASE.md).
