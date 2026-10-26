# Comprobaciones de seguridad locales

Herramienta de desarrollo, sin operar el servidor/VM ni leer credenciales,
backups o directorios privados existentes. Lee sólo su propio caché de
herramientas y sus informes en `.local`. Python 3.12 y Git existentes.
Ejecutar desde la raíz:

```powershell
C:/Python312/python.exe -B tools/security/secret_scan.py install
C:/Python312/python.exe -B tools/security/secret_scan.py scan --mode all
C:/Python312/python.exe -B -m unittest discover -s tools/tests/security -v
# Opt-in explícito; preserva configuraciones/hooks preexistentes:
C:/Python312/python.exe -B tools/security/secret_scan.py install-hook
```

`install` obtiene exclusivamente el release oficial fijado en `gitleaks.lock.json`.
Verifica SHA256 del manifiesto y del ZIP/tar antes de extraer un único binario;
cada scan verifica nuevamente archivo, binario y versión. No usa PATH para buscar
Gitleaks, no instala globalmente y no sustituye silenciosamente una instalación
alterada. Plataformas previstas: Windows x64 (ejecutada aquí) y Linux x64 (CI
pendiente). Los hashes de release garantizan integridad respecto de los valores
revisados; no se afirma una verificación de firma del autor.

`all` examina el historial alcanzable por todos los refs locales (`--all
--full-history -m`, incluidos cambios de cada padre de merges) y enlaces
temporales de archivos regulares tracked del working tree.
Los enlaces se usan sólo en lectura; retirarlos no cambia los originales.
La edición concurrente del working tree puede cambiar lo que lee ese barrido,
igual que un análisis directo de la carpeta; no se declara snapshot atómico.
Rechaza repositorios shallow. No examina objetos colgantes, archivos untracked,
archivos binarios que Gitleaks no interpreta como texto ni contenido dentro de
ZIP u otros archivos comprimidos; sí intenta decodificación de texto hasta dos
niveles. Esta cobertura no equivale a ausencia de cualquier secreto.
Un archivo tracked privado, enlace o entrada no regular deja la comprobación
incompleta. No se lee su contenido ni se amplían exclusiones para obtener verde.

El hook examina el contenido completo de archivos regulares añadidos o cambiados
en el índice, aunque el working tree tenga otra versión. Un archivo privado
staged se rechaza antes de leerlo. El hook no examina todo el historial en cada
commit. Es local y opt-in; no sustituye revisión ni la futura CI. Git permite
omitir hooks deliberadamente (`--no-verify`), por lo que no constituye una
frontera de autorización.

Códigos: **0** comprobación completa sin hallazgos; **10** hallazgos que requieren
clasificación; **2** error/comprobación incompleta. Sin baseline, exclusiones
globales ni `gitleaks:allow`; no rotación automática ni reescritura del historial.
Los stdout/stderr de Gitleaks siempre se capturan y nunca se imprimen. Se fuerza
`--redact=100`; el informe final conserva regla, ruta, líneas, nombre de campo
y clasificación orientativa por su contexto, sin Match,
Secret, hashes de commit, autores o emails. Se guarda bajo
`.local/security/PRIVADOS.local/<id>/`, ignorado por Git; el informe intermedio
redactado se retira. No subir estos informes al repositorio ni a servicios.
La clasificación distingue campos de digest, rutas de fixtures, candidatos de
credencial e indeterminados. No prueba que un valor sea real/falso ni elimina
hallazgos: todos siguen contando y bloqueando el barrido correspondiente.
Tras validar todos los nombres/tipos históricos sin leer blobs, la clasificación
consulta sólo la línea versionada correspondiente o la copia propia del working
tree. Distingue un escalar JSON HEX64 asociado a nombre de archivo y una clave
UUID de solicitudes; guarda sólo nombre de campo/contexto. HEX64 verifica forma,
no acredita por sí sola que el valor sea un SHA del archivo ni una credencial.

El instalador del hook modifica sólo `core.hooksPath` local a `.githooks` cuando
no hay configuración/hooks anteriores. Reversión, sólo si esa configuración fue
creada por este comando: `git config --local --unset core.hooksPath`.
La descarga/binario permanecen en `.local/security-tools`, sin afectar otros SDK.

`.github/workflows/security.yml` es un **borrador manual local**. No se ha
publicado, ejecutado en GitHub ni creado un remoto. Además de `workflow_dispatch`
exige un booleano explícito. Las acciones oficiales se fijan por SHA; SDK se
obtiene del `global.json` vigente, con `rollForward=disable`, restore locked,
build, auditoría NuGet directa/transitiva y arnés de dominio. Otro job opcional
llama al nuevo proyecto xUnit con Docker obligatorio en el runner; no instala
Docker aquí. No hay subida de informes, despliegue ni CodeQL configurado.
Repositorios privados requieren comprobar contrato/licencia y autorización de
hosting antes de activar herramientas externas.

Fuentes oficiales consultadas (21.10.2026):

- [Release Gitleaks v8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)
- [CLI/configuración de esa versión](https://github.com/gitleaks/gitleaks/blob/v8.30.1/README.md)
- [Checksums oficiales](https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt)
- [Auditoría dotnet package list](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-package-list)
- [setup-dotnet/global.json](https://github.com/actions/setup-dotnet)
- [Disponibilidad CodeQL en privados](https://docs.github.com/en/code-security/reference/code-scanning/troubleshoot-analysis-errors/private-repository-enablement)
