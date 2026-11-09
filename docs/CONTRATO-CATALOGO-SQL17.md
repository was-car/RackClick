# Definiciones de hardware en PostgreSQL — esquema17

30.10.2026. Desarrollo interno autorizado; ampliación del fundamento ya probado.
No modifica la instalación10 de Wascar. SQL001–016 y las cuatro definiciones
`hw-reference-v1` permanecen intactos.

## Modelo y revisión

La nueva017 crea cuatro tablas globales de definiciones, sin datos de clientes:

- `hardware_definition`: clave/revisión exactas, clase de montaje, reservaU,
  dimensiones, color, digest de autoría, identidad comercial y procedencia.
  Fabricante/familia/modelo/SKU siguen nulos para las cuatro referencias sintéticas.
- `hardware_group_template`: grupos identificados por clave, tipo, cara, cantidad,
  etiqueta, prefijo y orden dentro de una revisión.
- `hardware_mount_slot`: alojamientos de un soporte y sus dimensiones por revisión.
- `hardware_passthrough`: correspondencia1:1 de grupos frontal/trasera. No crea
  cables ni habilita un motor de trazado eléctrico.

Claves compuestas y colaciónC, sin selección implícita de latest. Una revisión
nueva puede coexistir con una anterior; no se reescriben las instancias.
Las semillas se emitieron una vez desde el catálogo normalizado revisado. Las
pruebas comparan todos sus campos/grupos/slots/correspondencias con esa fuente.
Una migración ya entregada no se regenera al añadir otro modelo.

El perfil de autoría cerrado16 sigue fijando **los mismos cuatro modelos**;
ese número de compatibilidad del conjunto no es la versión de la base. La
aplicación ahora exige base17. C# generado añade clase/slots/correspondencia y
digest desde la misma fuente; el JSON de dibujo no cambia.

## Borrador y sellado

Sólo el propietario de migración puede insertar una definición borrador y sus
componentes. La publicación técnica es una única transición `sealed=false→true`,
sin cambiar otros campos y comprobando la composición. Un soporte necesita
alojamiento; los otros tipos no lo tienen; se comprueban límites de grupos/puertos.
Esto no equivale a publicar un paquete para usuarios ni autoriza modelos nuevos.

Una revisión sellada no admite nuevos grupos/slots, actualización, borrado o
TRUNCATE. Los componentes de un borrador tampoco se editan o borran por este
recorrido; preparar una revisión correcta es una tarea transaccional del migrador.
No existe edición administrativa del catálogo por HTTP en este tramo.

La autoría usa READ COMMITTED. El bloqueo del padre coordina inserción y sellado;
otros aislamientos para escribir catálogo se rechazan expresamente para no
validar componentes con un snapshot antiguo. Lecturas en otros aislamientos
siguen permitidas. No se limita el aislamiento del inventario por esta regla.

## Relación con equipos y montaje

La revisión relacional de `inventory_device` se genera del valor protegido ya
existente en `properties.hardwareProfileVersion`. No hay dos campos editables
independientes. Una FK compuesta exige definición existente, y el trigger exige
que esté sellada. Clave/revisión de un equipo existente no pueden reescribirse.

Los controles de montaje dejan de contener las cuatro claves como reglas SQL:
consultan clase, U y alojamiento de la revisión. Se mantiene el padre en el mismo
Systemhaus/cliente/rack, sin ciclos/soportes anidados, con slot único y ajuste
dimensional. La ocupación sigue2+0+1+1=4U; el hijo conserva sus UUIDs y puertos.

El comando compara la definición SQL y sus componentes con la revisión compilada,
no sólo con un digest declarado. Consulta las dimensiones del alojamiento en vez
de suponer constantes. Un catálogo incoherente se rechaza sin materialización ni
éxito. La API sólo ofrece las cuatro referencias revisadas, aunque un fixture o
un migrador añada otra revisión a la base.

## Permisos y actualización

La cuenta de ejecución tiene SELECT en las cuatro tablas y conserva DML en su
inventario autorizado; no es propietaria, superusuario o migradora. El auxiliar de
laboratorio revoca concesiones generales y concede sólo lectura al catálogo.
El comando también detecta derechos DML heredados o concedidos por error y se
detiene con `hardware_catalog_permissions_invalid`, sin cambios parciales.

La actualización16→17 ocurre en la transacción de migración existente. Conserva
inventario, puertos/cables, cuentas, auditoría y operaciones. Si un equipo antiguo
no tiene una revisión válida, falla toda la actualización: no se infiere v1 ni se
repara o borra el dato. El inventario y el historial de migraciones anteriores
quedan como estaban. Repetir migrate sólo verifica digests.

## Límites de esta entrega interna

Sólo se prueba en laboratorios nuevos de Windows/PostgreSQL17.11. No se habilita
QA136/137, no se cambia VM ni el instalador10 y no se publica otra candidata.
Los operadores nativos/Restore/distribución aún no admiten esta entrega17; sus
GRANT generales deben adaptarse al catálogo antes de probarlos. No copiar sólo
la DLL a una instalación existente. La nueva candidata completa necesita New,
actualización/Restore, servicio/HTTPS, backups y reinicio antes de QA.

La rotación/publicación firmada y el rollback operativo del catálogo siguen
pendientes. Un propietario o superusuario puede desactivar triggers o cambiar
DDL: el catálogo no es una frontera frente al administrador de PostgreSQL.
Fabricantes, variantes, módulos/combos, selector por marca y recursos comerciales
requieren su validación y publicación separadas. No se añaden por editar este SQL.
