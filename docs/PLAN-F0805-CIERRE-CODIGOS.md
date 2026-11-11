# F-08.05 · plan de cierre técnico de códigos y recuperación restringida

> Ejecución del coordinador con verificación y revisión independiente acotada. Se conserva D/E, sin commits, push, publicación, instalación o adopción.

**Objetivo:** contrastar el criterio completo F-08 en los binarios corregidos de F-08.04: generación/entrega única, consumo concurrente, ausencia de API antes del factor nuevo, revocación/rollback, último administrador y corrección D2 de pending/disable.

**Arquitectura:** reutilizar código y build fijados de F-08.04 y las revisiones anteriores; no recompilar servidor ni crear otro flujo. Ejecutar en PostgreSQL nuevo los diez casos de las cuatro clases añadidas en F-08.01–.04 y dos negativos existentes (replay y rollback). Preparar una copia privada del frontend ya existente y ejecutar los dos recorridos de Edge/PG cuando sus requisitos de build estén disponibles. Si un guion de prueba contiene una expectativa anterior al contrato actual, reproducir y ajustar sólo ese guion, preservando el negativo real.

**Especificación:** [F-08 del ledger](PLAN-CIERRE-RACKCLICK.json), [pasos 24–28](PLAN-PENDIENTES-NUMERADO.md), [condiciones D2](D2-CONDICIONES-TECNICAS-F03-02.md), [gracia45/exención](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md), [procedimiento público](PUNTO3-FUNCIONES-PENDIENTES.md). La generación actual es expresa después del enrolamiento, como ordena conciliar el plan numerado; no se anuncia generación automática histórica ni custodia garantizada.

## Investigación y alcance

Se reutilizan investigaciones oficiales de PostgreSQL17/.NET10/OWASP, código y evidencias de los cuatro pasos previos, incluyendo el rojo/verde real del fallo D2. No se instala ni cambia una dependencia. El frontend se construye sólo en copia privada con RC9/fuentes y herramientas existentes; nunca se ejecuta build sobre el directorio compartido. Servidor/pruebas conservan los pines de F-08.04.

Integración de distribución/servicio Windows, SID efectivo, HTTPS nativo y aceptación/custodia manual permanecen fuera del cierre técnico. F-09 trata la emergencia sin almacén/sobre/códigos; aquí se presupone host disponible, contraseña y códigos válidos. No se tocan cuentas personales ni los datos de D. El guard de último administrador de seguridad usa security.manage global; la exención MFA y la condición de administrador global requieren además systemhaus.manage global.

## Tareas

- [x] **1. Identidad y matriz conjunta.** Comprobar hashes/sellos de los cuatro bloques, identificar el único delta de producto D2 ya revisado y mapear cada frase del criterio F-08 a fuente, prueba, revisión y límite. Preservar el antecedente del driver1/48PASS/1 navegador opcional del paso27.
- [x] **2. Verificación final acotada.** Mismos binarios del paso27, sin build .NET nuevo: doce casos PG/HTTP, sin omisiones previstas. Frontend privado y dos guiones Edge existentes, sin grabar DOM, QR, cookies o credenciales en evidencia pública. Reutilizar 68 Node y demás invariantes del paso27 sin repetirlos. Toda salida incierta/fallo se conserva, no se transforma en éxito histórico.
- [x] **3. Revisión distinta.** Revisor inspecciona el criterio completo y fuente/evidencia actual; repite entrega concurrente (1), canje concurrente (2), negativos disable/pending (2) y rollback (1) en otro clúster. Verifica cualquier cambio de guion de navegador y determina si los hitos técnicos están acreditados. No convierte pruebas sintéticas en aceptación nativa.
- [x] **4. Conciliar y documentar.** Ficha28, matriz, resultados/hashes/escaneo y dictamen; actualizar continuidad/changelog e índices. Sólo F-08.05 (+1/2) si corresponde. Proponer estados de definición, implementación, pruebas y revisión técnicas; mantener integración de candidata y aceptación pendientes. Preservar los 175 casos y resultados QA y extender sólo instrucciones pertinentes si cambia un guion visible.

## Foco de revisión

- Una respuesta/operación no vuelve a revelar códigos; dos solicitudes realmente solapadas no producen dos entregas o recuperaciones.
- Códigos/contraseña/challenge/pending no equivalen a sesión API; sólo confirmar factor nuevo concede autoridad, también para global exento.
- Disable/reset/activación de política no borran pending para eludir el factor nuevo; la corrección D2 conserva la exención para un factor activo no pendiente.
- Auditoría falla → rollback del consumo; otra cuenta y sus ámbitos no cambian. Valores conocidos originales no se persisten en las tablas inspeccionadas.
- La concordancia de fuente no afirma igualdad binaria con D ni custodia real; los hitos operativos no se marcan done por completar una matriz técnica.


Cierre técnico11.11: [resultados](../evidence/s1-20261111/f08-05-cierre/RESULTADOS.md) y [dictamen](../evidence/s1-20261111/f08-05-cierre/review/DICTAMEN.md). Se conservan fallos/positivos Edge como [observación abierta](../evidence/s1-20261111/f08-05-cierre/OBSERVACION-NAVEGADOR.md), sin cambio de producto/guiones ni atribución causal no probada. La revisión decide la acreditación del criterio técnico; integración y aceptación/custodia permanecen pendientes.
