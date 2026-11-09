# Paso17 · recuperación portable de claves MFA

03.11.2026 · **F-05.04 completado técnicamente, con revisión independiente favorable.** D se conserva sin comandos de invitado ni cambios de datos/MFA.

Se recuperó un anillo completamente sintético desde Windows LEAO hacia Windows Server E, con identidades físicas distintas y adaptación explícita de la instalación. La cuenta estándar real del servicio de E pudo usar la clave activa7 y la retirada1 para descifrar dos factores con sus IDs originales de Systemhaus/usuario/versión como AAD.

Pasaron los siete casos del destino: cuatro rechazos sin crear almacén, recuperación, lectura bajo token efectivo y rechazo de importación duplicada conservando el almacén. También se rechazaron seis AAD incorrectas y una versión inexistente; seis objetivos deniegan escritura y WRITE_DAC, cero concesiones o inconcluyentes.

Dump PostgreSQL sintético, sobre cifrado y contraseña permanecen separados. Se comprobaron la retirada de ambas tareas temporales, la entrada privada con contraseña y las copias temporales del sobre en E. Los servicios existentes mantienen sus procesos/imagen/fecha de inicio. El primer intento falló en el harness antes de importar; se conservó y se corrigió con una segunda ronda explícita revisada.

[Resultados y límites](../evidence/s1-20261103/f05-04-portable/RESULTADOS.md) · [Dictamen independiente](../evidence/s1-20261103/f05-04-portable/review/DICTAMEN-F0504.md).

Se acredita sólo **1/2 punto**: **18,13→18,63/100** del cierre restante (exacto1565/84),40checkpoints cerrados/240sin cierre. No es un porcentaje global nuevo del producto ni aceptación final.

**Sigue18/F-05.05:** cerrar el resultado integrado con sus dependencias. El ensayo portable offline no acredita RestoreDB/login/TOTP del usuario, journal/fence de D2 o integración en el instalador. [Trabajo pendiente trazado](F05-RECUPERACION-INTEGRADA-PENDIENTE.md). No necesitas ejecutar nada ni proporcionar claves para este paso terminado.
