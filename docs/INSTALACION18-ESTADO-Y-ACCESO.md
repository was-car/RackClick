# Instalación nueva en A · aplicación 48 y Demo50 trilingüe

Actualización: 12.11.2026. **Los 50 clientes ya están cargados en RackClick-W02-A** y se ha comprobado un backup posterior. **El servicio arrancó automáticamente y se comprobaron HTTPS, los 50 clientes y sus datos después del reinicio real de Wascar.** La verificación oficial manual pasó; la primera comprobación automática devolvió un error de HTTPS y se conserva como observación, sin atribuirle una causa no medida.

- URL desde el navegador de la VM: **https://192.168.206.128:5443/**.
- Cuenta de RackClick: **Wascar** (la identidad normalizada es `wascar`). La contraseña nueva está en **Acceso privado** del panel de instalación, dentro de la VM; no se entrega por chat ni viene predeterminada en el ZIP.
- En el Escritorio, el acceso **RackClick-VERIFICAR-17-…** de esta instalación abre el panel existente. No volver a instalar ni ejecutar limpieza para abrir RackClick.
- 50 empresas: 17 EN, 17 DE y 16 ES. Ejemplos: Oakbridge Office Supplies, Lindenwerk Büroservice y Papelería Encinar. Los nombres propios permanecen iguales al cambiar el idioma de interfaz.
- 180 racks, 1.563 equipos, 20.665 puertos y 2.207 conexiones. Comparadas completas las ocho colecciones y releídos los50nombres por API. Sin usuarios niMFA importados del origen.

## Cómo entrar ahora

En la VM abre el acceso del Escritorio **RackClick - Abrir** o la URL indicada. En **RackClick-VERIFICAR-17-83d680d6.cmd** puedes abrir **Acceso privado** para consultar la contraseña nueva y entrar con Wascar. Se dejó también **RackClick - Acceso y datos.txt**. No repitas la instalación ni la carga: los 50 clientes ya están dentro.

MFA está disponible, política global activa, gracia de 45 días y exención del administrador global contrastadas por API. Tu cuenta nueva todavía no tiene factor y puede activarlo desde su panel; no se ha habilitado ni deshabilitado un factor por ti. La interfaz servida coincide por SHA256 con la candidata revisada.

Desde otro PC, la CA pública de esta VM está disponible fuera del ZIP en `.local/install18-20261111/entrega-final/CA-PUBLICA-VM-A.cer` (sin clave privada). Su importación en un cliente es una decisión del operador; no se cambió el almacén de confianza de LEAO. Desde el navegador de la VM, HTTPS se verificó con confianza normal.

## Archivos para futuras instalaciones desde cero

- ZIP completo18 (entrega local, no descargable desde GitHub),144.203.012 bytes.
- SHA256 externo: `512fcaf6aa255e6ff6ae9610daa722f8b9d135972d33d5a249b9d42ad90625ed`.
- [Manual paso00–07](INSTALACION18-COMPLETA.html): crear carpeta, abrir PowerShell como administrador, verificar y extraer, formulario, acceso privado, reinicio, cargador50 y copia posterior.

El ZIP es una candidata de instalación **New48**, con datos/cargador separados para confirmar la carga sobre servidor vacío. No incluye contraseñas de esta VM. No ejecutar otra instalación sobre A/D/E; para repetir desde cero se necesita otra VM limpia o un snapshot limpio gestionado por Wascar.

## Incidencia y alcance real

A comenzó con la edición17. La aplicación y el backup inicial arrancaron, pero un cambio de ámbito de StrictMode en el asistente hizo fallar su cierre al leer un campo diagnóstico opcional. El fallo se conservó; no se reescribió como éxito.

Se corrigió y probó ese defecto en la edición18 y se completó en A sólo el registro de tareas y el recibo que faltaban, mediante un finalizador revisado y ligado a esa instancia. No se recrearon base, cuentas ni claves; el servicio mantuvo su proceso durante la finalización. Se ejecutó después el cargador y otra copia real. **No se declara que A sea una ejecución limpia completa de18**:18 está empaquetada/revisada; su cambio frente a17 es el asistente corregido y las etiquetas/manuales, con los mismos binarios/SQL/datos.

Restore48 y cambio automático de red48 no están habilitados. Operaciones avanzadas de custodia/rotación/pérdida y aceptación productiva conservan sus pendientes. D y E no se han operado. Índice26,63/100 del cierre restante, sin incremento por esta entrega.

[Evidencia y dictamen](../evidence/s1-20261111/instalacion17-demo50/RESULTADOS.md).

## Observación del comprobador automático

La primera tareaSYSTEM registró `postboot_https_health_failed` unos 11 segundos después del arranque, con resultado 1. No se demostró si fue por temporización u otra causa de transporte. El servicio había arrancado automáticamente y se confirmó después `ready`/esquema48; se ejecutó el comprobador oficial manual y devolvió `postboot_verified`. Se mantuvieron ambos resultados y no se declara que la tarea automática haya pasado. Los50nombres y ocho conteos se releyeron después, conMFA disponible y sin modificar su estado. Esta observación de automatización queda abierta; no impide el acceso comprobado al servidor.

## Alcance de esta copia en GitHub

Los ZIP nativos y la CA particular de la VM A no se publican. Las rutas `.local` de este registro son referencias del equipo de desarrollo, no archivos incluidos ni enlaces de descarga. Las URL y accesos de A describen aquella prueba y no son un servidor público. Para probar las fuentes utiliza la guía EN/DE/ES del repositorio.
