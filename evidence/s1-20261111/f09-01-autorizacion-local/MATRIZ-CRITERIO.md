# F-09.01 · autorización local, alcance y prueba

Literal: «Autorizar sólo operador local SYSTEM/Administradores; sin web anónima ni bypass password-only».

| Condición | Implementación y verificación | Límite |
|---|---|---|
| Entrada local identificada | Rama `--mfa-emergency-recovery` en Program antes de `CreateBuilder`, material SQL y listener | Modo exacto y stdin redirigido; aún sin protocolo de transición |
| SYSTEM o Administradores elevados | `WindowsIdentity`, SID SYSTEM conocido, pertenencia efectiva por WindowsPrincipal y TOKEN_ELEVATION consultado por identificador |64 casos de política son simulaciones; no positivo elevado/SYSTEM real |
| Ninguna autoridad por impersonación | Captura rechaza identidad de suplantación antes de evaluar SYSTEM/grupos | Prueba nativa con token propio y restauración del hilo; no modificación de privilegios |
| Sin elevación por app/JSON/env | La CLI sólo captura token real, no obtiene la decisión pura interna de DI/configuración; test de claims y proceso con variables falsas | Rol global web válido sólo obtiene404 en las cuatro rutas inexistentes probadas |
| Elevación desconocida falla cerrada | Fallo de consulta o longitud inesperada no autoriza; errores esperables de identidad sanitizados | Rama de fallo nativo se cubre en la política; no se provoca un fallo real del kernel |
| No se alcanza host/SQL con emergencia | Argumentos extra y siete conflictos rechazan; proceso con conexión/origen/Enabled inválidos devuelve JSON constante sin inicializar host | La salida de conflicto conserva el contrato histórico; no prueba todos los modos del servidor entero |
| Sin web anónima | No se registra endpoint nuevo; cuatro POST anónimos→401 y global autenticado→404; snapshot de diez tablas invariable | Prueba de esas rutas y revisión de fuente, no exploración exhaustiva de toda URL posible |
| Ningún bypass password-only durante recuperación | Reutilización de F0802 sobre el build nuevo: dos casos ordinario/global sólo acceden a API después de confirmar factor nuevo | Claves DI sintéticas y rol SQL restringido; no servicio/TLS/DPAPI instalados |
| No confundir autorización con recuperación | Salida1 aun para operador autorizado: `transition_unavailable`, operationsApplied0/sessionGrantedfalse | F0902–.05, anillo, factores, revocación/auditoría y pérdida total no se acreditan |
| Revisión independiente | [Dictamen](review/DICTAMEN.md), ejecución propia y sondas de entrada aislada | No aprobación de un instalador ni aceptación de Wascar |

## Continuidad

`RecoveryAdministrator`/D14-05 se conservan para Restore. No preparar anillo v1 sobre una instalación que ya tuvo factores, no desactivar el proveedor como reparación y no levantar web sin protección: las condiciones del paso30 se conservan en D2. La autoridad local se volverá a comprobar al implementar la operación real; la salida de esta compuerta no es una credencial o recibo transferible.

Los seis hitos del resultado completo F-09 y los checkpoints.02–.05 quedan pendientes. Esta matriz sólo permite acreditar.01 tras el dictamen y sin añadir peso por casos, sondas o builds.
