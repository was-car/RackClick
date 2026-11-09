# Integración de los pendientes 8–18 · candidata16

04.11.2026. **El escritor MFA corregido ya está incorporado a una candidata completa de aplicación45**, con la misma DLL Release utilizada en las pruebas nuevas. D y E permanecen intactas; no se ha instalado ni actualizado un servidor en esta tanda.

## Qué cambió frente a la revisión anterior

1. **Escritor integrado.** Se reconstruyó la copia congelada de413fuentes de aplicación45 sustituyendo únicamente el escritor aprobado F0401. Se conservaron frontend, SQL001–045, dependencias y servicio Windows. La candidata incluye distribución73archivos, bundle2018 y payload117, con envoltorio16 completo y manual propio.
2. **Compatibilidad de los operadores45.** La inicialización MFA admite los perfiles cerrados15/43/45. Readiness y el recibo instalado usan la versión exacta derivada del bundle autenticado, en lugar de fijar43. Restore acepta45→45 y las migraciones explícitas13/14/15/43→45; continúa rechazando44, historiales incoherentes y retrocesos.
3. **Pruebas de la combinación exacta.** Pasan16casos con la DLL Release del paquete: ocho de creación segura y ocho de DB restaurada/login MFA con factores conservados. En PostgreSQL17.11 real pasan New45, Restore45→45 y43→45, con identidades nuevas, veinte filas sintéticas conservadas por recorrido, reanudaciones y runtime sin DDL. Los cuatro clústeres de estos operadores y los dos clústeres de los intentos HTTP quedan detenidos.
4. **Paquete completo contrastado.** Los43casos de empaquetado y15focos de los operadores pasan. La verificación nativa del bundle y del payload pasa; un archivo extra o alterado del payload se rechaza. Los perfiles y ZIP históricos se conservan. La revisión independiente está enlazada en la evidencia.

Estas cifras no se suman como funciones o puntos nuevos. Las repeticiones del revisor corroboran las mismas pruebas.

## Qué sigue pendiente

- **Ensayo de instalación16 elevado en una VM limpia:** cuenta/SID reales, servicio, HTTPS, formato mínimo de secretosSQL, backup y reinicio. Los recorridos de seeding New/Restore de laboratorio usan formato protegido2 con mantenimiento del propietario; no se presentan como aceptación del formato mínimo3 de la instalación nativa.
- **Recuperación MFA por operador/instalador:** continúa la guardia `recovery_mfa_envelope_required` para cualquier factor existente, también deshabilitado. El nuevo paquete no importa ni genera claves para eludirla. Faltan coordinador D2, vínculo backup/material, fence/journal/marcador DB, conciliación y ensayos de interrupción antes de adoptar DB y material recuperados.
- **Rotación/emergencia y aceptación final:** mantienen sus pasos F-06/F-09/R-04 y condiciones de custodia. El ensayo TestServer no acredita SCM, TLS de red, reinicio, durabilidad ante corte o adopción.
- **D:** no se ha cambiado su aplicación45, datos, cuentas, MFA, certificados, servicios o URL. Este envoltorio es una candidata para ensayo; no es un actualizador45→45 de D. No ejecutar limpieza, New o Restore para actualizarla.

## Archivos y trazabilidad

Entrega privada local, sin publicación: [inventario y hashes completos](../evidence/s1-20261104/f04-integracion16/package/ENTREGA.json). El envoltorio está en `.local/f04-integration16-20261104/packaging/.local/RackClick-Servidor-16.zip`, SHA256 `a862565da3e8351d734206b87886e4d8653b3cf4526661496012acc37901345a`.

[Resultados y límites](../evidence/s1-20261104/f04-integracion16/RESULTADOS.md) · [revisión independiente](../evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md) · [manual de la candidata](INSTALADOR16-SQL-PROTEGIDO.html).

El avance concreto es pasar de «corrección sólo en fuentes» a «corrección integrada y probada en una candidata completa». No se vuelve a puntuar F-04.01/.04: el índice de cierre permanece **19,13/100**, exacto1607/84, sin porcentaje global nuevo. La aceptación de la instalación completa sigue pendiente.


## Retoma del cierre · 09.11.2026

La verificación de esta fecha confirma que los binarios, fuentes congeladas, cinco pins de entrega y evidencia revisada siguen idénticos. Pasan de nuevo las tres comprobaciones nativas de integridad de distribución, bundle y payload, sin ejecutar el instalador ni el producto. Se termina el escaneo/sello final y la conciliación documental que habían quedado pendientes. Los ensayos de aplicación/PostgreSQL citados arriba son del04.11; no se repitieron ni se alteraron sus recibos. No se instaló nada en D/E.

[Resultado de la retoma y pendientes exactos](../evidence/s1-20261104/f04-integracion16/cierre-20261109/RESULTADOS.md). La integraciónF04 en la candidata16 se conserva; aceptación nativa y recuperaciónMFA operativa siguen pendientes. El índice permanece19,13/100, sin crédito nuevo ni aceptación inferida.
