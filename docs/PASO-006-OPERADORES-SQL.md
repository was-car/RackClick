# Paso 6 · operadores, backup y ficha SQL

02.11.2026 · F-02.02 en progreso.

Se añadieron adaptadores para que el arranque reciba metadatos del archivo SQL cifrado, y para que el backup lea una contraseña protegida de Windows. La ficha nueva guarda información de conexión **sin contraseñas**; la consulta autorizada permanece en la ventana privada. Se corrigieron dos defectos detectados en revisión: alias de entorno de .NET y validación del formato normalizado del visor.

Pruebas: 27 focos PowerShell 5.1, 5 de interoperabilidad .NET/PowerShell, 94 del acceso privado y 4 del descriptor de instancia; regresiones legadas 8 de backup, 6 de preparación y 6 del lanzador. Backup protegido real en PostgreSQL 17.11, recuperación de 20 filas con otro rol/perfil, rechazo de ciphertext copiado y limpieza del pgpass temporal. No se suman como puntos de avance.

**Falta la integración completa con New/Restore, los recibos/paquete y la identidad efectiva del servicio/backup programado.** Los formatos aislados probados no acreditan una instalación cifrada completa.

**D, sus datos, cuentas, MFA, servicio y paquetes permanecen intactos.** No tienes que ejecutar nada ni sustituir scripts. QA-168 queda planificado para otra candidata; se conservan los 167 casos anteriores y tus respuestas.

Plan, continuidad y changelog actualizados. Índice de cierre: **11,01/100**, sin puntos nuevos ni porcentaje global nuevo. El siguiente trabajo dentro de este mismo paso es conectar y comprobar el circuito completo de provisionamiento, antes del ensayo final.

[Contrato operativo](OPERADORES-SQL-CIFRADOS-v2.md) · [Evidencia y revisión](../evidence/s1-20261102/f02-02-operadores/RESULTADOS.md) · [Plan numerado](PLAN-PENDIENTES-NUMERADO.md).
