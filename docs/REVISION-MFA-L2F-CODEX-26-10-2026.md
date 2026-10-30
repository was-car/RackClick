# Revisión independiente MFA-L2f · exportación y recuperación

**Dictamen favorable para el recorrido integrado de laboratorio.** Se acepta `CreateCore` con delegado privado como refactor acotado: conserva el orquestador/control de propiedad y evita duplicarlo. La creación inicial mantiene firma y rechazos. No es una validación del SID real o de recuperación entre equipos.

## Ejecución nueva de Codex

**123 archivos congelados y14 hashes contrastados**; copia anterior del escritor comprobada contra `1831ef9e…ee890e2e`. Restore locked/build Release SDK **10.0.401**, **0 errores/0 advertencias**.

| Grupo | Resultado |
|---|---|
| Focos de Claude: escritor14, recuperación19, payload28, sobre26 | **87 PASS** |
| Dos negativos originales independientes del escritor | **2 PASS** |
| Controles nuevos de preservación por Recover | **4 PASS** |

**93 PASS, cero fallos/omisiones;24,125s** para restore/build y los grupos. Los cuatro adicionales cubren:

- Instalación existente segura sin `mfa-keys`: recupera las dos claves, conserva centinela y ACL de raíz/instalación; origen preservado durante recuperación.
- Instalación existente insegura: rechazo sin alterar bytes o ACL.
- Instalación existente segura con fallo posterior: conserva los datos previos, sin almacén publicado, staging o residuo propio.
- Instalación ajena creada durante Recover: no se adopta/borra ni se cambia su ACL; conserva contenido y declara residuo.

Los snapshots propios comparan SHA256 del contenido de archivos además de ACL; los del autor comparan longitud/fecha/ACL y no se presentan como igualdad directa de bytes. [Resultados](../evidence/s1-20261026/mfa-l2f-codex/RESULTADOS-EJECUTADOS.json), [fuentes](../evidence/s1-20261026/mfa-l2f-codex/FUENTES-ENTREGADAS.json), [pruebas propias](../evidence/s1-20261026/mfa-l2f-codex/MfaL2fIndependentReviewTests.cs), [cierre](../evidence/s1-20261026/mfa-l2f-codex/CIERRE.md).

## Decisiones aceptadas y límites

Validar sobre/payload/identidad antes de escribir, adaptación explícita de instalación y reprotección con entropía destino/versión son conformes. Se mantienen las mismas claves, versiones/estados/fechas y los AAD/ciphertext de factores. Un destino `mfa-keys` existente se rechaza; una instalación existente segura sin ese almacén puede recibirlo. No se confunden ambos casos.

El residuo tras encontrar contenido ajeno es correcto: no borrar esa carpeta para simular limpieza. `DestinationRejected.Residue` debe mantenerse visible al futuro operador. No se exige duplicar `CreateCore` ni reabrir el refactor aprobado.

Subrevisor `mfa_l2_windows_review`, distinto del autor, confirmó por fuente recuperación, DPAPI/finally y diff del orquestador, sin defecto material nuevo. No compiló ni ejecutó: las cifras son del coordinador. No se repitieron las mutaciones de Claude ni se observó la limpieza de memoria con una sonda.

Doble lectura del anillo **no es snapshot transaccional**: ABA o cambio de archivos de clave sin anillo siguen sin detectarse. No se acredita rotación concurrente o durabilidad/atomicidad del conjunto ante cortes. DPAPI probada en la misma máquina/token de laboratorio, no bajo cuenta estándar efectiva del servicio. Las raíces eran TEMP nuevas; no se usó ninguna instalación existente.

Dos precisiones documentales sin otro build: `altered[^1]` modifica ciphertext final, no el tag situado en43..58; «sin disco» significa **sin archivo de sobre**, porque Recover sí escribe ring/DPAPI sintéticos.

Fuentes compartidas/congeladas y ocho documentos protegidos intactos; cinco binlogs, logs/TRX privados. Sin producto editado por Codex, dependencias, PostgreSQL/HTTP, cuentas/servicios, instaladores, VM/QA, commits/push o GitHub. [Siguiente L2g](MENSAJE-PARA-CLAUDE-MFA-L2F-REVISADO-26-10-2026.md): operador de archivos privados del sobre, sin activación del proveedor. **Índice del cierre pendiente7,63/100**, sin nuevo porcentaje global; MFA aún no disponible.
