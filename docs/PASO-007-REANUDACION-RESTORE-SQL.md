# Paso 7 · reanudación y Restore SQL protegido

02.11.2026 · F-02.03 en progreso. D se conserva.

Se conecta la protección SQL a New/Restore **de laboratorio**, con perfiles cifrados y un manifiesto v2. Cada destino genera sus identidades, roles, contraseñas y material local nuevos. El lector runtime valida los archivos privilegiados sin descifrarlos; el mantenimiento abre sus perfiles explícitamente.

El ensayo usa la aplicación43 ya fijada y PostgreSQL17.11 en dos clústeres nuevos. Se comprueban recuperación de datos sintéticos, dos reanudaciones, permisos runtime sin DDL y rechazo de claves ausentes, alteradas o de otro contexto. Se corrigen también dos retenciones de texto claro en el circuito protegido: la petición del intermediario y el pgpass de Restore.

**Falta la integración en el instalador completo y comprobar las identidades efectivas del servicio/backup y otro Windows.** Dos clústeres bajo el mismo usuario Windows no acreditan ese extremo. F-02.01/.02 siguen parciales; no se cierran al comenzar este ensayo.

No necesitas ejecutar nada ni cambiar archivos de D. No hay candidata nueva para instalar. Datos, MFA, servicios, catálogo, paquetes y respuestas QA conservados.

Índice de cierre acreditado: **11,01/100**, sin puntos nuevos ni nuevo porcentaje global. El código y el ensayo avanzan; el cierre queda sujeto al extremo operativo pendiente.

[Contrato y límites](REANUDACION-RESTORE-SQL-PROTEGIDO.md) · [Resultados](../evidence/s1-20261102/f02-03-restauracion/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261102/f02-03-restauracion/REVISION-INDEPENDIENTE.md).
