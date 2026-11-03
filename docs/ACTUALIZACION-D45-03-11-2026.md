# Servidor D actualizado · 03.11.2026

**Ya está disponible en [https://192.168.206.133:5443/](https://192.168.206.133:5443/).** Pulsa **Ctrl+F5** para cargar los archivos nuevos. Usa tu cuenta y autenticador habituales: no se han cambiado contraseñas ni restablecido MFA.

## Qué puedes ver

- Los seis routers FRITZ!Box/DrayTek y los diez repetidores FRITZ!, TP-Link, devolo y Telekom se han incorporado al servidor. Catálogo: **884 revisiones / 877 modelos comerciales distintos**, conservando los 506 seleccionados originalmente.
- En el selector del catálogo escribe **FRITZ**, **Fritzbox**, **AVM**, **DrayTek** o **Drytek**. Se filtra la lista desplegable; no hace falta recorrer todo el catálogo.
- Los repetidores se eligen al crear un **Dispositivo final en una sala**, dentro de la administración de la estructura del cliente. Busca **repetidor**, **repeter**, **Repeater**, **Verstärker** o la marca. Son objetos de sala; los de sobremesa no exigen una bandeja de rack. WiFi no se presenta como puerto de cable.
- En los racks, los datos secundarios están plegados, los nombres largos se ajustan y los equipos sobre soporte mantienen mejores proporciones. Puedes ampliar la vista sin cambiar medidas u ocupación. Los conectores siguen siendo interactivos.
- Puedes comparar los dibujos en los [routers](../VER-ROUTERS-ALEMANIA-01.html) y [repetidores](../VER-REPETIDORES-ALEMANIA-01.html) de revisión local; ahora esos cambios también están en D.

## Qué se conservó y qué se comprobó

La actualización se hizo sobre la misma instalación y base, con el mismo servicio, SID, certificados, dirección y material MFA. Se compararon **43 tablas de datos y seguridad** antes y después de migrar, con recuentos y SHA256 idénticos. No se repitió la carga de datos sintéticos.

Estado medido al actualizar: **50 clientes, 180 racks, 1561 equipos/objetos, 20650 puertos y 2202 conexiones**. Es el estado real previo a esta operación, incluidas las modificaciones que hubiera hecho Wascar; no se sustituyó por las cifras antiguas de la carga inicial.

El servicio está **Running/Auto**, con la misma cuenta estándar. HTTPS responde `ready`, esquema45, con validación TLS normal de Windows. Los bytes servidos de JavaScript y CSS coinciden exactamente con la interfaz nueva. El proveedor MFA está habilitado y la verificación con la cuenta efectiva del servicio conserva los hashes del material privado. El login TOTP personal después de actualizar queda para Wascar; Codex no ha pedido ni usado sus códigos.

Backup oficial previo completado y copia física completa con PostgreSQL detenido, además de certificados/material de recuperación y programa anterior, conservados en la gestión privada de D. Backup posterior45 completado con resultado0; tarea habilitada, Password/Limited y mismo servicio. La tarea de verificación del próximo arranque sigue habilitada. **No se ha reiniciado Windows para verificar postboot45**; el comprobante antiguo43 se conserva como antecedente.

## Registro técnico y límites

Aplicación completa45 y payload15 nuevos, con revisión independiente de inventarios, pins y operadores. La distribución contiene55 archivos de servidor y18 de frontend. Se actualizan coherentemente el contenido, staging y referencias de instancia, despliegue, instalación, perfil del servidor, configuración del servicio y backup.

La primera ejecución se detuvo antes de la parada por una dependencia auxiliar ausente del payload. La siguiente migró correctamente, pero el intercambio de la distribución protegida necesitó ajustar el acceso temporal a su raíz. La continuación terminó ese intercambio; su último tramo requirió convertir explícitamente el plan leído de JSON a Hashtable. Cada continuación se revisó y comprobó sobre el estado exacto. **No se volvió a ejecutar la migración ni se restauró la base**. Los intentos y las copias se conservan; no se ocultan como una actualización de una sola pasada.

Esta operación conserva el formato SQL legado de D; no convierte sus secretos al formato3 ni declara una recuperación portable MFA o un Restore45 ensayados. El instalador15 completo está preparado, pero su instalación limpia y Restore son recorridos diferentes. No volver a lanzar el actualizador43→45 sobre esta D, que ya está en45.

[Evidencia y revisiones](../evidence/s1-20261103/actualizacion45/RESULTADOS.md). Sin cambios en E, commits, push, publicación ni adopción automática. QA visual de Wascar y el resto del cierre continúan. Índice de cierre **14,76/100**, sin incremento por esta operación.
