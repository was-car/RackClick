"""Add detailed personal-preference cases, disabled in retained QA592/schema10."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);a=ap.parse_args()
    output=E/'QA-MATRIX-712.json'
    if output.exists():raise SystemExit('Preserve existing QA update')
    m=json.loads(a.manifest.read_bytes());assert m['schema']==11
    pair={'bundle':m['distributions']['frontend']['app.js'],'dll':m['distributions']['server']['RackClick.Server.dll']}
    p=ROOT/'docs/QA-CASOS-WASCAR.json';c=json.loads(p.read_bytes());previous=json.loads(p.read_bytes())['cases'];assert len(previous)==71
    intro='Este módulo todavía NO ESTÁ DISPONIBLE en tu QA592/esquema10 actual. Marca Bloqueado hasta que una actualización verificada indique DISPONIBLE EN TU SNAPSHOT. Entonces ejecuta INICIAR-QA-RESTAURADO.cmd y usa su guía y ACCESO-PRIVADO.txt. No ejecutes manualmente la candidata de desarrollo.'
    finish='En Tu resultado elige Pass, Not Pass o Bloqueado. Anota el usuario ficticio, paso y mensaje si falla, sin contraseñas/cookies/tokens. Arriba pulsa Guardar copia de mis resultados; las notas anteriores se conservan.'
    cases=[
      dict(id='QA-72',module='Preferencias personales · persistencia',title='Guardar idioma y tema para la misma cuenta en otra sesión',feature='userPreferencesGui',steps=[intro,
        'Cuando esté disponible, inicia sesión con una cuenta de QA. En la barra izquierda pulsa Todos los clientes para ver la página de tarjetas; si la barra está oculta, abre RackClick/menú arriba a la izquierda. Idioma y Tema están arriba a la derecha de la cabecera Clientes.',
        'Espera a que desaparezca Cargando configuración personal y a que los dos controles se habiliten. Si hay error, pulsa Recargar configuración personal debajo de la cabecera; no tomes el aspecto de la página como confirmación de carga.',
        'En el selector Idioma de la esquina superior derecha elige English. Espera la confirmación Personal setting confirmed by server. Mientras guarda no debe aceptar otra selección ni anunciar éxito antes de confirmar. Los nombres de clientes y equipos escritos por ti deben permanecer literales.',
        'A su lado, si el aspecto es oscuro, pulsa Light theme. Si ya es claro, pulsa Dark theme, espera confirmación y después Light theme para dejarlo claro. Espera la confirmación después de cada clic; cambia una cosa cada vez.',
        'Pulsa Ctrl+R y espera la carga personal. Debe seguir English y tema claro. Abre otro navegador o perfil separado e inicia sesión con la MISMA cuenta: tras cargar debe ver English y tema claro aunque la pantalla de login tuviese otra selección local.',
        'En la segunda sesión cambia a Deutsch y espera la confirmación del servidor. En la primera sesión pulsa Ctrl+R: debe cargar Deutsch. No se promete actualización automática de una sesión ya abierta; usa recarga.',
        'Vuelve a Español y al tema que prefieras, esperando su confirmación. Comprueba que no se han creado clientes, alterado inventario ni cambiado nombres por seleccionar idioma/tema.',finish],
        expected='Idioma y tema pertenecen a esa cuenta y se leen desde PostgreSQL tras recarga/otro navegador. Sólo cambian al confirmar el servidor; los valores anónimos no sobrescriben una preferencia guardada. No se modifica inventario ni se obtiene permiso de edición.'),
      dict(id='QA-73',module='Preferencias personales · aislamiento',title='Cambiar de cuenta sin heredar la configuración de otra',feature='userPreferencesGui',steps=[intro,
        'En la pantalla de login, antes de entrar, selecciona Español y Tema oscuro con los controles de la parte superior derecha. Esta selección sin sesión es propia de este navegador; no debe crear una preferencia de ninguna cuenta.',
        'Entra como Técnico u otra cuenta A y deja English y tema claro siguiendo QA-72. Espera confirmación. En la barra izquierda, abajo junto a la identidad, pulsa Sign out.',
        'La pantalla sin sesión debe volver al Español/tema oscuro anterior. Comprueba que el campo de usuario identifica la cuenta que introducirás; no debe mostrar confirmación personal de A como si fuera de otra cuenta.',
        'Entra con una cuenta B distinta, por ejemplo Lector, usando un perfil separado si quieres mantener A abierta. Si B ya tiene preferencias guardadas, anota sus valores antes de modificarlos. Si no las tiene, conserva el Español/oscuro de este navegador, sin guardado automático.',
        'Con B cambia idioma o tema y espera confirmación. Un Lector puede guardar su aspecto personal sin obtener botones de edición del inventario. Si tienes una cuenta ficticia sin clientes visibles, también puede guardar su configuración desde la cabecera Clientes.',
        'Cierra la sesión B y vuelve a entrar como A. A debe conservar English/claro y B sus propios valores. Confirma la identidad en Sesión de, en la barra izquierda. Dos pestañas normales comparten cookies: usa navegadores/perfiles separados para comparar cuentas simultáneamente.',
        'Comprueba Español, Deutsch y English y vuelve a los valores deseados para cada cuenta. Los datos de clientes, bibliotecas privadas y permisos no se transfieren al cambiar idioma/tema.',finish],
        expected='Cada propietario tiene configuración independiente. El login no copia ni guarda la preferencia de la cuenta anterior; logout recupera el fallback anónimo del navegador. Lector o usuario sin clientes cambia sólo sus preferencias, sin adquirir acceso a inventario ajeno.'),
      dict(id='QA-74',module='Preferencias personales · conflicto y recuperación',title='Resolver dos sesiones e intenciones pendientes sin sobrescribir',feature='userPreferencesGui',steps=[intro,
        'En dos navegadores o perfiles separados inicia sesión con la MISMA cuenta A y abre Todos los clientes. Espera la carga personal en ambos; no uses dos pestañas normales para simular usuarios distintos.',
        'En la sesión1 cambia el tema y espera confirmación. Sin recargar la sesión2, cambia allí el idioma. Debe avisar que otra sesión cambió tu configuración; no adaptar la revisión antigua automáticamente ni anunciar guardado de esa petición rechazada.',
        'Debajo de la cabecera Clientes busca el aviso de una preferencia con petición sin resolver. Pulsa Consultar original. Si indica que no tiene un resultado registrado, eso no confirma ni cancela; conserva la intención.',
        'Pulsa Cancelar original y lee la confirmación. Cancela primero el cuadro y comprueba que mantiene la intención. Repite y confirma; espera Petición original cancelada y la configuración recargada. El tema confirmado por sesión1 debe conservarse.',
        'Sólo después del resultado terminal elige de nuevo el idioma deseado como una petición nueva y espera confirmación. Pulsa Ctrl+R en ambos para comprobar el valor persistido. No se debe guardar una copia ni una segunda intención por un reintento.',
        'Si de forma natural aparece un envío sin confirmar, usa Consultar original o Reintentar original. Si pide contraseña, autentica la MISMA cuenta mediante el campo Contraseña y Volver a entrar debajo del aviso. Cambiar de usuario no debe enviar la intención anterior. No provoques fallos de red ni uses herramientas de desarrollador; si no ocurre, anota esa variante No realizada.',
        'Con ventana estrecha, usa Tab para llegar a Idioma, Tema y los controles de recuperación. Debe leerse el aviso y conservarse el último valor confirmado. Un error de carga ofrece Recargar configuración personal y no un éxito falso.',finish],
        expected='El servidor detecta conflicto personal412, no sobrescribe otra sesión y mantiene una única intención original recuperable. notRecorded, cancelled y committed se distinguen. Cambios de usuario/generación no aplican respuestas tardías; recuperación y controles son accesibles sin tocar inventario.')]
    c['cases']=previous+cases;c['revision']='2026-10-18-sesenta653-712';c['userPreferencesBuilds']=[pair]
    assert c['cases'][:71]==previous;p.write_bytes((json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    guide=ROOT/'tools/windows/qa_guide.py';data=guide.read_bytes();anchor=b"        'sharedTemplatesGui': catalog.get('sharedTemplatesBuilds', []),"
    assert data.count(anchor)==1 and b"'userPreferencesGui':" not in data
    nl=b'\r\n' if b'\r\n' in data else b'\n';data=data.replace(anchor,anchor+nl+b"        'userPreferencesGui': catalog.get('userPreferencesBuilds', []),")
    guide.write_bytes(data)
    output.write_text(json.dumps({'candidatePair':pair,'prior71CasesExact':True,'caseCount':74,'actualQaSelectedSchema':10,'realQaSelectionPerformed':False,'newCasesAvailableInCurrentQa':False,'manualWascarResultsWritten':False},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':74,'previous71Unchanged':True,'newCasesAvailableInActualQa':False}))
if __name__=='__main__':main()
