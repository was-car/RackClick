# Probar tus clientes originales en la VM C

29.10.2026. Datos cargados y confirmados en la instalación10 actual, conservando la cuenta de Wascar y su MFA. No reinstales ni repitas la importación para hacer estas pruebas.

## Pasos en el navegador

1. Dentro de la VM abre la web que ya utilizaste: **https://192.168.206.131:5443**. Si ya tienes sesión abierta, consérvala. Si pide entrar, usa tu cuenta y el autenticador que acabas de configurar.
2. En la barra lateral izquierda, debajo de Systemhaus, pulsa **Todos los clientes**.
3. En la parte central, debajo del título **Clientes**, pulsa **Actualizar**. También puedes pulsar **Ctrl+F5** para recargar la página completa.
4. Deben aparecer las **10 tarjetas de clientes del Full Backup original**. Los clientes añadidos en las copias posteriores del laboratorio no forman parte de este conjunto, por tu elección.
5. Pulsa la tarjeta de un cliente conocido. En el inventario central localiza un rack que reconozcas; también puedes abrirlo desde la lista de racks que se despliega bajo ese cliente en la barra izquierda.
6. Comprueba el nombre y la altura del rack, sus equipos y las etiquetas de puertos. Usa los controles **Frontal** y **Trasera** del rack para revisar ambas vistas.
7. Busca un cable conocido y comprueba sus dos extremos. Para esta primera comparación no desconectes ni borres nada.
8. Pulsa **Ctrl+R**, vuelve al mismo cliente/rack y comprueba que sigue igual. Luego puedes realizar tus pruebas de edición sobre estos datos sintéticos.
9. Abre **Mi seguridad**, junto a tu cuenta en la parte inferior izquierda: el factor debe seguir activo. No hace falta desactivarlo ni enrolarlo otra vez.

Referencia técnica del conjunto inicial: **10 clientes, 15 sitios, 25 edificios, 68 salas, 68 racks, 311 equipos, 633 grupos de puertos, 5.408 puertos y 623 conexiones**. Si después editas o añades datos, los recuentos cambiarán de forma legítima.

## Tus resultados

Copia esta tabla a un archivo propio si deseas rellenarla. No contiene resultados atribuidos a Wascar por las pruebas automáticas.

| ID | Prueba | Pass / Not Pass / No probado | Observación |
|---|---|---|---|
| DATOS10-01 | Aparecen los 10 clientes originales | No probado | |
| DATOS10-02 | Rack, equipos, puertos y cable conocido coinciden | No probado | |
| DATOS10-03 | Tras recargar sigue el mismo inventario | No probado | |
| DATOS10-04 | Mi seguridad conserva el factor MFA activo | No probado | |

Codex verificó la transacción y dejó backups nativos de antes y después, sin cambios de cuenta, claves o servicio. Eso no sustituye tu comparación visual. El original también se conserva fuera de la VM en `RackClick-Datos-Demo-Original-01.zip`.

Los botones de exportación/importación **desde el dashboard web** todavía están pendientes. El panel Windows mantiene **Exportar backup**. No confundas el JSON de datos con una restauración completa de PostgreSQL y claves MFA en otro servidor.
