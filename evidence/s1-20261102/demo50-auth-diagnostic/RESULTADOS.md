# Demo50 en D: compatibilidad MFA, limpieza autorizada y carga completa

02.11.2026. **Resultado final:50 clientes cargados y verificados en D**, con el cargador02; backup programado posterior completado. Instalador11, aplicación, servicios y otras VM conservados. Sin commits/push/adopción.

## Fallo y corrección

La salida original de Wascar indicaba cero clientes/comandos y un rechazo HTTP genérico después de pedir TOTP. No conservó ruta/estado/código del rechazo. No se atribuye a un código TOTP equivocado: esos datos originales faltan.

Se reprodujo un defecto suficiente para impedir el flujo: CookieContainer de .NET Framework/PowerShell5.1 descartaba la cookie del desafío, porque su Path es hermano del endpoint de login. Código/CSRF correctos, cookie ausente, verificación401. Las pruebas anteriores reemplazaban la función HTTP en ese recorrido y no lo detectaban. Se reutilizó la adaptación ya existente del ensayo nativo10; investigación oficial registrada antes de modificar esa parte.

La fuente final422a8996…729a importa únicamente la cookie de desafío validada del mismo origen, conservando Path/HttpOnly/SameSite/Secure en HTTPS. Rechaza Domain, cookies extra o atributos ambiguos. Añade un diagnóstico cerrado de cuatro campos, sin valores de cookies, cuerpos, cabeceras o secretos. Mantiene servidor vacío, autorización, TLS normal y cero reintentos automáticos. No se cambia C# ni política MFA.

## Comprobaciones distintas, sin sumar como una ejecución

- Implementador:31/31 pruebas focales PASS, incluidas11 variantes negativas de cabecera y flujo HTTP real. Rojo sobre4520 exacto y verde final, más intento fallido del fixture oversized, conservados en worker/ronda2 y su antecedente.
- Revisión del coordinador: diff, límites/atributos, flujo HTTP independiente con cookies/CSRF reales y confirmación rechazada antes de escribir. Primeros intentos fallaron por el entorno PSModulePath del fixture y después reprodujeron la cookie ausente; se conserva el primer FAIL. El foco final pasa. Es HTTP loopback sintético, no TLS ni criptografía MFA del producto.
- Nativo D: QA-MFA11 creada separadamente, enrolada y verificada con el servicio Windows/DPAPI real, TLS normal: login202→verify200→me200→rechazo esperado por falta de permisos globales→logout204. Cero comandos de inventario. La credencial/semilla sintéticas quedan privadas; no se usa el factor de Wascar.
- Wascar confirmó que él desactivó su propio MFA para probar. La observación nativa inicial de cookie devolvió login200 por esa elección: **no demuestra descarte de cookie en aquel instante**. La lectura inicial de clientes se repitió usando el JSON real y confirmó un cliente, que Wascar confirmó haber creado manualmente. El factor de Wascar no fue alterado por Codex.

## Limpieza autorizada

Wascar pidió explícitamente eliminar los datos de prueba para cargar la demo. Se limitó a la instancia D bbd2b6c2-abaf-4964-8c12-cf8f0c4af2aa y su DB validada, mediante identidad owner local separada. No hay endpoint de borrado de cliente y no se presentó como una función nueva del producto.

Preview real:1cliente/1rack/5equipos/106puertos/2conexiones. SQL estático, guardias de ámbito/versión/dependencias,16 DELETE hijos→padres más cascada existente de extremos, revisión independiente y transacción. Dryrun hizo ROLLBACK y conservó exactamente esos conteos. Apply se ejecutó una sola vez: commit/exit0, cero clientes, testigo de usuarios/grupos/permisos globales/sesiones/MFA igual antes del commit. Se conservan sólo metadatos/SQL/recibos públicos, no contraseñas ni dump. Diario local de autorización y auditoría en DB; revisión en reset-review/.

El intento de recoger el log HTTP antiguo no pudo copiar el archivo activo. Se conserva ese resultado como límite; no se aflojaron ACL ni se cambiaron servicios para leerlo.

## Carga y backup

Una nueva carga controlada, posterior al commit que dejó cero clientes, aplicó **2.553 comandos por API** en185,681s:50clientes,66sitios,88edificios,226salas,180racks,1.563equipos/objetos,2.869grupos,20.665puertos y2.207conexiones. El cargador comparó todas las colecciones y relaciones contra el plan, con UUID nuevos. `securityImported=false`, sin transacción global ni reanudación ciega.

Se utilizó la configuración de acceso vigente que Wascar eligió para su administrador global; esta ejecución completa no pidió TOTP. La prueba MFA nativa anterior es otra ejecución y otra cuenta, sin otorgarle permisos globales para cargar datos.

Tarea oficial de backup lanzada después de la carga:scheduled_backup_complete, LastTaskResult0/Ready, manifiesto2ab857da…21b5d. Dump y credenciales permanecen privados. No acredita Restore con factores MFA, sobre portable, emergencia o rotación.

## Entrega y continuidad

Parche local RackClick-Cargar-Demo50-02.zip,6entradas/1.920.706bytes, SHA7e743873abbde9ca4ce2eba0846f629024425519adf6c0a4af3ff03201fb62c2. Plan original a3b44a37…f423a y ZIP11 f090b56e…67b0 intactos. El acceso Cargar50 del Escritorio pasa al cargador02, pero D ya está poblada y no debe relanzarse. Guía/QA-167 actualizadas, respuestas personales y demás casos conservados; datos listos para F5/QA visual.

Código/helper revisados por alguien distinto del implementador; limpieza con revisión independiente separada de las acciones del coordinador. El revisor no accedió a VM, DB o credenciales. Sin adopción ni nuevo porcentaje global. Catálogo506/506, datos50/50; índice acreditado9,76/100 intacto, QA final pendiente.
