# Cargador Demo50 · corrección02

02.11.2026. La carga de los50 clientes ya terminó en D con `demo50_loaded_verified`:2.553 comandos API,180 racks,1.563 equipos/objetos,20.665 puertos y2.207 conexiones. El cargador contrastó todas las colecciones e identidades remapeadas de cada cliente. No lo ejecutes otra vez sobre esa instalación poblada.

## Corrección

PowerShell5.1 usa el CookieContainer de .NET Framework, que descarta una cookie emitida desde `/auth/login` si su Path apunta al hermano `/auth/mfa`. El navegador sí acepta ese contrato. Se reprodujo el fallo con código y CSRF correctos, pero cookie ausente, y se reutilizó la adaptación del ensayo nativo10.

El cargador conserva únicamente RackClick.MfaChallenge del mismo origen, con Path exacto, HttpOnly, SameSite=Strict y Secure en HTTPS. Rechaza cookies extra, Domain o atributos inválidos. No cambia el servidor ni su política MFA. Microsoft documenta la diferencia de [tratamiento de rutas](https://learn.microsoft.com/en-us/dotnet/core/compatibility/networking/5.0/cookie-path-conforms-to-rfc6265) y la API [CookieContainer.SetCookies](https://learn.microsoft.com/en-us/dotnet/api/system.net.cookiecontainer.setcookies).

Además, un rechazo devuelve `httpFailure` con método/ruta cerrados, estado HTTP y código permitido. No devuelve cuerpos, mensajes arbitrarios, cookies, cabeceras, contraseñas o TOTP. El logout de limpieza no sustituye el fallo inicial. Se conserva la prohibición de reintento automático y la guarda de servidor vacío.

## Entrega y comprobaciones

- [RackClick-Cargar-Demo50-02.zip](../RackClick-Cargar-Demo50-02.zip),1.920.706 bytes/6 entradas. SHA256 `7e743873abbde9ca4ce2eba0846f629024425519adf6c0a4af3ff03201fb62c2`.
- Script `422a89964ceabbc15db5f379dd33178a9b0d6fac91814981ef52a4b50b1b729a`; plan original `a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a`. Datos y ZIP11 originales intactos. No necesita instalar otro PowerShell ni dependencias.
-31 pruebas focales del implementador PASS; revisión y flujo HTTP propio del coordinador, con cookies/CSRF reales de un servidor sintético. Los intentos fallidos de los fixtures se conservan.
- Prueba nativa en D con QA-MFA11: proveedor DPAPI del servicio real, TLS normal, login202→verificación200→me200 y rechazo esperado por falta de permisos globales. Cero comandos de inventario. La prueba no usa el factor de Wascar.
- Wascar confirmó que desactivó su propio factor para probar. La carga50 posterior usa su configuración de acceso vigente; Codex no cambió ese factor. La prueba MFA y la carga completa son ejecuciones distintas.
- A petición explícita de Wascar se retiró el cliente manual anterior y su inventario dentro de una transacción local revisada:1 rack,5 equipos,106 puertos y2 conexiones. Dryrun con rollback y commit real registrados; usuarios/grupos/globalgrants/sesiones/MFA conservados por testigo. No es una nueva función de borrado del producto.

Para otra instalación vacía43, verifica el SHA externo, extrae este ZIP en una carpeta nueva y abre CARGAR-50-CLIENTES.cmd. Introduce URL HTTPS, usuario global, contraseña y un TOTP nuevo si se solicita. Confirma CARGAR 50 CLIENTES SINTETICOS y espera el resultado. No mezclar con datos existentes ni relanzar tras un resultado incierto.

[Evidencia, revisión y límites](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md). Falta la QA visual de Wascar; no se declara adopción, recuperación portable MFA ni cierre global. Índice acreditado9,76/100 sin cambio automático.
