# Paso 22 · cierre técnico de rotación MFA

11.11.2026 · F-06.04. Cerrado técnicamente, con revisión independiente favorable. **D y E se conservan sin operaciones.**

## Qué se comprueba

Se reutilizan las fases especificadas en F-06.01, el catálogo y la retirada de F-06.02 y las quince caídas reales de F-06.03. No se repiten sus suites invariantes. La brecha de este cierre era demostrar la recuperación de un catálogo **no vacío** después de rotar.

El ensayo nuevo crea tres factores sintéticos —activo, pendiente y desactivado— en versiones1/7. Obtiene un backup custom, su inventario desde la misma instantánea PostgreSQL exportada y un sobre RCKEY autenticado. Rota a8, conserva otra copia y rota a9; obtiene una tercera copia. Las tres permanecen en el catálogo declarado y verificado.

Cada backup se restaura en otro clúster nuevo y se autentican todos sus factores tanto con las claves conservadas del anillo final9 como con su propio sobre recuperado en un almacén nuevo. Se comparan los secretos TOTP por huella privada y los metadatos completos de factores, usuarios, política, códigos y Systemhaus. El origen conserva su huella de ciphertext y sus testigos durante cada Restore.

Las versiones1/7/8 siguen protegidas aunque ya no cifren factores vivos: su retirada devuelve `mfa_retirement_backup_referenced`. Quitar una clave requerida o alterar un dump bloquea otra rotación antes de crear un fence o cambiar DB/anillo. Una clave ausente en cada almacén recuperado también se rechaza; al restituir el objeto propio del fixture vuelve a autenticarse.

## Evidencia y alcance

[Resultados](../evidence/s1-20261111/f06-04-cierre/RESULTADOS.md) · [matriz del criterio](../evidence/s1-20261111/f06-04-cierre/MATRIZ-CIERRE.md) · [plan e investigación](PLAN-F0604-CIERRE-ROTACION.md).

Son cinco invocaciones de un trabajador de pruebas: preparación, dos rotaciones encadenadas y tres verificaciones de Restore. No son cinco funciones nuevas. Las227fuentes/archivos de producto son idénticas a la fuente congelada de F-06.03; sólo se añaden prueba y arnés. La DLL se recompila en otra ruta y tiene su propio pin, sin afirmar identidad binaria con la del10.11.

Los sobres de este ensayo están cifrados en carpetas privadas del mismo equipo, fuera de instancias y backups. Eso no sustituye la custodia externa de Wascar. No se prueba aquí portabilidad entre máquinas ni adaptación de identidad. El Restore es offline; no autoriza arrancar una DB antigua con el journal vivo de una rotación ya terminada.

## Qué cambia en tu servidor

Nada: no hay que copiar DLL, SQL o claves a D. Este cierre no entrega CLI pública de rotación ni instalador46. Continúan pendientes la integración operativa completa, cuenta efectiva del servicio, custodia externa real, servicio/HTTPS/login y aceptación de la candidata objetivo. Los cortes de proceso previos no acreditan un apagón ni durabilidad universal.

El criterio técnico puede conciliarse con revisión favorable; la integración y aceptación conservan sus hitos pendientes. No se acredita un porcentaje global del producto por aumentar pruebas.


Crédito exclusivo F-06.04: **+5/8**. Índice del cierre restante **21,01→21,63/100**, sin porcentaje global nuevo. Siguiente paso numerado:23/F-07.05. [Revisión independiente](../evidence/s1-20261111/f06-04-cierre/review/DICTAMEN.md).
