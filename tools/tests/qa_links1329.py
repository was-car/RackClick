"""Plan three precise manual cases; actual QA1209 retains its availability."""
import importlib.util,json,subprocess,time,unittest
from pathlib import Path
from block1329 import ROOT,E,BASE,GIT,sha,save
CASES=[
 dict(id='QA-88',module='Recorrido de relaciones de grupos',title='Abrir desde una concesión el grupo de clientes correcto',feature='planned',steps=[
 'NO DISPONIBLE en el QA1209 actual. La candidata1329 requiere integración Windows y selección revisada antes de probar. Registra Bloqueado; conserva tus resultados anteriores.',
 'Cuando se habilite: ejecuta INICIAR-QA-RESTAURADO.cmd y usa Administrador de su archivo privado. Elige Español arriba a la derecha. En la barra izquierda pulsa Usuarios, cerca de la parte inferior.',
 'Debajo de Lista de cuentas localiza el botón Grupos y permisos y púlsalo si está cerrado. Dentro busca Relaciones de grupos · solo lectura, encima de Crear grupo. No hay un botón Relaciones de grupos en Secciones de administración; no uses los formularios de asignación para este recorrido.',
 'En Tipo de grupo elige Grupos de usuarios; en Grupo seleccionado elige un grupo con una concesión explícita sobre un grupo de clientes, contrastando su UUID completo. Si no existe una relación preparada de laboratorio, anota Bloqueado para esta parte.',
 'Dentro de Permisos asignados, encuentra la concesión cuyo ámbito dice Grupo de clientes. Anota el UUID del destino y pulsa Ver grupo de clientes a su lado.',
 'Comprueba que Tipo de grupo cambia a Grupos de clientes y Grupo seleccionado corresponde al UUID anotado, incluso si hay otro grupo con el mismo nombre. El foco de teclado debe quedar en ese selector.',
 'Contrasta los clientes y grupos de usuarios origen que muestra la ficha. Las concesiones globales o directas sobre un cliente individual no deben tener un botón que las convierta en un grupo de clientes.'
 ],expected='El recorrido usa el UUID del snapshot actual y abre una ficha de sólo lectura. No concede permisos, añade miembros ni confirma una escritura; nombres iguales no sustituyen la identidad.'),
 dict(id='QA-89',module='Recorrido de relaciones de grupos',title='Volver a grupos de usuarios y conservar borradores',feature='planned',steps=[
 'NO DISPONIBLE en el QA1209 actual; pendiente integrar candidata1329. No marques Pass sólo por disponer de los formularios anteriores.',
 'Cuando se habilite: con Administrador, abre Usuarios y Grupos y permisos como en QA-88. En Crear grupo escribe un nombre de borrador único en Nombre del grupo, sin pulsar Crear grupo. Anota también Usuario seleccionado en la ficha común.',
 'En Relaciones de grupos elige un grupo de clientes con concesiones desde dos grupos de usuarios. Cada origen muestra su nombre y UUID y el botón Ver grupo de usuarios. Si faltan esas relaciones de prueba, anota Bloqueado para esa parte.',
 'Pulsa Ver grupo de usuarios junto al segundo origen, contrasta su UUID completo y revisa sus miembros y concesiones. Desde su concesión vuelve con Ver grupo de clientes; abre después el primer origen por su botón.',
 'Si los dos grupos de usuarios se llaman igual, confirma que los UUID siguen siendo distintos y que cada botón abre el origen correcto. Un mismo cliente puede aparecer en varios grupos; no debe desaparecer de uno por recorrer el otro.',
 'Vuelve al formulario Crear grupo y al selector común de usuario. Deben conservar exactamente el borrador y la cuenta que anotaste. No debe aparecer confirmación de guardado por navegar.',
 'La ayuda de Crear grupo indica los editores de membresías y Permisos de grupos de usuarios. Para asignar se usa su formulario y se espera confirmación del servidor; abrir la ficha de Relaciones no realiza esa asignación.'
 ],expected='Ida y vuelta sólo cambia la ficha de relaciones. UUID, múltiples pertenencias, usuario común y borrador se conservan; la nueva ayuda dirige al editor real y no promete permisos automáticos.'),
 dict(id='QA-90',module='Recorrido de relaciones de grupos',title='Teclado, idiomas y retirada de relaciones obsoletas',feature='planned',steps=[
 'NO DISPONIBLE en el QA1209 actual; pendiente integrar candidata1329. La retirada de acceso sólo se prueba con cuentas de laboratorio preparadas, nunca con el último administrador.',
 'Cuando se habilite: abre Relaciones de grupos y una concesión sobre un grupo de clientes. Pulsa Tab hasta Ver grupo de clientes y actívalo con Enter. El selector Grupo seleccionado debe recibir el foco y mostrar el UUID de destino.',
 'Pulsa Tab hasta Ver grupo de usuarios de un origen y actívalo con Enter. Debe actualizar la ficha y anunciar la selección sin mover el destino de los formularios de membresías o permisos.',
 'Elige Alemán e Inglés en el selector de idioma de la esquina superior derecha, esperando que termine de guardar antes de seguir. Repite ambos botones: cambian las etiquetas del sistema; nombres de grupos y UUID siguen literales.',
 'Si puedes reducir la ventana a unos390px, repite el recorrido y desplázate por el panel. Los botones y selectores deben ser alcanzables sin perder el foco. Si no usas lector de pantalla, deja la comprobación de voz Bloqueada; la prueba visual no acredita voz.',
 'Con dos cuentas administradoras de laboratorio y otro perfil de navegador, actualiza o retira sólo una relación de prueba conocida desde el editor existente. En la primera sesión pulsa Actualizar grupos. No debe seguirse un enlace hacia un grupo que ya no esté en el snapshot recibido.',
 'Si se prepara una retirada de administración para esa cuenta de prueba, el servidor debe denegar su lectura y la actualización retirar fichas y enlaces previos. No revoques ni elimines al último administrador; si no hay fixture segura, registra Bloqueado para esta parte.'
 ],expected='Teclado y foco estable funcionan en EN/DE/ES y ancho reducido. El snapshot actual controla los destinos y una denegación retira datos anteriores. Nada sustituye la autorización servidor ni equivale a voz comprobada.')
]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 assert not (E/'QA-TESTS-01.json').exists();p=ROOT/'docs/QA-CASOS-WASCAR.json';before=p.read_bytes();old=json.loads(before);assert len(old['cases'])==87
 saved=E/'qa-before';saved.mkdir();(saved/p.name).write_bytes(before);helper=ROOT/'tools/tests/qa_category_colors1089.py';raw=helper.read_bytes();(saved/helper.name).write_bytes(raw)
 old['cases']=old['cases']+CASES;old['revision']='2026-10-18-bloque1270-1329';nl='\r\n' if b'\r\n' in before else '\n';p.write_bytes((json.dumps(old,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
 needle=b"self.assertEqual(len(current['cases']),87)";assert raw.count(needle)==1;helper.write_bytes(raw.replace(needle,b"self.assertEqual(len(current['cases']),90)"))
 base=load('guide1329base','tools/tests/test_qa_guide.py');guide=base.guide
 for profile in ['manual','rc9']:guide.generate(profile=profile)
 class Current1329(unittest.TestCase):
  def test_original87_complete_and_all_build_gates_exact(self):
   original=json.loads(before);now=json.loads(p.read_bytes());self.assertEqual(now['cases'][:87],original['cases']);self.assertEqual({k:v for k,v in now.items() if k not in ['revision','cases']},{k:v for k,v in original.items() if k not in ['revision','cases']})
  def test_new_cases_planned_for_actual_and_future_pairs(self):
   now=json.loads(p.read_bytes());self.assertEqual(now['cases'][87:],CASES)
   for ctx in [guide.context(profile='rc9'),guide.context(profile='manual'),dict(configured=True,roles=True,restored=True,origin='',bundle='future',dll='future')]:
    cs=json.loads(guide.render(now,ctx).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual([cs[c['id']]['available'] for c in CASES],[False]*3)
  def test_real_counts90_catalog87and8_available(self):
   now=json.loads(p.read_bytes());self.assertEqual(len(now['cases']),90)
   for profile,count in [('manual',8),('rc9',87)]:
    self.assertTrue(guide.generate(check=True,profile=profile));cs=json.loads(guide.render(now,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(c['available'] for c in cs.values()),count)
  def test_generator_and_result_code_byte_exact(self):self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),subprocess.check_output([str(GIT),'show',BASE+':tools/windows/qa_guide.py']))
  def test_helper_changes_only_one_ascii_count(self):self.assertEqual(helper.read_bytes(),raw.replace(needle,b"self.assertEqual(len(current['cases']),90)"))
 modules=[base,load('excel1329','tools/tests/test_rc9_excel_guide832.py'),load('status1329','tools/tests/test_qa_relations_status848.py'),load('ports1329','tools/tests/qa_port_colors969.py'),load('category1329','tools/tests/qa_category_colors1089.py')];suite=unittest.TestSuite()
 for m in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Current1329));start=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 save('QA-TESTS-01.json',dict(successful=r.wasSuccessful(),testsRun=r.testsRun,seconds=round(time.monotonic()-start,3),caseCount=90,available=dict(manual=8,rc9=87),planned=[88,89,90],previous87CompleteCasesExact=True,existingBuildGatesExact=True,generatorAndUserResultLogicExact=True,manualWascarResultsWritten=False,actualQaAccessed=False));print(json.dumps(dict(successful=r.wasSuccessful(),testsRun=r.testsRun,planned=[88,89,90],available=dict(manual=8,rc9=87))));return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
