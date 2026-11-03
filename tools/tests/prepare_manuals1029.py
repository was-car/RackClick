"""Prepare the four Windows manuals before packaging the closed969 profile."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'
PIN='1f651be9a69c5bb225928ebd948f02ad00b19f790bcce967715d4fcc0c1e99d2'
MF='evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-WINDOWS.json'


def change(text,old,new):
    assert old in text,old
    return text.replace(old,new,1)


def main():
    out=E/'MANUALES-01.json';assert not out.exists()
    headers={
      'MANUAL-PAQUETE-WINDOWS-S1.md':'**Candidata interna969 · integración970–1029.** Esquema12 con paleta personal por diez tipos, además de preferencias011, bibliotecas privadas/compartidas, informes y aviso accesible de grupos.21servidor+18interfaz, sin recompilar. Se conservan siete perfiles anteriores. Servicio/identidad/PKI, Windows limpio/otro equipo, licencias, voz y adopción final pendientes.',
      'CONSTRUIR-PAQUETE-WINDOWS-S1.md':'**Integración970–1029.** Ocho perfiles cerrados:337/397/532 de9,592 de10,712/832/849 de11 y969 de12. Se reutilizan39artefactos exactos de969-01 mediante manifiesto derivado con totalBytes/procedencia.25operadores y4manuales congelados antes de dos ZIP nuevos idénticos; no builds ni pines arbitrarios.',
      'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':'**Aplicación969/esquema12.** Añade la paleta personal RC9 con SQL012 aditiva; SQL001–011/dependencias/CSS intactos. La copiaQA849→969 crea clúster nuevo con destino12 y recuperación849/11, conservando completo el origen849 y recuperación832/11. Sólo migra el destino; mantiene cuentas/sesiones/privados. Distinta de Restore administrativo.',
      'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':'**Compatibilidad969/esquema12.** Backup/Restore conserva37tablas, paletas personales y recibos originales. Restore administrativo crea ROOT/clúster/base/roles/TLS/administrador nuevos y revoca sesiones copiadas, con diferencias explícitas. CopiaQA849→969 mantiene cuentas/sesiones, migra sólo destino12 y deja recuperación849/11 separada; sin bootstrap/recover-admin. Recuperación integral de host y adopción pendientes.'}
    changes={}
    for name,header in headers.items():
        p=ROOT/'docs'/name;raw=p.read_bytes();text=raw.decode().replace('\r\n','\n');start=text.index('**');end=text.index('\n\n',start);text=text[:start]+header+text[end:]
        if name.startswith('MANUAL-'):
            text=change(text,'Aplicación e interfaz849/esquema11 reutilizadas sin recompilar en850–909. Los paquetes337/397/532/592/712/832','Aplicación e interfaz969/esquema12 reutilizadas sin recompilar en970–1029. Los paquetes337/397/532/592/712/832/849')
            text=change(text,'perfil337,397,532,592,712,832 o849 registrado','perfil337,397,532,592,712,832,849 o969 registrado')
            text=change(text,'con la misma historia/digests SQL001–011. Tras restaurar','con la misma historia/digests SQL001–011; un backup12 requiere969 y SQL001–012. Tras restaurar')
            text+='''\n\n## Paleta personal de tipos en969\n\nCon cualquier cuenta activa, incluida Lector, vuelve a Infraestructura/Clientes desde la barra izquierda. Arriba a la derecha, junto al idioma y tema, pulsa Paleta. En la ventana central usa el cuadrado de color de cada tipo; RJ45 y RJ45 PoE son independientes. Estos cambios sólo son borrador: Cerrar descarta los no guardados. Pulsa Guardar abajo a la derecha y espera confirmación y lectura del servidor. El botón ↺ restablece un tipo en el borrador; Restablecer todo prepara los diez valores iniciales. Ambos requieren Guardar.\n\nTu paleta se recupera al recargar o iniciar la misma cuenta en otra sesión. Otra cuenta conserva la suya. Los colores explícitos de puerto y cable, estados, PoE y Click-Click mantienen su prioridad; no cambia inventario ni cables existentes. La paleta automática por parejas de categorías es otra función pendiente. No se importan preferencias del HTML offline.\n\nAnte una petición pendiente usa Consultar original, Reintentar original o Cancelar original; conserva la intención y reautentica la misma cuenta si se solicita. Una respuesta incierta no significa guardado. QA79–81 contienen pasos detallados; sólo realizarlos cuando la guía de tu snapshot indique disponible. Los resultados anteriores de Wascar se conservan.\n'''
        elif name.startswith('CONSTRUIR-'):
            text=change(text,'estos siete perfiles','estos ocho perfiles')
            anchor='\n\nEl productor exige el hash externo'
            text=change(text,anchor,'\n| [969/paleta personal](../'+MF+') |12 /21+18|7.037.914|`'+PIN+'`|'+anchor)
            text=change(text,'--manifest evidence/s1-20261018/tanda-849/CANDIDATA849.json','--manifest '+MF)
            text=change(text,'--expected-manifest-sha 1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09','--expected-manifest-sha '+PIN)
            text=change(text,'--evidence evidence/s1-20261018/sesenta-tandas-850-909/packaging/NOMBRE-NUEVO','--evidence evidence/s1-20261018/sesenta-tandas-970-1029/packaging/NOMBRE-NUEVO')
        elif name.startswith('OPERAR-'):
            text=change(text,'712/832/849: esquema11)','712/832/849: esquema11;969: esquema12)')
            text=change(text,'[candidata849 de laboratorio](../evidence/s1-20261018/tanda-849/CANDIDATA849.json) tiene referencia `1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09` y20archivos','[candidata969 de laboratorio](../'+MF+') tiene referencia `'+PIN+'` y21archivos')
        else:
            text=change(text,'/712,832 y849 (esquema11) registrados','/712,832 y849 (esquema11)/969 (esquema12) registrados')
            text=change(text,'N=11 para712/832/849)','N=11 para712/832/849; N=12 para969)')
            text+='''\n\nIntegración970–1029: copiaQA849→969 conserva el origen completo, preparado/sello909 y recuperación832/11. Sólo la principal se copia a nuevas969/12 y recuperación849/11; SQL012 corre únicamente en destino. Se comparan por separado las dos bases del origen. Las35tablas/historia previas se conservan y las dos nuevas tablas de paleta arrancan vacías en12. Cuentas, contraseñas, sesiones y privados de aplicación permanecen; secretosPG nuevos. El retorno exige ausencia de actividad en todas las ramas, incluso INSERT+DELETE compensado. Si hay actividad/estado incierto, conservar ramas y resolver recovery_required; no arrancar binarios11 sobre12. New/Restore del ZIP y copiaQA son recorridos distintos. Sus evidencias nuevas se separan de910–969 y anteriores.\n'''
        p.write_bytes(text.replace('\n','\r\n' if b'\r\n' in raw else '\n').encode())
        changes['docs/'+name]=dict(before=hashlib.sha256(raw).hexdigest(),after=hashlib.sha256(p.read_bytes()).hexdigest())
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(dict(files=changes,scope='Packaged manuals before frozen inputs; operational evidence separate, not final adoption.'),indent=2)+'\n')
    print('4 manuals prepared for969/schema12')


if __name__=='__main__':main()
