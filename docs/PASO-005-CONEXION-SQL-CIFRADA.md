# Paso 5 · protección de la conexión SQL

02.11.2026 · F-02.01.

Se implementó en las fuentes la lectura cifrada de la conexión SQL mediante una opción explícita del servidor. El material queda vinculado a instalación, cuenta lectora, base y usuario de ejecución; un error no permite volver automáticamente a una conexión en claro. Las operaciones de migración y administración mantienen una identidad separada.

Se reutiliza el lector de archivos privados ya revisado para MFA, sin cambiarlo. Las pruebas usan Windows/DPAPI y PostgreSQL 17.11 reales en un laboratorio nuevo, con credenciales sintéticas. Comprueban permisos, corrupción, vínculo de identidad, rechazo al arrancar y permisos limitados del rol SQL.

**Todavía no está habilitado ni empaquetado para tu instalación.** Falta completar el provisionamiento en operadores y verificar el positivo con la cuenta efectiva del servicio en una instancia nueva. F-02.01 queda en progreso; no se acredita su cierre con el token de laboratorio.

**D se conserva íntegra**, con sus datos, cuentas, MFA, servicio y paquetes existentes. No tienes que ejecutar comandos ni modificar archivos de D por este paso.

Índice de cierre: **11,01/100**, sin puntos nuevos. El avance de esta tanda es código y pruebas de la protección, con sus límites registrados; no un nuevo porcentaje global del producto.

[Contrato y campos](CONTRATO-CONEXION-SQL-CIFRADA-v1.md) · [Resultados y revisión](../evidence/s1-20261102/f02-01-sql/RESULTADOS.md) · [Plan numerado](PLAN-PENDIENTES-NUMERADO.md).
