# Dictamen independiente · F-02.02

03.11.2026 · Revisor `/root/audit_steps_5_7`, distinto del implementador y del ejecutor del ensayo. Contraste de fuentes y recibos públicos sanitizados, sin operar VM o leer credenciales. No se cambian el ledger o dictámenes anteriores.

## Decisión

**F-02.02 cumple su criterio literal. Recomiendo acreditar exclusivamente sus `5/8` puntos (0,625), una sola vez.** F-02.03 y F-02.04 quedan reservados a su evaluación posterior; no se cierra F-02 ni se afirma postboot14 o QA manual.

Criterio vigente:

> Actualizar operadores/fichas de acceso, diagnóstico y backup para no filtrar la clave ni depender de copiar un secreto ligado al host antiguo.

Las lagunas concretas de mi matriz previa —escritura administrativa real de la ficha y confirmación del transporte de backup sin perfiles privados— tienen ahora evidencia. No es necesario añadir una navegación manual de Wascar, abrir las contraseñas o repetir suites invariantes para dar por actualizado este circuito técnico.

## Matriz del criterio

| Parte pedida | Evidencia y contraste | Resultado |
|---|---|---|
| Operadores y ficha de acceso | El getter instalado14-r2 está validado; `viewerSha256=85609cac…` coincide con los bytes revisados y empaquetados. `metadataCardWritten=true`, hash de ficha `d76b7069…`, `cardContainsPassword=false`, sin credenciales impresas. El formateador previamente revisado sólo toma metadatos autorizados, no las contraseñas web/SQL, conexión completa o ciphertext. | Ya existe el positivo del writer administrativo y de su lectura de datos protegidos, no sólo una prueba del formateador en memoria. |
| Diagnóstico sin filtrar las claves | El exportador real devuelve `report_exported`, salida observada0, archivo de una entrada y comparación negativa contra ambas contraseñas actuales. No afirma adjuntar logs crudos o privados. Se reutilizan las validaciones/códigos finitos de la fuente ligada al paquete. | Recorrido operativo observado y coherente con la implementación revisada. La comprobación queda acotada al diagnóstico emitido y a esos controles, sin declarar ausencia universal de secretos. |
| Backup con el actor correcto | Backup inicial completo y tarea Password/Limited con resultado0, manifiesto y dump coincidentes. La sonda de la cuenta real del servicio confirma lectura de20 clientes, rol backup distinto capaz de SELECT y sin escritura/DDL; runtime sin DDL. `sidMatchesService=true`, salida del padre0 y sin credenciales impresas. | Compatibilidad CurrentUser y privilegios del circuito real acreditados; no se confunde el administrador de la sonda fallida con el actor previsto. |
| No copiar el secreto ligado al host antiguo | Entrada desde LEAO a E: PostgreSQL17.11 custom, manifiesto `b22c127b…`, dump306638 bytes/hash `05f6987b…`,20 clientes sintéticos y `noSourceDpapiOrSqlProfilesCopied=true`. El destino tiene UUID/SID propios, roles ligados al ID nuevo, manifiesto3 y cuatro privados. El backup nuevo en E tiene otro manifiesto/dump, verificados bajo su actor real. | La recuperación del circuito usa dump/manifiesto y genera credenciales locales nuevas; no depende de trasladar DPAPI o perfiles SQL del origen. |

## Recibos y coherencia del ensayo

Consulté:

- `restore14-input-receipt.json`: origen LEAO, destino E, hashes/tamaño/formato del backup y exclusión explícita de DPAPI/perfiles SQL. La copia por VMware Tools no se presenta como ejecución de una exportación GUI.
- `restore14-launch.json`: broker original, una sola instalación Restore; no lanzamiento interactivo manual del wrapper.
- `restore14-observed.json`: archivo de entrega `90f9660d…` —el14-r2 que revisé—, instalación `57822410-3b69-4542-a829-260152db9f17`, servicio de recuperación Running/Auto con SID propio no administrador, HTTPS normal ready43 y origen13 conservado. La ficha y el diagnóstico se ligan a esa instalación.
- `service-probe14-r2-sanitized.json`: salida0, mismo manifiesto de backup `a1a950db…`,307531 bytes de dump coincidentes con su manifiesto, runtime/backup de20 filas y restricciones de permisos descritas. Conserva hashes del material, no su contenido.
- Las revisiones previas `REVISION-ACL.md`, `REVISION-PERFIL-MFA2.md` y `REVISION-PAQUETE14-R2.md`: fuentes y enlace byte a byte ya comprobados por mí. No se repiten aquellas pruebas ni se atribuyen sus ejecuciones a la instalación nueva.

El broker del Restore reportó y observó **salida3, `awaiting_reboot`**. Se conserva tal cual: el0 de `restore14-launch.json` corresponde al lanzador, y el0 de las sondas a sus comprobaciones, no a una aceptación postboot del instalador. El recibo indica `rebootVerified=false`, `productAdopted=false` y `manualBrowserClaimed=false`. Login HTTP,20 nombres exactos y logout son comprobaciones automatizadas, no QA manual de Wascar.

## Intentos de arnés preservados

Leí los cuatro recibos previos, todos conservados como fallos, sin contarlos como pruebas satisfactorias ni nuevas instalaciones:

- Recolección1: intento de releer la ficha mediante un lector cuya lista cerrada sólo permite archivos privados específicos.
- Recolección2: `private_acl_required` al ejecutar la sonda SQL con el administrador en vez de la cuenta prevista.
- Recolección3: discordancia de datos por el tratamiento de la respuesta array en el arnés HTTP.
- Sonda de servicio1: `PropertyNotFoundException` al construir su snapshot de rutas.

La corrección declarada fue de arneses, sin alterar producto o ACL; el paquete final conserva las fuentes revisadas. No he reproducido esos intentos ni atribuyo a partir de sus mensajes una nueva falla del producto. La evidencia positiva posterior se evalúa por separado y bajo la cuenta correcta.

## Límites y atribución

Esta ronda no ejecuta pruebas nuevas: las operaciones nativas son del coordinador; mis pruebas previas de componentes e integridad están registradas en sus informes. No leí la ficha privada, el dump, perfiles, contraseñas o archivos de claves de E. Los hashes/booleanos se toman de los recibos sanitizados y se contrastan con el código y el artefacto ya revisados.

Quedan pendientes la evaluación de reanudación/Restore de F-02.03 y el cierre íntegro/revisión de F-02.04. El postboot real de13 no se traslada al destino14-r2. No se exige reiniciar Windows como condición nueva de F-02.02: su criterio no lo pide. No se habilita QA-168 por arrastre ni se cambia el resultado manual del usuario. D y F01 permanecen fuera de este crédito.

**Propuesta al coordinador:** marcar sólo F-02.02 cumplido con esta evidencia y el peso ya congelado, manteniendo los estados reales de los demás checkpoints. No modifiqué producto, cuentas, servicios, VM, ACL, certificados, DB, paquetes, ledger o métricas.
