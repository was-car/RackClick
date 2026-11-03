"""Update the four packaged manuals for the closed832 profile before freezing ZIP inputs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
def replace(s,a,b):
    assert a in s,a[:90]
    return s.replace(a,b,1)
def main():
    out=E/'MANUALES-01.json';assert not out.exists()
    headers={
      'MANUAL-PAQUETE-WINDOWS-S1.md':'**Candidata interna832 · integración833–847.** Incluye XLS(HTMLRC9) por rack UUID con Devices/Connections/Summary, además de preferencias personales, compartidas/editor privado/XLSX/avisos. Perfil832 y712: esquema11/SQL001–011,20servidor+18GUI. Perfiles337/397/532/592/712 conservados; sin nuevas dependencias ni compilaciones. Entrega interna: servicio/identidad/PKI/Windowslimpio/licencias/QA y adopción final pendientes.',
      'CONSTRUIR-PAQUETE-WINDOWS-S1.md':'**Integración833–847.** Seis perfiles cerrados:337/397/532 de esquema9,592-FINAL02 de10 y712-FINAL02/832-02 de11. Aplicación/interfaz832-02 reutilizadas sin recompilar; candidata832-01 defectuosa excluida. Congelar25operadores y4manuales antes de producir dos ZIP nuevos idénticos. Motores de copia QA separados de los25operadores; sin esquema/pin arbitrarios.',
      'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':'**Aplicación832/esquema11.** Añade informe XLS(HTMLRC9) por UUID con lectura+reports.export vigentes en generación/recuperación y descarga. Mantiene preferencias por cuenta, compartidas/editor privado/XLSX, borradores y Click-Click. Sin migración ni nuevas concesiones: copiaQA712→832 conserva35tablas/cuentas/sesiones/privados, con clúster/bases/secretosPG nuevos y recuperación712 separada. No es Restore administrativo.',
      'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':'**Compatibilidad832/esquema11.** Backup/restore preservan35tablas, incluidos recibos y bytes del XLSHTML, bibliotecas y preferencias propias. Restore administrativo creaROOT/clúster/base/roles/TLS/administrador nuevos y revoca sesiones copiadas; conserva cuentas/datos salvo cambios explícitos de recuperación. CopiaQA712→832 es otra operación, sin recuperaradmin/migrar ni revocar sesiones. Perfiles anteriores conservados; esquema/historia/digests exactos, sin instalación final/SCM/PKI/recuperación integral del host acreditados.'}
    changes={}
    for name,header in headers.items():
        p=ROOT/'docs'/name;before=p.read_bytes();s=before.decode().replace('\r\n','\n');start=s.index('**');end=s.index('\n\n',start);s=s[:start]+header+s[end:]
        if name.startswith('MANUAL-'):
            s=replace(s,'Aplicación e interfaz712/esquema11 reutilizadas sin recompilar en713–772. Los paquetes337/397/532/592','Aplicación e interfaz832/esquema11 reutilizadas sin recompilar en833–847. Los paquetes337/397/532/592/712')
            s=replace(s,'perfil337,397,532,592 o712 registrado','perfil337,397,532,592,712 o832 registrado')
            s=replace(s,'un backup11 requiere712.','un backup11 requiere712 o832, con la misma historia/digests SQL001–011.')
            s+='''\n\n## XLS (HTML RC9) en832\n\nEntra con una cuenta que tenga lectura y reports.export para el cliente. Abre su tarjeta y Consultar inventario; al final del panel, inmediatamente después de Informes e impresión/SVG, pulsa XLS (HTML RC9). En Rack del informe elige por ruta/nombre/UUID; el texto completo aparece también debajo del selector. Pulsa Generar XLS (HTML RC9) y espera Generación confirmada por el servidor; después pulsa Descargar XLS (HTML RC9). Comprueba el archivo nuevo en Descargas(Ctrl+J). Generación confirmada no equivale a descarga ni guardado en disco.\n\nEs HTML con extensión.xls, distinto del XLSX tabular. Excel puede avisar de discrepancia de formato; no cambies su seguridad ni habilites macros/contenido. La prueba de desarrollo en Excel16.0build20430 conservó87valores exactos sin fórmulas; creó tres pestañas, pero las tres tablas consecutivas están en Devices y las otras dos vacías. No se prometen tres hojas pobladas ni compatibilidad universal. Nombres/etiquetas/ceros/Unicode quedan literales; Technician vacío porque no existe el campo persistido. Created usa textolegacy creado o creaciónPG, no fecha de exportación.\n\nUna solicitud incierta se consulta/reintenta con su identidad original en esta página. notRecorded no cancela. Recargar pierde la recuperaciónRAM; no se promete historial durable. Cambiar cuenta/cliente no habilita descargas anteriores. Un rechazo de permiso o sesión no se convierte en éxito. QA75–77 tienen guion detallado separado: sólo se habilitan al seleccionar la copia compatible, sin alterar observaciones anteriores.\n'''
        elif name.startswith('CONSTRUIR-'):
            s=replace(s,'estos cinco perfiles','estos seis perfiles')
            anchor='\n\nEl productor exige el hash externo'
            row='| [832/XLSHTML RC9](../evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json) |11 /20+18|7.108.267|`511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5`|'
            s=replace(s,anchor,'\n'+row+anchor)
            s=replace(s,'--manifest evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json','--manifest evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json')
            s=replace(s,'--expected-manifest-sha f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd','--expected-manifest-sha 511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5')
            s=replace(s,'--evidence evidence/s1-20261018/sesenta-tandas-713-772/packaging/NOMBRE-NUEVO','--evidence evidence/s1-20261018/quince-tandas-833-847/packaging/NOMBRE-NUEVO')
        elif name.startswith('OPERAR-'):
            s=replace(s,'712: esquema11)','712/832: esquema11)')
            s=replace(s,'[candidata712 de laboratorio](../evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json) tiene referencia `f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd`','[candidata832 de laboratorio](../evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json) tiene referencia `511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5`')
        else:
            s=replace(s,'/712 (esquema11) registrados','/712 y832 (esquema11) registrados')
            s=replace(s,'N=11 para712)','N=11 para712/832)')
            s+='''\n\nIntegración833–847:832-02 conserva esquema11 y añade XLSHTML con tres tablas; probar exportación/recuperación del recibo con autorización vigente tras Restore. La copiaQA11→11 guarda además recuperación712 separada y no ejecuta --migrate ni recover-admin. Sólo retorno por puntero sin actividad comprobada en ambas ramas, incluida actividad compensada. No intercambiar esta operación con Restore del instalador. Los ensayos847 y sus fallos se registran en su evidencia nueva, conservando los informes históricos.\n'''
        p.write_bytes(s.encode());changes['docs/'+name]=dict(before=hashlib.sha256(before).hexdigest(),after=hashlib.sha256(p.read_bytes()).hexdigest())
    out.write_text(json.dumps(dict(files=changes,purpose='Four packaged manuals updated before ZIP freeze. Scope/steps, not a claim of final Windows adoption.'),indent=2)+'\n',encoding='utf-8');print('4 manuals updated')
if __name__=='__main__':main()
