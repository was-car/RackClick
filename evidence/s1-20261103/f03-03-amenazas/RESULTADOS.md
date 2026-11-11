# Paso10 · F-03.03 · Registro de límites de amenaza

03.11.2026. Autor: coordinador Codex; revisión de seguridad por un agente distinto. Solicitud de Wascar: continuar F-03.03, conservar D y aprovechar la evidencia existente. El criterio congelado pide registrar que DPAPI LocalMachine no aísla del administrador local ni del proceso de servicio comprometido. Es parte de una decisión documental con peso0.

## Resultado

[Ficha de amenazas](../../../docs/D2-LIMITES-AMENAZA-F03-03.md): frontera de confianza del host y del servicio; DPAPI ligado al equipo frente a DACL por token; entropía de instalación/versión que no constituye otra contraseña; DB/dump aislados, blob aislado, imagen/snapshot completo y sobre portable. Registra riesgos de memoria/diagnósticos y que reencriptar un mismo TOTP no revoca una semilla ya sustraída. No identifica un incidente ni ordena rotar D.

La ficha conserva custodia confirmada y gracia45/exención global. La recuperación sigue restringida hasta confirmar un factor nuevo, también al global exento. Cifrado/ACL no se presentan como protección del servidor frente a su propio administrador o un proceso comprometido. No se adoptan otros proveedores, privilegios o versiones.

## Investigación y evidencia reutilizada

Se leyeron Git/continuidad/hoja/criterio, D2v2, revisiónD2, decisiones25/29.10, condiciones F-03.02 y fuentes `WindowsMfaKeyProvider`, escritor/lector, `MfaKeyRing.EntropyFor`, cifrado y composición. Los principios ya estaban registrados: se concilian y hacen visibles, sin diseñar otro proveedor.

Fuentes primarias consultadas03.11.2026: [Microsoft CryptProtectData/LocalMachine](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [Windows DACL/AccessCheck](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object). La primera documenta ámbito de equipo; la segunda el acceso por token/ACE. Las consecuencias para RackClick se contrastan con su implementación y no se atribuyen a una certificación externa.

[ENTRADAS-Y-REUSO.json](ENTRADAS-Y-REUSO.json) fija10fuentes de producto e identifica los componentes comparados con manifiestos L2b/L2d/L2f. Las revisiones se reutilizan dentro de su alcance; no se suman sus pruebas ni se presentan como nuevas ejecuciones de aislamiento. La fuente actual del proveedor se inspecciona directamente: las ampliaciones de selección activa posteriores no se atribuyen a la antigua suite L2b.

## Revisión y validación

El dictamen separado debe confirmar el SHA256 final de la ficha: [REVISION-INDEPENDIENTE.md](REVISION-INDEPENDIENTE.md). Tras ese dictamen se concilia únicamente F-03.03. F-03.01/.02 conservan su contenido; los hitos del resultado F-03 se cierran sólo como decisión y documentos registrados, con la confirmación de custodia25.10. No representan aceptación operativa/producción o una aprobación nueva de riesgos por Wascar.

Se conservan la huella de alcance, IDs, pesos y baselinev3; se regeneran y verifican informe de progreso, hoja y lista numerada, sin renumerar el10. Los10archivos de aplicación medidos deben seguir idénticos. No se cambia código de aplicación, SQL, instaladores, configuración de D, claves, credenciales, GUI o resultadosQA. **0operacionesVM** y ninguna prueba de producto nueva. Las comprobaciones nuevas son lectura, hashes, enlaces y validadores documentales.

## Métrica y pendientes

F-03.03 y F-03 pesan0. La definición puede cerrar F-03 documentalmente al estar sus tres checkpoints registrados y revisados, pero no acredita F-04/F-05/F-06/F-08/F-09/R-04, custodia operativa, recuperación portable, emergencia, rotación o QA. Índice2479/168=**14,76/100**, sin puntos añadidos ni porcentaje global nuevo.

Después de aplicar el cierre quedarán33checkpoints cerrados/247sin cierre,53resultados/280checkpoints/268opciones estables. Siguiente número:11/F-04.01, cuyo trabajo debe conciliar primero el proveedor y sus pruebas ya existentes. No se inicia ese paso por escribir este registro. Sin commits ni push.

Las salidas y el contraste selectivo antes/después se añaden en `CIERRE-VALIDADO.json` al finalizar.

## Cierre aplicado

**F-03.03 done** sobre fichaSHA256 `b19f3fc02ae7262bb1eee8a2823fd33068e3211dc8723229ebb890b32e420968`, con revisión independiente y [adenda de conciliación](ADENDA-PLANIFICACION.md). Sólo cambia ese checkpoint;279otros y52otras tareas conservados. F-03 completa la decisión documental, sin aceptación operativa. LedgerfinalSHA256 `252f062426e9ea354b23525fd5aa40163a2c1c956268ebc2525b91d1f335fcaf`; alcance9ef507b41abc2c8cab58e38bf345c4a4f30dd48a8a156b0d1d4ebd7ea45be974 y2479/168intactos.33done/247sin cierre,10conservado; siguiente11/F-04.01.

Tres generadores `--check` con salida0 ([VALIDACIONES.json](VALIDACIONES.json));10fuentes de producto idénticas antes/después,4componentes de revisiones previas exactos, enlaces del contrato válidos. Gitleaks8.30.1 sobre tres archivos documentales propios dio0coincidencias, sin relajar reglas ni escanear secretos/VM: [alcance acotado](SCAN-DOCUMENTAL.json), no higiene universal. Sin pruebas de producto o accesos a D/E. [Estado final](CIERRE-VALIDADO.json).
