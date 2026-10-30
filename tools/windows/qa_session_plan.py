"""Generate a read-only QA itinerary; results remain in the existing QA guide."""
import argparse
import html
import json
from pathlib import Path
import qa_guide

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'EMPEZAR-QA-WASCAR.html'
BLOCKS=[
    ('A · Primer vistazo, sin editar',['QA-01','QA-11'],
     'Entra como Administrador y revisa tu copia restaurada antes de modificarla. Los recuentos iniciales del backup son históricos; si ya trabajaste en la copia, anota diferencias sin borrar ni restaurar datos para igualarlos.'),
    ('B · Novedad: alta de grupos',['QA-91','QA-92','QA-93'],
     'Empieza por QA-91; puedes hacer sólo ese caso. QA-92 requiere un usuario y un cliente de laboratorio, además de grupos de usuarios y de clientes seleccionables. Si faltan, anota qué destino falta y deja ese tramo Bloqueado; no cambies permisos o la última cuenta administradora para forzarlo. QA-93 requiere un recibo nuevo al recargar o salir de Administración y una cuenta Lector preparada. Voz sin lector de pantalla y fallo de red no ensayado se anotan como partes Bloqueadas, con el paso exacto. No apagues el servidor ni borres el journal para provocar errores.'),
    ('C · Recorrido cotidiano',['QA-02','QA-03','QA-04','QA-05','QA-06'],
     'Antes de este bloque vuelve a Administrador si terminaste QA-93 como Lector. Sigue el orden indicado. QA-04 compara los nombres guardados en QA-02/03 desde otra sesión de Administrador; puedes hacerlo tú solo. QA-06 utiliza el cliente ficticio B creado en QA-03. Puedes detenerte después de cualquier caso.')
]

def render():
    catalog=json.loads(qa_guide.CATALOG.read_text(encoding='utf-8'))
    ctx=qa_guide.context(profile='rc9')
    payload=json.loads(qa_guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])
    cases={c['id']:c for c in catalog['cases']}
    e=html.escape;sections=[]
    for title,ids,note in BLOCKS:
        rows=[]
        for case_id in ids:
            case=cases[case_id]
            state='Disponible en esta copia' if payload['cases'][case_id]['available'] else 'Bloqueado · no disponible en esta copia'
            rows.append(f'<tr><td><strong>{e(case_id)}</strong></td><td>{e(case["title"])}</td><td>{state}</td></tr>')
        sections.append(f'<section><h2>{e(title)}</h2><p>{e(note)}</p><table><thead><tr><th>Caso</th><th>Qué probar</th><th>Disponibilidad del guion</th></tr></thead><tbody>{"".join(rows)}</tbody></table><p>En la guía completa pulsa <strong>Ctrl+F</strong>, escribe el ID exacto, por ejemplo <strong>{e(ids[0])}</strong>, y pulsa Escape para volver a leer. Cada caso contiene los botones/campos, ubicación y resultado esperado.</p></section>')
    available=sum(c['available'] for c in payload['cases'].values())
    origin=f'<a href="{e(ctx["origin"])}" target="_blank" rel="noopener">Abrir la web de QA configurada</a>' if ctx['origin'] else 'Laboratorio no configurado; deja las pruebas Bloqueadas y comunica ese mensaje.'
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RackClick · Mi recorrido de QA</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;max-width:1000px;margin:2em auto;padding:0 1em;background:#f4f6f8;color:#182733}}section{{padding:1.2em;background:white;border:1px solid #ccd6df;border-radius:8px;margin:1em 0}}h1,h2{{line-height:1.25}}li{{margin:.6em 0}}a{{color:#074e92}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;border:1px solid #ccd6df;padding:.6em;vertical-align:top}}code{{overflow-wrap:anywhere}}.notice{{border-left:5px solid #b37700;padding-left:1em}}@media(max-width:650px){{table{{font-size:.9em}}th,td{{padding:.3em}}}}@media print{{section{{break-inside:avoid}}body{{background:white;font-size:12pt}}}}</style></head><body>
<h1>Tu QA, por partes y sin prisa</h1>
<p>Preparado el19.10.2026 para que puedas comenzar el20 o cuando tengas tiempo. Puedes hacer un solo caso y continuar otro día. El recorrido prioriza una primera revisión y las novedades; los demás casos pueden esperar otra sesión.</p>
<p>Este archivo organiza el recorrido. Tus resultados se anotan únicamente en la <a href="GUIA-QA-RESTAURADO.html" target="_blank" rel="noopener"><strong>guía completa de la copia restaurada</strong></a>. No crea otro registro ni cambia tus respuestas anteriores.</p>
<section><h2>1 · Abrir el laboratorio correcto</h2><ol>
<li>Estas pruebas disponibles se hacen en el Windows donde está <code>C:\\RackClick_SVR</code>. El acceso desde otras VM, servicio Windows y pruebasLAN siguen pendientes de C4: no necesitas probarlos ahora ni instalar RackClick en clientes.</li>
<li>En ese equipo, pulsa <strong>Windows+E</strong>. En la barra de dirección superior escribe <code>C:\\RackClick_SVR</code> y pulsa Enter. Haz doble clic en <strong>INICIAR-QA-RESTAURADO.cmd</strong> y espera la web, la guía y <strong>ACCESO-PRIVADO.txt</strong>. No uses INICIAR-QA.cmd, que abre otro laboratorio.</li>
<li>En el recuadro central del login elige Español, copia el usuario y contraseña de Administrador desde ese archivo privado y pulsa <strong>Iniciar sesión</strong>. No copies contraseñas a observaciones ni capturas. Las demás cuentas y sus contraseñas están en el archivo privado del mismo entorno.</li>
<li>Mantén la guía de resultados en una <strong>ventana normal de tu navegador/perfil habitual</strong>. Para la aplicación utiliza un perfil distinto al QA original; las cookies no se separan sólo por puerto. Cuando un caso pida otra cuenta/sesión, abre sólo la web en InPrivate u otro perfil. Dos pestañas normales comparten login. No lleves tus notas a InPrivate.</li>
</ol><p>{origin}. Versión configurada: <code>{e(ctx['bundle'][:12] or 'sin laboratorio')}</code>; catálogo {e(catalog['revision'])}. Hay {available} de{len(cases)} guiones disponibles. Esto no acredita servidor encendido ni pruebasPass.</p></section>
<section><h2>2 · Antes de repetir una prueba o recuperar una copia</h2><ol>
<li>En la parte superior de la guía completa pulsa <strong>Guardar copia de mis resultados</strong>. Conserva ese JSON anterior antes de cambiar respuestas; puedes renombrarlo con fecha y versión.</li>
<li>Si tus notas ya aparecen, no importes nada. Para recuperar una copia, arriba pulsa el selector de archivo junto a <strong>Recuperar copia</strong>, elige el JSON del entorno restaurado y lee la confirmación: reemplaza las respuestas de los casos incluidos. Conserva primero la copia actual.</li>
<li>Debajo del campo de cada caso se muestra fecha/versión. Si indica que cambió el caso o la versión, conserva las notas anteriores como histórico y vuelve a probar cuando puedas; unPass antiguo no acredita la versión actual.</li>
</ol><p class="notice">La guía conserva un registro por caso y entorno, no un historial de todas las versiones. Al editar un resultado o nota se actualiza ese registro. Tus copiasJSON preservan las respuestas anteriores.</p></section>
{''.join(sections)}
<section><h2>3 · Anotar y devolver resultados</h2><ol>
<li>En la guía, a la derecha de los pasos de cada caso (debajo de ellos en una ventana estrecha), abre <strong>Tu resultado</strong>: Pass si se cumple todo lo ensayado y requerido; Not Pass si ves un fallo; Bloqueado si falta un requisito o no pudiste hacer un tramo; Sin probar para lo que aún no comenzaste.</li>
<li>En <strong>Observaciones</strong>, debajo del selector, escribe: <em>Paso3. Pulsé… Esperaba… Ocurrió…</em> y el nombre/UUID ficticio pertinente. Para un caso parcial: <em>Pasos1–4 correctos;5–7 Bloqueados porque…</em>. No marquesPass completo cuando queda un tramo requerido sin comprobar.</li>
<li>Al terminar cualquier rato, pulsa arriba <strong>Guardar copia de mis resultados</strong>. En el navegador abre Descargas con <strong>Ctrl+J</strong> y localiza el último archivo <strong>Resultados-QA-Wascar-…json</strong>. Guarda cada copia; no hace falta esperar a terminar todo para enviarla por este chat.</li>
<li>Para retomar, abre <strong>ABRIR-PLAN-QA-WASCAR.cmd</strong>. Si el laboratorio está detenido, inicia INICIAR-QA-RESTAURADO.cmd. Sigue en el mismo navegador/perfil; si las notas no aparecen, recupera tu copia conservando antes el estado actual.</li>
<li>Para finalizar el laboratorio, vuelve al Explorador y ejecuta <strong>DETENER-QA-RESTAURADO.cmd</strong>. No cierres servicios ni bases ajenos.</li>
</ol><p>Si algo falla, puedes parar ese caso, anotar el paso y mandarme el resultado parcial. No necesitas borrar datos, cambiar bases ni resolver el fallo técnico tú mismo. Los ensayos internos y sus correcciones siguen siendo trabajo del desarrollo.</p></section>
<section><h2>Lo que puede esperar</h2><p>Los demás casos siguen en la guía completa para otra sesión. El inventario de posibles servidores Windows11/Server2025 es una preparación distinta y opcional para elegir alojamiento; no es requisito de un usuario de navegador. LAN,SCM,instalación/reinicioWindows y recuperación final no se presentan como disponibles aquí. Voz requiere un lector de pantalla habitual.</p><p>Avance global aproximado:{e(str(catalog.get('globalProgressEstimate',78)))} %. Tus respuestas no se marcan automáticamente y tu aceptación final sigue pendiente.</p></section>
</body></html>'''

def generate(check=False):
    output=render()
    if check:return OUTPUT.is_file() and OUTPUT.read_text(encoding='utf-8')==output
    qa_guide.generate(profile='rc9')
    OUTPUT.write_text(output,encoding='utf-8')
    return True

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    raise SystemExit(0 if generate(args.check) else 1)
