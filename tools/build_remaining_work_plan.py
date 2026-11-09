"""Generate a numbered documentation plan; never modify ledger, product or VM.

Numbers are seeded explicitly in PLAN-PENDIENTES-CONFIG.json and stay stable
after closure. RC10 details are mapped to outcomes, not counted as new work.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "docs/PLAN-PENDIENTES-CONFIG.json"
MASTER = "docs/REGISTRO-REQUISITOS-MAESTRO.json"
LEDGER = "docs/PLAN-CIERRE-RACKCLICK.json"
AREA_ORDER = ["F", "I", "A", "P", "W", "R", "E", "C", "FUT", "OPS"]
EXTRA_NAMES = {"C": "Catálogo: aceptación y mantenimiento", "FUT": "Evolución posterior a la primera entrega", "OPS": "Repositorio privado y mantenimiento"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def clean(text):
    """Repair adjacent words/numbers in legacy display prose, never IDs/paths."""
    text = str(text or "")
    replacements = {
        "los506": "los 506", "las12008definiciones": "las 12.008 definiciones",
        "de506": "de 506", "seleccion506": "selección de 506", "censo506/506,868revisiones y861comerciales": "censo 506/506, 868 revisiones y 861 modelos comerciales",
        "contrato43": "contrato 43", "instalacion43/11": "instalación 43/11",
        "tipoEntra": "tipo Entra", "perfil600000": "perfil de 600.000 iteraciones",
        "politica45": "política de 45 días", "cuentan45dias": "cuentan 45 días",
        ":45dias": ": 45 días", "reutilizando43/11": "reutilizando 43/11",
        "readiness43": "readiness 43", "readiness14": "readiness 14",
        "cargador02": "cargador 02",
        "167casos": "167 casos", "14casos": "14 casos",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\b(los|las|de|del|por|con|en|tras|y|desde|cuentan|esquema|selección|catalogo|catálogo|criterios|revisión)(?=\d|S[1-5]\b)", r"\1 ", text)
    text = re.sub(r"(?<=\d)(?=[a-záéíóúñ])", " ", text)
    return text


def build():
    config, master, ledger = read(CONFIG), read(MASTER), read(LEDGER)
    tasks = {t["id"]: t for t in master["baseResults"]}
    checkpoints = {c["id"]: (t, c) for t in tasks.values() for c in t["checkpoints"]}
    extra = config["additionalActions"]
    sequence = config["stableStepIds"]
    if len(sequence) != len(set(sequence)):
        raise ValueError("duplicate_stable_number")
    expected = {cid for cid, (_, c) in checkpoints.items() if c["status"] != "done"}
    if not expected.issubset(set(sequence)):
        raise ValueError("unlisted_pending_checkpoint_review_numbering")
    if set(sequence) - set(checkpoints) != set(extra):
        raise ValueError("extra_action_coverage_mismatch")
    if not set(config["overrides"]).issubset(set(checkpoints)):
        raise ValueError("override_unknown_checkpoint")
    additional = {x["id"]: x for x in master["additionalRegister"]}
    declared_extra = {x["id"] for x in additional.values() if x["classification"] in ("ampliacion_catalogo", "evolucion_posterior", "proceso_operativo")}
    if set(extra) != declared_extra:
        raise ValueError("unlisted_additional_action")
    areas = {a["id"]: a["name"] for a in ledger["areas"]} | EXTRA_NAMES
    steps = []
    for number, sid in enumerate(sequence, 1):
        if sid in checkpoints:
            task, check = checkpoints[sid]
            override = config["overrides"].get(sid, {})
            action = override.get("action", check["text"])
            if check.get("closure_review_required") and not override:
                action = "Cerrar «" + task["title"] + "» con evidencia, revisión independiente y aceptación manual cuando corresponda."
            steps.append({
                "number": number, "id": sid, "taskId": task["id"],
                "title": clean(task["title"]), "area": task["area"],
                "scope": "Primera entrega", "action": clean(action),
                "technicalStage": override.get("technicalStage", "Contrastar cierre; puede existir implementación"),
                "ledgerStatus": check["status"], "ledgerText": check["text"],
                "historicalCriterionOverride": bool(override),
                "formalAlignmentRequired": sid in task["ledgerAlignmentRequired"],
                "context": clean(task["currentContext"]),
                "acceptance": clean(task["closureCriterion"]),
                "dependencies": task["dependencies"],
                "evidence": list(dict.fromkeys(task["contextEvidence"] + override.get("evidence", []) + check.get("evidence", []))),
                "responsibleBaseResult": task["id"], "addsClosureWeight": False,
            })
        else:
            source, action = additional[sid], extra[sid]
            area = "C" if sid.startswith("C-HW") else sid.split("-")[0]
            steps.append({
                "number": number, "id": sid, "taskId": sid, "title": clean(action["title"]),
                "area": area, "scope": "Catálogo" if area == "C" else action["scope"],
                "action": clean(action["action"]),
                "technicalStage": "Plan posterior; no bloquea la primera entrega" if area == "FUT" else "Conciliar, aceptar o mantener lo existente",
                "ledgerStatus": "not_scored", "ledgerText": None,
                "historicalCriterionOverride": False, "formalAlignmentRequired": False,
                "context": clean(source.get("state", "")) + ". " + clean(source.get("outcome", source.get("description", ""))),
                "acceptance": clean(action["acceptance"]), "dependencies": [],
                "evidence": [source["source"]] if source.get("source") else [],
                "responsibleBaseResult": action["responsibleBaseResult"], "addsClosureWeight": False,
            })
    by_task = collections.defaultdict(list)
    for step in steps:
        by_task[step["taskId"]].append(step["number"])
    requests, references = [], []
    for source in additional.values():
        if source["classification"] == "peticion_usuario_trazada":
            owner = source["owner"]
            if owner not in by_task:
                raise ValueError("request_without_numbered_owner:" + source["id"])
            requests.append(source | {"stepNumbers": by_task[owner]})
        elif source["classification"] == "referencia_no_requisito":
            references.append(source)
    rc10 = []
    for row in master["rc10DetailMapping"]:
        if row["canonicalOwner"] not in by_task:
            raise ValueError("rc10_without_numbered_owner:" + row["id"])
        rc10.append(row | {"stepNumbers": by_task[row["canonicalOwner"]], "statusMeaning": "Contraste histórico RC10; no diagnóstico actualizado del servidor"})
    if len({r["id"] for r in rc10}) != len(rc10) or len(rc10) != 302:
        raise ValueError("rc10_coverage_changed_review")
    sources = list(dict.fromkeys([CONFIG] + config["sources"]))
    for path in sources:
        if not (ROOT / path).is_file():
            raise ValueError("missing_source:" + path)
    for step in steps:
        for path in step["evidence"]:
            if not (ROOT / path).exists():
                raise ValueError("missing_step_reference:" + step["id"] + ":" + path)
    grouped = []
    for area in AREA_ORDER:
        selected = [s for s in steps if s["area"] == area]
        if selected:
            grouped.append({"id": area, "name": areas[area], "first": selected[0]["number"], "last": selected[-1]["number"], "count": len(selected)})
    done = [{"id": c["id"], "taskId": t["id"], "title": t["title"], "action": c["text"], "evidence": c.get("evidence", [])} for t, c in checkpoints.values() if c["status"] == "done"]
    counts = {"numberedChoices": len(steps), "closedNumberedChoices": sum(s["ledgerStatus"] == "done" for s in steps), "unclosedLedgerCheckpoints": len(expected), "ledgerPending": sum(c["status"] == "pending" for _, c in checkpoints.values()), "ledgerInProgress": sum(c["status"] == "in_progress" for _, c in checkpoints.values()), "ledgerDone": len(done), "catalogChoices": sum(s["area"] == "C" for s in steps), "futureChoices": sum(s["area"] == "FUT" for s in steps), "maintenanceChoices": sum(s["area"] == "OPS" for s in steps), "rc10Details": len(rc10), "requestsMapped": len(requests), "referenceEntries": len(references)}
    return {
        "schemaVersion": 1, "planVersion": config["planVersion"], "date": config["date"],
        "purpose": "Lista completa del alcance registrado para elegir el siguiente paso; no autoriza operaciones ni declara funciones ausentes.",
        "numberingRule": config["numberingRule"], "vmRule": config["vmRule"],
        "metric": master["metric"], "counts": counts, "areas": grouped,
        "catalogCoverage": read("docs/FAMILIAS-CATALOGO-PENDIENTES.json")["counts"],
        "recommendedTasks": config["recommendedTasks"],
        "sourceSha256": {p: sha(p) for p in sources},
        "steps": steps, "rc10Details": rc10, "userRequests": requests,
        "references": references, "alreadyCredited": done,
        "rules": ["Un número estable por subpaso: cerrar no renumera los demás.", "Antes de implementar, contrastar evidencia y código; reutilizar lo ya probado y ejecutar sólo los casos afectados.", "Los 302 detalles RC10 conservan su responsable y no crean puntos ni 302 funciones pendientes nuevas.", "Los 7 cierres de catálogo están ligados a resultados existentes; los 3 futuros no bloquean la primera entrega.", "Ningún paso concede crédito por documentación, número de pruebas o publicación.", "Las decisiones vigentes de MFA, custodia y exención global prevalecen sobre textos históricos; conciliación versionada antes de acreditación incompatible.", "La instalación D y los resultados de Wascar se conservan; esta lista no los modifica."],
    }


def m(text):
    return html.escape(str(text or ""), quote=False).replace("|", "\\|").replace("\n", " ")


def relative(path, for_html=False):
    return path if for_html else "../" + path


def markdown(plan):
    c = plan["counts"]
    task_evidence = collections.defaultdict(list)
    for step in plan["steps"]:
        for path in step["evidence"]:
            if path not in task_evidence[step["taskId"]]:
                task_evidence[step["taskId"]].append(path)
    out = ["# Plan pendiente de RackClick: pasos numerados", "", f"Fecha: {plan['date']} · Versión: {plan['planVersion']}", "", "**Para elegir:** «Continúa con el paso 80» o «Continúa con F-05.04». Los números se conservan al cerrar pasos. Cada resultado incluye contexto, criterio de cierre y referencias; sus subpasos son seleccionables por separado.", "", "[Abrir visor con búsqueda](../VER-PENDIENTES-RACKCLICK.html) · [Datos completos](PLAN-PENDIENTES-NUMERADO.json) · [Hoja maestra](HOJA-DE-RUTA-MAESTRA.md)", "", "## Qué representa esta lista", "", f"Hay **{c['numberedChoices']} opciones numeradas**: {c['unclosedLedgerCheckpoints']} subpasos del cierre ({c['ledgerPending']} pendientes y {c['ledgerInProgress']} en curso), 7 cierres/mantenimiento del catálogo, 3 iniciativas posteriores y 1 proceso de repositorio. Son desgloses de trabajo, no 268 funciones ausentes ni una estimación de duración. Los 23 subpasos con crédito previo se conservan en el apéndice, fuera de los pendientes iniciales.", "", "**Índice acreditado del cierre: 9,76/100, sin cambio. No hay un nuevo porcentaje global del producto.** Los estados formales congelados no describen por sí solos la implementación actual. Un paso puede requerir sólo conciliar pruebas existentes, integración o QA. Las 302 acciones RC10 y 13 peticiones están trazadas en los apéndices; no se suman como trabajo duplicado.", "", f"**Se conserva D:** {plan['vmRule']}", "", "## Orden aconsejado", "", "1. Conciliar los criterios históricos con las decisiones actuales y acreditar evidencia existente: E-07 y F-10. Evitar rehacer funciones ya probadas.", "2. Completar recuperación operativa MFA, emergencia y backups restaurables: F-05, F-06, F-08, F-09, R-03 y R-04.", "3. Cerrar importación/preview/round-trip JSON y paridad restante: P-01, P-02, P-03 y P-04.", "4. Completar aceptación de permisos, inventario, administración, catálogo e idiomas usando los recorridos actuales.", "5. Consolidar Windows/actualización, pruebas prolongadas, manuales, licencias, QA de Wascar y aceptación final. Elegir el laboratorio cuando el paso lo requiera; no reutilizar D automáticamente.", "", "Los números agrupan áreas, no obligan a ejecutar secuencialmente. Las dependencias indicadas pertenecen al resultado completo; investigar primero qué parte ya está satisfecha.", "", "## Índice", "", "| Pasos | Área | Cantidad |", "|---|---|---:|"]
    for area in plan["areas"]:
        out.append(f"| {area['first']}–{area['last']} | {m(area['name'])} | {area['count']} |")
    out += ["", "## Decisiones vigentes y decisiones aún abiertas", "", "- Confirmado: MFA tras 45 días; cuentas existentes desde activación de política, nuevas desde creación. Exención sólo del administrador global con las dos capacidades globales. Desactivar no reinicia el plazo.", "- Confirmado: custodia fuera de PostgreSQL, sobre de recuperación fuera del servidor y sus backups, medios separados; recuperación y nuevo enrolamiento según la decisión aprobada. No se vuelve a pedir estas decisiones.", "- Por concretar en su paso: catálogo finito de compensaciones mixtas (I-02), alcance de terminales internos (I-07), obligación/formato de PDF (P-07), matriz de hosts soportados (W-02), retención y objetivos medidos RPO/RTO/rendimiento (R-01, R-04 y E-06). Son propuestas técnicas a documentar, no motivos para detener todo el proyecto.", "- USB/UNC siguen en R-02 mientras no haya una exclusión explícita. SNMP/LLDP, campo offline y federación real son posteriores; se mantienen visibles sin ampliar el primer cierre.", ""]
    last_area = last_task = None
    for step in plan["steps"]:
        if step["area"] != last_area:
            area = next(a for a in plan["areas"] if a["id"] == step["area"])
            out += [f"## {area['id']} · {m(area['name'])}", ""]
            last_area = step["area"]
        if step["taskId"] != last_task:
            out += [f"### {step['taskId']} · {m(step['title'])}", "", f"**Situación conocida:** {m(step['context'])}", "", f"**Cierre esperado:** {m(step['acceptance'])}", "", "**Dependencias del resultado:** " + (", ".join(step["dependencies"]) or "Sin dependencia previa declarada; contrastar antes de ejecutar.") + ".", "", "**Fuentes:** " + (" · ".join(f"[{m(p)}]({relative(p)})" for p in task_evidence[step["taskId"]]) or "Ledger y hoja maestra; contrastar evidencia antes de implementar.") + ".", ""]
            last_task = step["taskId"]
        out += [f"#### Paso {step['number']:03d} · {step['id']}", "", m(step["action"]), "", f"- Tipo de trabajo: {m(step['technicalStage'])}.", f"- Estado formal: {step['ledgerStatus']}; ámbito: {step['scope']}; responsable: {step['responsibleBaseResult']}."]
        if step["ledgerText"] and step["action"] != step["ledgerText"]:
            out.append(f"- Texto histórico trazable: {m(step['ledgerText'])}")
        if step["formalAlignmentRequired"]:
            out.append("- Conciliación formal requerida antes de acreditar: prevalece la decisión vigente, no el criterio histórico incompatible.")
        if step["ledgerStatus"] == "done":
            out.append("- Número conservado tras el cierre: no repetir como nueva implementación.")
        if step["area"] in ("C", "FUT", "OPS"):
            out.append("- Sin peso nuevo. " + ("Fuera de la primera entrega." if step["area"] == "FUT" else "Ligado al resultado responsable; no suma por separado."))
        out.append("")
    out += ["## Apéndice A · Todas las acciones RC10, sin duplicar puntos", "", "Clasificación de la comparación del 29.10.2026; «ausente» o «parcial» no son un diagnóstico actualizado. Antes de programar se contrasta el servidor y la evidencia actual. Cada fila conserva acción, trabajo previsto, aceptación y responsable. Puedes pedir un PAR concreto además del número principal.", "", "| ID | Área y acción | Contraste histórico | Trabajo previsto / decisión | Aceptación | Responsable y pasos |", "|---|---|---|---|---|---|"]
    for row in plan["rc10Details"]:
        out.append(f"| {row['id']} / {row['offlineId']} | {m(row['area'])}: {m(row['action'])} | {m(row['status'])} | {m(row['workNeeded'])} {m(row.get('decisionNote'))} | {m(row['acceptance'])} | {row['canonicalOwner']}: {', '.join(str(n) for n in row['stepNumbers'])} |")
    out += ["", "## Apéndice B · Peticiones de Wascar y dónde se cierran", "", "| Petición | Resultado esperado y situación registrada | Responsable | Pasos |", "|---|---|---|---|"]
    for row in plan["userRequests"]:
        out.append(f"| {row['id']} · {m(row['title'])} | {m(row['outcome'])} Estado documental: {m(row['state'])}. | {row['owner']} | {', '.join(str(n) for n in row['stepNumbers'])} |")
    out += ["", "## Apéndice C · Subpasos que ya tienen crédito", "", "Se conservan por trazabilidad; no se ofrecen como nueva implementación ni se suman otra vez.", "", "| ID | Resultado / comprobación acreditada |", "|---|---|"]
    out.extend(f"| {row['id']} | {m(row['title'])}: {m(row['action'])} |" for row in plan["alreadyCredited"])
    out += ["", "## Apéndice D · Referencias y herramientas, no requisitos del producto", ""]
    for row in plan["references"]:
        out.append(f"- **{row['id']} · {m(row['title'])}:** {m(row.get('outcome', row.get('description', '')))} Fuente: [{m(row.get('source', ''))}]({relative(row.get('source', ''))}).")
    out += ["", "## Actualización y límites", "", "La lista abarca todo el alcance registrado en las fuentes actuales; no afirma que se conozcan defectos aún no descubiertos. Nuevos requisitos se incorporan con decisión y versión explicada, sin renumerar ni aumentar pesos silenciosamente. Cerrar un paso exige su evidencia y revisión; esta lista no lo cierra.", "", "```powershell", "C:/Python312/python.exe -X utf8 -B tools/build_master_roadmap.py --write", "C:/Python312/python.exe -X utf8 -B tools/build_remaining_work_plan.py --write", "C:/Python312/python.exe -X utf8 -B tools/build_master_roadmap.py --check", "C:/Python312/python.exe -X utf8 -B tools/build_remaining_work_plan.py --check", "```", "", "Fuentes y SHA256 completos en el JSON generado. No se modifica el ledger, los pesos, el producto, las VM ni los resultados de QA.", ""]
    result = "\n".join(out).replace("no 268 funciones", f"no {c['numberedChoices']} funciones").replace("Los 23 subpasos", f"Los {c['ledgerDone']} subpasos")
    result = result.replace("9,76/100", f"{plan['metric']['closedPoints']:.2f}".replace(".", ",") + "/100")
    if c["closedNumberedChoices"]:
        result = result.replace("## Qué representa esta lista", f"Números conservados tras un cierre posterior: {c['closedNumberedChoices']}. Ya están acreditados y no se ofrecen como nueva implementación.\n\n## Qué representa esta lista")
    return result


def h(text):
    return html.escape(str(text or ""), quote=True)


def html_page(plan):
    groups = collections.OrderedDict()
    for step in plan["steps"]:
        groups.setdefault(step["taskId"], []).append(step)
    cards = []
    for tid, steps in groups.items():
        first = steps[0]
        group_evidence = list(dict.fromkeys(p for step in steps for p in step["evidence"]))
        refs = " · ".join(f'<a href="{h(p)}">{h(p)}</a>' for p in group_evidence)
        body = [f'<details class="group" data-area="{h(first["area"])}" data-scope="{h(first["scope"])}"><summary>{steps[0]["number"]}–{steps[-1]["number"]} · {h(tid)} · {h(first["title"])}</summary>', f'<div class="context"><p><strong>Situación conocida:</strong> {h(first["context"])}</p><p><strong>Cierre esperado:</strong> {h(first["acceptance"])}</p><p><strong>Dependencias:</strong> {h(", ".join(first["dependencies"]) or "Ninguna previa declarada; contrastar antes de ejecutar.")}</p><p class="refs">{refs}</p></div>']
        for step in steps:
            body += [f'<article id="paso-{step["number"]}" class="step" data-number="{step["number"]}"><h3>Paso {step["number"]:03d} · {h(step["id"])}</h3><p>{h(step["action"])}</p>', f'<p class="meta">{h(step["technicalStage"])} · {h(step["scope"])} · estado formal: {h(step["ledgerStatus"])} · responsable: {h(step["responsibleBaseResult"])}</p>']
            if step["ledgerText"] and step["action"] != step["ledgerText"]:
                body.append(f'<p class="historical"><strong>Texto histórico:</strong> {h(step["ledgerText"])}</p>')
            if step["formalAlignmentRequired"]:
                body.append('<p class="note">Conciliar formalmente el criterio histórico con la decisión vigente antes de acreditar.</p>')
            if step["area"] in ("C", "FUT", "OPS"):
                body.append('<p class="note">Sin peso nuevo. ' + ("Posterior: no bloquea la primera entrega." if step["area"] == "FUT" else "Se cierra en el resultado responsable.") + '</p>')
            disabled = " disabled" if step["ledgerStatus"] == "done" else ""
            label = "Ya acreditado; número conservado" if disabled else "Elegir este paso"
            body.append(f'<button class="choose" data-number="{step["number"]}" data-id="{h(step["id"])}"{disabled}>{label}</button> <a href="#paso-{step["number"]}">Enlace al paso</a></article>')
        body.append('</details>')
        cards.append("\n".join(body))
    rc_rows = "".join(f'<tr><td>{h(r["id"])} / {h(r["offlineId"])}</td><td>{h(r["area"])} · {h(r["action"])}</td><td>{h(r["status"])}</td><td>{h(r["workNeeded"])} {h(r.get("decisionNote"))}<br><strong>Aceptación:</strong> {h(r["acceptance"])}</td><td>{h(r["canonicalOwner"])} · {", ".join(str(n) for n in r["stepNumbers"])}</td></tr>' for r in plan["rc10Details"])
    request_rows = "".join(f'<tr><td>{h(r["id"])} · {h(r["title"])}</td><td>{h(r["outcome"])}</td><td>{h(r["owner"])} · {", ".join(str(n) for n in r["stepNumbers"])}</td></tr>' for r in plan["userRequests"])
    credited = "".join(f'<li><strong>{h(r["id"])}</strong>: {h(r["action"])}</li>' for r in plan["alreadyCredited"])
    references = "".join(f'<li><strong>{h(r["id"])} · {h(r["title"])}</strong>: {h(r.get("outcome", r.get("description", "")))} <a href="{h(r.get("source", ""))}">Fuente</a></li>' for r in plan["references"])
    area_options = "".join(f'<option value="{h(a["id"])}">{h(a["name"])} ({a["first"]}–{a["last"]})</option>' for a in plan["areas"])
    page = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>RackClick · pendientes numerados</title><style>
:root{color-scheme:light;--ink:#172a42;--blue:#145a86}*{box-sizing:border-box}body{font:16px/1.55 system-ui,sans-serif;margin:0;background:#f1f5f8;color:var(--ink)}header,main,footer{max-width:1200px;margin:auto;padding:24px}header h1{margin:0 0 12px;font-size:2rem}.lead{font-size:1.08rem}.stats{display:flex;gap:12px;flex-wrap:wrap}.stat{background:white;padding:12px 18px;border:1px solid #ccd9e3;border-radius:10px}.stat b{font-size:1.5rem;display:block}.note{background:#fff4d9;border-left:4px solid #9c6500;padding:10px 14px}a{color:var(--blue)}nav{display:flex;gap:18px;flex-wrap:wrap;margin:16px 0}.controls{background:#e3edf4;padding:16px;border-radius:8px;display:flex;gap:14px;flex-wrap:wrap}.controls label{display:flex;flex-direction:column;flex:1;min-width:180px}input,select,textarea,button{font:inherit;padding:9px;border:1px solid #7792a6;border-radius:5px}button{background:var(--blue);color:white;cursor:pointer}button.secondary{background:white;color:var(--blue)}:focus-visible{outline:3px solid #ab5800;outline-offset:3px}.group{margin:14px 0;border:1px solid #c4d4e0;background:white;border-radius:8px;overflow:hidden}.group>summary{font-size:1.08rem;font-weight:700;cursor:pointer;padding:17px;background:#eaf1f6}.context{padding:0 18px;border-bottom:1px solid #c4d4e0}.refs{font-size:.85rem;overflow-wrap:anywhere}.step{padding:16px 20px;border-bottom:1px solid #d8e3eb;scroll-margin-top:15px}.step h3{margin:0 0 8px}.meta,.historical{font-size:.9rem;color:#435e71}.historical{border-left:2px solid #b3c6d4;padding-left:12px}.choose{margin:8px 16px 8px 0}.selection{padding:16px;background:#dceee6;border:1px solid #80a28f;border-radius:8px}.selection textarea{width:100%;margin-top:8px;background:white}.table-wrap{overflow:auto}table{border-collapse:collapse;background:white;width:100%;font-size:.9rem}th,td{border:1px solid #c4d4e0;padding:10px;text-align:left;vertical-align:top}th{background:#e3edf4}.appendix{margin:18px 0}.appendix>summary{cursor:pointer;font-weight:700;padding:14px;background:#dfe9ef}.empty{padding:20px}footer{font-size:.9rem} [hidden]{display:none!important}@media print{.controls,.choose,.selection,nav{display:none}body{background:white}.group{break-inside:avoid}.group>summary{background:white}header,main{padding:0}details:not([open])>*:not(summary){display:block}}
</style></head><body><header><h1>RackClick: elige el siguiente paso</h1><p class="lead">Lista completa del alcance registrado · __DATE__ · números estables, sin rehacer lo ya probado.</p><div class="stats"><div class="stat"><b>268</b>opciones numeradas</div><div class="stat"><b>257</b>subpasos sin cierre acreditado</div><div class="stat"><b>9,76/100</b>índice de cierre, sin cambio</div><div class="stat"><b>506/506 · 50/50</b>modelos integrados y clientes cargados</div></div><p class="note"><strong>No son 268 funciones ausentes ni un porcentaje global nuevo.</strong> 257 subpasos pertenecen al cierre; 7 son de catálogo, 3 de evolución posterior y 1 de repositorio. Los 302 detalles RC10 conservan su responsable sin duplicar puntos. Se mantiene D exactamente como está.</p><nav><a href="docs/PLAN-PENDIENTES-NUMERADO.md">Lista Markdown</a><a href="docs/PLAN-PENDIENTES-NUMERADO.json">JSON completo</a><a href="docs/HOJA-DE-RUTA-MAESTRA.md">Hoja maestra</a><a href="#apendices">302 detalles, peticiones y referencias</a></nav><details><summary>Cómo continuar y qué ya está decidido</summary><p>Recomendación: conciliar evidencia y criterios (E-07/F-10); recuperación operativa MFA y backups; importación JSON y paridad; aceptación de permisos, inventario y catálogo; Windows, rendimiento, manuales, licencias y QA final. Las dependencias se indican por resultado; los números no son un orden obligatorio.</p><p>MFA: 45 días desde creación de cuenta nueva o activación para existentes; desactivar no reinicia el plazo. Exención sólo de administradores globales con ambas capacidades globales. Custodia y recuperación ya confirmadas. No se vuelven a pedir estas decisiones.</p><p>Quedan por concretar en su paso: compensaciones mixtas, terminales internos, PDF, hosts soportados y objetivos medidos de retención/RPO/RTO/rendimiento. SNMP/LLDP, campo offline y federación real son posteriores.</p><p>La lista no inicia pruebas, no marca resultados ni cambia datos. Los estados congelados se conservan por trazabilidad: antes de implementar se revisa la evidencia existente.</p></details></header><main><div class="controls"><label>Buscar número, ID o texto<input id="search" type="search" placeholder="80, F-05, JSON, MFA…"></label><label>Área<select id="area"><option value="">Todas las áreas</option>__AREAS__</select></label><label>Ámbito<select id="scope"><option value="">Todos</option><option>Primera entrega</option><option>Catálogo</option><option>Posterior</option><option>Mantenimiento</option></select></label><button id="expand" class="secondary">Desplegar visibles</button><button id="collapse" class="secondary">Plegar</button></div><p id="count" role="status" aria-live="polite"></p><section class="selection" id="selection" hidden><label for="message">Mensaje para continuar</label><textarea id="message" rows="2" readonly></textarea><p>No inicia trabajo automáticamente. Selecciona y copia el texto a la conversación.</p></section><p id="empty" class="empty" hidden>No hay pasos con estos filtros.</p><div id="steps">__CARDS__</div><section id="apendices"><h2>Detalles sin duplicar trabajo</h2><p>Consulta histórica, no diagnóstico actualizado de ausencias. Si un detalle RC10 dice «ausente», primero se contrasta la candidata actual. Las peticiones están asignadas al resultado que las cierra.</p><details class="appendix"><summary>302 acciones RC10: acción, trabajo, aceptación y responsable</summary><div class="table-wrap"><table><thead><tr><th>ID</th><th>Área / acción</th><th>Contraste histórico</th><th>Trabajo y aceptación</th><th>Resultado / pasos</th></tr></thead><tbody>__RC10__</tbody></table></div></details><details class="appendix"><summary>13 peticiones de Wascar: dónde se cierran</summary><div class="table-wrap"><table><thead><tr><th>Petición</th><th>Resultado esperado</th><th>Responsable / pasos</th></tr></thead><tbody>__REQUESTS__</tbody></table></div></details><details class="appendix"><summary>23 subpasos con crédito previo</summary><ul>__CREDITED__</ul></details><details class="appendix"><summary>6 referencias y herramientas: no son funciones pendientes</summary><ul>__REFERENCES__</ul></details></section></main><footer><p>Versión __VERSION__. Los números se mantienen al cerrar pasos. Requisitos nuevos necesitan versión explicada; esta lista no aumenta pesos ni acredita resultados. Datos y huellas en el JSON. Funciona localmente sin red, almacenamiento ni conexión a la aplicación o a las VM.</p></footer><script>
'use strict';
const groups=[...document.querySelectorAll('.group')];
const search=document.getElementById('search'),area=document.getElementById('area'),scope=document.getElementById('scope');
function filter(){const q=search.value.trim().toLocaleLowerCase('es');const exact=/^\d+$/.test(q);let count=0;for(const g of groups){let found=0;const eligible=(!area.value||area.value===g.dataset.area)&&(!scope.value||scope.value===g.dataset.scope);for(const s of g.querySelectorAll('.step')){const matches=!q||(exact?Number(s.dataset.number)===Number(q):(g.querySelector('summary').textContent+' '+g.querySelector('.context').textContent+' '+s.textContent).toLocaleLowerCase('es').includes(q));s.hidden=!(eligible&&matches);if(!s.hidden){found++;count++;}}g.hidden=!found;if(q&&found)g.open=true;}document.getElementById('count').textContent=count+' de 268 pasos visibles. Los filtros no cambian el estado del proyecto.';document.getElementById('empty').hidden=count!==0;}
for(const control of [search,area,scope])control.addEventListener('input',filter);
document.getElementById('expand').addEventListener('click',()=>groups.filter(g=>!g.hidden).forEach(g=>g.open=true));
document.getElementById('collapse').addEventListener('click',()=>groups.forEach(g=>g.open=false));
for(const button of document.querySelectorAll('.choose'))button.addEventListener('click',()=>{document.getElementById('selection').hidden=false;const message=document.getElementById('message');message.value='Continúa con el paso '+button.dataset.number+' ('+button.dataset.id+') del plan numerado de RackClick. Conserva D y reutiliza la evidencia existente antes de implementar.';message.focus();message.select();});
function openHash(){if(!/^#paso-\d+$/.test(location.hash))return;const el=document.getElementById(location.hash.slice(1));if(!el)return;search.value='';area.value='';scope.value='';filter();el.closest('details').open=true;el.scrollIntoView();}
window.addEventListener('hashchange',openHash);filter();openHash();
</script></body></html>'''
    page = page.replace("268", str(plan["counts"]["numberedChoices"])).replace("257", str(plan["counts"]["unclosedLedgerCheckpoints"])).replace("23 subpasos", str(plan["counts"]["ledgerDone"]) + " subpasos")
    page = page.replace("9,76/100", f"{plan['metric']['closedPoints']:.2f}".replace(".", ",") + "/100")
    page = page.replace("13 peticiones de Wascar", str(plan["counts"]["requestsMapped"]) + " peticiones de Wascar").replace("6 referencias y herramientas", str(plan["counts"]["referenceEntries"]) + " referencias y herramientas")
    if plan["counts"]["closedNumberedChoices"]:
        page = page.replace("Se mantiene D exactamente como está.", f"Se mantienen además {plan['counts']['closedNumberedChoices']} números ya acreditados, sin ofrecerlos como nueva implementación. Se mantiene D exactamente como está.")
    replacements = {"__DATE__": h(plan["date"]), "__VERSION__": h(plan["planVersion"]), "__AREAS__": area_options, "__CARDS__": "\n".join(cards), "__RC10__": rc_rows, "__REQUESTS__": request_rows, "__CREDITED__": credited, "__REFERENCES__": references}
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    return page + "\n"


def outputs(plan):
    return {
        "docs/PLAN-PENDIENTES-NUMERADO.json": json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        "docs/PLAN-PENDIENTES-NUMERADO.md": markdown(plan),
        "VER-PENDIENTES-RACKCLICK.html": html_page(plan),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    ledger_before = sha(LEDGER)
    plan = build()
    differences = []
    for path, content in outputs(plan).items():
        encoded = content.encode("utf-8")
        target = ROOT / path
        if args.write:
            target.write_bytes(encoded)
        elif not target.is_file() or target.read_bytes() != encoded:
            differences.append(path)
    if sha(LEDGER) != ledger_before:
        raise RuntimeError("ledger_changed")
    print(json.dumps({"valid": not differences, "counts": plan["counts"], "closedPointsUnchanged": plan["metric"]["closedPoints"], "ledgerSha256": ledger_before, "differentFiles": differences, "writesProductOrVm": False}, ensure_ascii=False))
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
