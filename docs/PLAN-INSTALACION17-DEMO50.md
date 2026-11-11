# Instalación nueva 17 · aplicación 48 · Demo50 trilingüe

Solicitud de Wascar, 11.11.2026. Preparar una instalación Windows Server nueva con los cambios revisados y los 50 clientes ficticios. Conservar D y las instalaciones anteriores de E. Destino pendiente de identificar por Wascar; encendido, snapshots y reinicio manual a su cargo.

## Contrato y reutilización

- Reutilizar el producto48 revisado en F-09.04, sin reconstruir funciones ni mezclar fuentes anteriores45. Comprobar sus hashes y publicar sin recompilar cuando coincidan.
- Reutilizar la cadena oficial de distribución/bundle/envoltorio16, sus dependencias fijadas (SDK10.0.401, runtime10.0.12, PostgreSQL17.11) y servicio Windows. Crear perfil48 y edición17 separados; conservar entregas históricas.
- Instalación **New**. Restore48 y cambio automático de red48 no están ensayados y no se habilitan por analogía.
- Demo50: 17 empresas EN,17 DE,16 ES. Nombres propios permanentes, independientes del idioma de interfaz. Conservar inventarios, comandos, relaciones y modelos; importar sólo inventario, sin usuarios, sesiones, contraseñas ni factores del origen.
- Catálogo instalado884 revisiones/877 modelos; Demo50 conserva cobertura de868 revisiones/506 modelos originales. No afirmar que las16 revisiones posteriores estén colocadas en estos datos.
- Política MFA vigente: gracia45/exención global; no desactivar un factor del operador para cargar los datos.

## Investigación antes de implementar

Se contrastaron `INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md`, el lector nativo, recolectores, `RackClick.Instance.ps1`, migraciones046–048 y `CARGADOR-DEMO50-02.md`. Fuentes y licencias ya fijadas en `development/offline-bundle14.sources.json`; no se añade dependencia ni se descarga una versión nueva.

Referencias oficiales reutilizadas: [GRANT PostgreSQL17](https://www.postgresql.org/docs/17/sql-grant.html), [pg_dump17](https://www.postgresql.org/docs/17/app-pgdump.html), [dotnet publish](https://learn.microsoft.com/dotnet/core/tools/dotnet-publish), [PowerShell5.1](https://learn.microsoft.com/powershell/scripting/windows-powershell/overview?view=powershell-5.1).

Decisión: adaptar el pipeline existente. Runtime sólo lee catálogo y testigos; no accede al archivo privado. Backup mínimo3 necesita SELECT sobre las dos tablas privadas nuevas para el dump completo. Se verificará con PostgreSQL real, no sólo con búsqueda de texto.

## Secuencia

1. Congelar fuentes y procedencia; agregar perfil48 y contratos cerrados, permisos y pruebas negativas.
2. Publicar/validar distribución48; construir bundle, payload y envoltorio17; comprobar cadena de hashes y contenidos. Manual autónomo paso00–fin.
3. Preparar variante Demo50 y cargador03, con invariantes de topología y pruebas de rechazo. Revisión independiente acotada de ambos cambios.
4. Sólo sobre VM nueva identificada: instalación completa, cuenta estándar/SQL mínimo3, HTTPS/MFA, backup y reinicio; conservar D/E.
5. Cargar50 por API y comparar ocho colecciones, nombres EN/DE/ES, guardado y nueva copia. Registrar pruebas reales y límites.
6. Actualizar continuidad, changelog y guía QA. No acreditar puntos por fabricar paquetes ni anunciar adopción productiva.

## Registro

- Preparación iniciada. La edición16 es45; no se presenta como48.
- VM destino: pendiente de respuesta. No se ha accedido a D/E ni iniciado instalación.
- Índice acreditado conservado:26,63/100 del cierre restante. No es porcentaje global nuevo del producto.

-Preparación y revisión independiente completadas: entrega73miembros,New48/backup/dump probados en laboratorio. SinVM identificada todavía; pasos4–5/instalación y carga real pendientes. No se ha operado D/E.
