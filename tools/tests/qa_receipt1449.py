"""Append three unavailable receipt cases; preserve original90 and Wascar results."""
import importlib.util,json,subprocess,time,unittest
from block1449 import ROOT,E,BASE,GIT,sha,save
UNAVAILABLE='NO DISPONIBLE en el QA1329 actual. La candidata1449 necesita integración Windows y selección revisada. Registra Bloqueado; no cambies los resultados anteriores.'
CASES=[
 dict(id='QA-91',module='Continuación del alta de grupos',title='Crear un grupo y abrir sus relaciones por UUID',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: ejecuta INICIAR-QA-RESTAURADO.cmd y usa Administrador de su archivo privado. Elige Español arriba a la derecha. En la barra izquierda pulsa Usuarios, cerca de la parte inferior; debajo de Lista de cuentas pulsa Grupos y permisos si está cerrado.',
  'Dentro de Grupos y permisos baja hasta Crear grupo, debajo del visor Relaciones de grupos · solo lectura. En Tipo de grupo elige Grupo de usuarios y en Nombre del grupo escribe un nombre de laboratorio único con una letra acentuada y, si quieres, caracteres como 東京. Pulsa Crear grupo y espera confirmación.',
  'Busca la tarjeta Grupo creado dentro de este panel. Contrasta el nombre literal, tipo y UUID completo. El formulario ya no debe mostrar una solicitud pendiente. Sin pulsar nada, el visor de relaciones no debe haberse cambiado automáticamente al grupo nuevo.',
  'En la tarjeta pulsa Abrir relaciones. La página debe llevarte al visor Relaciones de grupos · solo lectura, seleccionar Grupos de usuarios y el UUID anotado en Grupo seleccionado. El foco debe quedar en este selector.',
  'Comprueba que el grupo nuevo tiene sus propias relaciones; crearlo o abrirlo no añade usuarios ni concede permisos. Si hay un grupo de nombre igual, contrasta los UUID completos para distinguirlos.',
  'Recarga con Ctrl+F5 y vuelve a Usuarios→Grupos y permisos. El grupo debe seguir en la lista, pero la tarjeta temporal Grupo creado ya no debe aparecer. En otra ventana InPrivate inicia Administrador y comprueba el mismo UUID en la lista.'
 ],expected='La tarjeta acredita un commit confirmado, identifica tipo/UUID y ofrece una navegación explícita de solo lectura. La creación persiste; el recibo temporal no persiste ni asigna permisos.'),
 dict(id='QA-92',module='Continuación del alta de grupos',title='Grupo de clientes, borradores y solicitud pendiente',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: con Administrador abre Usuarios→Grupos y permisos. En Membresía de grupos de usuarios, Clientes en grupos de clientes y Permisos de grupos de usuarios elige destinos de laboratorio para preparar borradores, sin pulsar sus botones de guardado. Anota cada selección y Usuario seleccionado de la ficha común.',
  'En Crear grupo elige Grupo de clientes, escribe un nombre de prueba y pulsa Crear grupo. En Grupo creado anota tipo y UUID; pulsa Abrir relaciones. Debe seleccionar exactamente ese grupo de clientes y conservar los tres borradores y el usuario común.',
  'Para iniciar otra intención, cambia Nombre del grupo o Tipo de grupo. La tarjeta anterior debe retirarse; el nuevo texto aún no es un alta confirmada. No envíes otra solicitud si aparece una pendiente.',
  'Si ocurre un fallo de red real durante el alta, conserva la pestaña. Busca la advertencia de solicitud pendiente y pulsa Consultar resultado del grupo. No registrado no significa guardado ni cancelado; usa Reintentar alta original o Cancelar alta de grupo pendiente para resolver esa misma intención, siguiendo la ayuda visible. No desconectes el servidor ni borres el journal.',
  'Sólo si Consultar resultado del grupo devuelve el alta ya confirmada debe aparecer Grupo creado con su UUID original. Una cancelación real o error no debe inventar una tarjeta. Mientras quede pendiente o falle Actualizar grupos, Abrir relaciones debe estar bloqueado.',
  'Si no se produjo un fallo de red o no puedes provocar uno de forma segura, marca esa parte Bloqueada y anota el paso. No es necesario alterar bases, contraseñas o la última cuenta administradora para esta prueba.'
 ],expected='Ambos tipos usan su UUID confirmado. La navegación conserva borradores y no escribe asignaciones. Las solicitudes inciertas se consultan por su identidad original; no hay confirmación por coincidencia de nombre.'),
 dict(id='QA-93',module='Continuación del alta de grupos',title='Teclado, idiomas y actualización sin repetir navegación',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: crea un grupo de laboratorio como en QA-91. Con Tab llega al botón Abrir relaciones de Grupo creado y actívalo con Enter. El foco debe ir a Grupo seleccionado y su valor debe corresponder al UUID de la tarjeta.',
  'En el visor elige manualmente otro grupo. Pulsa Actualizar grupos, encima del visor, y espera que termine de leer. La navegación anterior no debe volver a ejecutarse automáticamente ni reemplazar destinos de formularios de asignación.',
  'Para cada idioma, vuelve a Todos los clientes con el botón de la barra izquierda; al salir de Administración se pierde el recibo temporal. En la esquina superior derecha elige Alemán o Inglés y espera que termine de guardar. Vuelve a Usuarios y Grupos y permisos, crea otro grupo de laboratorio y pulsa el botón de su tarjeta. Cambian las etiquetas del sistema; conserva el nombre literal y UUID de cada grupo. Repite para volver a Español. No busques el selector de idioma dentro de Administración.',
  'Reduce la ventana a unos390px si puedes. Desplázate hasta Grupo creado y activa el botón con teclado. La tarjeta, UUID completo y controles deben ser legibles y alcanzables sin desbordamiento horizontal de la página.',
  'Cierra sesión desde la parte inferior izquierda e inicia otra cuenta preparada de laboratorio en el mismo navegador. No debe ver la tarjeta temporal de la cuenta anterior. Una cuenta Lector no obtiene controles de administración por haber abierto antes la sesión Administrador.',
  'Si no utilizas lector de pantalla, deja la comprobación de voz Bloqueada: una prueba visual/teclado no acredita el anuncio de voz. No copies secretos en observaciones; registra Pass/Not Pass/Bloqueado y el paso concreto.'
 ],expected='La continuación es accesible por teclado y de un solo uso. Idiomas/ancho reducido conservan nombres/UUID y controles; cambiar de actor retira el recibo y el servidor sigue comprobando permisos.')
]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 assert not (E/'QA-TESTS-01.json').exists();p=ROOT/'docs/QA-CASOS-WASCAR.json';before=p.read_bytes();old=json.loads(before);assert len(old['cases'])==90
 saved=E/'qa-before';saved.mkdir();(saved/p.name).write_bytes(before);helper=ROOT/'tools/tests/qa_category_colors1089.py';raw=helper.read_bytes();(saved/helper.name).write_bytes(raw)
 old['cases']+=CASES;old['revision']='2026-10-18-bloque1390-1449';nl='\r\n' if b'\r\n' in before else '\n';p.write_bytes((json.dumps(old,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
 needle=b"self.assertEqual(len(current['cases']),90)";assert raw.count(needle)==1;helper.write_bytes(raw.replace(needle,b"self.assertEqual(len(current['cases']),93)"))
 base=load('guide1449base','tools/tests/test_qa_guide.py');guide=base.guide
 for profile in ['manual','rc9']:guide.generate(profile=profile)
 class Current1449(unittest.TestCase):
  def test_original90_complete_and_build_lists_exact(self):
   previous=json.loads(before);now=json.loads(p.read_bytes());self.assertEqual(now['cases'][:90],previous['cases']);self.assertEqual({k:v for k,v in now.items() if k not in ['revision','cases']},{k:v for k,v in previous.items() if k not in ['revision','cases']})
  def test_three_cases_unavailable_even_for_future_pair(self):
   now=json.loads(p.read_bytes());self.assertEqual(now['cases'][90:],CASES)
   for ctx in [guide.context(profile='rc9'),guide.context(profile='manual'),dict(configured=True,roles=True,restored=True,origin='',bundle='future',dll='future')]:
    cases=json.loads(guide.render(now,ctx).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual([cases[c['id']]['available'] for c in CASES],[False]*3)
  def test_catalog93_actual_counts90_and8(self):
   now=json.loads(p.read_bytes());self.assertEqual(len(now['cases']),93)
   for profile,count in [('manual',8),('rc9',90)]:
    self.assertTrue(guide.generate(check=True,profile=profile));cases=json.loads(guide.render(now,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(v['available'] for v in cases.values()),count)
  def test_generator_and_result_logic_exact(self):self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),subprocess.check_output([str(GIT),'show',BASE+':tools/windows/qa_guide.py']))
  def test_only_existing_test_count_changed(self):self.assertEqual(helper.read_bytes(),raw.replace(needle,b"self.assertEqual(len(current['cases']),93)"))
 modules=[base,load('excel1449','tools/tests/test_rc9_excel_guide832.py'),load('status1449','tools/tests/test_qa_relations_status848.py'),load('ports1449','tools/tests/qa_port_colors969.py'),load('category1449','tools/tests/qa_category_colors1089.py')];suite=unittest.TestSuite()
 for m in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Current1449));start=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 save('QA-TESTS-01.json',dict(successful=r.wasSuccessful(),testsRun=r.testsRun,seconds=round(time.monotonic()-start,3),caseCount=93,available=dict(manual=8,rc9=90),planned=[91,92,93],previous90CompleteCasesExact=True,existingBuildGatesExact=True,generatorAndUserResultLogicExact=True,manualWascarResultsWritten=False,actualQaAccessed=False));print(json.dumps(dict(successful=r.wasSuccessful(),testsRun=r.testsRun,planned=[91,92,93],available=dict(manual=8,rc9=90))));return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
