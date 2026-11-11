# Paso 19 · fases seguras de rotación MFA

09.11.2026 · **F-06.01 completado como especificación, con revisión independiente favorable.** D y E se conservan. No necesitas ejecutar comandos ni entregar claves, sobres, contraseñas o códigos.

El [protocolo de rotación v1](PROTOCOLO-ROTACION-MFA-v1.md) concreta el orden ya acordado en D2:

1. Preparar mantenimiento exclusivo, journal y bloqueo persistente del arranque.
2. Crear, proteger, persistir y comprobar la clave nueva antes de que pueda usarla ningún factor.
3. Publicar un anillo aditivo con la activa anterior, conservando las versiones necesarias y comprobando el sobre externo.
4. Recifrar los mismos secretos TOTP en una transacción PostgreSQL, con un testigo de commit y sin reiniciar estados, antirreplay o política de gracia.
5. Publicar la nueva activa, comprobar DB/material y sólo entonces permitir el arranque controlado.
6. Conciliar una interrupción por hechos de DB/material; después de un commit, completar hacia delante. No confiar en el exit de un proceso ni borrar versiones antiguas por terminar la rotación.

Se reutilizan anillo, proveedor, cifrado y evidencia F04/F05 existentes. **Esto especifica la operación; no la implementa o ensaya.** Las versiones antiguas se conservan, incluso si el recifrado actual ya no las usa: los backups retenidos pueden necesitarlas.

[Matriz del criterio](../evidence/s1-20261109/f06-01-fases/MATRIZ-CRITERIO.md) · [Resultado y límites](../evidence/s1-20261109/f06-01-fases/RESULTADOS.md). F-06 completo, retirada/inventario de versiones, fallos controlados, rotación operativa y aceptación siguen abiertos. El siguiente paso es **20 / F-06.02**.

[Dictamen independiente](../evidence/s1-20261109/f06-01-fases/review/DICTAMEN-F0601.md). Se acredita únicamente **5/8 de punto**: el índice del cierre restante pasa de **19,13 a 19,76/100** (exacto 3319/168). No es porcentaje global del producto ni aprobación para ejecutar una rotación.
