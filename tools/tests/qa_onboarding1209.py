"""Append three planned manual cases; preserve old cases, gates and result logic."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import unittest
from init_onboarding1209 import ROOT,E,BASE,GIT,sha

UNAVAILABLE='NO DISPONIBLE en el QA1089/esquema13 actual. La candidata1209 conserva el esquema, pero necesita integrar y seleccionar su interfaz revisada antes de probar. Registra Bloqueado; conserva los resultados anteriores.'
CASES=[
 dict(id='QA-85',module='Alta administrativa guiada',title='Crear cuenta y continuar con el UUID confirmado',feature='planned',steps=[
  UNAVAILABLE,
  'Cuando esté habilitada: ejecuta INICIAR-QA-RESTAURADO.cmd. Usa la cuenta Administrador que muestra ese CMD y elige Español arriba a la derecha antes de entrar a administración. No copies contraseñas en observaciones.',
  'En la barra lateral izquierda pulsa Usuarios, cerca de la parte inferior. En Secciones de administración, a la izquierda del contenido, pulsa Crear cuenta. En el centro verás Nombre de usuario y Contraseña.',
  'Escribe un nombre de prueba único, por ejemplo qa-usuario-fecha-hora, y una contraseña privada de16 a1024 caracteres. Pulsa Crear usuario debajo de los campos. Espera confirmación del servidor.',
  'Desplázate un poco hacia arriba hasta Cuenta creada. Contrasta el nombre guardado y el UUID completo con la lista de cuentas. El texto no debe decir que ya tiene acceso a clientes.',
  'En esa tarjeta pulsa Continuar a membresías. Debe abrirse Grupos y permisos y enfocarse Membresías de usuarios. El Usuario seleccionado común y el destino del panel deben corresponder al mismo UUID confirmado.',
  'Si el panel ya estaba abierto antes del alta, pulsa Actualizar grupos para cargar la cuenta nueva. Comprueba el nombre y UUID antes de elegir un grupo. Abrir este recorrido por sí solo no asigna ningún grupo.',
  'Conserva la página abierta para QA-86. Si recargas o sales de Usuarios, la tarjeta temporal puede desaparecer; la cuenta confirmada debe seguir en la lista y poder seleccionarse por el selector común.'
 ],expected='Sólo un recibo confirmado muestra Cuenta creada. Nombre y UUID proceden del servidor, sin selección por coincidencia de nombre. Continuar abre el panel existente y no concede acceso automáticamente. La cuenta persiste aunque la tarjeta temporal desaparezca.'),
 dict(id='QA-86',module='Alta administrativa guiada',title='Asignar un grupo y comprobar acceso efectivo desde otra sesión',feature='planned',steps=[
  UNAVAILABLE,
  'Comienza desde la tarjeta Cuenta creada de QA-85, sin recargarla. En Membresías de usuarios pulsa Actualizar grupos si falta la cuenta. Verifica Usuario seleccionado y el UUID de destino; no uses otra cuenta con un nombre parecido.',
  'En Grupo de usuarios elige un grupo de prueba con acceso limitado a un cliente, usando también su UUID. Si no existe ese grupo de laboratorio, deja esta parte Bloqueada y anótalo; no utilices el último grupo administrador para experimentar.',
  'En Acción deja Añadir y pulsa Guardar asignación debajo del formulario. Espera Asignación confirmada por el servidor. Si hay pendiente, error o conflicto, resuélvelo en ese panel antes de continuar.',
  'Vuelve hacia arriba a Cuenta creada y pulsa Revisar permisos efectivos. En el panel enfocado pulsa Actualizar cuentas y luego Consultar permisos. Contrasta la cuenta y UUID, los clientes accesibles y Procedencia de los permisos.',
  'Abre otro perfil de navegador o ventana InPrivate. Inicia con la cuenta nueva y su contraseña privada. Debe ver sólo los clientes concedidos por sus grupos; no debe aparecer Usuarios si no tiene administración global.',
  'Recarga ambas sesiones. La cuenta y su membresía deben persistir; en administración puedes seleccionarla de nuevo y volver a consultar sus permisos. No esperes que la tarjeta temporal sobreviva a la recarga.',
  'No uses dos pestañas normales para representar usuarios distintos: comparten la cookie. No añadas contraseñas al archivo de resultados.'
 ],expected='Membresía y permisos se confirman por operaciones independientes del servidor. La navegación no sustituye Guardar asignación ni Consultar permisos. Otra sesión lee el acceso real, limitado por cliente; la recarga conserva los datos confirmados.'),
 dict(id='QA-87',module='Alta administrativa guiada',title='Proteger borradores y resolver un alta incierta sin éxitos fantasma',feature='planned',steps=[
  UNAVAILABLE,
  'Con una tarjeta Cuenta creada visible, desplázate al panel Restablecer contraseña y escribe sólo un borrador en su campo, sin enviarlo. Vuelve a Cuenta creada: los botones de continuación deben quedar bloqueados; nombre, UUID y borrador no deben cambiar.',
  'Vacía ese campo de contraseña. Espera que termine cualquier carga o recuperación. Los botones vuelven a estar disponibles. En Membresías de usuarios elige un grupo sin guardar: la continuación debe bloquearse también; usa Descartar borrador de membresía para liberarla.',
  'La parte de red es opcional y sólo afecta a tu pestaña de laboratorio. Si no encuentras F12/Red/Network o el selector Offline, registra Bloqueado para esta parte; no desconectes la red de otras personas.',
  'Antes de intentar otra alta, vuelve a Usuarios y pulsa Actualizar. Pulsa F12, abre Red/Network y cambia Sin limitación/No throttling a Sin conexión/Offline. Rellena otro nombre único y contraseña privada en Crear cuenta; pulsa Crear usuario. No debe aparecer una tarjeta de éxito por esa solicitud incierta.',
  'Vuelve a Sin limitación en el mismo selector y cierra F12. En el aviso pendiente pulsa Consultar resultado original. Si devuelve el alta confirmada, aparece su nombre y UUID; si no está registrada, sigue pendiente y no hay tarjeta de éxito.',
  'Para una solicitud no registrada usa Cancelar alta pendiente y espera la confirmación. La cancelación real no crea cuenta ni tarjeta. Si el servidor ya había confirmado el alta, cancelar recupera ese resultado y debe mostrar la cuenta realmente creada.',
  'No crees otra intención con el mismo nombre para adivinar el resultado. Resuelve primero la solicitud original. Anota mensajes y UUID, sin incluir la contraseña. Las pruebas de retirada401/403 requieren una fixture preparada; no revoques al último administrador real.'
 ],expected='Borradores, cargas y solicitudes pendientes bloquean la continuación sin cambiar su destino. Un resultado incierto/no registrado no se presenta como creación. Consultar o cancelar recupera el resultado original; la cancelación confirmada no se confunde con un alta.')
]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    output=E/'QA-TESTS-01.json';assert not output.exists()
    catalog_path=ROOT/'docs/QA-CASOS-WASCAR.json';before=catalog_path.read_bytes();original=json.loads(before);assert len(original['cases'])==84
    saved=E/'qa-guide/source-before';saved.mkdir(parents=True,exist_ok=False);(saved/'QA-CASOS-WASCAR.json').write_bytes(before)
    catalog=json.loads(before);catalog['revision']='2026-10-18-bloque1150-1209';catalog['cases'].extend(CASES)
    nl='\r\n' if b'\r\n' in before else '\n';catalog_path.write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
    p=ROOT/'tools/tests/qa_category_colors1089.py';old=p.read_bytes();(saved/p.name).write_bytes(old)
    needle=b"self.assertEqual(len(current['cases']),84)";assert old.count(needle)==1
    p.write_bytes(old.replace(needle,b"self.assertEqual(len(current['cases']),87)"))
    base=load('guide1209base','tools/tests/test_qa_guide.py');guide=base.guide
    for profile in ['manual','rc9']:guide.generate(profile=profile)
    class OnboardingGuide1209(unittest.TestCase):
        def test_old84_cases_and_all_existing_gates_are_exact(self):
            current=json.loads(catalog_path.read_bytes());self.assertEqual(current['cases'][:84],original['cases'])
            self.assertEqual({k:v for k,v in current.items() if k not in ['cases','revision']},{k:v for k,v in original.items() if k not in ['cases','revision']})
        def test_three_new_cases_have_closed_planned_availability(self):
            current=json.loads(catalog_path.read_bytes());self.assertEqual(current['cases'][84:],CASES)
            for context in [guide.context(profile='manual'),guide.context(profile='rc9'),dict(configured=True,roles=True,origin='',dll='future',bundle='future')]:
                cases=json.loads(guide.render(current,context).split('const guide=',1)[1].split(';',1)[0])['cases']
                self.assertEqual([cases[c['id']]['available'] for c in CASES],[False]*3)
        def test_actual87_catalog_keeps84_and8_available(self):
            current=json.loads(catalog_path.read_bytes());self.assertEqual(len(current['cases']),87)
            for profile,count in [('manual',8),('rc9',84)]:
                self.assertTrue(guide.generate(check=True,profile=profile))
                cases=json.loads(guide.render(current,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(c['available'] for c in cases.values()),count)
        def test_generator_and_user_result_logic_are_byte_identical(self):
            baseline=subprocess.check_output([str(GIT),'show',BASE+':tools/windows/qa_guide.py']);self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),baseline)
        def test_old_helper_only_changes_one_ascii_count(self):
            self.assertEqual(p.read_bytes(),old.replace(needle,b"self.assertEqual(len(current['cases']),87)"))
    modules=[base,load('excel1209','tools/tests/test_rc9_excel_guide832.py'),load('status1209','tools/tests/test_qa_relations_status848.py'),load('ports1209','tools/tests/qa_port_colors969.py'),load('categories1209','tools/tests/qa_category_colors1089.py')]
    suite=unittest.TestSuite()
    for module in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OnboardingGuide1209));started=time.monotonic()
    with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    record=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
        caseCount=87,available=dict(manual=8,rc9=84),previous84CompleteCasesExact=True,previousBuildGatesExact=True,newCasesPlanned=['QA-85','QA-86','QA-87'],
        generatorAndUserResultLogicExact=True,manualWascarResultsWritten=False,postgresAccess=False)
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record));return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
