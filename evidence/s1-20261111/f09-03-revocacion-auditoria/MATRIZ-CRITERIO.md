# Matriz F-09.03 · paso31

| Criterio | Implementación/evidencia | Límite |
|---|---|---|
| Revocar sesiones/desafíos | Reutiliza Apply F0902; sesiones eliminadas, desafíos verify/enroll incluidos expirados consumidos; invocaciones anteriores rechazadas | Componentes/backend, no host reanudado |
| Retirar códigos anteriores | Consumo en la misma transacción; intento con un código real previamente generado y desafío anterior rechazado | No vuelve a probar toda la UI de códigos F08 |
| No afectados | Material, sesiones, desafíos/códigos e inventario/identidades/gracia de los demás conservados | Fixture sintético, no Demo50 |
| Auditoría sin secretos | Witness dedicado con19campos cerrados, autoridad/SID Windows, identidades, UUID, versiones, hashes/conteos y fecha; no appactor inventado | No es historial web ni éxito de servicio/usuario |
| Atomicidad | Fallos de INSERT/UPDATE del witness y nueve supresiones/corrupciones inducidas: rollback de seguridad/archivo/witness | No afirma esos triggers en producción ni resistencia a un dueño PG hostil arbitrario |
| Primera aplicación | Recuentos de archivo/pending/finish y validación fresh del testigo/hashes antes del commit, incluido cero factores | No transacción conjunta disco/DB |
| Último global | Una sola cuenta global activa, grupos/capacidades/gracia conservados; contraseña→enroll, código inválido sin sesión; TOTP nuevo→sesión nueva/administración; last_admin_required | SID/trust de fixture, no operador Windows elevado ni servicio real |
| Reentrada | Mismo UUID no duplica witness/revisión y publicación repetida conserva el registro | Reentradas sin actividad posterior; nuevas escrituras exigen conciliación |
| Fronteras | Componentes, HTTP restringido y F08 pertinentes sobre binarios finales; fuente/SQL047/Program/dependencias previas conservados salvo adaptador DB mínimo | F0904/.05, aceptación y observación Edge siguen pendientes |

`FOCOS.json` y el dictamen distinguen ejecuciones nuevas del coordinador/revisor, rojo y evidencia previa reutilizada. No se suman pruebas o variantes como nuevos puntos.
