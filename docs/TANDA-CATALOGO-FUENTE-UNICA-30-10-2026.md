# Catálogo normalizado: fuente única del conjunto de referencia

30.10.2026. Completado y revisado el primer tramo de normalización de autoría.
Servidor e interfaz derivan sus cuatro referencias del mismo documento validado.
No hay modelos comerciales añadidos, migración nueva ni actualización de la VM.

## Resultado

- Se elimina la duplicación manual de dimensiones y grupos en C# frente al JSON
  de la interfaz. Se conservan los valores físicos, etiquetas, prefijos y colores
  anteriores, la búsqueda exacta y las instancias guardadas.
- El compilador rechaza duplicados, campos desconocidos, números/dimensiones
  inválidos, caras/tipos no soportados y correspondencias de panel incoherentes.
  El lock del target16 impide ampliar silenciosamente las cuatro referencias.
- Los builds .NET y frontend rechazan entradas o derivados desactualizados. El
  control frontend se ejecuta antes de modificar su salida existente.
- Fuente, derivados, hashes y pasos están descritos en el
  [contrato](CONTRATO-CATALOGO-FUENTE-UNICA-v1.md). La revisión está en el
  [dictamen independiente](REVISION-CATALOGO-FUENTE-UNICA-30-10-2026.md).

## Verificación ejecutada

| Foco | Resultado y alcance |
|---|---|
| Compilador | 27 pruebas Python PASS; casos negativos, reproducibilidad, ausencia de escrituras al rechazar y guard Node real. |
| Compilación | SDK10.0.401, restore locked y build Release:0errores/0advertencias; binlogs privados únicos. |
| Registro C# | 4 pruebas existentes PASS, sin ejecutar toda la suite Quality. |
| Frontend | Build/37adaptadores y regresión814/814 PASS; no dependencias nuevas. |
| Compuertas reales | 1control MSBuild íntegro,6alteraciones rechazadas y1build frontend obsoleto rechazado conservando dist:8/8. |
| PostgreSQL17.11 | Foco de revisión5comprobaciones y montaje20comprobaciones: creación, permisos, IDs/puertos/cables, conflictos/replay, constraints, rollback, recarga/otra cuenta/reinicio. Laboratorios nuevos y detenidos. |
| Hoja de ruta | 3pruebas de referencias documentales; desconocidos rechazados y métrica igual. No se cambia el ledger. |
| Revisión independiente | 7focos propios PASS tras corregir2diagnósticos numéricos. No se atribuyen PG/build al revisor. |

No se repite Edge: no cambia la interacción visible y la proyección generada es
igual a la referencia congelada. Los recorridos Edge anteriores se conservan
como históricos, no como ejecuciones nuevas. Tampoco se repite15→16: no cambia
SQL016 y no se proporcionó una DLL15 al nuevo foco. No es un ensayo de instalación.

Se conserva la primera regresión Node fallida: mi copia privada tenía dos
fixtures anteriores a sus correcciones ya existentes en la raíz. Se repusieron
esas versiones vigentes sin modificar producto ni tests compartidos. La pasada
final814/814 utiliza la misma candidata del build. El revisor encontró también
dos diagnósticos no controlados ante enteros extremos, reproducidos antes de
corregir y cubiertos después; no producían derivados ni cambios de DB.

Al actualizar la hoja se detectó otra restricción documental previa: el
generador rechazaba el propietario C-HW-02 de una observación ya registrada.
Ahora los enlaces documentales aceptan extensiones declaradas; RC10 y el
cálculo del ledger siguen usando exclusivamente los53resultados originales.
La primera prueba nueva usaba por error la clave closure en vez de metric:
se corrigió el fixture antes de la pasada final, sin cambiar la contabilidad.

Evidencia, hashes y comandos:
`evidence/s1-20261030/hardware-catalog/RESULTADOS.md`.

## Próximo tramo

Normalizar las definiciones y capacidades de montaje en PostgreSQL con una
migración nueva, preservar las revisiones de instancia y limitar la cuenta de
ejecución a la lectura del catálogo. Después validar un modelo comercial, no
importar miles de nombres como si fueran plantillas listas.

QA136/137 permanecen planned y las respuestas de Wascar se conservan. Instalación10,
MFA, cuentas y datos de la VM intactos; sin commits/push ni paquetes publicados.
**Índice de cierre restante:9,76/100**, sin incremento automático. No es un nuevo
porcentaje global del producto ni cierre completo de C-HW-02/C-HW-06.
