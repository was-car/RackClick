# Instalador 07 (esquema 14) · D14-07 integrado, validación de edición y edición nueva · resultados

Implementador: Claude. Revisión independiente: **pendiente (Codex)**. Estado: **candidata interna de ensayo; NO adoptada; NO instalada en Windows Server; no aprobada para QA**. No hay commits, no hay cambios en QA ni en la VM. La edición 06 queda intacta. Avance global aproximado: **~78 %**, sin incremento.

Origen de la tanda (`docs/MENSAJE-PARA-CLAUDE-INSTALADOR06-25-10-2026.md`, `docs/REVISION-INSTALADOR14-06-CODEX.md`):

1. Integrar **D14-07** (parada del runtime) y repetir sus pruebas.
2. Validar `edition` antes de crear archivos, con negativos sin salidas.
3. Corregir la afirmación de que los valores por defecto reproducían la 05.
4. Generar una **edición nueva** de payload, envoltorio y CMD sin sobrescribir la 06.

## 1. D14-07 · publicación atómica de `stop-request.json`

**Problema.** `Invoke-RackClickServerRuntime.ps1` escribía la orden de parada directamente en `stop-request.json`. El lector del arranque podía verla antes de terminar y responder `stop_request_invalid`, con la aplicación ya parada.

**Cambio.** Se aplicó **la propuesta atómica de Codex** (`PROPUESTA-ATOMICA.patch`, copiada en `d14-07/`) sobre el fichero compartido. Escritura a un temporal único en el mismo directorio privado, comprobación de ACL, `File.Move` sin sobrescribir, y si otro Stop ya publicó primero se valida su contenido. El temporal se borra siempre.

| Fichero | SHA256 antes | SHA256 después |
|---|---|---|
| `tools/windows/server-install/Invoke-RackClickServerRuntime.ps1` | `29c55fd16eef55aab2e8d1640257fc5990656f195fcec0915faf7e6645ce94b9` | `f08466f2a7633074131ad0a261bdb98f83f5a292e5a8a366c04e76cd6cfca2ed` |

**Foco determinista** (`reproduce_stop_publish_writer.ps1`, bloque real del escritor y del lector, punto de ruptura justo después de `CreateNew`):

| Variante | Lector durante la escritura | Después de publicar |
|---|---|---|
| Original (copia S2, `29c55fd1…`) | `stop_request_invalid` con el fichero final visible | Acepta la orden |
| Atomica (`f08466f2…`) | `no_final_request` (solo existe el temporal) | Acepta la orden |

Ambas variantes rechazan un fichero malformado. Salidas en `d14-07/FOCO-WRITER-*.json`.

**Ciclo de vida completo** (`evidence/s1-20261025/runtime14-perfil-codex/observe_server_runtime.py`, runtime de producción en primer plano, aplicación `e9c58c0c…`, DLL `19c94d4e…`, PostgreSQL 17.11 propio, laboratorio privado nuevo):

| Paso | Resultado |
|---|---|
| Despliegue privado nuevo (`New-RackClickPrivateDeployment`) | `deployment_prepared` |
| Perfil del servidor y verificación | `server_profile_prepared`, `server_profile_verified` |
| Pin de perfil incorrecto | Rechazado `server_manifest_hash_mismatch` |
| Primer arranque | Listo; HTTPS verificado con CA del cliente; esquema 14; login; CSRF negativo; escritura y lectura |
| Parada de una ejecución ajena | Rechazada `server_active_run_changed`; el runtime sigue listo |
| Backup online | `backup_complete` |
| Primera parada | `server_stopped`, `postgresCleanStop=true`, `applicationGracefulExit=true` |
| Repetición exacta de la parada | `server_stopped` |
| Reinicio en primer plano | Dato escrito antes persiste |
| Parada tras reinicio | `server_stopped`, salida limpia |

`exitCode` 0, `inputFilesUnchanged`, `postmasterFileAbsent` y `portsClosed` en verdadero. Informe en `d14-07/LIFECYCLE-RESULT.json`.

**Límites:** se usó la interfaz de solo anfitrión de VMware (`192.168.206.1`), porque el perfil rechaza loopback. El observador crea recibos de instalación **sintéticos y explícitos** para enlazar el despliegue privado, sin ejecutar el instalador. No prueba instalación limpia, host C# de servicio, SCM, cuenta de servicio ni reinicio de Windows Server. `applicationHttpDrain` sigue en falso, como en el informe de Codex.

## 2. Validación de `edition` antes de crear nada

Codex reprodujo nombres ZIP con `../` usando `edition='06/../../escape'` en el envoltorio exterior.

**Cambio.** `checked_edition(edition, bundle_sha256)` en `tools/package_server_installer.py`, llamada en la primera línea de `build` y de `clean_build`. Reglas:

- `edition` debe ser exactamente dos dígitos (`[0-9]{2}`).
- `bundle_sha256` debe ser un SHA256 hexadecimal minúsculo de 64 caracteres.
- El bundle debe coincidir con el pin que fijan las fuentes (`RackClick.Setup.ps1`), o se rechaza.

`package_cambio_ip.build` valida la edición y el hash de `payload.json` de la misma forma, antes de crear salida.

**Negativos** (`tools/tests/test_installer_edition_guard.py`, 7 pruebas): `06/../../escape`, `..`, cadena vacía, `6`, `006`, `0a`, `06 `, `06\..`, `06/x`, dígitos de ancho completo, `AA`, `06` con salto de línea; también bundle malformado y edición `05` frente a fuentes de la 06. Cada caso verifica que la carpeta de salida queda **exactamente igual** (ningún fichero nuevo). Las rutas de entrada pasadas no existen, para demostrar que el rechazo llega antes que cualquier lectura.

**Red check obligatoria:** el empaquetador anterior (copia S2, sin validación) con `06/../../escape` produjo `RackClick-Servidor-06/../../escape/INICIAR.ps1` y otros miembros inseguros. El nuevo rechaza con `edition_invalid` sin crear nada.

## 3. Corrección de la afirmación sobre la reproducción 05

La evidencia 06 decía que los valores por defecto (`edition='05'`, bundle `a0df90ed…`) reproducían los bytes históricos de la 05. **Era incorrecto**: el generador lee las fuentes vivas, que ya fijan el bundle 06, y el CMD de IP de la 05 ya no se puede reconstruir igual (su motor de red apunta al payload 06).

**Cambio.** Se eliminaron los valores por defecto. `edition` y `bundle_sha256` son **obligatorios** en `build`, `clean_build`, `package_cambio_ip.build` y sus CLI. La combinación incoherente (05 con las fuentes 06) se rechaza con `edition_source_pin_mismatch`, sin crear salida. Los ZIP 05 originales **no se han tocado** ni se han reconstruido. La evidencia 06 lleva la corrección en su tabla de cambios.

## 4. Edición 07 · payload, envoltorio y CMD nuevos

El bundle **14-07 se reutiliza sin cambios** (sus 25 operadores no han cambiado desde su construcción; el cambio D14-07 está en el runtime del payload, no en el bundle). Las copias de fuentes son identificadas y se crearon con `.local/instalador-06/make_snapshot.py`:

| Copia | Uso | `SNAPSHOT.json` SHA256 |
|---|---|---|
| S4 | Payload y envoltorio 07 (con D14-07) | `b274a88d7a783438b1c23ff3bde87012c27da159a2c31ed0db53673b6cf0764f` |
| S5 | CMD de IP 07 (pins de red nuevos) | `7bbbf17bf93cc556357afedb7fec2fdc55c7c5c035748076c101ce96f34dd92e` |

**Cadena de pins 07:**

```
bundle 14-07        6d5a3896…  (reutilizado)  --pinado en--> RackClick.Setup.ps1 y compañía
payload.json 07     25a764a9…                  --pinado en--> Set-RackClickInstanceNetwork.ps1, Set-RackClickServerNetwork.ps1, Cambiar-IP-RackClick.ps1
payload zip 07      71469d1e…                  --pinado en--> INICIAR.ps1 del envoltorio
```

Comandos (desde S4 y S5, con `python -B`):

- Payload y envoltorio: `package_clean_server_installer.clean_build(archive=…/bundle07, service_publish=…/service-host-c4-publish-06, output=…/RackClick-Servidor-07.zip, payload_output=…/RackClick-Servidor-07-payload.zip, bundle_sha256=6d5a…, edition='07', stamp=(2026,10,25,0,0,0))`. Resultado: payload con 114 entradas (113 del manifiesto y `payload.json`).
- CMD de IP: `package_cambio_ip.build(…/payload-07.zip, …/RackClick-Cambiar-IP-07.zip, edition='07', payload_json_sha256='25a764a9…')`. Resultado: motor `2eb1473b…`, 65 entradas.

| Artefacto 07 | SHA256 |
|---|---|
| `RackClick-Servidor-07.zip` (envoltorio) | `3ca223230fc5ea1ab1e2ce7e40c9b7ca222ef65e4735412cb3fdb7cfd19ddca1` |
| `RackClick-Servidor-07-payload.zip` | `71469d1e084fe1927eadfc2122540868c1db8bf9ac1d22f8819574e4afef8d37` |
| `payload.json` (dentro del payload) | `25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7` |
| `RackClick-Cambiar-IP-07.zip` (CMD) | `b36fd6d394f090d4fcbc16fa7c278132486a58ed8c774199b5001ea0030703bd` |
| Motor de red dentro del CMD | `2eb1473b390f9697c698677fe97f877036f3c521ce9bdb8fe10f3e57ed89c551` |
| `RackClick-Bundle-M3-14-07.zip` (reutilizado) | `6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8` |
| `Invoke-RackClickServerRuntime.ps1` dentro del payload | `f08466f2a7633074131ad0a261bdb98f83f5a292e5a8a366c04e76cd6cfca2ed` |

Entrega: `.local/instalador-07/entrega/` con `SHA256SUMS.txt` (enlaces físicos a las copias). **La entrega 06 no se ha tocado**: su envoltorio sigue siendo `d6b67ae2…`.

## 5. Ficheros de producto modificados en esta tanda

| Fichero | SHA256 |
|---|---|
| `tools/windows/server-install/Invoke-RackClickServerRuntime.ps1` (D14-07) | `f08466f2a7633074131ad0a261bdb98f83f5a292e5a8a366c04e76cd6cfca2ed` |
| `tools/package_server_installer.py` | `d998d898e2460816687b4dca4c3aa2778d00fbcc8d3b36a660c1252d3e6232ce` |
| `tools/package_clean_server_installer.py` | `49ce188165ecca2da636e834e4d0534ab94860b22d93ea70c3a6d194ba478732` |
| `tools/package_cambio_ip.py` | `e7d4b8273cc091d930635af888da994f5c4803941816f9a3b84b53a24ef62c95` |
| `tools/windows/server-install/Set-RackClickInstanceNetwork.ps1` (pin 07) | `2eb1473b390f9697c698677fe97f877036f3c521ce9bdb8fe10f3e57ed89c551` |
| `tools/windows/server-install/Set-RackClickServerNetwork.ps1` (pin 07) | `d6db6f264895efc5f97bc36f68c64de55ada9ab3f5e90953debb697619dec89b` |
| `tools/windows/network-change/Cambiar-IP-RackClick.ps1` (pin 07) | `5272d701ba146104d47a2eeafcebbb7d95dab353eea15f4c8caeeb2c7d2a6cef` |
| `tools/tests/test_installer07_candidate.py` (nuevo) | `3f4c2f263201af17c14ca8501f66b5158645c56df61c11180faa5fcf8ab506c0` |
| `tools/tests/test_installer_edition_guard.py` (nuevo) | `ef93ce17366c4cadb4bc63eea840b25b42e343a8fb8284e6cc0f0bc27a7ab0e3` |
| `tools/tests/test_cambio_ip_package.py` (pin 07) | `eae68f45a1a6203230481b5b1a61859f0657417e9e138649545070447a35b19f` |

## 6. Pruebas ejecutadas (en este equipo)

```
python -B -m unittest tools/tests/test_installer07_candidate.py tools/tests/test_installer06_candidate.py tools/tests/test_installer_edition_guard.py tools/tests/test_cambio_ip_package.py tools/tests/test_server_culture_alias.py tools/tests/test_bundle14_matrix_notice.py tools/tests/test_offline_bundle_builder.py tools/tests/test_bundle14_collect.py tools/tests/test_distribution14.py tools/tests/test_stage14_contract.py
```

Resultado: **95 pruebas OK**, 0 fallos, 0 errores, 132 s.

| Grupo | Qué comprueba |
|---|---|
| `test_installer07_candidate.py` (7) | Sumas de la entrega; envoltorio fija el payload; manifiesto de envoltorio lista todos sus miembros con hash; `payload.json` fija el bundle 14-07 y todos sus ficheros; sin pins viejos; operadores iguales a las fuentes y sin guardia 14; **el runtime del payload es la publicación atómica (D14-07)**; CMD de IP fija `payload.json` y motor. |
| `test_installer_edition_guard.py` (7) | Negativos de edición y de bundle; combinaciones incoherentes; ninguna salida creada; edición obligatoria. |
| `test_installer06_candidate.py` (6) | La entrega 06 sigue coherente. |
| Empaquetado de IP, cultura, bundle, distribución y stage | Sin regresiones. |

Además, sobre el payload 07 y el lifecycle del apartado 1 (ver límites).

## 7. Límites y riesgos para revisión

1. **Ninguna instalación limpia ni instalador de servicios** se ha ejecutado. El ensayo completo del observador se hizo con recibos sintéticos explícitos, en un laboratorio privado; no sustituye a la prueba en Windows Server.
2. **La guardia 14 de la instalación sigue retirada** en la candidata (decisión de la tanda 06). El camino New/Restore de instalación no se ha ejecutado de extremo a extremo para 14 en esta tanda.
3. **Reparación de red y `prepare_server_step2.py`** siguen con referencias de la 05 (`Cambiar-IP-02`, bundle `a0df90ed…`). Quedan identificados como 05 y fuera de esta edición.
4. **Un fallo posterior del empaquetador exterior** (después de escribir el payload interno y antes del envoltorio) puede dejar el payload interno; la validación de edición evita salidas en el caso de entrada inválida, no en cualquier fallo posterior.
5. **PDB:** la publicación del runtime de la candidata 03 registra la ruta de compilación de la copia.
6. **Reproducibilidad:** depende de `.local/` (SDK, PostgreSQL, candidata, publicación del servicio). Sin aprovisionamiento pinado no se repite desde un clon limpio.
7. **Derechos de redistribución** del bundle: abiertos. **Custodia D2, MFA por HTTP con proveedor de laboratorio y aceptación final:** pendientes.
8. **`edition` obligatoria:** las llamadas antiguas sin `edition`/`bundle_sha256` fallan con `TypeError`. Es intencionado.

## 8. Próximo orden

1. Revisión de Codex de D14-07, de la validación de edición y de la edición 07 (hashes del apartado 4).
2. **Ensayo limpio en otra VM Windows Server** (no la QA actual): `INICIAR.ps1`, New y Restore del instalador, cuenta y servicio, HTTPS, backup y reinicio real del servicio.
3. Decidir si la reparación de red y `prepare_server_step2.py` pasan a 07 o quedan como 05.
4. Aprovisionamiento reproducible pinado de `.local/` antes de cerrar la entrega.
