"""Validate and render the versioned remaining-work inventory; never runs product tests.

The computed percentage closes a dated backlog, NOT the entire product. Historical
capability milestones and old global percentages never award new closure points.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'docs/PLAN-CIERRE-RACKCLICK.json'


def percent(value):
    return f'{float(value):.2f}'.replace('.', ',')


def scope_fingerprint(data):
    """Freeze the result promised, not just its numeric weight.

    Status and evidence may evolve without rebaselining; reducing the promised
    result, removing a review or changing its weight requires a new baseline.
    """
    frozen = dict(baseline_id=data['baseline_id'], scope=data['scope'],
        areas=data['areas'], tasks=[dict(
            **{k: t[k] for k in ('id', 'area', 'title', 'kind', 'scored',
                                'criteria', 'dependencies', 'closure', 'weight_points')},
            checkpoints=[dict(id=s['id'], text=s['text'],
                weight_points=s['weight_points'],
                closure_review_required=s.get('closure_review_required', False))
                for s in t['checkpoints']]) for t in data['tasks']])
    return hashlib.sha256(json.dumps(frozen, ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate(data, root=ROOT):
    if data['metric']['global_product_percentage'] is not None:
        raise ValueError('This inventory cannot assert an overall product percentage')
    if data['metric']['total_points'] != 100:
        raise ValueError('Baseline closure denominator must be 100')
    areas = {a['id']: a for a in data['areas']}
    if len(areas) != len(data['areas']):
        raise ValueError('Duplicate area ID')
    if sum(Fraction(a['weight_points']) for a in areas.values()) != 100:
        raise ValueError('Area weights must total 100')
    tasks = data['tasks']
    actual_fingerprint = scope_fingerprint(data)
    if actual_fingerprint != data['frozen_structure_sha256']:
        raise ValueError('Scope/weights changed: create an explained baseline revision')
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate task ID')
    all_steps = set()
    coverage = set()
    points = {a: Fraction(0) for a in areas}
    assigned = dict(points)
    completed_tasks = 0
    for task in tasks:
        if task['area'] not in areas:
            raise ValueError('Unknown area')
        weight = Fraction(task['weight_points'])
        if weight < 0 or (not task['scored'] and weight != 0) or (task['scored'] and weight == 0):
            raise ValueError('Invalid task weight')
        assigned[task['area']] += weight
        for c in task['criteria']:
            coverage.update(re.findall(r'S-\d{2}', c))
        steps = task['checkpoints']
        if not steps or sum(Fraction(s['weight_points']) for s in steps) != weight:
            raise ValueError('Checkpoint weights differ from frozen task weight')
        if task['scored'] and not steps[-1].get('closure_review_required'):
            raise ValueError('Every scored result needs its explicit final review checkpoint')
        for evidence in task['evidence']:
            if not (root / evidence.split('#')[0]).is_file():
                raise ValueError('Missing task evidence: ' + evidence)
        for step in steps:
            if Fraction(step['weight_points']) < 0:
                raise ValueError('Checkpoint weights cannot be negative')
            if step['id'] in all_steps:
                raise ValueError('Duplicate checkpoint ID')
            all_steps.add(step['id'])
            if step['status'] not in ('pending', 'in_progress', 'done', 'blocked', 'unknown', 'reopened'):
                raise ValueError('Unknown checkpoint status')
            if step['status'] == 'done':
                if not step['evidence']:
                    raise ValueError('Done checkpoint requires evidence')
                for evidence in step['evidence']:
                    if not (root / evidence.split('#')[0]).is_file():
                        raise ValueError('Missing completion evidence')
                if step.get('closure_review_required') and not step.get('review_evidence'):
                    raise ValueError('Final closure requires independent review evidence')
                for evidence in step.get('review_evidence', []):
                    if not (root / evidence.split('#')[0]).is_file():
                        raise ValueError('Missing independent review evidence')
                points[task['area']] += Fraction(step['weight_points'])
        if task['scored'] and all(s['status'] == 'done' for s in steps):
            completed_tasks += 1
    if any(assigned[k] != Fraction(a['weight_points']) for k, a in areas.items()):
        raise ValueError('Frozen area and task weights differ')
    expected = {f'S-{i:02}' for i in range(1, 57)} - {'S-50'}
    if expected - coverage:
        raise ValueError('Missing S1-S4 coverage: ' + ','.join(sorted(expected-coverage)))
    return dict(points=points, total=sum(points.values()), coverage=sorted(expected),
                scored_tasks=sum(t['scored'] for t in tasks), tasks=len(tasks),
                steps=len(all_steps), completed_tasks=completed_tasks)


def text_value(value):
    if isinstance(value, dict):
        labels={'developer':'Desarrollo','wascar':'Wascar','environment':'Entorno',
                'responsables':'Responsables','owner':'Responsable','question':'Por concretar',
                'developer_work_can_continue':'Trabajo que puede continuar','note':'Nota',
                'item':'Tema','state':'Estado','treatment':'Tratamiento','elemento':'Tema',
                'motivo':'Motivo','id':'ID','estado':'Estado','tema':'Tema','conflicto':'Conflicto',
                'tratamiento':'Tratamiento','evidencia':'Referencia','evidence':'Referencia'}
        return '; '.join(labels.get(k,k)+': '+text_value(v) for k,v in value.items())
    if isinstance(value, list):
        return '; '.join(text_value(v) for v in value)
    return str(value)


def evidence_link(path):
    # Rendered document is under docs/.
    target = path.removeprefix('docs/') if path.startswith('docs/') else '../' + path
    return '[' + path + '](' + target + ')'


def render(data):
    result = validate(data)
    rows = ['# RackClick · inventario completo y plan de cierre medible', '',
        f"Base **{data['baseline_id']}**, {data['date']}. El inventario inicial se creó mediante conciliación documental. Los avances posteriores y sus pruebas se acreditan en los subpasos, con evidencias propias; no se convierten en aceptación de QA.", '',
        '**El 78 % anterior queda retirado como indicador vigente.** Sus 7 puntos pendientes funcionales eran 2 de fundamento, 3 de inventario, 1 de administración y 1 de paridad: no eran 7 tareas. El inventario actual distingue 7 bloques, con trabajo concreto y evidencia.', '',
        f"**Cierre de este trabajo restante: {percent(result['total'])}/100 puntos.** No significa que el producto esté al 0 %. Lo ya construido se reconoce abajo. No se conoce aquí un nuevo porcentaje global del producto y no se utiliza 78+22×cierre.", '',
        f"El inventario tiene **{result['tasks']} entradas: {result['scored_tasks']} resultados ponderados y {result['tasks']-result['scored_tasks']} decisiones/controles sin doble puntuación; {result['steps']} subpasos**. No son jornadas, pruebas nuevas ni nuevas funciones. Los {len(result['coverage'])} criterios S1–S4 están trazados; S-50/retorno de campo pertenece a S5.", '',
        '## Cómo se calcula y qué cambia desde hoy', '',
        'Cada bloque recibe un peso de cierre explícito. Es una propuesta de prioridad/riesgo, no una estimación objetiva de horas o créditos. Dentro de cada bloque se reparte el peso entre sus resultados únicos; cada subpaso conserva una fracción fijada antes de ejecutarlo.', '',
        '`Puntos cerrados = suma del peso de los subpasos terminados y respaldados por evidencia.`', '',
        'Un subpaso implementado/probado puede dar avance parcial; cerrar la tarea completa exige su comprobación final y revisión independiente. La aceptación de Wascar se pide sólo donde corresponde, no como permiso para desarrollar. Una decisión pendiente no se presenta como ausencia de código ni obliga a rehacer lo ya probado.', '',
        'El denominador inicial es 100. No aumenta por bugs, ZIPs, pruebas repetidas o subdivisiones. Un resultado reabierto pierde crédito; un requisito realmente nuevo/omitido exige una versión explicada del inventario, conservando la anterior. La huella fija también títulos, criterios, cierre y texto de subpasos: reducirlos no puede aparentar avance. Los hitos históricos done/pending/unknown del JSON son informativos y no suman otra vez al cierre pendiente.', '',
        '| Bloque | Peso del cierre | Cerrado | Resultados con peso |', '|---|---:|---:|---:|']
    for area in data['areas']:
        count = sum(t['area']==area['id'] and t['scored'] for t in data['tasks'])
        rows.append(f"| {area['id']} · {area['name']} | {area['weight_points']} | {percent(result['points'][area['id']])} | {count} |")
    example=next(t for t in data['tasks'] if t['id']=='W-01')
    example_step=Fraction(example['checkpoints'][0]['weight_points'])
    rows += ['', f"**Ejemplo:** W-01 tiene {percent(Fraction(example['weight_points']))} puntos, repartidos en {len(example['checkpoints'])} subpasos. Terminar y acreditar el primero mueve el cierre pendiente {percent(example_step)} puntos; repetir la misma prueba no lo vuelve a sumar. Es un ejemplo del reparto real de esta base, no una ejecución nueva.", '',
        '## Lista resumida de todos los resultados pendientes', '',
        '| ID | Resultado | Tipo de pendiente | Puntos de cierre |', '|---|---|---|---:|']
    for area in data['areas']:
        for task in (t for t in data['tasks'] if t['area']==area['id']):
            rows.append(f"| {task['id']} | {task['title']} | {task['status']} | {percent(Fraction(task['weight_points']))} |")
    rows += ['', '## Trabajo existente que se conserva', '',
        'Las referencias acreditan sus builds/entornos originales y límites; no se convierten en pruebas nuevas de la candidata final. Esta lista no vuelve a cero ni recibe otro peso por copiarla al plan.', '']
    for base in data['available_capabilities']:
        rows += [f"- **{base['title']}**: {base['scope']} Referencia: " + ', '.join(evidence_link(p) for p in base['evidence'][:2]) + '.']
    for area in data['areas']:
        rows += ['', f"## {area['id']}. {area['name']} · {area['weight_points']} puntos del cierre", '']
        for task in (t for t in data['tasks'] if t['area']==area['id']):
            rows += [f"### {task['id']} · {task['title']}", '',
                f"**Situación:** {task['current']}", '',
                '**Qué falta:**', '']
            for step in task['checkpoints']:
                tick = 'x' if step['status']=='done' else ' '
                rows.append(f"- [{tick}] {step['id']} · {step['text']}")
            rows += ['', f"**Se cierra cuando:** {task['closure']}", '',
                f"**Responsable:** {text_value(task['owners'])}. **Dependencias:** {text_value(task['dependencies']) or 'Sin dependencia previa nueva identificada.'}", '',
                f"**Tipo de pendiente:** {task['status']}. **Peso:** {percent(Fraction(task['weight_points']))} puntos. {task['counting_note']}", '',
                '**Criterios:** ' + '; '.join(task['criteria']) + '.', '',
                '**Evidencia existente:** ' + ', '.join(evidence_link(p) for p in task['evidence'][:3]) + '. Todas las referencias e hitos separados están en elJSON.', '']
    rows += ['## Lo definido que no se vuelve a discutir', '',
        '- ASP.NET Core/.NET 10, Npgsql directo, migraciones SQL y PostgreSQL 17; no SQLite ni otro piloto.',
        '- Los usuarios trabajan en navegador. Instalar el servidor no significa instalar la aplicación en cada Windows 11 cliente.',
        '- RC9 y Click-Click son la referencia; IDs/grupo/tipo dirigen lotes, no un gn ambiguo. Permisos y confirmación del guardado se resuelven en servidor.',
        '- MFA obligatorio para todos antes de producción. Excepciones temporales de QA no lo revocan.',
        '- Laboratorios y restauraciones en destinos nuevos, sin borrar bases ajenas. Desarrollo ya autorizado; adopción final por Wascar.', '',
        '## Decisiones y aspectos todavía por concretar', '',
        'No son nuevas autorizaciones de arranque. Desarrollo prepara diseños/ensayos; Wascar decide custodia, necesidades operativas y cualquier reducción explícita del alcance. No se le traslada diseñar la criptografía.', '']
    for item in data['decisions']:
        rows += ['- ' + text_value(item)]
    rows += ['', '## Investigación o prueba técnica todavía necesaria', '',
        'Son preguntas acotadas con salida verificable, no tareas indefinidas de estudiar ni nuevas funciones por defecto:', '',
        '| Qué falta determinar | Cómo se resuelve | Resultado al que pertenece |', '|---|---|---|',
        '| Acceso de la cuenta estándar a claves y transición disco/DB al rotarlas | Proveedor real, fallos forzados, ACL y recuperación en otro SID | F-04 a F-06 |',
        '| Portabilidad de secretos/PKI y cifrado de backup | Restore en otro Windows con clave correcta, incorrecta y ausente | F-02, F-05, R-03, R-04 |',
        '| Comportamiento real de SCM y del CRT cuando requiere reinicio | Instalación limpia, parada, fallos y reinicio del host | W-02, W-03 |',
        '| Copia USB/UNC con NAS ausente o disco lleno | Copia local previa, verificación, retención y restauración por destino | R-01, R-02 |',
        '| Mapeo de extensiones RC9, doble ocupación e identidad documental | Fixtures acotados de importación/exportación y round-trip | P-01 a P-06 |',
        '| Límites de latencia/memoria con diez usuarios | Fijar umbrales antes de medir; optimizar sólo cuellos demostrados | E-06 |',
        '| Reproducción limpia y rutas de PDB | Aprovisionamiento pinado y construcción desde entorno nuevo | E-02 |',
        '| PDF nativo y circuitos internos Dose | Resolver alcance explícitamente; no retirar impresión/modelo ya contratados | P-07, I-07, D4/D5 |', '',
        '## Herramientas y fases futuras: separadas del cierre del producto', '',
        'No tener un plugin no es por sí solo un fallo del producto. La siguiente relación conserva propuestas y trabajo técnico sin convertir cada herramienta en función obligatoria:', '']
    for item in data['tooling']:
        rows.append('- ' + text_value(item))
    rows += ['', 'Roadmap y condiciones de alcance:', '']
    for item in data['roadmap']:
        rows.append('- ' + text_value(item))
    rows += ['', '## Fuentes antiguas que no deben generar otra vez trabajo cerrado', '']
    for item in data['superseded']:
        rows.append('- ' + text_value(item))
    rows += ['', '## Orden de ejecución y reparto', '',
        '1. Cerrar W-01 y preparar una edición coherente de ensayo. Reutilizar el bundle si sus bytes no cambian; no reconstruir los históricos05 como requisito nuevo.',
        '2. En paralelo independiente: MFA/proveedor/enrolamiento y GUI C2/importación. Un solo propietario por archivo; revisión distinta sobre cambios ya estabilizados. Las pruebasHTTP de laboratorio no tienen que esperar a la decisión de custodia productivaD2.',
        '3. Integrar una candidata coordinada, no una publicación por cada documento. Reutilizar pruebas válidas no afectadas y correr regresión pertinente una vez.',
        '4. Instalar en otra VM limpia; servicio, HTTPS, reinicio, backup/restore y recuperación. Después QA por módulos a ritmo de Wascar y adopción.', '',
        'Las pruebas del usuario no son el único trabajo pendiente: la mayoría de los pasos de este inventario corresponde a desarrollo, integración, operación y revisión.', '',
        '## Mantener el cálculo', '',
        'Fuente editable: [PLAN-CIERRE-RACKCLICK.json](PLAN-CIERRE-RACKCLICK.json). Al cambiar un subpaso, registrar estado y evidencia; no marcar done por existir código o generar un ZIP. El último subpaso de cada tarea exige referencia de revisión distinta.', '',
        '```powershell', "& 'C:/Python312/python.exe' -X utf8 -B tools/progress_report.py --write", '```', '',
        'Comprobar coherencia sin modificar los informes:', '',
        '```powershell', "& 'C:/Python312/python.exe' -X utf8 -B tools/progress_report.py --check", '```', '',
        'El generador valida alcance fijado, pesos, IDs, cobertura de criterios y existencia de evidencias; no puede decidir que una prueba fue suficiente ni ejecuta pruebas del producto. El cierre se revisa por una persona/agente distinto del implementador. Regenera también CIERRE-METRICA.json y MAPA-ENTREGA.json; el mapa anterior está archivado como histórico.', '']
    return '\n'.join(rows), result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=DEFAULT)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--write', action='store_true')
    group.add_argument('--check', action='store_true')
    args = p.parse_args()
    data = json.loads(args.source.read_bytes())
    report, result = render(data)
    output = ROOT / 'docs/PLAN-CIERRE-RACKCLICK.md'
    summary_path = ROOT / 'docs/CIERRE-METRICA.json'
    summary = dict(baseline_id=data['baseline_id'], measurement_kind='remaining_work_closure_not_product_progress',
        global_product_percentage=None, historical_78_retired=True,
        closure_points=float(result['total']), total_closure_points=100,
        tasks=result['tasks'], scored_tasks=result['scored_tasks'], completed_tasks=result['completed_tasks'],
        checkpoints=result['steps'], criteria_covered=len(result['coverage']),
        areas=[dict(id=a['id'], name=a['name'], assigned=a['weight_points'],
                    closed=float(result['points'][a['id']])) for a in data['areas']])
    summary_text=json.dumps(summary,indent=2,ensure_ascii=False)+'\n'
    map_path = ROOT / 'docs/MAPA-ENTREGA.json'
    map_data = dict(schema_version=2, revision=data['baseline_id'],
        measurement_kind='remaining_work_closure_not_product_progress',
        progress=None, global_product_percentage=None,
        snapshot='Inventario fechado del pendiente; no reinicia el trabajo ya construido.',
        basis='Cierre de 100 puntos del trabajo restante desde 25.10.2026; no porcentaje global del producto.',
        closure_points=summary['closure_points'], total_closure_points=100,
        historical_map='evidence/s1-20261025/plan-cierre-medible/MAPA-ENTREGA-ANTERIOR.json',
        historical_78_retired=True,
        sources=['docs/PLAN-CIERRE-RACKCLICK.json', 'docs/PLAN-CIERRE-RACKCLICK.md', 'docs/CIERRE-METRICA.json'],
        streams=[dict(id=a['id'], name=a['name'], weight=a['weight_points'],
            closure_points=float(result['points'][a['id']]),
            children=[dict(id=t['id'], name=t['title'], pending_kind=t['status'],
                weight_points=t['weight_points'],
                closed_points=float(sum((Fraction(s['weight_points']) for s in t['checkpoints']
                    if s['status']=='done'), Fraction(0))),
                checkpoints=[dict(id=s['id'], name=s['text'], status=s['status'],
                    weight_points=s['weight_points']) for s in t['checkpoints']])
                for t in data['tasks'] if t['area']==a['id']]) for a in data['areas']])
    map_text = json.dumps(map_data, indent=2, ensure_ascii=False)+'\n'
    outputs = [(output, report), (summary_path, summary_text), (map_path, map_text)]
    if args.write:
        for path, content in outputs:
            path.write_text(content,encoding='utf-8')
    if args.check and any(not path.is_file() or path.read_text(encoding='utf-8')!=content
                          for path, content in outputs):
        raise ValueError('Generated report/summary are stale; run --write')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
