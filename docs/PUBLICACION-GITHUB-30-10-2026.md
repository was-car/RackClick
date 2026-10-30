# Actualización privada de RackClick · 30.10.2026

Wascar solicitó actualizar `was-car/RackClick` antes de continuar el siguiente bloque de producto. El repositorio ya existía y se comprobó privado, con acceso a su cuenta. La selección se prepara y publica desde un clon separado: no se incorpora el árbol concurrente completo ni se modifica la instalación de QA.

## Contenido de la actualización

- Fuentes congeladas de servidor y frontend de la candidata 10, esquema 15: panel MFA propio y administrativo, enrolamiento/login, custodia Windows y política confirmada de 45 días/exención global. La identidad acreditada es de fuentes; no se promete reproducir el mismo binario bit a bit.
- Inventario sintético original en `development/examples/demo-original.inventory.json`, SHA256 `cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7`. Sólo tablas de inventario: 10 clientes, 68 racks, 311 equipos, 5408 puertos y 623 conexiones. Sin datos de autenticación ni dump de la base instalada.
- [Manual de instalación desde GitHub](INSTALACION-DESDE-GITHUB.md) y `tools/start_demo.py`: herramientas oficiales fijadas, compilación y laboratorio PostgreSQL nuevo con claves locales aleatorias, carga confirmada y parada de sus propios procesos. El laboratorio es HTTP en loopback y mantiene el proveedor MFA desactivado; no es el servicio Windows ni el ensayo de activación real.
- [Guía de fuentes oficiales](FUENTES-OFICIALES-DESARROLLO.md): JavaScript/DOM/React, .NET/Windows/PowerShell, PostgreSQL/Npgsql y repositorios originales. Distingue referencias, ejemplos y licencias. Se mantiene la regla de investigar antes de implementar y de probar la adaptación en RackClick.
- Hoja de ruta, registro maestro, comparación RC10 y decisiones vigentes. Se actualiza OPS-01 sin añadir puntos de cierre por publicar código.

`BASELINE-SOURCES.json` del repositorio identifica los 221 archivos de producto contrastados. `PUBLICATION-TRANSFORMS.json` registra seis sustituciones de contraseñas constantes de pruebas por generación CSPRNG, sólo en la selección exportada. Las aserciones y las fuentes de producto no cambian por esas sustituciones; los originales siguen en su workspace.

## Límites de la entrega

El instalador nativo 10 y sus ZIP históricos se conservan localmente, intactos. **No se suben binarios como Release**: la [revisión independiente de publicación](REVISION-PUBLICACION-30-10-2026.md) mantiene abiertas condiciones de redistribución VC++ y una referencia de licencia del servicio. El manual nativo se incorpora, sin anunciar que descargar las fuentes equivale a disponer del instalador completo.

No se incluyen claves DPAPI, sobres MFA, certificados privados, cuentas, sesiones, contraseñas, cadenas de conexión, bases, binlogs, transcripciones ni exportaciones personales de Wascar. El código propio no recibe licencia abierta. No se habilita CI, despliegue automático ni visibilidad pública.

La recuperación portable de MFA, códigos/emergencia, rotación, recuperación integral y QA/adopción final siguen pendientes. La carga automática del ejemplo no implementa importación/exportación general desde el dashboard.

## Verificación de esta selección

Resultado final sobre esta selección: servidor378 Pass/0 Fail/3 omitidas, dominio76 Pass, frontend801 Pass, cargador PostgreSQL11 Pass y guardas del auxiliar6 Pass; smoke correcto con inventario completo. [Pruebas, correcciones y límites](../evidence/s1-20261030/github-update/RESULTADOS.md). Los resultados anteriores de Windows/VM no se convierten en ejecuciones nuevas. Se conserva un primer intento de regresión interrumpido: el lanzador privado heredó `MfaKeyStore__Enabled=false` del modo demo y anuló la configuración JSON de una prueba de arranque. Se corrigió el entorno del lanzador, sin cambiar producto ni expectativas, antes de repetir la regresión.

La revisión de fuentes es de una persona distinta del implementador. El revisor contrastó fuentes, transformaciones, seed y manual; las compilaciones, pruebas y smoke declarados como del implementador no se atribuyen al revisor.

## Continuación

Tras esta actualización se retoma [la prioridad maestra](HOJA-DE-RUTA-MAESTRA.md): racks primero e informes compactos; contrato del catálogo por fabricante; recuperación portable MFA aprovechando los componentes existentes. El índice de cierre restante permanece **9,76/100**, con la misma base y pesos; no se recalcula un porcentaje global del producto por este trabajo de publicación.
