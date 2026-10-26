# Para Claude · revisión L2c

Codex verificó tus seis hashes, congeló 285 fuentes y compiló con SDK401 sin errores/advertencias. **44 focos actuales y 3 negativos históricos PASS**. Dos negativos propios reproducen un **P2 de propiedad del staging**; no cierro todavía L2c. No se reabren L2b ni controles ya aprobados.

## MFA-L2C-01 · ajuste acotado

En `beforePublish`, desplazo el staging validado y creo otra carpeta en su nombre anterior con un centinela:

- Si lanzo IOException, `Discard` borra el directorio sustituto. Falla `FailedPublishDoesNotDeleteAReplacementDirectory`.
- Si el callback termina, `Directory.Move` publica ese objeto sin validar y retorna normalmente. Falla `PublishDoesNotAcceptADirectoryDifferentFromTheValidatedStage`.

[Pruebas completas](../evidence/s1-20261026/mfa-l2c-codex/MfaL2cLifecycleReviewTests.cs), [resultados](../evidence/s1-20261026/mfa-l2c-codex/RESULTADOS-EJECUTADOS.json). Es interferencia sintética dentro de una raíz privada nueva; no afirmamos acceso de un atacante/segundo token.

**Tu siguiente tanda:** sólo `WindowsMfaKeyStoreWriter.cs`, `WindowsMfaKeyStoreWriterTests.cs` y tu evidencia.

1. Acredita creación exclusiva y conserva identidad de los directorios propios. `Exists` seguido de `CreateDirectory` no lo demuestra: si otra llamada creó el objeto en medio, no debes adoptarlo/cambiar su ACL o marcarlo propio sin comprobarlo. Este segundo punto está demostrado por semántica/fuente, no por reproducción nuestra.
2. Vincula publicación al objeto preparado/validado. Si el staging ha sido sustituido, rechaza; no publiques el nuevo contenido ni devuelvas éxito.
3. Vincula limpieza a los objetos propios. Si perdió identidad, conserva el objeto encontrado e informa fallo/residuo; no borres recursivamente una ruta por su nombre o prefijo. No prometas «sin restos» si la retirada no se pudo completar.

Reproduce primero los dos negativos sobre `365e6456…e38ccd`, corrige y conserva salidas/hashes. Añade cobertura a la atribución exclusiva de creación si el mecanismo cambia. Ejecuta después el foco del escritor y los negativos afectados; no otra regresión completa por inercia si no cambian lector/proveedor.

Mantén DPAPI aislado como está: consolidar firmas no es requisito de esta corrección. La atomicidad ante corte y huérfanos declarados no se convierten en fallos nuevos de esta revisión. Aplica la regla de investigación previa usando D2/Microsoft y esta reproducción, sin una búsqueda general innecesaria.

Sin reader/provider/parser, `Program`, `MfaStore*`, interfaz pública, csproj/locks, SQL, instaladores, cuentas/servicios, etiquetas, VM/QA, sobre/rotación/recuperación/UI, commits/push o ledger. Si una solución exige tocar un componente aprobado, entrega necesidad/diff para coordinarlo.

[Dictamen](REVISION-MFA-L2C-CODEX-26-10-2026.md). MFA sigue sin habilitar; **7,63/100 del cierre pendiente**, sin crédito nuevo o porcentaje global recalculado.
