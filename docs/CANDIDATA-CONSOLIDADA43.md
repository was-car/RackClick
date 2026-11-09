# Candidata consolidada43 · punto2 ·02.11.2026

La distribución de aplicación reúne **catálogo, interfaz, MFA/gracia45 y administración existentes**. Está congelada y comprobada en laboratorio. El ZIP de revisión contiene servidor, frontend,43 migraciones, manifiestos, verificadores de sólo lectura y avisos de licencias.

[Descargar ZIP de revisión](../RackClick-Candidata43-Revision-01.zip) · [SHA256 externo](../RackClick-Candidata43-Revision-01.zip.sha256) · [Resultados](../evidence/s1-20261102/candidata43/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261102/candidata43/review/REVISION.md).

**Es la distribución de aplicación del punto2. El instalador Windows completo corresponde al punto5.** No se ha actualizado tu VM ni QA. No uses los instaladores10/15 para aplicar esta distribución ni copies DLL/SQL sobre un servidor instalado.

## Qué contiene y qué se conserva

- 71 archivos de aplicación:53 de servidor (10 de aplicación y43 SQL) y18 de frontend. El ZIP de revisión tiene82 entradas, incluidos metadatos, verificadores y licencias.
- 868 definiciones/revisiones del catálogo:862 revisiones comerciales,861 modelos comerciales distintos. Selección original506/506 y355 adicionales fuera de ese denominador. Se mantienen las reservas de geometría, BOM y funcionalidad por modelo.
- Las37 fuentes backend y38 frontend de MFA/administración contrastadas son idénticas a la candidata10 y a la base43. No se reimplementó MFA ni se mezcló el árbol de trabajo concurrente.
- Se mantienen45 días de gracia, el inicio correspondiente a cuentas nuevas/existentes y la exención sólo para administradores globales del Systemhaus. El proveedor Windows continúa requiriendo configuración explícita y custodia válida. El ZIP no contiene claves ni activa políticas por sí mismo.
- Se reutilizan los binarios y frontend exactos del punto1. La publicación Release se hizo sin restaurar, recompilar ni añadir apphost, con binlog privado. No se cambian versiones de dependencias.

## Verificar el ZIP sin instalar

1. En el equipo donde descargaste el archivo, abre Inicio, escribe **PowerShell** y pulsa Enter. No hace falta abrirlo como administrador.
2. Ejecuta este comando, ajustando sólo la ubicación del ZIP si lo guardaste en otra carpeta:

```powershell
Get-FileHash -LiteralPath 'C:\RackClick_SVR\RackClick-Candidata43-Revision-01.zip' -Algorithm SHA256
```

Debe devolver `af1c54b288ecbf5dd42ee6db138979254817a31665a2b36e5b642ed19f554808`. Si no coincide, detente.

3. Extrae el ZIP en una carpeta nueva, por ejemplo `C:\RackClick-Revision43`. Abre la carpeta interior `RackClick-Candidata43-Revision-01` y sigue **LEEME.md**. Su comprobación sólo lee los archivos: debe devolver `artifacts_verified`, esquema43,71 archivos y salida0.
4. Conserva el ZIP, su SHA externo y el resultado. No lances una instalación ni cambies el servidor con este paquete. Las pruebas de interfaz en tu VM siguen usando la candidata allí instalada.

## Pruebas de esta consolidación

| Comprobación | Resultado y límite |
|---|---|
| Publicación |10 archivos de aplicación+43 SQL; DLL, dependencias y SQL coinciden con la base probada; frontend exacto. |
| Generador/verificador |33 pruebas pasan sin omisiones:17 del perfil43 y16 de regresión15. Rechazos de digest, manifiesto rehecho, SQL ausente/alterado, frontend alterado, apphost y extras. El perfil15 histórico sigue verificándose. |
| Publicación real en PG17.11 |Bootstrap43,868 definiciones, siete tablas de catálogo conSELECT-only para runtime, alta de switch con29 extremos, lectura de administración/estadoMFA, lector403 sin cambios, segunda cuenta y reinicio de proceso. |
| MFA y administración |18 pruebas pasan sin omisiones sobre los mismos ensamblados y el frontend publicado. Incluyen política/permisos, HTTP y Edge: aviso35 días, exención global,EN/DE/ES, activación propia/administrativa, enrolamiento, reset y siguiente login TOTP. |
| Revisión independiente |Cuatro focos propios de integridad/negativos e histórico15; revisión de inventario, dependencias y alcance. Los ensayos PG/MFA son del coordinador, no del revisor. |

Los ensayos MFA usan proveedor sintético sólo en el host de pruebas y HTTP loopback. No sustituyen la prueba bajo la cuenta real del servicio, HTTPS o reinicio Windows. El catálogo del punto1 conserva sus propias pruebas sin repetir las124caras ni las suites995Node/35C# por empaquetar bytes idénticos.

## Reproducir la distribución

El generador de producción es `tools/build_server_distribution.py`, con perfil cerrado `docs/DISTRIBUCION43-PERFIL.json`. Requiere publicación Release sin apphost de la fuente congelada y el frontend identificado. Usar una carpeta de salida nueva y los argumentos exactos de procedencia del manifiesto. El generador no acepta un perfil copiado o desconocido y conserva los perfiles14/15.

La publicación se puede preparar con el SDK fijado10.0.401 mediante `dotnet publish -c Release --no-build --no-restore -p:UseAppHost=false`, manteniendo las opciones del build validado y un binlog privado. Después deben verificarse los hashes del contenido; un build nuevo puede cambiar PDB/manifiesto por rutas de origen. No se promete reproducción binaria universal desde cualquier ruta o clon. Los PDB de esta entrega contienen rutas de desarrollo y símbolos.

El manifiesto de esta candidata tiene SHA256 `eb274f1f82deb9936c69214fae07e4188275063cf35ec775fe41d560a1806830`. No es firma ni prueba de autenticidad. La reconstrucción actual depende de la fuente congelada y cachés locales identificadas; cerrar la entrega reproducible de instalación sigue siendo parte del punto5.

## Lo que sigue abierto

1. Punto3: recuperaciónMFA integral, rotación/códigos/emergencia y últimos controles; administración/permisos e importación/exportación/backup desde dashboard según la hoja de ruta. Se conserva lo ya implementado.
2. Laboratorio de50 clientes sintéticos con infraestructuras y matriz por perfil, después de fijar esta candidata. Esta distribución no incorpora usuarios, factores ni la base privada del laboratorio.
3. Punto5: propagar esquema43 al instalador, OfflineBundle,Stage,runtime,New/Restore y red; aplicarSELECT-only a las siete tablas del catálogo tras las concesiones DML deNew/Restore. Sin ello, el servidor rechazaría crear hardware con `hardware_catalog_permissions_invalid`.
4. Ensayar Windows limpio, restauración, cuentas/servicio,HTTPS,backup/reinicio y actualización/recuperación; completar manual y QA de Wascar. Los operadores antiguos permanecen sin ampliar a43 en esta tanda.

No hay commits, push, publicación ni adopción. QA-162 sigue planificada para una instalación adecuada; resultados anteriores de Wascar intactos. **Catálogo elegido100% en desarrollo; índice de cierre restante9,76/100 sin cambio y sin porcentaje global nuevo.**
