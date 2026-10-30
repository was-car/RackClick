# Carga local del original sintético RC9

Componente operativo acotado; no upload público ni restauración de DB completa.
Sólo acepta el plan SHA256 `cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7`
del original `cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0`.

Preparar con `tools/prepare_rc9_demo_load.py --source <original> --output <nueva .local/rc9-demo-...>`.
Usar SDK10.0.401 fijado y `RackClickServerDir` apuntando a la publicación10 verificada;
no descargar ni sustituir Npgsql. El proyecto referencia su Npgsql.dll existente y
el framework ASP.NET Core10. Guardar los binlogs/diagnósticos bajo `.local`.

Invocación: `dotnet RackClick.Rc9DemoLoad.dll --plan <demo-plan.json>`.
La entrada JSON se recibe exclusivamente por stdin: mode(check/apply), connectionString,
actorName, expectedHouseId, expectedRevision, requestId. Nunca poner credenciales
en argumentos, historial, documentación, logs públicos ni Git.

`check` valida conexión runtime restringida/loopback, esquema15/digests, actor
global y destino vacío. Devuelve UUID y revisión, sin mutaciones. `apply` requiere
esos valores explícitos y un requestId nuevo; inserta inventario, revisión,
auditoría y recibo en una transacción. Un replay válido devuelve el recibo previo.
No modifica cuentas, sesiones, factores, claves o nombre Systemhaus.

Si se pierde la respuesta durante commit, el resultado es incierto; conservar
requestId/recibo y conciliar antes de repetir. No declarar rollback por timeout.
Guardar backup previo y posterior; conservar la fuente y la identidad del destino.

Pruebas reproducibles (sin instalar servicios):

```
C:/Python312/python.exe -B development/server/tests/test_rc9_demo_loader.py --publication <publicacion10> --loader <RackClick.Rc9DemoLoad.dll> --plan <demo-plan.json> -v
```

Crean PostgreSQL17 nuevo bajo `.local/labs`, roles nuevos y secretos locales; lo
detienen al terminar. No usan la VM ni bases existentes. El factor sintético de
los fixtures comprueba conservación de bytes, no un login TOTP real.

Decisiones, pruebas, revisión y resultado operativo:
`evidence/s1-20261029/rc9-demo-original-codex/`.
