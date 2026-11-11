# Restore · rechazo explicado del administrador existente

25.10.2026 · Windows/LEAO. [Cambio y alcance](../../../docs/CORRECCION-DIAGNOSTICO-RESTORE-25-10-2026.md). Tres fuentes de operador/preparación/panel, un foco nativo nuevo y ampliación opcional de la prueba PostgreSQL existente. [Fuentes/digests](FUENTES.json), [revisión distinta](REVISION.md).

| Ejecución nueva | Resultado |
|---|---|
| Foco nativo antes de corregir el operador | [Rojo esperado](FASE-ROJA.json): exit 1, causa conocida ocultada. |
| Foco nativo final | [34 PASS](NATIVO.json). Funciones reales mediante AST; no procesos del producto. |
| Regresión existente `Test-SetupChildProcess.ps1` | [20 PASS](REGRESION-BROKER.json), 15 procesos propios, 0 cuentas/servicios/VM. |
| PostgreSQL 17.11 y operador de procesos real | [PASS 18,08 s](POSTGRESQL.json), DLL exacta 07, esquema14. Colisión sin cambios en 14 tablas/marcador, nombre nuevo conservando original/auditoría y laboratorio detenido. |
| Revisor independiente | Focos propios rojo 3 fallos/5 y verde 5/5 para tipos array; no ejecutó el PostgreSQL del autor. |

Comandos ejecutados, con salidas/credenciales en el directorio privado nuevo `.local/recovery-diagnostic-20261025T145807Z-302bbb69/`:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/tests/setup_recovery/Test-RecoveryDiagnostics.ps1 -ResultPath <salida-privada-nueva.json>
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/tests/setup_broker/Test-SetupChildProcess.ps1 -OutputPath <salida-privada-nueva.json>
C:/Python312/python.exe -X utf8 -B development/server/tests/test_recovery_username_collision.py --dll C:/RackClick_SVR/.local/w02-ejecucion-review-20261025T142111Z-56a4e28c/frozen-server/RackClick.Server.dll --output C:/RackClick_SVR/.local/recovery-diagnostic-20261025T145807Z-302bbb69/owned-pg --owned-operator
C:/Python312/python.exe -B tools/windows/qa_guide.py
C:/Python312/python.exe -B tools/windows/qa_guide.py --profile rc9
```

Se conserva el primer verde fallido del test por su cargador AST, y el fallo/tipos detectado por revisión, sin presentarlos como éxitos. Snapshot previo y diff privados preservados. Las ejecuciones históricas/ZIP07 permanecen originales.

Límites: no `pg_restore`, copia de Wascar, instalador, interfaz gráfica real, cambio de identidad Windows, servicio, reinicio o VM. La prueba PostgreSQL construye un marcador de recuperación sintético en una base nueva y llama al hijo .NET real bajo el operador de procesos. No confirma la causa exacta del primer intento histórico ni aceptación de instalación. No hay build/SQL de producto nuevo; se reutiliza la DLL congelada. Los secretos de laboratorio permanecen privados.

QA-119 planned, catálogo previo y resultados personales conservados; 2 guías regeneradas. W02-R3/Claude, estado postboot y nueva candidata pendientes. **Delta de crédito0; cierre restante67/14=4,79/100,11/280subpasos,1/50resultados.** No se cambia el ledger ni se modifica QA/VM o paquetes. [Controles](CONTROLES.json), [escaneo](ESCANEO.json), [manifiesto](SHA256SUMS.txt).
