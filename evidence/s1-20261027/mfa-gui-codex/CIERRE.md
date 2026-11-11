# Cierre · GUI MFA · 27.10.2026

Resultado: enrolamiento y login con segundo factor implementados en la GUI y comprobados con Edge/Kestrel/PostgreSQL reales de laboratorio. Backend de producto y versiones de dependencias intactos. No se ha instalado esta GUI en QA/VM.

## Ejecuciones

| Comprobación | Resultado | Alcance |
|---|---|---|
| Node: API existente + MFA + mensajes + QR | 38 PASS, 0 FAIL, 0 omitidas | NODE-38.txt |
| Build Release .NET SDK 10.0.401 | 0 errores, 0 advertencias | Copia privada, logs/binlogs fuera de Git |
| Build frontend Node 24.21.0/esbuild 0.25.10 | exit 0 | Dist privado, no reemplaza QA |
| MfaBrowserGuiTests · filtro único | 1 PASS, 0 FAIL, 0 omitidas | 6,406 s de comando test; Edge 156.0.4314.42 |
| Autoridad PostgreSQL | DML con DDL rechazado | Rol de ejecución nuevo, no propietario |
| Revisión independiente | Favorable, 22 Node PASS | Fuente y contrato; no ejecución PG del revisor |

El navegador comprueba contraseña → desafío sin sesión/API → inicio explícito → QR local/clave manual → código erróneo rechazado → confirmación correcta → clientes → logout → desafío verify → recarga sin acceso → nuevo login y verificación. EN/DE/ES comprobados en el cuadro. Sin excepciones JavaScript; la petición automática de favicon devuelve 404, ajena al flujo MFA.

Comandos reproducibles desde un entorno de desarrollo preparado:

```powershell
& '.local/node-v24.21.0-win-x64/node.exe' --test development/frontend/tests/api.test.mjs development/frontend/tests/mfa-api.test.mjs development/frontend/tests/mfa-words.test.mjs development/frontend/tests/mfa-qr.test.mjs
# En una copia privada con dist construido y PG17 nuevo, fijar RACKCLICK_TEST_PG_ADMIN,
# RACKCLICK_MFA_GUI_FRONTEND y RACKCLICK_MFA_GUI_OUTPUT mediante entorno privado.
# restore/build con el SDK fijado y binlogs privados; después:
dotnet test tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj -c Release --no-build --no-restore --filter FullyQualifiedName~MfaBrowserGuiTests '-bl:<ruta-privada>/gui-test.binlog'
```

La integración es opt-in y no crea por sí sola el servidor PostgreSQL. Necesita Edge y Node existentes y una conexión administrativa a un clúster de laboratorio dedicado; crea y retira sólo su base y rol aleatorios. Sin esas variables se omite y **no cuenta como PASS**. La corrida acreditada no tuvo omisiones. Ver el fixture para el contrato de entorno. Los binlogs y conexiones no se distribuyen.

## Fuentes y trazabilidad

FUENTES.json fija los 16 archivos propios y nuevos. CAMBIOS-EXISTENTES.diff compara únicamente api.ts, ServerApp.jsx y build.mjs con sus copias capturadas al comenzar este lote; conserva el trabajo previo de otros desarrolladores. INVARIANTES.json compara las fuentes frontend/fixture actuales con las probadas en la copia y las 132 fuentes backend protegidas anteriores, sin diferencias. Los scripts de pruebas frontend se ejecutan directamente desde el repositorio, con sus hashes registrados. Los archivos nuevos no se confunden con modificaciones de backend.

El apuntador privado `.local/mfa-gui-current-test.json` identifica la corrida final y la copia usada. Logs/TRX/binlogs quedan bajo esa carpeta privada. Resultado público: RESULTADO-NAVEGADOR.json y ALCANCE-LABORATORIO.json, sin contraseñas, códigos, semillas, cuerpos HTTP, QR o cookies.

## Intentos anteriores conservados, no contados como PASS

1. Primera compilación: tres xUnit1051 por falta de CancellationToken en el fixture nuevo. Se corrigieron las llamadas; no se relajó el analizador. No se inició PG en ese intento.
2. Primer recorrido: el formulario de contraseña vacío seguía montado detrás del cuadro. Se ocultó durante el desafío.
3. Segundo recorrido: el cambio de idioma no alcanzaba al cuadro. La revisión también detectó el alcance de preferencias suspendido. Se conservó el alcance de los hooks y el cuadro pasó a tener idioma local. El selector del ensayo se acotó al diálogo abierto.
4. Node rojo inicial: 10 FAIL de 10 antes de incorporar el contrato MFA en la API. Primer verde con una clasificación de error tardío incorrecta; se comprobó la generación antes del desafío. Final consolidado: 38 PASS.

Los laboratorios de los intentos se cerraron mediante finally. No se repitieron suites backend de custodia sin cambios. Se probó sólo el ámbito afectado, después de estabilizarlo.

## Límites y continuidad

Proveedor sintético por DI únicamente en pruebas y HTTP loopback; no lectura con token del servicio, HTTPS productivo, escaneo físico del QR ni prueba GUI exhaustiva de los trece consumidores de reautenticación. El estado se descarta lógicamente; no se promete borrado físico de strings JavaScript. La cancelación no elimina la cookie HttpOnly desde JS: el desafío caduca o se sustituye al volver a iniciar sesión.

No se tocaron VM, servicios, instaladores, cuentas/bases existentes, QA desplegada, commits o push. Claude conserva L2l02; no se repite la inicialización03. Casos futuros QA-124/125/126, inicialmente planned, y guías regeneradas sin cambiar las notas de Wascar.

Revisión y crédito: REVISION-INDEPENDIENTE.md. Sólo F-07.02 añade 0,50: **8,13/100 del cierre restante**, 20/280 subpasos. No equivale a porcentaje global del producto ni MFA productivo terminado.

## Validación documental final

Se preservaron los 123 casos QA previos sin cambios; tres nuevos planned. Ambas guías pasan --check. progress_report --write/--check confirma 8,130952/100 y estructura congelada intacta; sólo F-07.02 cambió de pending a done. Mapa de código actualizado: 983 archivos, ready; conserva límites de análisis (71 declaraciones parciales y un SQL no analizable), sin presentar el mapa como cobertura completa. VALIDACION-CIERRE.json registra las comprobaciones.

Se alinearon además AUTENTICACION-MFA-S1.md e IMPLEMENTACION-REV4.md: la GUI y la composición Windows existen en desarrollo; la identidad efectiva, candidata y QA siguen pendientes. Los estados anteriores quedan fechados como historia.
