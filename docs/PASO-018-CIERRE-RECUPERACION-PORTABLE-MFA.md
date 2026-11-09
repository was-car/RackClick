# Paso18 · cierre técnico de recuperación portable MFA

03.11.2026 · **F-05.05 completado técnicamente, con revisión independiente favorable.** D y E se conservan sin comandos de invitado ni cambios de datos/MFA.

Se restauró una base de aplicación45 completa en un laboratorio PostgreSQL17.11 nuevo, con roles nuevos y claves recuperadas mediante el proveedor Windows real. Se comprobó la igualdad de todas las filas públicas antes de los cambios administrativos previstos y se conservaron ambos factores, IDs y versiones1retirada/7activa.

**8/8 casos pasan, sin omisiones:** login de los dos usuarios con su TOTP conservado, desafío sin acceso a API, sesión/CSRF nuevos, cierre y replay rechazado; contraseñas/material/AAD/TOTP incorrectos no conceden autoridad nueva. El código real de recuperación revoca sesiones/desafíos del backup. Roles runtime noowner/nosuper/sinDDL y catálogos globales sólo lectura. El origen permanece invariable.

Los endpoints y middleware son de Program; HTTP usa TestServer en memoria con identidad Windows LAB declarada. La prueba de otroWindows y token real del servicio ya está en F-05.04 y no se repite. No se declara instalador, TLS de red, servicio/reinicio o adopción por este ensayo.

[Resultado y límites](../evidence/s1-20261103/f05-05-cierre/RESULTADOS.md) · [Dictamen independiente](../evidence/s1-20261103/f05-05-cierre/review/DICTAMEN-F0505.md) · [Matriz de cierre](../evidence/s1-20261103/f05-05-cierre/MATRIZ-CIERRE.md).

Se acredita sólo **1/2 punto**: **18,63→19,13/100** del cierre restante (exacto1607/84),41checkpoints cerrados y239sin cierre. Los checkpoints técnicos F-05 quedan completos; implementación operativa, candidata integrada y aceptación final conservan sus hitos pendientes. No es porcentaje global nuevo del producto.

Sigue **19/F-06.01**: especificar y conciliar las fases de rotación/coherencia disco–PostgreSQL antes de implementarlas. El coordinador/fence/journal y el Restore operativo mantienen sus criterios; no necesitas ejecutar nada para este paso18 terminado.
