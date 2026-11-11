# F-04.01 · revisión independiente

03.11.2026. Revisor: agente `rackclick_security`, distinto del autor del escritor y del coordinador que corrigió los auxiliares. No se modificó producto, pruebas del producto, ledger, VM, D, cuentas, servicios ni bases de datos durante esta revisión.

**Dictamen: favorable al cierre técnico de F-04.01 en fuentes.** No hay hallazgo bloqueante nuevo dentro de ese subpaso. No equivale a cerrar F-04 completo, acreditar F-04.02/.04, actualizar el binario de D o adoptar una candidata Windows nueva.

## Archivos y símbolos contrastados

- `WindowsMfaKeyStoreWriter.cs`: `CreateCore`, `CreateInitialStore`, `CreateStoreFromMaterial`, `CreationSecurity`, `TryCreateOwnedDirectory`, `CreateExclusiveFile`, `ValidateCreatedFolder`, `Publish`, `Tracked.PreservePublished`, `Discard`, `Failed`, declaraciones Win32.
- `WindowsMfaKeyStoreCreationSecurityTests.cs`: ocho casos nuevos y fixture; referencia original y versión instrumental roja conservadas por el implementador.
- `MfaKeyStoreInitCommand.cs`: entrada elevada, confianza productiva fija SYSTEM/Administradores, delegación al mismo escritor y recibo sanitizado. `RackClick.SetupMfa.ps1` / `RackClick.MfaRuntime.ps1`: perfil, ruta separada y llamada de init. No se amplía la confianza ni se abre management.
- `test_mfa_runtime_wiring.py`: se añade únicamente la carga del auxiliar SQL real omitida por su fixture; conserva las aserciones MFA y las funciones del lanzador real.
- `build_master_roadmap.py` / `test_master_roadmap_refs.py`: el pie toma los contadores reales del registro en lugar de fijar 23 acreditados. La prueba comprueba el ledger actual y la reapertura de un checkpoint. No modifica pesos, estados o criterios.

Fuentes finales medidas: [review/RESULTADOS.json](review/RESULTADOS.json). El escritor revisado es `76e6dfc3364cb43260ef95e02bb88816702b21dc8f0230946645878d7c894d55`; sus pruebas nuevas, `fd904249f353825cca810db5cf4e4d90a80f89c85fb44705d704507e9aabc8b5`.

## Hallazgos contrastados y corrección

1. **Relevante para F-04.01, corregido:** la referencia creaba con descriptor NULL y protegía después. La versión final entrega `SECURITY_ATTRIBUTES` con DACL protegida y los mismos derechos desde la llamada de creación exclusiva. El descriptor nativo se mantiene vivo durante la llamada y se libera; los handles no son heredables. Se elimina el cambio posterior de ACL por ruta. Las observaciones anteriores a la escritura verifican el DACL, no sólo el estado final.
2. **Relevante para F-04.01, corregido:** una IOException posterior al rename podía confundirse con una colisión y dejar rutas antiguas del staging en la explicación del residuo. Ahora distingue si el rename ocurrió, conserva el conjunto publicado completo y declara la ruta final ante fallo. No desmonta sólo una parte de un almacén ya publicado. El reintento rechaza ese destino sin modificarlo.
3. **Preparación de pruebas/documentación, corregido:** carga ausente de auxiliar SQL y contador 23 fijo. Diffs acotados y aserciones conservadas; verificación independiente Python en verde.

## Pruebas ejecutadas por el revisor

Laboratorio Windows, SDK 10.0.401, carpetas TEMP nuevas y copia de fuentes independiente. `restore --locked-mode` terminó en 0. Cada invocación MSBuild conserva su binlog privado único; no se incorporan binlogs ni TRX completos a esta evidencia pública.

- **3/3 focos propios PASS**, código 0, compilados en una copia separada: [review/F0401IndependentReviewTests.cs](review/F0401IndependentReviewTests.cs).
  - Padre con Everyone FullControl: los cinco objetos nuevos ya tienen DACL protegida sin ese ACE ni herencia; los archivos aún tienen longitud cero. El padre permanece intacto.
  - Excepción mientras el primer archivo creado sigue vacío: ningún almacén final parcial y ningún residuo; se retira exclusivamente lo creado.
  - Instalación segura preexistente y fallo de permisos inmediatamente después del rename: `PublishFailed`, almacén completo y legible, ruta final declarada, sin rutas antiguas de staging. El segundo init conserva hashes y ACL; la carpeta ajena previa permanece.
- **13/13 PASS**, código 0: ocho casos nuevos del autor más colisión al publicar y cuatro variantes de destino existente. Se ejecutaron sobre los binarios propios del revisor, no sobre los del implementador.
- **8/8 Python PASS**, código 0: cuatro de wiring MFA con auxiliares reales y cuatro del generador del registro. Incluye la reapertura sin alterar el ledger en disco.

Se leyeron los TRX privados del implementador y se contrastaron sus contadores: rojo completo 5 FAIL/3 PASS; verde 8/8; regresión afectada 195/195, sin omitidas. Estos 195 no se ejecutaron otra vez ni se suman como pruebas únicas adicionales a los focos repetidos. Los positivos históricos C10/D11 se reutilizan como evidencia histórica de la cadena de instalación y servicio; no se presentan como nuevos ensayos.

## Contraste literal y límites

El almacén permanece fuera de management. La cadena elevada del instalador/CLI sigue usando el mismo escritor; sus contratos no cambiaron. La creación protegida se demuestra por el descriptor pasado a Win32 y por la inspección antes de escribir. La ruta final permanece ausente durante preparación; el conjunto completo se valida y se publica mediante un único rename sin reemplazo. Los fallos antes y después del rename no dan éxito falso ni un final desmontado parcialmente. Esto satisface el subpaso de creación/publicación inicial y permite acreditarlo sin operar D ni repetir su instalación.

La observación de seguridad ocurre tras capturar identidad, no mide cada instante de ejecución; el descriptor inicial se acredita también por revisión de la llamada nativa. Persisten límites explícitos de captura de identidad y del padre/destino absoluto. Los fixtures usan el SID de laboratorio como principal confiable y no sustituyen los negativos del token efectivo, todos los ancestros, otros usuarios o WRITE_DAC reservados a F-04.02.

No se ensayó una instalación nueva, token de servicio real nuevo, reinicio, corte de proceso/energía, durabilidad de la entrada de directorio, rotación ni transacción disco/DB. `FlushToDisk` de archivos no prueba esas propiedades. El cierre no las atribuye al rename ni reduce los criterios congelados de sus otros resultados. No se acredita adopción productiva o nuevo porcentaje global; la contabilidad del único 5/8 corresponde al coordinador.
