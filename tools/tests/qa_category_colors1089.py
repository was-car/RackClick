"""Append planned category-palette cases while preserving all existing QA and result logic."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089'
BASE='eb97a85dc439c03718fa2af7db3f531567c0dccc'
CATALOG=ROOT/'docs/QA-CASOS-WASCAR.json'
UNAVAILABLE='NO DISPONIBLE en el QA969/esquema12 actual. Esta función está en desarrollo13 y necesita integrar distribución Windows y seleccionar una copia revisada antes de probar. Registra Bloqueado; conserva tus resultados anteriores.'
CASES=[
 dict(id='QA-82',module='Paleta personal por categorías',title='Guardar parejas de categorías, alternar y descartar borradores',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: ejecuta INICIAR-QA-RESTAURADO.cmd. Usa las credenciales privadas de Lector que muestra el CMD en un perfil de navegador separado y elige Español arriba a la derecha.',
  'En la barra izquierda pulsa Todos los clientes, debajo del título Infraestructura, para ir a las tarjetas de clientes. En la esquina superior derecha, junto al idioma y tema, pulsa Paleta. Dentro de la ventana central pulsa Parejas de categorías.',
  'Busca la fila Panel de parcheo ↔ Switch. Pulsa una muestra azul. Cambia a Tipos de puerto con el botón superior del diálogo y vuelve a Parejas de categorías: el borrador debe conservarse. Todavía no pulses Guardar.',
  'Pulsa Cerrar abajo. Vuelve a Paleta y Parejas de categorías: el cambio descartado no debe aparecer guardado.',
  'Vuelve a seleccionar la muestra azul de Panel de parcheo ↔ Switch y otra muestra para Switch ↔ Switch. Pulsa Guardar abajo a la derecha y espera el mensaje confirmado por el servidor.',
  'Recarga con Ctrl+F5 y abre de nuevo la sección. Comprueba los colores guardados. En otra ventana InPrivate inicia la MISMA cuenta: debe leer la misma paleta.',
  'Pulsa de nuevo la muestra activa o × en una fila. Sólo cambia el borrador; pulsa Guardar para quitar ese color. Comprueba que no se modifica la otra pareja ni los colores de Tipos de puerto.'
 ],expected='El Lector guarda sólo su preferencia personal. Hay28 parejas, incluidas consigo mismas, y10 muestras. Alternar secciones conserva borradores; Cerrar los descarta. Toggle/× requieren Guardar. La misma cuenta recupera el mapa desde el servidor.'),
 dict(id='QA-83',module='Paleta personal por categorías',title='Aplicar color a conexiones nuevas, prioridad y no recolorear existentes',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: inicia la cuenta Técnico del CMD en otro perfil. En la barra izquierda pulsa Todos los clientes, debajo de Infraestructura. Arriba a la derecha abre Paleta y Parejas de categorías; guarda azul para Panel de parcheo ↔ Switch y rojo para Switch ↔ Switch.',
  'Abre un cliente de laboratorio que Técnico pueda editar, luego un rack con un Patch Panel pp24/pp48/ppf24 y un Switch sw24/sw48/swsfp del catálogo. Usa puertos libres; si faltan equipos, créalos desde + Dispositivo y el catálogo. No uses el número gn como identidad ni puertos ocupados.',
  'Deja el color manual de cable en su estado automático/sin selección. Pulsa un puerto del Patch Panel y después uno compatible del Switch, siguiendo Click-Click. Espera confirmación del servidor y recarga: la conexión nueva debe quedar azul. En las dos caras el cable conserva ese mismo color.',
  'Crea otra conexión libre entre dos Switch: debe usar rojo. Para una tercera conexión Panel↔Switch elige antes un color manual distinto en el selector de cable; ese color explícito tiene prioridad sobre la pareja.',
  'Anota o captura los tres cables. En la barra izquierda pulsa Todos los clientes, debajo de Infraestructura; abre Paleta arriba a la derecha y cambia/guarda otro color para Panel↔Switch. Regresa al rack y recarga: los cables anteriores deben conservar sus colores; sólo nuevas conexiones automáticas usan la preferencia nueva.',
  'Si dispones de dos racks y del control de conexión entre racks, repite con extremos libres del mismo cliente. El orden de los extremos no cambia la pareja; no mezcles clientes. Los puertos con color explícito y estados/PoE mantienen sus indicadores.',
  'En un perfil con otra cuenta autorizada abre ese mismo rack y recarga: debe ver los colores guardados de los cables, aunque su paleta personal sea distinta. El Lector puede verlos pero no crear conexiones.'
 ],expected='El servidor decide el color inicial según categorías reales por UUID. Prioridad: color manual válido→pareja del actor→sin color. El color queda en el cable compartido y persiste tras recarga. No se recolorean cables previos, reconexiones, puertos ni estados; no se conceden permisos de inventario.'),
 dict(id='QA-84',module='Paleta personal por categorías',title='Separar usuarios y resolver errores sin éxitos fantasma',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: en dos perfiles independientes inicia Lector y Técnico con las credenciales privadas del CMD. En la barra izquierda pulsa Todos los clientes, debajo de Infraestructura; arriba a la derecha abre Paleta→Parejas de categorías y guarda un color distinto para la misma pareja en cada cuenta.',
  'Recarga ambos perfiles y comprueba que cada cuenta conserva su color. Cierra sesión abajo a la izquierda en uno de ellos e inicia la otra cuenta: no debe heredar el borrador ni la paleta del usuario anterior.',
  'Para el fallo opcional de esta pestaña, pulsa F12 y abre Red/Network. En su barra superior cambia Sin limitación/No throttling a Sin conexión/Offline. Si no encuentras el selector, anota Bloqueado para esta parte. Desconectar WiFi no corta el servidor local127.0.0.1.',
  'Cambia una muestra en Parejas de categorías y pulsa Guardar. No debe aparecer confirmación de éxito. Devuelve Red a Sin limitación y cierra las herramientas con F12.',
  'En el diálogo pulsa Consultar original. No registrado no significa guardado ni cancelado: usa Reintentar original o Cancelar original para resolver la misma intención. Si pide login, usa la misma cuenta. No envíes una intención nueva mientras siga pendiente.',
  'Después de resolver, recarga y comprueba el valor real. Con Tab recorre los botones de sección y muestras; Enter/Espacio deben activar el botón enfocado. En ancho390px debe poderse desplazar el panel sin perder Guardar/Cerrar.',
  'Repite la apertura en Alemán e Inglés desde el selector superior. Cambian etiquetas del sistema, sin traducir nombres que tú hayas escrito. No copies contraseñas en observaciones; registra Pass/Not Pass/Bloqueado y el paso concreto.'
 ],expected='Las cuentas conservan mapas independientes. Un fallo mantiene la intención original y sólo se confirma después de commit y lectura. El diálogo conserva controles de teclado y desplazamiento; se mantienen EN/DE/ES y los nombres del usuario.')
]

def baseline():
 return json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',BASE+':docs/QA-CASOS-WASCAR.json']))

def append():
 before=baseline();current=json.loads(CATALOG.read_bytes());assert current==before and len(current['cases'])==81
 current['revision']='2026-10-18-categorias1030-1089';current['cases']+=CASES
 CATALOG.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

spec=importlib.util.spec_from_file_location('guide1089',ROOT/'tools/windows/qa_guide.py')
guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)

class CategoryGuide1089(unittest.TestCase):
 def test_existing81_and_all_build_lists_unchanged(self):
  old=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','60868854ce40a0eda773fd1817f48f7da41aae46:docs/QA-CASOS-WASCAR.json']))
  current=json.loads(CATALOG.read_bytes());matrix=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/QA-MATRIX-1149.json').read_bytes())
  self.assertEqual(current['cases'][:81],old['cases'][:81])
  for case,original in zip(current['cases'][81:],old['cases'][81:]):
   self.assertEqual(case,{**original,'feature':'userCategoryColorsGui','steps':[case['steps'][0]]+original['steps'][1:]})
   self.assertIn('DISPONIBLE EN TU SNAPSHOT',case['steps'][0])
  for key,value in old.items():
   if key in ['cases','revision']:continue
   expected=value+[matrix['pair']] if key in matrix['inheritedBuildLists'] else value
   self.assertEqual(current[key][:len(expected)] if key in matrix['inheritedBuildLists'] else current[key],expected)
  self.assertEqual(current['userCategoryColorsBuilds'][:1],[matrix['pair']])

 def test_closed_1149_availability_owner_config_and_generator(self):
  current=json.loads(CATALOG.read_bytes());matrix=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/QA-MATRIX-1149.json').read_bytes());self.assertEqual(len(current['cases']),93)
  def available(ctx,catalog=current):
   cases=json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
   return [cases['QA-'+str(i)]['available'] for i in [82,83,84]]
  ctx=dict(configured=True,roles=True,restored=True,origin='',**matrix['pair'])
  self.assertEqual(available(ctx),[True]*3)
  for delta in [matrix['sourcePair'],dict(dll='future'),dict(bundle='future'),dict(roles=False),dict(configured=False)]:
   self.assertEqual(available({**ctx,**delta}),[False]*3)
  missing={k:v for k,v in current.items() if k!='userCategoryColorsBuilds'};self.assertEqual(available(ctx,missing),[False]*3)
  for profile,count in [('manual',8),('rc9',93)]:
   self.assertTrue(guide.generate(check=True,profile=profile))
   cases=json.loads(guide.render(current,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(v['available'] for v in cases.values()),count)
  before=(ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/qa-guide/source-before/qa_guide.py').read_bytes()
  anchor=b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"
  nl=b'\r\n' if b'\r\n' in before else b'\n'
  self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),before.replace(anchor,anchor+nl+b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),").replace(b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),",b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),"+nl+b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),").replace(b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),",b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),"+nl+b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),").replace(b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),",b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),"+nl+b"        'adminGroupReceiptGui': catalog.get('adminGroupReceiptBuilds', []),"))

if __name__=='__main__':
 import sys
 if '--append' in sys.argv:append()
 else:unittest.main()
