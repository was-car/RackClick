"""Append planned manual palette cases, retaining every previous case and user result logic."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = 'a71d508289f23b62a00fff0d75225f2ca015b22d'
CATALOG = ROOT / 'docs/QA-CASOS-WASCAR.json'
spec = importlib.util.spec_from_file_location('guide969', ROOT / 'tools/windows/qa_guide.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


CASES = [
 dict(id='QA-79', module='Paleta personal RC9', title='Editar colores por tipo y confirmar guardado', feature='planned', steps=[
  'NO DISPONIBLE en el QA849 actual. Esta función de desarrollo requiere integrar y seleccionar una candidata de esquema12 antes de probar. Hoy registra Bloqueado y conserva tus resultados anteriores.',
  'Cuando se habilite: ejecuta INICIAR-QA-RESTAURADO.cmd. Abre la guía restaurada y usa las credenciales privadas de Lector indicadas por ese CMD, en un perfil de navegador independiente.',
  'En la barra izquierda pulsa RackClick o Infraestructura para volver a las tarjetas de clientes. Arriba a la derecha, junto al idioma y tema, pulsa Paleta.',
  'En la ventana central identifica RJ45 y RJ45 PoE. Pulsa el cuadrado de color de RJ45 y elige otro color; haz lo mismo con RJ45 PoE. Los dos tipos son independientes.',
  'Sin pulsar Guardar, cierra la ventana con Cerrar en la parte inferior. Vuelve a abrirla: deben aparecer los colores guardados anteriores.',
  'Elige otra vez los dos colores y pulsa Guardar en la parte inferior derecha. Espera a la confirmación del servidor; un error o pendiente no significa guardado.',
  'Cierra la ventana. Abre un cliente y un rack desde las tarjetas o árbol izquierdo. Observa puertos libres sin color explícito: usan tu paleta. Los colores explícitos y de cables, estados y PoE mantienen su prioridad.'
 ], expected='El Lector puede cambiar su preferencia personal sin editar inventario. El borrador descartado no persiste. Sólo tras confirmación y lectura del servidor cambia la paleta; RJ45 y RJ45 PoE son distintos.'),
 dict(id='QA-80', module='Paleta personal RC9', title='Recarga, otra sesión y separación de usuarios', feature='planned', steps=[
  'NO DISPONIBLE en el QA849 actual; pendiente integrar esquema12. No repitas los casos anteriores por este guion nuevo.',
  'Después de QA-79, recarga la página y vuelve a Paleta, arriba a la derecha de Infraestructura. Comprueba tus colores confirmados.',
  'Abre otro perfil de navegador o ventana InPrivate e inicia sesión con la MISMA cuenta de Lector del CMD. Abre Paleta: debe recuperar los mismos colores desde el servidor.',
  'En un tercer perfil inicia sesión con Técnico u otra cuenta del CMD. Abre su paleta, cambia y guarda un color. Vuelve al Lector y recarga: debe conservar su propia paleta.',
  'Cierra sesión mediante el botón de la parte inferior izquierda; inicia con la otra cuenta en ese mismo navegador. Abre la paleta: no debe heredar los colores de quien cerró sesión.',
  'No uses dos pestañas normales para representar usuarios diferentes: comparten la cookie de login. No copies contraseñas en las observaciones.'
 ], expected='Los colores confirmados sobreviven a la recarga y se comparten entre sesiones de la misma cuenta. Cada cuenta conserva su propia paleta, sin cambiar puertos ni cables del inventario.'),
 dict(id='QA-81', module='Paleta personal RC9', title='Restaurar valores y recuperar un guardado incierto', feature='planned', steps=[
  'NO DISPONIBLE en el QA849 actual; pendiente integrar esquema12. La parte de fallo de red sólo se prueba cuando puedas cortar temporalmente tu conexión de prueba sin afectar otros usuarios; en caso contrario anota Bloqueado para esa parte.',
  'Desde Infraestructura abre Paleta, arriba a la derecha. Cambia dos tipos y pulsa Guardar; espera la confirmación.',
  'Pulsa ↺ a la derecha de un tipo modificado: sólo cambia su borrador. Pulsa Guardar y comprueba el valor inicial de ese tipo y que el otro conserva su color.',
  'Pulsa Restablecer todo y después Guardar. Cierra, recarga y vuelve a abrir: todos deben tener los valores iniciales.',
  'Para el fallo controlado de esta pestaña: pulsa F12; abre la pestaña Red (Network) del panel de herramientas. En su barra superior cambia Sin limitación (No throttling) a Sin conexión (Offline). Si no localizas ese selector, deja esta parte Bloqueada. Cambia un color en Paleta y pulsa Guardar: no debe confirmar éxito. Desactivar WiFi no sirve para el servidor local127.0.0.1.',
  'En el mismo selector de Red vuelve a Sin limitación (No throttling) y cierra las herramientas con F12. En la ventana Paleta pulsa Consultar original. Si no se registró, sigue pendiente: puedes usar Reintentar original o Cancelar original. Si pide login, usa la misma cuenta.',
  'Consulta antes de repetir una operación con una intención nueva. Tras resolverla, recarga y anota el valor real y cualquier error. Con 390px de ancho prueba desplazamiento y Tab sin controles recortados.'
 ], expected='Restaurar individual/todos requiere Guardar. Un fallo conserva la intención original y nunca declara éxito sin commit. Consultar no registrado no es guardado; reintento/cancelación resuelven el pendiente sin cambiar inventario.')
]


def update():
    catalog = json.loads(CATALOG.read_bytes())
    assert len(catalog['cases']) == 78
    catalog['revision'] = '2026-10-18-bloque910-969'
    catalog['cases'].extend(CASES)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for profile in ['manual','rc9']:
        guide.generate(profile=profile)


class GuidePalette969(unittest.TestCase):
    def test_previous_cases_and_build_gates_unchanged(self):
        original=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','962948f48543429d22cc806d5951ea94e2c90dc2:docs/QA-CASOS-WASCAR.json']))
        current=json.loads(CATALOG.read_bytes())
        matrix=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/QA-MATRIX-1029.json').read_bytes())
        self.assertEqual(current['cases'][:78],original['cases'][:78])
        for key,value in original.items():
            if key in ['revision','cases']:continue
            expected=value+[matrix['pair']] if key in matrix['inheritedBuildLists'] else value
            self.assertEqual(current[key][:len(expected)] if key in matrix['inheritedBuildLists'] else current[key],expected)

    def test_three_new_cases_require_the_closed_1029_pair(self):
        catalog=json.loads(CATALOG.read_bytes())
        original=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','962948f48543429d22cc806d5951ea94e2c90dc2:docs/QA-CASOS-WASCAR.json']))
        m=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/QA-MATRIX-1029.json').read_bytes())
        self.assertIn(m['pair'],catalog['userPortColorsBuilds'])
        for case,old in zip(catalog['cases'][78:],original['cases'][78:]):
            self.assertEqual(case,{**old,'feature':'userPortColorsGui','steps':[case['steps'][0]]+old['steps'][1:]})
        def availability(ctx):
            data=json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
            return [data['QA-'+str(n)]['available'] for n in [79,80,81]]
        ctx=dict(configured=True,roles=True,restored=True,origin='',**m['pair'])
        self.assertEqual(availability(ctx),[True]*3)
        for delta in [m['sourcePair'],dict(bundle='future'),dict(dll='future'),dict(roles=False),dict(configured=False)]:
            self.assertEqual(availability({**ctx,**delta}),[False]*3)

    def test_actual_availability_and_result_logic_preserved(self):
        catalog=json.loads(CATALOG.read_bytes())
        for profile,count in [('manual',8),('rc9',93)]:
            metadata=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases']
            self.assertEqual(sum(v['available'] for v in metadata.values()),count)
            self.assertTrue(guide.generate(check=True,profile=profile))
        before=(ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/qa-guide/source-before/qa_guide.py').read_bytes()
        anchor=b"        'adminGroupRelationsAnnouncementGui': catalog.get('adminGroupRelationsAnnouncementBuilds', []),"
        newline=b'\r\n' if b'\r\n' in before else b'\n'
        added=newline+b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"
        self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),before.replace(anchor,anchor+added).replace(b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),",b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"+newline+b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),").replace(b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),",b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),"+newline+b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),").replace(b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),",b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),"+newline+b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),").replace(b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),",b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),"+newline+b"        'adminGroupReceiptGui': catalog.get('adminGroupReceiptBuilds', []),"))


if __name__ == '__main__':
    import sys
    if '--update' in sys.argv:
        update()
    else:
        unittest.main()
