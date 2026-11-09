# Revisión independiente — catálogo PostgreSQL17 / esquema17

30.10.2026. Revisor `sql17_review`, distinto del implementador. Dictamen
**favorable para el tramo interno revisado**, con dos hallazgos P2 corregidos.
No acredita instalación, Restore, GUI, modelos comerciales o adopción de Wascar.

## Fuentes y alcance

Revisados:

- `database/017-hardware-catalog.sql`: tablas de definición, grupos, alojamientos
  y correspondencias; seeds; estado borrador/sellado; permisos y triggers.
- `SchemaMigrations.cs`: inclusión explícita de017 y última versión17.
- `InventoryHardwareCatalog.cs`: lectura de revisiones selladas, control de
  privilegios efectivos y contraste de valores con la definición compilada.
- `InventoryHardwareMounting.cs`: resolución de soporte/alojamiento desde el
  catálogo; dimensiones, grupos y correspondencias conservados.
- `InventoryHardwareProfiles.cs`, su derivado y el cambio de emisión de
  `tools/build_hardware_catalog.py`: Kind, Slots, Passthrough y digest de autoría.
- `tests/pg_support.py`: concesión específica SELECT para las cuatro tablas,
  posterior al grant genérico de inventario; fixtures anteriores sin catálogo
  no reciben esa concesión específica.
- `test_hardware_catalog17.py`: leído como ensayo del coordinador, no ejecutado
  su `main` por el revisor. El foco propio reutiliza sus auxiliares Session/state
  y runtime_sql, no su batería ni sus resultados.

Se reutilizó la investigación de PostgreSQL17 registrada en
`evidence/s1-20261030/hardware-sql17/INVESTIGACION-PREVIA.md`. La columna de revisión
es generada desde las propiedades; el BEFORE trigger consulta esas propiedades
directamente, sin depender de NEW de la columna generada.

SQL016, `hardware-reference.json`, la autoría y el lock16 conservan sus hashes
anteriores. El conjunto de compatibilidad del generador sigue siendo las cuatro
referencias sintéticas16; no se interpreta ese perfil como versión actual de DB.

## Hallazgos P2 y corrección

**SQL17-R1 · Una definición podía ampliarse sin cambiar su revisión.** La primera
versión impedía UPDATE/DELETE/TRUNCATE, pero el migrador podía insertar otro slot
o grupo sobre una pareja publicada. Ambos negativos se reprodujeron en PG17.11:
FOCOS-ANTES.json contiene7PASS/2FAIL. Cada inserción se ejecutó en una transacción
con ROLLBACK explícito; los estados posteriores quedaron iguales.

Se añade sellado: creación como borrador; inserción de componentes sólo mientras
el padre no está sellado; transición única false→true sin modificar otros datos
y con validación de composición. Una revisión sellada rechaza nuevas filas de
componentes. Runtime no obtiene escritura en catálogo. El revisor señaló además
la dirección inversa de una carrera con un publicador de snapshot antiguo;
la solución elegida restringe la autoría a READ COMMITTED, sin restringir lectura.

**SQL17-R2 · El trigger de inventario admitía una definición borrador.** El host
C# ya exigía una revisión sellada, pero un INSERT SQL con el login runtime podía
vincular una instancia al borrador. FOCOS-SELLADO-PARCIAL.json reproduce este
único fallo (13PASS/1FAIL), también con ROLLBACK. El coordinador identificó el
mismo punto durante su revisión del código. La selección del BEFORE trigger
exige ahora `sealed`; la instancia borrador queda rechazada por PostgreSQL.

Los dos hallazgos quedan **cerrados para la fuente final identificada**. Las
versiones SQL intermedias de esta tanda sólo se ensayaron en bases nuevas; no se
consideran migraciones aplicadas en la instalación de Wascar.

## Pruebas ejecutadas por el revisor

Comando propio reproducible desde la raíz:

```powershell
C:/Python312/python.exe -X utf8 -B evidence/s1-20261030/hardware-sql17/review/probe_sql17_review.py --output <nuevo informe JSON>
```

El foco lee la DLL del puntero privado `.local/hardware-sql17-current.txt`, crea
un clúster PostgreSQL17.11 y cuentas/base nuevos, usa el login runtime para las
comprobaciones indicadas y detiene sus servidores/clúster al terminar.

**Final:15PASS/0FAIL** en FOCOS-FINALES.json:

- Ensamblado v1 conocido con siete puertos bajo el runtime; identidad de revisión
  de instancia y rechazo de slot sobre un modelo que no es soporte.
- SELECT real y rechazo de DELETE con los privilegios efectivos medidos en las
  cuatro tablas globales. No se sustituye esa prueba por consultar ACL como dueño.
- Rechazo de grupo y slot adicionales en revisiones ya selladas, con estado
  exacto conservado tras cada intento.
- Rechazo de instancia asociada a borrador; nueva revisión borrador→sellada y
  posterior rechazo de componentes adicionales.
- Autoría rechazada bajo REPEATABLE READ y SERIALIZABLE; lectura del catálogo
  bajo REPEATABLE READ sigue permitida.
- Carrera real de dos conexiones READ COMMITTED: el publicador retiene el lock
  del padre después de sellar; se observa al escritor de componentes esperando
  en `pg_stat_activity`; al confirmar el publicador, el escritor se rechaza y no
  aparece el slot tardío. No es una simulación de orden de llamadas.

SQL final root/copia junto a la DLL:
`d037ef96c84ee8b7211b933bf2775da6a6e28b19451818c19ca3056516d21615`.
DLL usada:
`e51b953779aabd37bc99f85eed08a180fd11e3e9cb9325861faba0ec0e874e68`.
Huellas completas de fuentes consultadas en review/HASHES-REVISADOS.json.

## Límites

El revisor no compila, no ejecuta la migración CLI16→17 ni toda la regresión del
coordinador, no abre navegador y no toca VM, QA, instaladores o servicios Windows.
El bootstrap propio sí aplica1..17 a una base nueva; no prueba actualización de
una instalación ya existente. Los rechazos del foco preservan sus estados, pero
la preservación de UUID/cables/operaciones durante16→17 corresponde al ensayo
separado del coordinador. No se acredita durabilidad frente a corte del host.

No hay una frontera frente a un propietario/superusuario que deshabilite
triggers o cambie el esquema. El flujo de publicación de modelos comerciales,
sus licencias/recursos, importación y paquete de catálogo siguen pendientes.
El estado de borrador no implica catálogo instalable o visible al usuario.
Las reglas de READ COMMITTED de autoría deben conservarse al diseñar ese flujo.

Laboratorio propio y todos sus servidores detenidos. Sin cambios de producto,
commits, push, ledger o crédito por parte del revisor.
