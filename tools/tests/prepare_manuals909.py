"""Update the four packaged manuals before freezing the849 Windows ZIP."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-850-909'


def replace(text, before, after):
    assert before in text, before[:100]
    return text.replace(before, after, 1)


def main():
    output = E / 'MANUALES-01.json'
    assert not output.exists()
    headers = {
        'MANUAL-PAQUETE-WINDOWS-S1.md': '**Candidata interna849 · integración850–909.** Incluye el aviso accesible persistente al seleccionar grupos, XLS(HTMLRC9), preferencias personales y bibliotecas privadas/compartidas. Perfiles712/832/849 de esquema11 y20servidor+18interfaz; anteriores conservados. Se reutiliza la candidata849 probada con Edge/PostgreSQL, sin compilar otra vez. Voz con lector, servicio/identidad/PKI, Windows limpio, licencias y adopción final siguen pendientes.',
        'CONSTRUIR-PAQUETE-WINDOWS-S1.md': '**Integración850–909.** Siete perfiles cerrados:337/397/532 de esquema9,592-FINAL02 de10 y712-FINAL02/832-02/849 de11. Candidata849 congelada, sin nuevas compilaciones. Se fijan25operadores y4manuales antes de producir dos ZIP nuevos idénticos. Motores de copia QA separados; no se admiten pines ni esquemas arbitrarios.',
        'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md': '**Aplicación849/esquema11.** Conserva el servidor832 exacto y añade el aviso accesible compacto de grupos en la interfaz. SQL001–011, dependencias y CSS sin cambios. La copiaQA832→849 crea un laboratorio nuevo con recuperación832; conserva íntegro el origen832 y su recuperación712, cuentas/sesiones/privados y permisos. No es Restore administrativo ni una prueba de voz de lector de pantalla.',
        'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md': '**Compatibilidad849/esquema11.** Backup/Restore conservan35tablas y recibos de informes. Restore administrativo crea ROOT/clúster/base/roles/TLS/administrador nuevos y revoca sesiones copiadas, con diferencias explícitas. La copiaQA832→849 conserva cuentas/sesiones/privados, genera sólo secretosPG nuevos y añade recuperación832 separada; no migra ni recupera administrador. No acredita recuperación integral del host, servicio/PKI o adopción final.'
    }
    changes = {}
    for name, header in headers.items():
        path = ROOT / 'docs' / name
        before = path.read_bytes()
        text = before.decode().replace('\r\n', '\n')
        start = text.index('**')
        end = text.index('\n\n', start)
        text = text[:start] + header + text[end:]
        if name.startswith('MANUAL-'):
            text = replace(text, 'Aplicación e interfaz832/esquema11 reutilizadas sin recompilar en833–847. Los paquetes337/397/532/592/712', 'Aplicación e interfaz849/esquema11 reutilizadas sin recompilar en850–909. Los paquetes337/397/532/592/712/832')
            text = replace(text, 'perfil337,397,532,592,712 o832 registrado', 'perfil337,397,532,592,712,832 o849 registrado')
            text = replace(text, 'un backup11 requiere712 o832,', 'un backup11 requiere712,832 o849,')
            text += '''\n\n## Aviso accesible de grupos en849

Inicia sesión con una cuenta sintética que pueda administrar seguridad. En Usuarios abre Grupos y permisos y localiza Relaciones de grupos · solo lectura, debajo de Actualizar grupos. Usa Tipo de grupo y Grupo seleccionado para elegir por nombre y UUID. La ficha mantiene el ID completo; el selector nativo puede recortarlo visualmente. Cambiar tipo retira la ficha anterior. Un aviso accesible compacto permanece desde la primera selección; no convierte la lista completa de relaciones en un anuncio.

Los nombres escritos por el usuario se conservan literalmente en EN/DE/ES. Elegir o navegar no cambia permisos ni guarda datos. Un error de lectura retira los detalles anteriores; la autorización se comprueba en el servidor. Las comprobaciones DOM/AX no prueban voz de Narrador/NVDA/JAWS. QA-78 explica la prueba manual con lector habitual; sólo realizarla cuando la guía del laboratorio indique disponible. Si no se dispone de lector, registrar la variante no realizada y Bloqueado. No se sobrescriben resultados anteriores.
'''
        elif name.startswith('CONSTRUIR-'):
            text = replace(text, 'estos seis perfiles', 'estos siete perfiles')
            anchor = '\n\nEl productor exige el hash externo'
            row = '| [849/aviso accesible](../evidence/s1-20261018/tanda-849/CANDIDATA849.json) |11 /20+18|7.108.622|`1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`|'
            text = replace(text, anchor, '\n' + row + anchor)
            text = replace(text, '--manifest evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json', '--manifest evidence/s1-20261018/tanda-849/CANDIDATA849.json')
            text = replace(text, '--expected-manifest-sha 511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5', '--expected-manifest-sha 1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09')
            text = replace(text, '--evidence evidence/s1-20261018/quince-tandas-833-847/packaging/NOMBRE-NUEVO', '--evidence evidence/s1-20261018/sesenta-tandas-850-909/packaging/NOMBRE-NUEVO')
        elif name.startswith('OPERAR-'):
            text = replace(text, '712/832: esquema11)', '712/832/849: esquema11)')
            text = replace(text, '[candidata832 de laboratorio](../evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json) tiene referencia `511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5`', '[candidata849 de laboratorio](../evidence/s1-20261018/tanda-849/CANDIDATA849.json) tiene referencia `1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`')
        else:
            text = replace(text, '/712 y832 (esquema11) registrados', '/712,832 y849 (esquema11) registrados')
            text = replace(text, 'N=11 para712/832)', 'N=11 para712/832/849)')
            text += '''\n\nIntegración850–909: la nueva copia conserva el laboratorio832 completo, incluidos su preparado/sello847 y la recuperación712. Se copian sólo los datos actuales de su base principal a las ramas849 y recuperación832 en un clúster nuevo. No se supone igualdad entre las dos bases del origen: se protegen sus snapshots por separado. El retorno exige ausencia de actividad en todas las ramas, incluida actividad compensada; si hay actividad se conservan las ramas y se requiere recuperación explícita. No sustituye el Restore administrativo del instalador. Los resultados nuevos se registran separados de847/848/849 y de las pruebas históricas.\n'''
        newline = '\r\n' if b'\r\n' in before else '\n'
        path.write_bytes(text.replace('\n', newline).encode())
        changes['docs/' + name] = dict(before=hashlib.sha256(before).hexdigest(), after=hashlib.sha256(path.read_bytes()).hexdigest())
    output.write_text(json.dumps(dict(files=changes, purpose='Four manuals frozen before package construction; no claim of final adoption or screen-reader speech.'), indent=2) + '\n', encoding='utf-8')
    print('4 manuals updated for closed849')


if __name__ == '__main__':
    main()
