# MFA en el navegador · primer flujo completo · 27.10.2026

El desarrollo permite configurar un autenticador desde el primer login y usar el segundo factor en los siguientes. El recorrido funciona en Edge con el servidor real y PostgreSQL de laboratorio. La instalación existente de Wascar no se ha actualizado ni tiene esta función habilitada.

## Qué se implementó

- Tras una contraseña válida, un desafío de enrolamiento o verificación abre un cuadro central. El desafío no se interpreta como sesión ni autoriza la API.
- La configuración empieza sólo al pulsar **Configurar autenticador**. Muestra un QR generado localmente y una **Clave de configuración manual** desplegable. No se envía el secreto a un servicio QR externo ni se guarda en localStorage/sessionStorage.
- El usuario confirma seis dígitos. Sólo la respuesta confirmada del servidor, seguida de `/me`, establece la sesión. Un código incorrecto permite corregirlo; una respuesta incierta obliga a volver al login, sin repetir automáticamente la creación del factor.
- En los siguientes accesos se solicita el código, sin mostrar otra vez el secreto. Cancelar o recargar descarta el estado temporal. EN/DE/ES disponibles dentro del cuadro, sin depender de guardar preferencias autenticadas.
- La firma de `api.login(): Promise<Session>` se conserva para sus trece consumidores de reautenticación. El cuadro modal bloquea la interacción con el fondo. La revisión corrigió la suspensión de preferencias que invalidaba el alcance de una reautenticación.

## Qué se ejecutó

- **38/38 pruebas Node:** API existente (16), desafío MFA (10), mensajes (8), QR (4), sin omitidas.
- **1/1 prueba de integración con navegador real:** Edge 156.0.4314.42, Kestrel, PostgreSQL 17.11 nuevo, esquema 14 y cuenta de ejecución DML sin DDL. Incluye enrolamiento sin autoridad, EN/DE/ES, rechazo de código incorrecto, confirmación, acceso a clientes, logout, login con verificación y recarga del desafío sin sesión.
- Build Release con SDK fijado 10.0.401: cero errores y advertencias. Frontend con Node 24.21.0/esbuild 0.25.10 existentes. Publicación de frontend sólo en copia privada.
- Revisión de seguridad independiente por fuente y 22 pruebas Node. No se atribuye al revisor la ejecución PostgreSQL/navegador del coordinador.

La prueba usa un proveedor de clave **sintético, registrado sólo en DI del host de pruebas**, y HTTP loopback de desarrollo. No acredita el token del servicio Windows, HTTPS productivo, recuperación administrativa, los trece cuadros de reautenticación por GUI ni escaneo físico del QR con teléfono. El laboratorio nuevo quedó detenido.

## Reutilización

Se reutilizaron rutas, cookies, CSRF y transacciones ya existentes de RackClick. QR: [Nayuki v1.8.0](https://github.com/nayuki/QR-Code-generator/tree/720f62bddb7226106071d4728c292cb1df519ceb), MIT, commit fijado y fuentes/aviso incluidos; adaptación ES module separada. No cambian versiones de paquetes ni backend de producto. El build comprueba los hashes del original y del módulo generado; conserva el aviso MIT dentro del JavaScript distribuido.

## Qué falta para probarlo en tu servidor

1. Cerrar la lectura del almacén con la identidad real del servicio (L2l02, trabajo separado de Claude).
2. Integrar la custodia y el flujo web en una candidata identificada; comprobarla con HTTPS, cuenta restringida y recuperación. No activar por defecto en tu QA actual.
3. Entregar esa candidata y habilitar los casos QA-124 a QA-126. Hoy figuran **Bloqueados / no disponibles** para evitar probar una función que aún no está desplegada.

La revisión de contrato acredita sólo **F-07.02, 0,50 puntos**. El índice de cierre del trabajo restante pasa de **7,63 a 8,13/100** (20/280 subpasos). Esto no es el porcentaje global del producto. F-07.04/.05, F-04 y la adopción final continúan pendientes.

[Evidencia y límites](../evidence/s1-20261027/mfa-gui-codex/CIERRE.md). Sin commits, push, cambios en VM, servicios instalados ni bases existentes.
