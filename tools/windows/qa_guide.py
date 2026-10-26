"""Generate Wascar's offline QA guide without writing or replacing his results."""
import argparse
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'docs/QA-CASOS-WASCAR.json'
OUTPUT = ROOT / 'GUIA-QA-WASCAR.html'


def context(root=ROOT, profile='manual'):
    result = {'origin': '', 'bundle': '', 'roles': False, 'configured': False, 'profile': profile, 'restored': False, 'dll': ''}
    pointer = root / '.local' / ('qa-rc9' if profile == 'rc9' else 'qa-wascar') / 'current.json'
    if not pointer.is_file():
        return result
    directory = Path(json.loads(pointer.read_text(encoding='utf-8'))['directory']).resolve()
    if directory.parent != (root / '.local/labs').resolve() or not directory.name.startswith('manual-qa-'):
        raise ValueError('Invalid QA laboratory pointer')
    cfg = json.loads((directory / 'manual-qa.json').read_text(encoding='utf-8'))
    if cfg['host'] != '127.0.0.1' or cfg['directory'] != str(directory) or not 1 <= int(cfg['webPort']) <= 65535:
        raise ValueError('Invalid QA laboratory identity')
    if cfg.get('profile', 'manual') != profile:
        raise ValueError('QA guide profile mismatch')
    roles = directory / 'QA-CUENTAS-ESTADO.json'
    result.update(origin=f'http://127.0.0.1:{int(cfg["webPort"])}', bundle=cfg['bundleSha256'], dll=cfg.get('dllSha256', ''),
                  roles=roles.is_file() and json.loads(roles.read_text(encoding='utf-8')).get('ready') is True,
                  configured=True)
    restored = directory / 'RESTORE-ESTADO.json'
    result['restored'] = profile == 'rc9' and restored.is_file() and json.loads(restored.read_text(encoding='utf-8')).get('restored') is True
    return result


def render(catalog, ctx):
    cases = catalog['cases']
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate QA IDs')
    rows = []
    metadata = {}
    member_builds = catalog.get('membersBuilds', [{'bundle': catalog.get('membersBundle'), 'dll': catalog.get('membersDll')}])
    customer_member_builds = catalog.get('customerMembersBuilds', [{'bundle': catalog.get('customerMembersBundle'), 'dll': catalog.get('customerMembersDll')}])
    grant_builds = catalog.get('grantBuilds', [])
    group_builds = catalog.get('groupsBuilds', [])
    user_state_builds = catalog.get('userStateBuilds', [])
    user_password_builds = catalog.get('userPasswordBuilds', [])
    user_sessions_builds = catalog.get('userSessionsBuilds', [])
    user_effective_permissions_builds = catalog.get('userEffectivePermissionsBuilds', [])
    audit_builds = catalog.get('auditBuilds', [])
    audit_filter_builds = catalog.get('auditFilterBuilds', [])
    audit_detail_builds = catalog.get('auditDetailBuilds', [])
    audit_administrative_builds = catalog.get('auditAdministrativeBuilds', [])
    admin_navigation_builds = catalog.get('adminNavigationBuilds', [])
    inventory_movement_builds = catalog.get('inventoryMovementBuilds', [])
    admin_selection_builds = catalog.get('adminSelectionBuilds', [])
    inventory_duplicate_builds = catalog.get('inventoryDuplicateBuilds', [])
    inventory_poe_face_builds = catalog.get('inventoryPoeFaceBuilds', [])
    additional_builds = {
        'clientChangesGui': catalog.get('clientChangesBuilds', []),
        'inventoryChangeDetailsGui': catalog.get('inventoryChangeDetailsBuilds', []),
        'privateConfigurationGui': catalog.get('privateConfigurationBuilds', []),
        'sharedTemplatesGui': catalog.get('sharedTemplatesBuilds', []),
        'userPreferencesGui': catalog.get('userPreferencesBuilds', []),
        'rc9ExcelGui': catalog.get('rc9ExcelBuilds', []),
        'rc9ExcelTextGui': catalog.get('rc9ExcelTextBuilds', []),
        'rc9ExcelSafetyGui': catalog.get('rc9ExcelSafetyBuilds', []),
        'inventoryDeleteBatchGui': catalog.get('inventoryDeleteBatchBuilds', []),
        'roomDeviceMoveGui': catalog.get('roomDeviceMoveBuilds', []),
        'adminGroupRelationsGui': catalog.get('adminGroupRelationsBuilds', []),
        'adminGroupRelationsAnnouncementGui': catalog.get('adminGroupRelationsAnnouncementBuilds', []),
        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),
        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),
        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),
        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),
        'adminGroupReceiptGui': catalog.get('adminGroupReceiptBuilds', []),
        'poeBudgetGui': catalog.get('poeBudgetBuilds', []),
        'inventoryCompensationGui': catalog.get('inventoryCompensationBuilds', []),
        'inventoryPortsCsvGui': catalog.get('reportsPortsBuilds', []),
        'inventoryConnectionsCsvGui': catalog.get('reportsConnectionsBuilds', []),
        'inventoryRackCsvGui': catalog.get('reportsRackBuilds', []),
        'inventorySpreadsheetGui': catalog.get('inventorySpreadsheetBuilds', []),
        'printableRackGui': catalog.get('printableRackBuilds', []),
        'printableClientGui': catalog.get('printableClientBuilds', []),
        'printableRackLabelsGui': catalog.get('printableRackLabelBuilds', []),
        'inventoryCatalogGui': catalog.get('inventoryCatalogBuilds', []),
        'inventoryCatalogCreateGui': catalog.get('inventoryCatalogCreateBuilds', []),
        'inventoryCatalogSafetyGui': catalog.get('inventoryCatalogSafetyBuilds', []),
        'catalogFavoritesGui': catalog.get('catalogFavoritesBuilds', []),
        'catalogFavoritesPersistenceGui': catalog.get('catalogFavoritesPersistenceBuilds', []),
        'catalogFavoritesSafetyGui': catalog.get('catalogFavoritesSafetyBuilds', []),
        'rackSvgGui': catalog.get('rackSvgBuilds', []),
        'rackSvgFacesGui': catalog.get('rackSvgFacesBuilds', []),
        'rackSvgSafetyGui': catalog.get('rackSvgSafetyBuilds', []),
        'privateTemplatesGui': catalog.get('privateTemplatesBuilds', []),
        'privateTemplatesCreateGui': catalog.get('privateTemplatesCreateBuilds', []),
        'privateTemplatesSafetyGui': catalog.get('privateTemplatesSafetyBuilds', []),
        'privateTemplateRenameGui': catalog.get('privateTemplateRenameBuilds', []),
        'compensationPowerGui': catalog.get('compensationPowerBuilds', []),
        'inventoryCompensationCancelGui': catalog.get('inventoryCompensationCancelBuilds', []),
        'inventorySearchGui': catalog.get('inventorySearchBuilds', []),
        'inventoryPortViewGui': catalog.get('inventoryPortViewBuilds', []),
        'inventoryConnectionViewGui': catalog.get('inventoryConnectionViewBuilds', []),
        'auditContextGui': catalog.get('auditContextBuilds', []),
        'inventoryBatchGui': catalog.get('inventoryBatchBuilds', []),
        'inventoryPatchGui': catalog.get('inventoryPatchBuilds', []),
        'inventoryHierarchyGui': catalog.get('inventoryHierarchyBuilds', []),
    }
    for case in cases:
        feature = case['feature']
        if feature not in ('base', 'roles', 'groupsGui', 'membersGui', 'customerMembersGui', 'grantsGui', 'userStateGui', 'userPasswordGui', 'userSessionsGui', 'userEffectivePermissionsGui', 'auditGui', 'auditFiltersGui', 'auditDetailsGui', 'auditAdministrativeGui', 'adminNavigationGui', 'inventoryMovementGui', 'adminSelectionGui', 'inventoryDuplicateGui', 'inventoryPoeFaceGui', 'restored', 'planned') and feature not in additional_builds or not case['steps']:
            raise ValueError('Invalid QA case')
        available = ctx['configured'] and (feature == 'base' or feature == 'roles' and ctx['roles'] or
                    feature == 'groupsGui' and (ctx['bundle'] in catalog.get('groupsBundles', [catalog['groupsBundle']]) or any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in group_builds)) or feature == 'membersGui' and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in member_builds) or feature == 'customerMembersGui' and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in customer_member_builds) or feature == 'grantsGui' and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in grant_builds) or feature == 'userStateGui' and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in user_state_builds) or feature == 'userPasswordGui' and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in user_password_builds) or feature == 'userSessionsGui' and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in user_sessions_builds) or feature == 'userEffectivePermissionsGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in user_effective_permissions_builds) or feature == 'auditGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in audit_builds) or feature == 'auditFiltersGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in audit_filter_builds) or feature == 'auditDetailsGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in audit_detail_builds) or feature == 'auditAdministrativeGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in audit_administrative_builds) or feature == 'adminNavigationGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in admin_navigation_builds) or feature == 'inventoryMovementGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in inventory_movement_builds) or feature == 'adminSelectionGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in admin_selection_builds) or feature == 'inventoryDuplicateGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in inventory_duplicate_builds) or feature == 'inventoryPoeFaceGui' and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in inventory_poe_face_builds) or feature == 'restored' and ctx.get('restored', False) or feature in additional_builds and ctx['roles'] and any(ctx['bundle'] == build['bundle'] and ctx.get('dll') == build['dll'] for build in additional_builds[feature]))
        fingerprint = hashlib.sha256(json.dumps(case, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        metadata[case['id']] = {'hash': fingerprint, 'available': available}
        e = html.escape
        steps = ''.join('<li>' + e(s) + '</li>' for s in case['steps'])
        options = ''.join('<option value="' + x + '">' + x + '</option>' for x in ('Sin probar', 'Pass', 'Not Pass', 'Bloqueado'))
        rows.append(f'''<article data-case="{e(case['id'])}"><h2>{e(case['id'])} · {e(case['title'])}</h2>
<p class="module">{e(case['module'])} · <strong>{'DISPONIBLE EN TU SNAPSHOT' if available else 'NO DISPONIBLE · pendiente'}</strong></p>
<div class="columns"><div><ol>{steps}</ol><p class="expected"><b>Resultado esperado:</b> {e(case['expected'])}</p></div>
<div class="result"><label>Tu resultado<select data-result>{options}</select></label><label>Observaciones<textarea data-notes rows="5" placeholder="Qué hice, qué esperaba y qué ocurrió. Sin contraseñas."></textarea></label><small data-stamp></small></div></div></article>''')
    payload = json.dumps({'revision': catalog['revision'], 'bundle': ctx['bundle'], 'profile': ctx.get('profile', 'manual'), 'cases': metadata}, ensure_ascii=False).replace('<', '\\u003c')
    origin = html.escape(ctx['origin'])
    link = f'<a href="{origin}" target="_blank" rel="noopener">Abrir interfaz de QA</a>' if origin else 'Primero ejecuta INICIAR-QA.cmd.'
    environment = 'COPIA RESTAURADA RC9: usa INICIAR-QA-RESTAURADO.cmd y sus credenciales privadas. Primero realiza QA-11, antes de crear o editar datos. Usa otro perfil/navegador respecto a QA original: las cookies no se separan solo por puerto.' if ctx.get('profile') == 'rc9' else 'QA ORIGINAL: usa INICIAR-QA.cmd. La copia restaurada tiene otro CMD, guía, dirección y contraseñas.'
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guía de QA de Wascar · RackClick</title><style>
body{{font:16px system-ui,sans-serif;background:#101820;color:#e5edf3;max-width:1250px;margin:auto;padding:24px;line-height:1.6}}a{{color:#59e3bb}}h1{{font-size:28px}}h2{{font-size:21px}}article{{background:#19232e;border:1px solid #435566;border-radius:12px;margin:20px 0;padding:22px}}.columns{{display:grid;grid-template-columns:2fr 1fr;gap:24px}}li{{padding:5px 0}}label{{display:block;margin-bottom:15px}}select,textarea,input,button{{font:inherit;padding:10px;border-radius:6px;border:1px solid #71869a;background:#10202c;color:#fff}}select,textarea{{width:100%;box-sizing:border-box}}button{{cursor:pointer;margin:5px}}.expected{{border-left:4px solid #59e3bb;padding-left:15px}}.module,small{{color:#bfd0df}}.toolbar{{position:sticky;top:0;background:#101820;padding:10px;border-bottom:1px solid #71869a;z-index:1}}#notice{{color:#ffda82}}@media(max-width:800px){{.columns{{display:block}}body{{padding:12px}}}}@media print{{.toolbar,button{{display:none}}body{{color:#000;background:#fff}}article{{background:#fff;color:#000;break-inside:avoid}}}}
</style><header><h1>RackClick · tus pruebas de QA</h1><p>Guía {html.escape(catalog['revision'])}. El avance se consulta en el <a href="docs/PLAN-CIERRE-RACKCLICK.md">plan de cierre del proyecto</a>; el porcentaje global anterior es histórico. Prueba cuando tengas tiempo; no hace falta completar todo de una vez.</p>
<p>{link} · Versión de tu copia: <code>{html.escape(ctx['bundle'][:12] or 'sin laboratorio')}</code>. Esto identifica el snapshot, no comprueba que el servidor esté encendido.</p>
<p><strong>{environment}</strong></p>
<p>Trabaja en Español y con datos ficticios. Los pasos describen la pantalla de escritorio: si la barra lateral está oculta, pulsa el botón RackClick/menú arriba a la izquierda. La guía no cambia tus datos. No marques Pass en casos NO DISPONIBLES; usa Bloqueado.</p>
<p>Credenciales: el CMD de tu entorno abre su ACCESO-PRIVADO.txt. Usa perfiles/navegadores separados para cuentas simultáneas; dos pestañas normales comparten login. No copies contraseñas en notas o capturas.</p></header>
<div class="toolbar"><button id="export">Guardar copia de mis resultados</button><label style="display:inline">Recuperar copia <input id="import" type="file" accept=".json,application/json"></label><button onclick="window.print()">Imprimir</button><p id="notice" role="status">Las notas se guardan en este navegador. Exporta una copia al terminar cada sesión para conservarlas y enviarlas por el chat.</p></div>
{''.join(rows)}
<script>const guide={payload};
const key='RackClick.QA.Wascar.results.v1'+(guide.profile==='rc9'?'.rc9':''), notice=document.querySelector('#notice');let records={{}};
try{{records=JSON.parse(localStorage.getItem(key)||'{{}}');if(!records||Array.isArray(records)||typeof records!=='object')throw Error();}}catch{{records={{}};notice.textContent='No se pudo recuperar el guardado del navegador. Importa tu copia JSON si la tienes.';}}
function paint(){{document.querySelectorAll('[data-case]').forEach(row=>{{const id=row.dataset.case,r=records[id];row.querySelector('[data-result]').value=r?.result||'Sin probar';row.querySelector('[data-notes]').value=r?.notes||'';row.querySelector('[data-stamp]').textContent=r?'Anotado: '+r.updated+' · versión '+(r.bundle?.slice(0,12)||'sin identificar')+(r.hash!==guide.cases[id].hash||r.bundle!==guide.bundle?' · El caso o versión cambió; conservar notas y volver a probar.':''):'';}});}}
function persist(){{try{{localStorage.setItem(key,JSON.stringify(records));notice.textContent='Notas guardadas en este navegador. Al terminar, pulsa Guardar copia de mis resultados.';}}catch{{notice.textContent='No se pudo guardar en el navegador. Pulsa Guardar copia de mis resultados antes de cerrar.';}}}}
document.querySelectorAll('[data-case]').forEach(row=>{{const save=()=>{{const id=row.dataset.case;records[id]={{result:row.querySelector('[data-result]').value,notes:row.querySelector('[data-notes]').value,updated:new Date().toLocaleString(),revision:guide.revision,bundle:guide.bundle,hash:guide.cases[id].hash}};persist();paint();}};row.querySelector('[data-result]').addEventListener('change',save);row.querySelector('[data-notes]').addEventListener('input',save);}});
document.querySelector('#export').onclick=()=>{{const blob=new Blob([JSON.stringify({{format:'RackClick-QA-v1',profile:guide.profile,records}},null,2)],{{type:'application/json'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='Resultados-QA-Wascar-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}};
document.querySelector('#import').onchange=async e=>{{try{{const file=e.target.files[0];if(!file)return;if(file.size>2000000)throw Error();const data=JSON.parse(await file.text());if((data.profile||'manual')!==guide.profile)throw Error();if(data.format!=='RackClick-QA-v1'||!data.records||typeof data.records!=='object'||Array.isArray(data.records))throw Error();const accepted={{}};for(const [id,r] of Object.entries(data.records)){{if(!/^QA-[0-9]+$/.test(id)||!r||!['Sin probar','Pass','Not Pass','Bloqueado'].includes(r.result)||typeof r.notes!=='string'||r.notes.length>50000||typeof r.updated!=='string'||typeof r.hash!=='string'||typeof r.bundle!=='string')throw Error();accepted[id]=r;}}if(!confirm('Importar estos resultados? Se reemplazarán solo las notas de los casos incluidos en la copia. Los casos retirados se conservarán en futuras exportaciones.'))return;records={{...records,...accepted}};persist();paint();}}catch{{notice.textContent='No se pudo importar: formato de resultados no válido. Tus notas actuales se conservaron.';}}e.target.value='';}};paint();
</script></html>'''


def guide_path(profile='manual'):
    return ROOT / ('GUIA-QA-RESTAURADO.html' if profile == 'rc9' else 'GUIA-QA-WASCAR.html')


def generate(check=False, profile='manual'):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    output = render(catalog, context(profile=profile))
    target = guide_path(profile)
    if check:
        return target.is_file() and target.read_text(encoding='utf-8') == output
    target.write_text(output, encoding='utf-8')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--profile', choices=('manual', 'rc9'), default='manual')
    args = parser.parse_args()
    raise SystemExit(0 if generate(args.check, args.profile) else 1)
