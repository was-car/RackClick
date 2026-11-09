# Catálogo de hardware: fuente única, primer tramo

30.10.2026. Desarrollo interno, esquema16 conservado. Extiende el vínculo exacto
clave/revisión, sin ampliar la selección de modelos ni la instalación de Wascar.

## Datos y derivados

`development/hardware/catalog-source-v1.json` es la fuente de autoría. Separa:

- Identidad de definición: clave y revisión exactas. Las cuatro referencias son
  sintéticas: fabricante, familia, modelo y SKU son nulos, no marcas inventadas.
- Procedencia: diseño propio de ensayo, documento de origen y lista de recursos
  vacía. No hay fotografías, código o modelos importados de terceros.
- Montaje: clase, reserva en U y dimensiones físicas independientes; alojamiento
  identificado con sus propias dimensiones.
- Componentes: grupos con clave, cara, tipo, cantidad, nombre y prefijo. La
  materialización sigue creando UUIDs distintos para las instancias y sus puertos.
- Correspondencia frontal/trasera: referencias a grupos existentes, cantidad
  concordante y regla1:1. Sigue sin activar trazado o crear cables internos.

El compilador `tools/build_hardware_catalog.py` genera el registro C#, el JSON
que consume la interfaz, un manifiesto y un target MSBuild de coherencia.
El registro exacto e inmutable ya aprobado conserva su API y sus rechazos.
`hardware-reference.json` permanece intacto como referencia histórica.

## Target cerrado16

`catalog-schema16.lock.json` fija las cuatro parejas y el digest canónico de cada
definición completa, incluidos etiquetas, prefijos y colores. Antes de escribir
se validan todos los datos, el lock, el hash de la referencia y la igualdad de la
proyección. Un cambio de v1, otro modelo/revisión o un conector desconocido se
rechaza; no existe una opción force ni un mapeo automático a RJ45.

Este formato admite exclusivamente el primer conjunto sintético. Altura y
profundidad son enteras por compatibilidad con el contrato C# actual; no se
truncan fracciones. Múltiples alojamientos, fabricantes, módulos, combos y
revisiones nuevas requieren ampliar y revisar el contrato, no editar el lock
para saltarse SQL016. No se edita una migración ya aplicada.

## Flujo del desarrollador

Desde la raíz, con Python3.12 instalado según el manual de herramientas:

```powershell
C:/Python312/python.exe -X utf8 -B tools/build_hardware_catalog.py --check
C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_hardware_catalog
```

Sólo para regenerar derivados después de un cambio de autoría compatible y
revisado, se usa `--write` y después `--check`. La herramienta sólo escribe sus
cuatro rutas de salida predeterminadas. No toca DB, VM, secretos o instaladores.
Los datos y derivados se versionan juntos. `.gitattributes` conserva sus bytes
frente a conversiones automáticas de fin de línea durante un checkout.

.NET comprueba hashes con la tarea nativa `GetFileHash` antes de `CoreCompile`.
El build frontend usa `node:crypto` antes de escribir `dist/` o `generated/`.
No se añade Python al runtime ni como proceso de la compilación .NET/frontend.
Un derivado ausente/desactualizado detiene la compilación con diagnóstico.

## Límites de integridad y siguiente paso

Los hashes son comprobaciones de coherencia del repositorio, **no firmas** ni
autorizaciones para importar catálogos no confiables. Un desarrollador que cambie
código, lock y referencia debe pasar otra revisión. El compilador no descarga
ni ejecuta contenido externo. Rechaza enlaces/junctions en sus rutas; no se
presenta como una frontera frente a un administrador que cambie esas rutas
concurrentemente.

Las cuatro publicaciones usan reemplazo individual de archivo; no son una
transacción conjunta ni se acredita durabilidad ante un corte. Tras una
interrupción, regenerar y comprobar antes de construir/empaquetar. No cambia
instancias existentes, nombres, UUIDs, grupos, puertos o cables.

**Pendiente:** catálogo de definiciones en PostgreSQL con una migración nueva,
permisos de sólo lectura para la cuenta de ejecución, coherencia de soportes por
revisión y pruebas de actualización/rollback. Después, primer modelo comercial
con especificaciones y derechos verificados. La distribución/operadores16 y la
candidata completa para QA136/137 siguen pendientes.
