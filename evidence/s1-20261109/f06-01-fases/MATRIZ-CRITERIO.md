# Matriz de criterio · F-06.01

09.11.2026. Criterio congelado: «Especificar fases: persistir/verificar clave nueva antes de usarla, conservar versiones requeridas, reenvolver factores y publicar anillo coherente». Peso existente: 5/8. No se agregan pasos ni pesos.

| Parte del criterio | Especificación y comprobación documental | Evidencia de funcionamiento que no se atribuye a este lote |
|---|---|---|
| Persistir/verificar antes de usar | Protocolo §§2–4: key_staged → additive_published → material_ready; R+ conserva a activa, n retirada y legible; sobre externo/durabilidad exigidos antes de DB. | Crear un almacén ya está cubierto por F04. Falta publicar un anillo existente y ensayar la persistencia del coordinador. |
| Conservar versiones | §§2,4,6: K ∪ U ∪ B, sin omitir disabled/pending ni backups; no borrar en verified, cupo/colisión/versión ausente detienen. | F-06.02 no se cierra: falta censo operativo y prueba de retirada. |
| Reenvolver factores | §5: mismo TOTP, AAD antigua/nueva, nonce nuevo; sólo cambia cipher/key_version; conservar antirreplay/estados/política; una transacción con testigo y revocaciones explícitas. | Open/Seal y factores versionados ya existen; no se ejecutó recifrado real ni se cambió SQL. |
| Anillo coherente | §§3–6: DB commit testimoniado antes de Rf; guard/fence antes de listener; comparación de identidades/material, no sólo nombres o exit. | Proveedor/anillo actuales reutilizables; publicador/fence/guard/testigo futuros aún ausentes. |
| Commit incierto | §6: confirmar fin de transacción/DB primaria y testigo ligado; presente → terminar hacia delante; ausente no basta para rollback; desconocido → fence. | F-06.03 conserva inyección de caídas y prueba de conciliación. |
| Contexto confirmado | §§1–2,5: no cambiar custodia, rutas nativas, AAD de identidades, gracia45/exención global, secretosTOTP o cuentas; D/E sin operar. | No se declara adopción ni validación productiva adicional. |

## Casos razonados que debe contrastar el revisor

1. Se corta tras crear el archivo n y antes de publicar R+: ninguna fila puede depender de n; host permanece bloqueado.
2. Se corta con R+ publicado y antes del commit: a sigue activa, n legible; no se elimina material por asumir rollback.
3. Se pierde la respuesta del commit y el journal aún indica material_ready: la existencia del testigo exacto determina continuar hacia Rf.
4. La transacción sigue viva o DB no responde: no inferir ausencia definitiva del testigo ni quitar fence.
5. Se publica Rf y no se actualiza journal: verificar hechos y continuar; no repetir recifrado.
6. Factor disabled/pending, contador antirreplay o gracia: se conservan metadatos y se incluye la fila; no reactivar ni conceder acceso.
7. n supera el rango o requiere una entrada65: parar, no reciclar/borrar una versión.
8. La tabla de factores está vacía pero un backup requiere a: rotación con testigo cero, sin retirar a.
9. Cambia inventario, identidad de material o vínculo DB: no continuar con un plan distinto bajo el mismo UUID.
10. Falla guard/HTTPS después de abrir: detener y reponer fence, sin revertir automáticamente el commit/material.

Estos son contrastes de consistencia del contrato, **no pruebas ejecutadas de un programa o de caída de Windows/PostgreSQL**. La revisión registra sus propios controles y su suficiencia para el paso de especificación.
