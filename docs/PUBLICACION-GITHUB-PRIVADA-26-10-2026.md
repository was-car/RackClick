# Preparación de RackClick para GitHub privado

## Estado vigente · publicación completada

**26.10.2026:** publicado [was-car/RackClick](https://github.com/was-car/RackClick), **privado**, rama principal `main`, commit `1dc0c1f33c26c339d06d05b07ec3ce84fabed935` (995 archivos). Git Credential Manager autenticó `was-car`; la API oficial confirmó la cuenta y la ausencia del repositorio antes de crearlo privado, sin contenido inicial. Se subió la copia preparada mediante un push normal, sin reescribir ramas.

La API oficial volvió a comprobar `private:true`, `visibility:private`, rama predeterminada `main` y el SHA remoto exacto a las `2026-10-26T00:24:15.843951Z`. [Registro sanitizado](../evidence/s1-20261026/github-private-preparation/PUBLICACION-VERIFICADA.json). El repositorio original conserva su HEAD e historial; su índice y las fuentes concurrentes no se incorporaron al push. Las secciones de preparación siguientes conservan el estado anterior como historia.

Las próximas actualizaciones deben salir de fuentes revisadas, con selección y escaneo; no copiar indiscriminadamente el workspace. La publicación no habilita MFA ni constituye una release, un instalador o una adopción del servidor. Sin operaciones sobre VM/QA. **Cierre funcional pendiente: 7,63/100**, sin crédito nuevo por publicar.

## Preparación histórica · anterior a la conexión

**Autorización de Wascar · 26.10.2026:** repositorio privado, cuenta `was-car`, nombre previsto `RackClick`. Publicar fuentes de desarrollo e ir actualizándolas; no hacer público el repositorio, desplegar o declarar una release por esta autorización.

## Qué se ha preparado

Una copia seleccionada bajo `.local/github-private-…/repository`, independiente del índice/historial del workspace. Su ubicación actual está en `.local/github-private-current.json`. Se conserva `C:\RackClick_SVR` con sus cambios, evidencias y commits originales.

La selección incluye código servidor/frontend/servicio Windows, SQL, pruebas, herramientas propias, locks, documentación clave y la referencia RC9 adoptada que requiere el build frontend. Excluye laboratorios, backups/dumps, certificados/claves, binlogs/diagnósticos, resultados de Wascar, transcripciones, las evidencias históricas masivas y los repositorios externos descargados para investigación. No se publican candidatas o instaladores congelados.

No se asigna MIT u otra licencia abierta al código propio. Se conservan avisos de terceros. Derechos de redistribución de paquetes y una eventual apertura pública se decidirán aparte.

## Ajustes sólo en la copia exportada

- Cuatro contraseñas constantes de fixtures se generan con CSPRNG al ejecutar las pruebas. Se conserva el resto de sus bytes, incluidos finales de línea. `PUBLICATION-TRANSFORMS.json` contiene rutas y hashes, sin valores.
- Se excluyen 20 auxiliares de cierre histórico `tools/tests/close_*.py` que no forman parte del flujo normal del clon.
- Escritor L2c/tests fijados a la última copia revisada (`365e…38ccd`/`4c9b…e7e5e`), con MFA-L2C-01 declarado pendiente. Los cambios concurrentes posteriores del workspace no se pisan ni se anuncian revisados.
- README/continuidad/progreso/changelog de la copia describen su alcance actual; el historial documental completo se conserva localmente.
- Configuración VS Code sin rutas privadas; workflow de seguridad como ejemplo no activo. No se activa CI o despliegue automático.

## Verificaciones realmente ejecutadas

- Gitleaks oficial **8.30.1**, fijado y verificado: escaneo de la selección y del índice sin hallazgos tras los ajustes. El primer intento detectó cinco coincidencias, preservadas en el informe privado; no se silenció ni relajó el escáner.
- Se auditó también el contenido textual del ZIP de referencia RC9, extraído en un directorio privado separado: cero hallazgos. No se ejecutó el contenido.
- SDK10.0.401, restore locked/build Release y **54 pruebas afectadas PASS, sin omisiones**, con PostgreSQL17.11 nuevo. 76,547s, laboratorio detenido. No es un ensayo completo de producto ni instalación Windows.
- Revisor distinto confirmó las cuatro sustituciones exactas en bytes y los dos pins. El primer exportado alteraba EOL y se rehízo antes del commit; no se modificaron las fuentes originales.
- Hook de secretos habilitado sólo en la copia. Logs/TRX/binlogs y reportes completos permanecen privados.

No se promete que toda la regresión histórica o los instaladores congelados se reconstruyan desde este clon: requieren artefactos locales excluidos. El frontend declara `test:build` con un archivo actualmente ausente; se documenta, no se anuncia ese chequeo como disponible.

## Estado remoto y continuación

**Aún no se ha subido nada desde esta sesión.** No existe acceso GitHub conectado en las herramientas de esta conversación y Git Credential Manager no devolvió cuentas disponibles. La cuenta pública `was-car` sí se verificó por API oficial. El estado de un repositorio privado homónimo no puede decidirse por una consulta anónima.

Falta conectar GitHub con `was-car`. Con acceso disponible: comprobar primero si `was-car/RackClick` existe y es privado; crear sólo si corresponde, conservar repositorios existentes, subir la copia preparada y verificar visibilidad/commit. No convertir un repositorio público existente o sobrescribir ramas sin resolver ese estado concreto. No se necesita otra aprobación de arranque para el destino privado ya autorizado.

Las actualizaciones deben salir de fuentes revisadas, con pruebas pertinentes, selección y escaneo; no importar el historial local completo ni añadir archivos indiscriminadamente. Conservar la asignación de Claude y las revisiones antes de incorporar correcciones concurrentes.

El estado local de commit/bundle y verificación se registra en el cierre de evidencia de esta preparación. **Cierre funcional pendiente 7,63/100**, sin crédito por preparar/publicar el repositorio. MFA sigue sin habilitar y adopción/QA final pendientes.

## Foto local final preparada

Commit `1dc0c1f33c26c339d06d05b07ec3ce84fabed935`, **995 archivos**, copia sin modificaciones pendientes. Fuentes finales e historial nuevo: cero hallazgos. ZIP de fuentes y bundle Git verificados disponibles bajo el puntero privado; [cierre y hashes](../evidence/s1-20261026/github-private-preparation/CIERRE.md). **Todavía `pushed:false`**: queda conectar GitHub y verificar/subir al destino privado autorizado.
