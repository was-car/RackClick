"""Update the four packaged operator manuals before freezing the schema10 ZIP."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def replace(text,old,new):
    if old not in text:raise RuntimeError('Missing manual anchor: '+old[:100])
    return text.replace(old,new,1)
def main():
    receipt=E/'MANUALES-01.json'
    if receipt.exists():raise SystemExit('Preserve existing receipt')
    changes={}
    for name in ['MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md']:
        p=ROOT/'docs'/name;before=p.read_bytes();s=before.decode('utf-8').replace('\r\n','\n')
        if name.startswith('MANUAL-'):
            a=s.index('**Candidata interna532');b=s.index('\n\n',a)
            s=s[:a]+'**Candidata interna592 · integración Windows593–652.** Incluye plantillas compartidas por cliente, editor privado, XLSX y avisos de inventario. El perfil592 usa SQL001–010,19 archivos de servidor y18 de interfaz. Los perfiles337/397/532 conservan SQL001–009 y36 archivos; usar el perfil y hash externo correspondientes. Las dependencias fijadas no cambian. Adopción final, servicio/identidad/PKI/Windows limpio/licencias siguen pendientes; no es un instalador final certificado.'+s[b:]
            s=replace(s,'Grupo398–427, aplicación397/esquema9 e interfaz397 con XLSX. El paquete337/interfaz185 del grupo338–367 se conserva como evidencia histórica y perfil admitido.','Aplicación e interfaz592/esquema10 reutilizadas sin recompilar en593–652. Los paquetes337/397/532 y sus informes se conservan como evidencia histórica y perfiles admitidos.')
            s=replace(s,'perfil337 o397 registrado','perfil337,397,532 o592 registrado')
            s=replace(s,'Unicode de hasta100caracteres según la política del servidor','Unicode de hasta100 valores escalares según la política del servidor')
            s=replace(s,'todo el content397 y recuperar directamente el snapshot','todo el content del perfil elegido y recuperar directamente un snapshot del mismo esquema SQL')
            s=replace(s,'La salida correcta conserva installation_prepared,','Restore no migra el esquema. Un backup9 requiere un perfil9; un backup10 requiere592. Tras restaurar en la base nueva se exige historia exacta1..N y los digests SQL del perfil. Una mezcla9→10 falla conservando el parcial antes de crear administrador, sin recibo de éxito.\n\nLa salida correcta conserva installation_prepared,')
            s=replace(s,'se atribuyen al cierre del grupo338–367','se atribuyen al cierre del grupo593–652; los informes338–367 y posteriores anteriores se conservan como históricos')
        elif name.startswith('CONSTRUIR-'):
            a=s.index('**Actualización473–532.');b=s.index('\n\n',a)
            s=s[:a]+'**Integración593–652.** El productor y lector admiten cuatro perfiles cerrados:337/397/532 de esquema9 y592-FINAL02 de esquema10. No admitir un hash arbitrario como nueva versión. Se reutilizan los bytes de aplicación592; los perfiles provisionales no son entradas aceptadas. Construir dos ZIP en salidas nuevas después de congelar aplicación,25 operadores y4 manuales, y comparar sus bytes/manifiestos. Los motores de copia QA son herramientas de desarrollo separadas y no forman parte de esos25 operadores.'+s[b:]
            a=s.index('El productor y el lector Windows admiten exclusivamente dos perfiles');b=s.index('\n`development/toolchain.lock.json`',a)
            s=s[:a]+'''El productor y el lector Windows admiten exclusivamente estos cuatro perfiles.
El manifiesto identifica la carpeta de candidata y cada archivo se comprueba de nuevo.

| Perfil | Esquema / archivos | Bytes de aplicación | SHA256 del manifiesto |
|---|---|---:|---|
| [337/GUI185](../evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json) |9 /18 servidor+18 interfaz|6.578.061|`b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00`|
| [397/XLSX](../evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json) |9 /18+18|6.653.702|`cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685`|
| [532/editor privado](../evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json) |9 /18+18|6.794.984|`c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e`|
| [592/compartidas](../evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json) |10 /19+18|6.939.574|`66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9`|

El productor exige el hash externo correspondiente y los36 o37 hashes del perfil.
Rechaza cualquier hash no registrado y los manifiestos cruzados entre perfiles.
No hay opción para confiar otra versión. El tamaño de aplicación de REPORT.json,
las cantidades y SQL001..N proceden del perfil, sin arrastrar constantes de otro.
El lector Windows verifica los mismos límites y la secuencia SQL completa.
Construir un paquete no selecciona QA ni cambia datos/cuentas de ningún laboratorio.
''' +s[b:]
            s=replace(s,'--manifest evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json','--manifest evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json')
            s=replace(s,'--expected-manifest-sha cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685','--expected-manifest-sha 66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9')
            s=replace(s,'--evidence evidence/s1-20261017/treinta-tandas-398-427/builder/NOMBRE-NUEVO','--evidence evidence/s1-20261018/sesenta-tandas-593-652/packaging/NOMBRE-NUEVO')
            s=replace(s,'Para reconstruir337 se cambian únicamente','Para reconstruir un perfil9 se cambian únicamente')
            s=replace(s,'por la pareja337\nde la tabla','por la pareja correspondiente\nde la tabla')
        elif name.startswith('OPERAR-'):
            a=s.index('**Aplicación532.');b=s.index('\n\n',a)
            s=s[:a]+'**Aplicación592/esquema10.** La operación Windows conserva recibos y protocolo. El editor privado usa revisión personal y confirma commit. Las plantillas compartidas pertenecen al cliente: lectura e instanciación requieren acceso vigente al cliente; publicar/retirar exige además templates.publish mediante grupos. La copia del QA9 a QA10 no concede este permiso automáticamente: el administrador lo asigna explícitamente. Avisos, conflictos y peticiones inciertas mantienen Consultar/Cancelar y no aplican cambios automáticamente a otra sesión. No cambiar rutas o digests de un recibo.'+s[b:]
            s=replace(s,'del servidor277 con la interfaz185','del perfil cerrado seleccionado (337/397/532: esquema9;592: esquema10)')
            a=s.index('La [candidata277');b=s.index(' Los scripts de operación',a)
            s=s[:a]+'La [candidata592 de laboratorio](../evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json) tiene referencia `66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9` y19 archivos de servidor más18 de interfaz. La selección del QA de Wascar es una operación separada y se registra en su cierre.'+s[b:]
            s=replace(s,'Una restauración completa de instalación requiere aún su contrato y ensayo propios.','La recuperación de datos en otra instalación usa RECUPERACION-DESPLIEGUE-WINDOWS-S1.md; la recuperación integral del host sigue pendiente.')
        else:
            a=s.index('**Compatibilidad532.');b=s.index('\n\n',a)
            s=s[:a]+'**Compatibilidad592/esquema10.** Backup/restore preservan las33 tablas SQL10, las configuraciones privadas de sus propietarios y las compartidas con cliente/autor/bytes/recibos. El administrador nuevo tiene biblioteca personal propia; no hereda bibliotecas ajenas. Las sesiones copiadas se revocan. Se crean ROOT/clúster/base/roles/secretos/TLS nuevos, conservando el origen. Los perfiles337/397/532 siguen usando esquema9/30 tablas; Restore exige el mismo esquema que el backup, sin migrar. La recuperación de aplicación no certifica recuperación integral del host, servicio, PKI o retención.'+s[b:]
            s=replace(s,'Usar el ZIP397 de procedencia confiable','Usar el ZIP del perfil de procedencia confiable')
            s=replace(s,'sólo admite los perfiles337 y397 registrados','sólo admite los perfiles337/397/532 (esquema9) y592 (esquema10) registrados')
            s=replace(s,'El ensayo337→397 usa','El ensayo histórico337→397 usa')
            s=replace(s,'Consultar los XLSX nuevos sólo en397.','Consultar XLSX en397/532/592, editor privado en532/592 y compartidas sólo en592.')
            s=replace(s,'pertenecen al cierre398–427, no a los ensayos históricos.','se atribuyen por ejecución al cierre593–652;398–427 y los demás informes anteriores son evidencia histórica.')
            s=replace(s,'GUI185 en337 o GUI397 en397 y los nueve SQL aprobados','la interfaz de su perfil y la secuencia aprobada SQL001..N (N=9 para337/397/532; N=10 para592)')
            s=replace(s,'los36artefactos de distribución','los36 o37 artefactos de distribución según el perfil')
            s=replace(s,'Se comprueba historia exacta1..9; el CLI verifica también digests de los nueve SQL antes de escribir, sin migrar ni bootstrap implícito.','Se comprueba historia exacta1..N y digests según el perfil validado9/10; el CLI los comprueba también antes de escribir, sin migración ni bootstrap implícitos. Si un backup9 se usa con Stage10, se conserva la nueva base parcial tras pg_restore y se rechaza antes del CLI administrativo; no hay recibo de éxito ni cambios en el origen.')
            s=replace(s,'los nueve grants FoundationAdmin actuales','los grants FoundationAdmin de ese esquema (9 o10, incluido templates.publish en10 únicamente para el grupo administrativo nuevo)')
            s=replace(s,'## Diez hitos318–327 y evidencia','## Diez hitos históricos318–327 y evidencia')
            s=replace(s,'instalador que suministre dependencias, ','')
            s+='\n\nLa integración593–652 añade el perfil10 a la instalación nativa y a Restore; sus comandos, resultados reales y revisión se registran en evidence/s1-20261018/sesenta-tandas-593-652. No confundir Restore administrativo (revoca sesiones y crea administrador) con la copia QA9→10: ésta conserva cuentas/sesiones y permisos originales, y no otorga templates.publish automáticamente.\n'
        p.write_bytes(s.encode('utf-8'))
        changes['docs/'+name]={'before':hashlib.sha256(before).hexdigest(),'after':hashlib.sha256(p.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps({'purpose':'Packaged manual freeze before schema10 ZIP; execution evidence attributed separately','files':changes},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'manuals':len(changes),'receipt':str(receipt.relative_to(ROOT))}))
if __name__=='__main__':main()
