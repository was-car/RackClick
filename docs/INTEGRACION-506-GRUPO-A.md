# Integración de los 506 elegidos · grupo A

01.11.2026. Objetivo confirmado por Wascar: **los 506 modelos utilizables en RackClick y después incluidos en el paquete completo**. Preparar expedientes no cumple ese objetivo. Este grupo incorpora 17 perfiles reales a la aplicación de desarrollo; no declara los 506 terminados.

[Abrir los 17 modelos](../VER-SELECCION-506-A.html) · [Cobertura de los 506](COBERTURA-MODELOS-ELEGIDOS.md) · [Criterio visual](CRITERIO-VISUAL-CARCASAS.md)

## Resultado comprobado

- 12 Aruba y 5 Ubiquiti nuevos, 34 caras propias, 655 extremos. Revisión `selected506a-20261101-v1`, nueva migración 029 y selector/renderizado integrados.
- Siete correspondencias de SKU revisadas reutilizan perfiles anteriores; no son altas. La conciliación pasa de 44 coincidencias por nombre a 51 existentes reconocidas; con las 17 altas queda **68/506 (13,44%) y 438 pendientes**. Es cobertura del catálogo elegido, no porcentaje global ni aceptación QA.
- Se conservan 411 definiciones anteriores; total 428, de las cuales 423 comerciales y 5 sintéticas. Se preservan 406 instancias comerciales y sus UUID al actualizar 28→29.
- PostgreSQL 17.11: creación por API de los 17, 51 cables (17 cobre, 17 SFP y 17 AC), recarga, segunda sesión, permisos, conflictos, idempotencia, rollback de auditoría y persistencia tras reiniciar el host.
- SDK 10.0.401: compilación sin errores ni advertencias y diez pruebas C# pertinentes. Frontend final: 886 pruebas Node. Python: 21 pruebas focales y comprobaciones de reproducción.

| Modelo elegido | SKU | Montaje | Extremos |
|---|---|---|---:|
| HPE Aruba Networking JL675A | JL675A | 1 U | 53 |
| HPE Aruba Networking R9Y04A | R9Y04A | 1 U | 53 |
| Ubiquiti UniFi Switch Enterprise 24 PoE | USW-Enterprise-24-PoE | 1 U | 27 |
| HPE Aruba 6100-12G-POE4-2SFP+ | JL679A | Bandeja explícita, 0 U adicionales | 17 |
| HPE Aruba 6000-48G-POE4-4SFP 740W | R9Y03A | 1 U | 53 |
| HPE Aruba 6000-24G-4SFP | R8N88A | 1 U | 29 |
| HPE Aruba 6000-48G-POE4-4SFP | R8N85A | 1 U | 53 |
| HPE Aruba 6000-24G-POE4-4SFP | R8N87A | 1 U | 29 |
| HPE Aruba 6000-12G-POE4-2SFP | R8N89A | Bandeja explícita, 0 U adicionales | 17 |
| HPE Aruba 6100-48G-4SFP+ | JL676A | 1 U | 53 |
| HPE Aruba 6100-24G-POE4-4SFP+ | JL677A | 1 U | 29 |
| Ubiquiti UniFi Switch 48 Pro PoE Gen2 | USW-PRO-48-POE | 1 U | 53 |
| Ubiquiti UniFi Switch 24 Pro PoE Gen2 | USW-Pro-24-POE | 1 U | 27 |
| Ubiquiti UniFi Switch Pro Max 24 PoE | USW-Pro-Max-24-PoE | 1 U | 27 |
| HPE Aruba 6000-48G-4SFP | R8N86A | 1 U | 53 |
| HPE Aruba 6100-24G-4SFP+ | JL678A | 1 U | 29 |
| Ubiquiti UniFi Switch Pro Max 48 PoE | USW-Pro-Max-48-PoE | 1 U | 53 |

## Cómo ver y revisar las carcasas

1. Abre `VER-SELECCION-506-A.html` desde la raíz de RackClick con Edge o Chrome. Conserva la carpeta `PERFILES-SELECCION-506-A` a su lado. No requiere cuenta ni PowerShell.
2. Arriba a la izquierda, en **Buscar marca o modelo**, escribe el SKU o nombre. Debajo, pulsa el modelo. Comprueba título, SKU y dimensiones en el centro.
3. Revisa **Frontal** y **Trasera** y despliega **Alcance y límites de las fuentes de este modelo**. Las referencias comunitarias se indican como tales; el dibujo no certifica una revisión serial, instalación de módulos, carga o ventilación.
4. Pulsa una boca y su puerto de prueba compatible debajo de las caras. Para AC usa **Salida AC de prueba**. Desplaza la cara y verifica el anclaje. Esta conexión es sólo demostración local.
5. Debajo, en **Tu revisión de este modelo**, marca Pass, Not Pass o No probado y escribe tu observación. A la izquierda, **Exportar mis resultados JSON** guarda `RackClick-Revision-Visual-506A.json`. Sus notas están separadas de los lotes anteriores; importar sólo rellena casillas vacías.

## Uso en el sistema y paquete

En una futura candidata completa de esquema 29 identificada, abre **Clientes**, entra al rack sintético y pulsa arriba **Añadir hardware de referencia**. Elige el modelo/SKU con revisión `selected506a-20261101-v1`, escribe el nombre y selecciona rack. Los dos compactos R8N89A/JL679A requieren una bandeja explícita compatible; no se incluyen orejas instaladas por suposición. Espera **Guardado por el servidor**, conecta extremos compatibles, recarga y contrasta otra sesión. Un lector consulta y no edita.

La integración ha sido ensayada en laboratorio de desarrollo. **No se actualizó la instalación QA, ninguna VM ni su MFA.** El ZIP de revisión no es instalador; no copies DLL, SQL o JS aislados al servidor. El paquete completo con todos los 506, consumidores, distribución, operadores, Restore e instalación Windows sigue pendiente.

## Correcciones y límites

La revisión reprodujo y se corrigieron: activar PoE sobre RJ45 hacía perder la geometría específica; un hardware con entrada eléctrica fija admitía cambiar su rol a salida. Se conservaron los negativos contra la DLL/módulos 28, y los positivos finales permiten PoE sin perder UUID, rechazan el cambio de rol sin mutación y mantienen editables los puertos genéricos. También se corrigió el contraste de rótulos claros sobre placas plateadas, sin alterar el color del producto o sus conectores.

El primer test Node del autor confundía el primer puerto del modelo con el primero en orden físico; se corrigió para localizarlo por UUID. El fallo de fixture se conserva, no se presenta como defecto del producto. Las referencias originales, primera app/Atlas y pruebas previas a la corrección de contraste se conservan separadas.

Consola, USB y RPS/DC sin contrato siguen inertes y rotulados. SFP representa la jaula vacía, no módulos ópticos instalados ni negociación de velocidad. AC es documentación general, no certificación de clavija, cable, tensión o carga. La aceptación estética sigue siendo de Wascar.

## Trabajo siguiente para completar la petición

Continuar desde los 438 ID aún sin perfil; reutilizar coincidencias exactas revisadas antes de duplicar. Ampliar los contratos que corresponden a conectores, chasis modulares, racks, 0U/DIN y fracciones, sin inventar cotas, puertos o montaje. El [contrato operativo](INTEGRACION-506-CONTRATO-OPERATIVO.md) distingue alternativas y lo que no satisfaría una carcasa física exacta. No sustituir estos trabajos por expedientes o variantes contadas como nuevos modelos.

Investigación, hashes y resultados: `evidence/s1-20261101/integracion506/`. Binlogs, secretos, capturas y logs crudos sólo en `.local`. Índice del cierre restante **9,76/100**, sin incremento automático; no se calcula un nuevo porcentaje global.
