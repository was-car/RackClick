# Revisión independiente — primer modelo comercial

30.10.2026. Revisor `commercial_review`, distinto de los implementadores.
**Favorable para este foco interno**, sin bloqueo funcional identificado.
No es adopción, publicación externa o autorización de instalación en QA.

## Alcance y contraste físico

Leídos los datos comerciales/facts/lock18 y sus derivados, los compiladores16/18,
SQL018, registro y lector de catálogo C#/Npgsql, creación/persistencia de identidad,
catálogo dual y selector por pareja, proyección y representación de caras,
diccionarios/CSS y compuertas de build. Los hashes están en
`evidence/s1-20261030/hardware-commercial/review/HASHES-REVISADOS.json`.

Consultada directamente la [ficha oficial de StarTech.com](https://media.startech.com/cms/pdfs/c6panelutp241uft_datasheet.pdf).
Se confirma el SKU C6PANELUTP241UFT, panel1U con24acopladoresRJ45 preinstalados,
acceso directo por ambas caras, negro y magnitudes métricas nominales.
El eje largo de19pulgadas se representa como ancho montado:483mm; fondo138mm y
altura44,3mm. No se mezclan valores más precisos de otras fichas/cachés.
**24acopladores equivalen a48extremos físicos, no48interfaces Ethernet activas.**

La revisión de catálogo `startech-20261030-v1` no se presenta como revisión física
del fabricante. Fecha de lanzamiento/revisiónHW permanecen desconocidas. La
numeración trasera es lógica; no se afirma que esté impresa. La inversión del
orden trasero representa una vista esquemática exterior, sin afirmar coordenadas
CAD verificadas. No se incorporan alimentación, IDC, módulos ausentes o PoE
por deducción. La correspondencia declarada no añade cables ni trazado interno.

No se copian fotografías/logotipos al renderer. La vista y el enlace a ficha
distinguen esquema propio y fuente. Los campos escritos por el usuario siguen
siendo datos de React, sin HTML añadido. La imagen/PDF privada del coordinador
no se usa como recurso de producto por esta revisión.

## Coherencia técnica revisada

- La fuente comercial se separa de las cuatro referencias congeladas. Su lock
  fija fuente, hechos, digest canónico y migración017 de base. Los hashes son
  coherencia del repositorio, no firmas o permisos para adoptar otro modelo.
- SQL018 amplía altura/fondo a numeric sin truncar valores anteriores; no
  desactiva los triggers17. Inserta borrador/componentes y sella al terminar.
  La migración sigue dentro de la transacción de migración existente.
- El lector usa decimal y compara identidad, dimensiones, grupos, slots y
  correspondencia con la revisión compilada. Runtime conserva sóloSELECT del
  catálogo y no se usa como migrador.
- El registro se compone perezosamente para no depender del orden de campos
  estáticos entre archivos parciales. Conserva claves/revisiones exactas y
  colecciones protegidas. La creación comercial sin revisión explícita no se
  convierte en latest: queda rechazada; el alias anterior permanece v1.
- Las opciones se identifican por pareja clave/revisión. Se guarda también la
  identidad del modelo en la instancia y se protege contra edición genérica.
  Las dos caras usan UUIDs/grupos distintos aunque repitan el ordinal1.
- Se contrastaron byte a byte las migraciones001–017 con la copia17 anterior:
  todas intactas. JSONhistórico `hardware-reference.json` conserva su hash.

Detalle documental menor: el resumenXML de `InventoryHardwareProfiles` aún
describe exclusivamente perfiles sintéticos. No cambia la ejecución ni los
datos; conviene actualizarlo al mantener este módulo.

## Focos ejecutados por el revisor

Comando propio reproducible:

```powershell
C:/Python312/python.exe -X utf8 -B evidence/s1-20261030/hardware-commercial/review/probe_commercial_review.py
```

Windows, Python3.12, Node24.21.0 y PostgreSQL17.11. **8focos PASS,0FAIL** en
`review/FOCOS.json`:

1. 44,3 conservado en C#, SQL y JSON derivados.
2. Cambio no revisado de altura rechazado sin alterar derivados existentes.
3. Node real: parejas exactas, preservación de referencias, revisión explícita,
identidad inmutable y ausencia de tipos de conector inventados.
4. Bootstrap18 real con definición sellada y dimensiones exactas.
5. Dos instancias HTTP con96UUIDs distintos,48conectores por objeto y replay
sin nuevas filas/auditoría/revisión.
6. Versión incorrecta y reescritura de identidad422sin cambios de estado.
7. Login PostgreSQL de runtime real: lectura de cinco definiciones y UPDATE
del modelo comercial denegado.
8. Solicitud antigua sin versión aún crea el switch de referencia v1.

El laboratorio independiente fue nuevo y quedó detenido, igual que su servidor.
DLL ensayada:
`0a63c71f26737fecf762e6723b3fda2c255ec4ba3f66e8462280d684401b0610`.
SQL018:
`71b9151c7ddd8b2c8b28f2de49f4ef312b3ca6d406f1054685424392c85535ad`.

## Límites

No ejecuté Edge, la actualización17→18 del coordinador, la suite completa,
compilaciones, instalador, rollback operativo, servicioWindows, backup/restore,
VM o QA. No se me atribuyen los resultados de esos ensayos. No se prueba equipo
físico, carga eléctrica, rendimiento de línea o autenticidad industrial del
dibujo. El catálogo comercial completo y sus variantes continúan fuera del foco.
No se incrementan pesos, porcentaje o aceptación por esta revisión.
