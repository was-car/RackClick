# F-06.01 · fases de rotación · resultado de la tanda

09.11.2026 · Cerrado como especificación con revisión independiente favorable. Petición: continuar paso19 conservando D y reutilizando evidencia. Este criterio pide especificar fases; no ejecutar una rotación.

Se contrastaron D2 vigente/F-03.02, la ampliación GetActiveKey/L2h, parser/proveedor/cifrado y SQL014 actuales, y las revisiones F04/F05 conservadas. El manifiesto FUENTES-CONTRASTADAS.json identifica doce fuentes/recibos; los resultados anteriores no se convierten en nuevas ejecuciones.

Entregable: docs/PROTOCOLO-ROTACION-MFA-v1.md y docs/PASO-019-FASES-ROTACION-MFA.md. Se desarrolla el protocolo offline ya elegido: preparar n y anillo aditivo con activa anterior; persistencia/sobre externos antes de DB; recifrado en transacción con testigo local; publicación final; verificación offline y guard de arranque. Todas las claves requeridas por factores de cualquier estado y backups se conservan. Se distinguen el contrato aceptable y los componentes todavía ausentes.

Investigación: consulta de fuentes primarias el09.11 en PostgreSQL17, Microsoft AES-GCM y OWASP, enlazadas en el protocolo. No se copia código de repositorios ni se instalan dependencias. Se descartan 2PC con archivos ordinarios y un rotador online nuevo; se mantiene D2 y el producto existente.

La matriz del criterio conserva las cuatro exigencias y diez interrupciones/negativos razonados. No se han ejecutado pruebas de producto, PostgreSQL, compilaciones, rotación/rewrap, servicios, claves, cuentas o VM. Las comprobaciones nuevas son de fuentes, enlaces, integridad documental y planificación, más la revisión distinta que se anexará. No se lee material MFA privado o credenciales, no se publica nada y no se modifica D/E.

Dictamen favorable en [review/DICTAMEN-F0601.md](review/DICTAMEN-F0601.md): razonamiento separado de los diez casos, contraste con código actual y doce pins de fuentes/recibos. No se le atribuyen pruebas de producto o ensayos previos. Conciliación: sólo F-06.01 pasa de pending a done, **+5/8**; 1607/84 → **3319/168 = 19,755952…/100**, redondeado19,76. Quedan42done/236pending/2in_progress,53resultados/280checkpoints/268números, sin alterar baselinev3, estructura, pesos o criterios. Los hitos del resultado completo F06 permanecen pendientes, incluido definition_confirmed.

El resultado completo F-06 y sus hitos de implementación/pruebas/integración/aceptación no se cierran por este contrato. F-06.02 conserva el censo operativo/retirada; .03 los componentes e interrupciones reales; .04 la revisión final. No es un instalador nuevo ni una activación de MFA. El encabezado/guía se actualizan sólo para reflejar el dictamen y la contabilidad; protocolo y matriz revisados permanecen idénticos.
