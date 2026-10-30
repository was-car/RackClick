"""Update only four packaged manuals before the schema11 source freeze."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
def replace(s,a,b):
    if a not in s:raise RuntimeError('Missing manual anchor: '+a[:110])
    return s.replace(a,b,1)
def main():
    out=E/'MANUALES-01.json'
    if out.exists():raise SystemExit('Preserve receipt')
    files={}
    intro={
    'MANUAL-PAQUETE-WINDOWS-S1.md':'**Candidata interna712 · integración Windows713–772.** Incluye idioma EN/DE/ES y tema claro/oscuro personales, además de compartidas/editor privado/XLSX/avisos. Perfil712: SQL001–011,20archivos servidor+18GUI; perfil592: SQL001–010/37archivos;337/397/532: SQL001–009/36archivos. Dependencias fijadas intactas. Entrega interna: servicio/identidad/PKI/Windows limpio/licencias/QA y adopción final siguen pendientes.',
    'CONSTRUIR-PAQUETE-WINDOWS-S1.md':'**Integración713–772.** Cinco perfiles cerrados:337/397/532 de esquema9,592-FINAL02 de10 y712-FINAL02 de11. Sin hashes arbitrarios ni perfiles provisionales. Aplicación/interfaz712 reutilizadas sin recompilar. Congelar25operadores y4manuales antes de producir dos ZIP en salidas nuevas y comparar bytes/manifiestos. Motores de copia QA separados de los25operadores.',
    'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':'**Aplicación712/esquema11.** Settings conserva selector de idioma y tema: tras login guarda sólo la configuración personal de esa cuenta y aplica después de commit+lectura. Cualquier usuario activo, incluido lector sin clientes, puede cambiarla; no obtiene edición. Recarga/otra sesión leen preferencias del propietario. Conflicto o petición incierta requieren Consultar/Reintentar original/Cancelar original; no hay rebase automático. Logout recupera fallback anónimo. Compartidas siguen exigiendo templates.publish por grupos y ámbito de cliente; la copia QA10→11 conserva permisos sin autoconcesiones.',
    'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':'**Compatibilidad712/esquema11.** Backup/restore preservan35tablas, bibliotecas privadas/compartidas, preferencias y recibos/fences ligados a sus propietarios. Recuperación administrativa revoca sesiones copiadas y crea ROOT/clúster/base/roles/secretos/TLS/administrador nuevos. El administrador nuevo no hereda preferencias o bibliotecas privadas de otro usuario. Perfiles9 y10 conservados; Restore exige esquema/digests exactos, sin migración implícita. Recuperar datos/aplicación no acredita recuperación integral del host/servicio/PKI/retención.'}
    for name,header in intro.items():
        p=ROOT/'docs'/name;old=p.read_bytes();s=old.decode().replace('\r\n','\n');first=s.index('**');end=s.index('\n\n',first);s=s[:first]+header+s[end:]
        if name.startswith('MANUAL-'):
            s=replace(s,'Aplicación e interfaz592/esquema10 reutilizadas sin recompilar en593–652. Los paquetes337/397/532','Aplicación e interfaz712/esquema11 reutilizadas sin recompilar en713–772. Los paquetes337/397/532/592')
            s=replace(s,'perfil337,397,532 o592 registrado','perfil337,397,532,592 o712 registrado')
            s=replace(s,'Un backup9 requiere un perfil9; un backup10 requiere592.','Un backup9 requiere un perfil9; un backup10 requiere592; un backup11 requiere712.')
            s=replace(s,'Una mezcla9→10 falla','Una mezcla entre esquemas (por ejemplo10→11) falla')
            s+='\n\nEn712, abre Settings arriba a la derecha de Clientes para cambiar idioma o tema de tu cuenta. Espera confirmación del servidor; recarga y comprueba desde otra sesión de la misma cuenta. Otra cuenta conserva sus propios ajustes. En login sin sesión el ajuste es sólo fallback de ese navegador. Si aparece recuperación, consulta antes de reenviar; no se guarda el cambio como exitoso antes de confirmarlo.\n'
        elif name.startswith('CONSTRUIR-'):
            s=replace(s,'estos cuatro perfiles','estos cinco perfiles')
            row='| [712/preferencias](../evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json) |11 /20+18|7.028.507|`f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd`|'
            anchor='\n\nEl productor exige el hash externo';s=replace(s,anchor,'\n'+row+anchor)
            s=s.replace('los36 o37 hashes','los36,37 o38 hashes')
            s=replace(s,'--manifest evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json','--manifest evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json')
            s=replace(s,'--expected-manifest-sha 66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9','--expected-manifest-sha f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd')
            s=replace(s,'--evidence evidence/s1-20261018/sesenta-tandas-593-652/packaging/NOMBRE-NUEVO','--evidence evidence/s1-20261018/sesenta-tandas-713-772/packaging/NOMBRE-NUEVO')
        elif name.startswith('OPERAR-'):
            s=replace(s,'(337/397/532: esquema9;592: esquema10)','(337/397/532: esquema9;592: esquema10;712: esquema11)')
            a=s.index('La [candidata592');b=s.index(' Los scripts de operación',a)
            s=s[:a]+'La [candidata712 de laboratorio](../evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json) tiene referencia `f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd` y20archivos de servidor más18GUI. La selección QA es una operación separada, documentada en su cierre.'+s[b:]
        else:
            s=s.replace('y592 (esquema10) registrados','y592 (esquema10)/712 (esquema11) registrados')
            s=s.replace('compartidas sólo en592.','compartidas en592/712 y preferencias personales en712.')
            s=s.replace('XLSX en397/532/592, editor privado en532/592','XLSX en397/532/592/712, editor privado en532/592/712')
            s=s.replace('La evidencia real y los fallos conservados se atribuyen por ejecución al cierre593–652;398–427 y los demás informes anteriores son evidencia histórica.','Las ejecuciones nuevas y sus fallos se atribuyen al cierre713–772;593–652 y los demás informes anteriores se conservan como evidencia histórica.')
            s=s.replace('(N=9 para337/397/532; N=10 para592)','(N=9 para337/397/532; N=10 para592; N=11 para712)')
            s=s.replace('los36 o37 artefactos','los36,37 o38 artefactos').replace('perfil validado9/10','perfil validado9/10/11')
            s=s.replace('(9 o10, incluido templates.publish en10 únicamente','(9,10 u11, incluido templates.publish en10/11 únicamente')
            s+='\n\nIntegración713–772: perfil11 y recuperación administrativa CLI11 se comprueban con pruebas NUEVAS en su cierre. No confundir Restore administrativo (revoca sesiones, crea administrador) con copiaQA10→11 (conserva cuentas/sesiones/permisos, origen10 y recuperación10 separada). Retorno de QA sólo sin actividad comprobada; después de trabajar no se promete rollback de escrituras.\n'
        p.write_bytes(s.encode());files['docs/'+name]=dict(before=hashlib.sha256(old).hexdigest(),after=hashlib.sha256(p.read_bytes()).hexdigest())
    out.write_bytes((json.dumps(dict(purpose='Packaged manual updates before schema11 ZIP freeze; execution outcomes separately attributed',files=files),indent=2)+'\n').encode());print('4 manuals updated')
if __name__=='__main__':main()
