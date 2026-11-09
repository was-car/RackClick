# RackClick · Demo50 · inventario opcional

50 clientes ficticios, siete escenarios, todas las 868 parejas perfil/revisión de esquema43 y conexiones persistidas y probadas. Las áreas de negocio se separan de las muestras de catálogo. La matriz muestra instancias, UUID, grupos, puertos y conexiones; 24 perfiles sin extremos propios quedan no aplicables con motivo, sin puertos inventados.

Extrae el ZIP en una carpeta nueva y abre VER-50-CLIENTES.html con el navegador. Busca un cliente y usa Detalles o descarga su JSON. SHA256SUMS.txt fija cada archivo. No hay ejecutables, fotos de proveedor, bases, cuentas, sesiones, contraseñas, factores MFA ni cadena PostgreSQL.

No es un instalador, un backup PostgreSQL ni el Full Backup original RC9. Los JSON son RackClickInventory-v1 por cliente: la importación desde el panel sigue pendiente. No copies archivos a una base instalada. La selección opcional de esta demo en el paquete completo corresponde al punto5 y no está habilitada en el instalador actual.

Para reproducir el laboratorio nuevo desde el repositorio: docs/LABORATORIO-50-CLIENTES.md, tools/build_demo50_plan.py y tools/prepare_demo50.py. Las herramientas están fijadas por el proyecto. Los UUID de recursos proceden del servidor; semilla e identidades lógicas/requestId son reproducibles. Cada ejecución nueva genera credenciales y recursos nuevos; repetir sobre una salida existente se rechaza.

Los verificadores de puertos genéricos son fixtures sintéticos rotulados, no otros productos de fabricante. Los enlaces entre edificios representan un campus de laboratorio; no inventan circuitos WAN ni certifican transceptores, longitud o parámetros eléctricos. El backup PostgreSQL de recuperación y las credenciales se conservan exclusivamente en .local y no están en este ZIP.
