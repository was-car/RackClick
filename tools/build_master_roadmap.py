"""Build documentation only. Never changes the frozen closure ledger or product."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs/REGISTRO-MAESTRO-CONFIG.json"


def load(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("source_outside_project")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def md(text):
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;"
    ).replace("|", r"\|").replace("\r", "").replace("\n", " ")


def doclink(path):
    return "../" + path if not path.startswith("docs/") else path[5:]


def owner(row):
    oid = row["offlineId"]
    explicit = {
        **{f"O-{n:03}": "P-06" for n in range(28, 33)},
        "O-033": "R-06", "O-050": "P-11", "O-051": "P-11",
        "O-052": "P-11", "O-081": "I-04", "O-082": "I-04",
        "O-091": "I-03", "O-093": "I-03", "O-223": "P-11",
        "O-224": "P-11", "O-227": "P-03", "O-228": "P-03",
        "O-229": "P-03", "O-234": "P-04", "O-235": "P-02",
        "O-236": "P-02", "O-237": "P-02", "O-238": "P-04",
        "O-239": "P-03", "O-265": "P-07", "O-270": "P-07",
        "O-271": "E-05", "O-272": "E-05", "O-274": "E-05",
        "O-277": "R-01", "O-281": "R-01", "O-282": "R-01",
        "O-283": "R-04", "O-284": "R-01",
    }
    areas = {
        "Navegación": "I-04", "Ámbito": "I-04",
        "Systemhaus e infraestructura": "I-04", "Cliente y proyecto": "P-06",
        "Rack": "I-04", "Equipo": "I-04", "Catálogo y plantillas": "P-08",
        "Equipo personalizado": "I-04", "Caras y alimentación": "I-03",
        "Puerto": "I-03", "Lotes de puertos": "I-03",
        "Conexiones": "I-05", "Conexiones en lote": "I-05",
        "Búsqueda y filtros": "P-05", "Preferencias visuales": "P-10",
        "Historial y atajos": "I-02", "JSON e importación": "P-01",
        "CSV e intercambio": "P-05", "Informes": "P-07",
        "Imágenes y documentos": "P-07", "Etiquetas y QR": "P-07",
        "Demo e idioma": "P-10", "Persistencia y recuperación": "P-05",
        "Fallo de aplicación": "P-05",
    }
    if oid in explicit:
        return explicit[oid]
    if row["area"] not in areas:
        raise ValueError("unmapped_rc10_area")
    return areas[row["area"]]


def build():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for source in config["sources"]:
        if not (ROOT / source).is_file():
            raise ValueError("missing_source:" + source)
    ledger = load("docs/PLAN-CIERRE-RACKCLICK.json")
    actions = load(
        "evidence/s1-20261029/comparacion-rc10-servidor/PLAN-ACCIONES.json"
    )
    matrix = load(
        "evidence/s1-20261029/comparacion-rc10-servidor/MATRIZ-CONSOLIDADA.json"
    )
    ids = {t["id"] for t in ledger["tasks"]}
    if len(ids) != 53 or len(actions) != 302:
        raise ValueError("source_inventory_changed_review_mapping")
    if {a["offlineId"] for a in actions} != {a["id"] for a in matrix}:
        raise ValueError("rc10_inventories_disagree")
    requirements = []
    for task in ledger["tasks"]:
        context = config["latestContext"].get(task["id"], {})
        steps = task["checkpoints"]
        complete = sum(s["status"] == "done" for s in steps)
        requirements.append({
            "id": task["id"], "area": task["area"],
            "title": context.get("title", task["title"]),
            "ledgerTitle": task["title"],
            "classification": "resultado_base",
            "state": "cerrado_acreditado" if complete == len(steps) else (
                "parcial_acreditado" if complete else "pendiente_de_cierre_acreditado"
            ),
            "currentContext": context.get("text", task["current"]),
            "contextIsCurrentOverride": bool(context),
            "contextEvidence": context.get("evidence", task["evidence"]),
            "closureCriterion": context.get("closureText", task["closure"]),
            "ledgerClosureCriterion": task["closure"],
            "dependencies": task["dependencies"],
            "weightPoints": task["weight_points"],
            "closedPoints": str(sum(
                (Fraction(s["weight_points"]) for s in steps if s["status"] == "done"),
                Fraction(0),
            )),
            "completedCheckpoints": complete, "totalCheckpoints": len(steps),
            "checkpoints": steps,
            "ledgerAlignmentRequired": context.get("ledgerAlignmentRequired", []),
            "checkpointTextRole": "Copia literal del ledger congelado para trazabilidad. "
                "La decisión vigente y currentContext prevalecen para programar; "
                "los criterios señalados requieren conciliación versionada antes de acreditación.",
            "source": "docs/PLAN-CIERRE-RACKCLICK.json",
        })
    mappings = []
    for action in actions:
        primary = owner(action)
        if primary not in ids:
            raise ValueError("invalid_canonical_owner")
        related = set()
        if action["area"] in {"Ámbito", "Systemhaus e infraestructura"}:
            related.add("A-01")
        if action["area"] in {"Conexiones", "Conexiones en lote"}:
            related.add("I-03")
        if action["area"] in {"CSV e intercambio", "JSON e importación"}:
            related.update(["P-01", "P-02", "P-03", "P-04"])
        if action["offlineId"] == "O-277":
            related.update(["R-03", "R-04", "F-05"])
        if action["offlineId"] == "O-265":
            related.add("P-06")
        related.discard(primary)
        mappings.append({
            **action, "canonicalOwner": primary, "relatedResults": sorted(related),
            "addsClosureWeight": False,
            "mappingRole": "Clasificación documental para planificar, no prueba de "
                "implementación ni exclusión de su criterio original.",
        })
    extensions = []
    # Unweighted catalog/future results can own an observation. This does not
    # extend the ledger IDs used for RC10 mappings or weight calculations.
    reference_ids = ids | {item['id'] for section in
        ('observations', 'catalogStream', 'future', 'references', 'operations') for item in config[section]}
    for key, classification in [
        ("observations", "peticion_usuario_trazada"),
        ("catalogStream", "ampliacion_catalogo"),
        ("future", "evolucion_posterior"),
        ("references", "referencia_no_requisito"),
        ("operations", "proceso_operativo"),
    ]:
        for item in config[key]:
            if item.get("owner") and item["owner"] not in reference_ids:
                raise ValueError("invalid_observation_owner")
            if not set(item.get("related", [])) <= reference_ids:
                raise ValueError("invalid_related_result")
            extensions.append({
                **item, "classification": classification, "addsClosureWeight": False,
                "source": item.get("source", (
                    "docs/ALCANCE-CATALOGO-FABRICANTES.md" if key == "catalogStream"
                    else "docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md"
                )),
            })
    if len({x["id"] for x in requirements + extensions}) != len(requirements + extensions):
        raise ValueError("duplicate_master_id")
    total = sum(
        (Fraction(s["weight_points"]) for t in ledger["tasks"]
         for s in t["checkpoints"] if s["status"] == "done"), Fraction(0)
    )
    inputs = [{
        "file": source,
        "sha256": hashlib.sha256((ROOT / source).read_bytes()).hexdigest(),
    } for source in ["docs/REGISTRO-MAESTRO-CONFIG.json"] + config["sources"]]
    registry = {
        "schemaVersion": 1, "date": config["date"],
        "role": "Entrada única de planificación. El ledger conserva la contabilidad; "
            "las decisiones confirmadas más recientes rigen la ejecución.",
        "sourceBaseline": ledger["baseline_id"],
        "sourceFrozenFingerprint": ledger["frozen_structure_sha256"],
        "metric": {
            "kind": "remaining_work_closure_not_global_product_percentage",
            "closedPointsExact": str(total), "closedPoints": float(total),
            "totalPoints": 100, "globalProductPercentage": None,
            "sourceTasks": 53, "scoredSourceTasks": sum(t["scored"] for t in ledger["tasks"]),
            "checkpoints": sum(len(t["checkpoints"]) for t in ledger["tasks"]),
            "doneCheckpoints": sum(s["status"] == "done" for t in ledger["tasks"]
                                   for s in t["checkpoints"]),
            "newWeightAllocated": 0,
        },
        "inputs": inputs, "baseResults": requirements,
        "rc10DetailMapping": mappings, "additionalRegister": extensions,
        "nextBatch": config["nextBatch"],
        "rules": [
            "No sumar53resultados+302acciones como355implementaciones.",
            "Una observación/defecto se vincula a un resultado; no añade puntos.",
            "Una ampliación nueva exige alcance/corte de entrega y versión explicada "
            "si se incorpora a la métrica. No inventar pesos ni ocultar su coste.",
            "Fuente/código/prueba/revisión/candidata/QA/adopción son estados distintos.",
            "Los criterios F-10.03/.04 congelados no anulan la decisión45días/exención global.",
            "Descubrimiento y federación real no bloquean el cierre actual por estar referenciados.",
        ],
    }
    points = f"{float(total):.2f}".replace(".", ",")
    lines = [
        "# Hoja de ruta maestra de RackClick", "",
        f"{config['date']} · Entrada única para continuar el proyecto. "
        "Integra el cierre existente, las peticiones de Wascar, la comparación RC10 "
        "y el catálogo de fabricantes. No declara implementado lo que sólo está investigado.", "",
        "**Abrir este documento al planificar.** "
        "[Registro completo JSON](REGISTRO-REQUISITOS-MAESTRO.json) · "
        "[Trazabilidad de las302acciones](TRAZABILIDAD-RC10-MAESTRA.csv) · "
        "[Pasos numerados para elegir](PLAN-PENDIENTES-NUMERADO.md) · "
        "[Conciliación de documentos](CONCILIACION-PLANES-30-10-2026.md).", "",
        "## Estado que se conserva", "",
        config.get("currentSnapshot", {}).get("text", "El servidor10 funciona con PostgreSQL17, servicio Windows/HTTPS y MFA real "
        "probado por Wascar. Los10clientes originales ya se cargaron con su inventario "
        "y la seguridad conservada. Hay jerarquía, Click-Click, grupos/permisos, "
        "plantillas/favoritos y varios formatos de exportación. "
        "Faltan resultados de integración, recuperación, variantes y aceptación; "
        "no se comienza otro piloto."), "",
        f"El cierre cuantificado mantiene {registry['metric']['sourceTasks']} resultados "
        f"({registry['metric']['scoredSourceTasks']} con peso y "
        f"{registry['metric']['sourceTasks'] - registry['metric']['scoredSourceTasks']} controles), "
        f"{registry['metric']['checkpoints']} subpasos y {registry['metric']['doneCheckpoints']} acreditados. "
        "Son comprobaciones de cierre, no funciones nuevas "
        "que haya que escribir. Las302acciones RC10 son detalle trazado; "
        "el catálogo nuevo es una ampliación diferenciada.", "",
        "## Qué falta, por bloques", "",
        "| Bloque | Trabajo que falta cerrar |",
        "|---|---|",
        "| F · Seguridad/MFA | Clasificación de hallazgos reales; configuración SQL "
        "y secretos recuperables; custodia/ACL finales; sobre portable, rotación, "
        "custodia/cierre de códigos y emergencia del último administrador; reautenticación y matriz "
        "final. Conservar panel/login/gracia45 ya construidos. |",
        "| I · Inventario y colaboración | Variantes de conectores/caras/PoE, "
        "reconexión y lotes por IDs/grupo/tipo; compensación/rehacer seguro, "
        "concurrencia GUI, Dosen/finales y decisión separada sobre terminales internos. |",
        "| A · Administración | Recorrido más visual de usuarios/grupos/ámbitos, "
        "aceptación de C1 vigente, auditoría fuera de las21formas y retención/correlación. "
        "La autorización sigue en servidor. |",
        "| P · Paridad RC9/RC10 | Import/export JSON normal y merge/round-trip; "
        "branding/técnico/logo; PNG y cierre de formatos; herramientas/atajos; "
        "racks primero, detalles plegables, avisos, EN/DE/ES y accesibilidad. |",
        "| W · Windows y red | Matriz soportada y negativos de cuenta/servicio; "
        "red/certificados casa-trabajo sencillos; repetición/cancelación/diagnóstico "
        "y recorrido instalado completo. New11/postboot deD ya probado se conserva. |",
        "| R · Backup y recuperación | Retención, destinos local/USB/UNC, "
        "cifrado y secretos/MFA, restore completo en otroWindows, "
        "actualización/rollback y reset delimitado. Integrar operación en dashboard. |",
        "| E · Entrega | Candidata única, build repetible, licencias/SBOM/avisos, "
        "manual final y QA por módulos, carga10usuarios con demo completa y adopción. |",
        "| C-HW · Fabricantes | Selección506/506 integrada en43 y cargada enD. "
        "Cerrar QA/reservas de configuración/geometría, procedencia/licencias, "
        "publicación y mantenimiento; no repetir la autoría de esos modelos. |",
        "| FUT · Después | Descubrimiento SNMP/LLDP/API, paquetes de campo S5 "
        "y federación AD/OIDC real; mantienen su alcance posterior. |", "",
        "Rendimiento requiere medición en la candidata con datos/usuarios "
        "representativos. La lista no demuestra un fallo de PostgreSQL ni exige "
        "cambiar de base. Las mejoras se decidirán sobre resultados reproducidos.", "",
        "## Peticiones de Wascar registradas", "",
    ]
    for item in config["observations"]:
        lines.extend([
            f"- **{item['id']} · {md(item['title'])}** → {item['owner']} "
            f"(relacionados:{', '.join(item['related'])}). "
            f"{md(item['outcome'])} Estado:{md(item['state'])}.",
        ])
    lines.extend([
        "", "## Catálogo de fabricantes: ampliación trazada", "",
        "[Alcance completo](ALCANCE-CATALOGO-FABRICANTES.md) · "
        "[Visor de consulta](../CATALOGO-HARDWARE.html). "
        "12.008definiciones comunitarias y144racks no son12.152plantillas aprobadas. "
        "195registros primarios pueden solaparse;19tienen campos físicos parciales. "
        "Fechas/revisiones desconocidas se conservan. "
        "No se instala PacketTracer ni se copian fotos por estar publicadas.", "",
    ])
    for item in config["catalogStream"]:
        lines.extend([
            f"- **{item['id']} · {md(item['title'])}** — "
            f"{md(item['state'])}. {md(item['outcome'])}",
        ])
    lines.extend(["", "## Evolución posterior y referencias", ""])
    for item in config["future"]:
        lines.append(f"- **{item['id']} · {md(item['title'])}** — "
                     f"{md(item['state'])}. {md(item['outcome'])}")
    lines.extend(["", "Las alternativas investigadas también quedan registradas, "
                  "con su disposición. No se implementa cada repositorio como una "
                  "función obligatoria:", ""])
    for item in config["references"] + config["operations"]:
        lines.append(f"- **{item['id']} · {md(item['title'])}.** {md(item['outcome'])}")
    lines.extend([
        "", "## Cómo queda integrada la información", "",
        "| Documento | Papel |",
        "|---|---|",
        "| HOJA-DE-RUTA-MAESTRA.md | Punto de entrada humano y orden de trabajo. |",
        "| REGISTRO-MAESTRO-CONFIG.json | Contexto vigente, peticiones y frentes; "
        "se edita aquí la parte manual. |",
        "| REGISTRO-REQUISITOS-MAESTRO.json | Registro generado:53resultados/"
        "280subpasos,302correspondencias y ampliaciones/referencias. |",
        "| PLAN-CIERRE-RACKCLICK.json | Ledger congelado de pesos, estados "
        "acreditados y evidencias. No se cambia por subdividir. |",
        "| Matriz/plan RC10 | Definición detallada de acciones; cada O-ID "
        "se vincula a un resultado existente. |",
        "| Alcance/catálogo de fabricantes | Fuentes, modelos y aceptación del "
        "frenteC-HW; separado del catálogo instalado. |",
        "| Protocolo de evolución | Investigación futura; conserva lo hablado "
        "sin convertirlo en dependencia de entrega. |",
        "| QA-CASOS-WASCAR.json y guías | Casos ejecutables por candidata, "
        "roles y disponibilidad; resultados de Wascar separados/conservados. |", "",
        "Una decisión explícita más reciente de Wascar prevalece sobre resúmenes "
        "históricos. La custodia está confirmada; MFA45/exención global rigen la "
        "ejecución. F-05 y F-10 tienen resúmenes antiguos en el ledger; "
        "el contexto vigente se muestra en este registro. Antes de acreditar "
        "criterios incompatibles se debe conciliar la versión del ledger, "
        "preservando pesos y evidencia. No se pide de nuevo una decisión ya tomada.", "",
        "## Procedimiento para cada trabajo", "",
        "1. Abrir esta hoja, elegir resultado existente o identificador de "
        "ampliación y anotar el problema/resultado concreto. Un bug o variante "
        "se adjunta a su resultado; no genera puntos nuevos.",
        "2. Definir archivos/responsable, dependencias y aceptación; aprovechar "
        "código/investigación existente. Separar implementador y revisor. "
        "No asignar a dos personas el mismo archivo sin coordinación.",
        "3. Implementar en laboratorio independiente y probar el cambio afectado. "
        "Registrar fuente/build/hash/entorno, negativo cuando corresponda y resultado; "
        "una prueba histórica conserva su fecha.",
        "4. Integrar sólo la revisión aceptada en una candidata compatible. "
        "Actualizar QA visible con ubicación/botón/campo/resultado y disponibilidad "
        "real. No reemplazar notas o PASS de Wascar.",
        "5. Acreditar sólo el subpaso comprobado, actualizar continuidad/changelog "
        "y regenerar esta hoja. Informar ID, qué avanzó, prueba, qué falta y "
        "si cambió o no la métrica.",
        "6. Si un requisito es realmente nuevo y se incorpora al compromiso "
        "de entrega, explicar corte/alcance y versionar la base antes de ponderarlo. "
        "El catálogo y la investigación futura no alteran automáticamente100puntos.", "",
        "Regeneración documental desde la raíz: "
        "C:/Python312/python.exe -B tools/build_master_roadmap.py --write. "
        "Para verificar: mismo comando con --check. Sólo escribe los tres "
        "artefactos generados; no instala, cambia el ledger, DB, VM, GUI o QA.", "",
        "## Siguiente grupo propuesto", "",
    ])
    for item in config["nextBatch"]:
        lines.append(f"- **{item['id']} · {md(item['title'])}** "
                     f"({', '.join(item['references'])}). {md(item['output'])}")
    lines.extend([
        "", "Estas tres salidas pueden prepararse con archivos/responsables "
        "separados; sus dependencias se revisan antes de implementar. "
        "Este bloque sólo consolida documentos; no inicia esas tres tandas, "
        "instalaciones o ensayos VM.", "",
        "Después:intercambio JSON/backup desde dashboard, administración visual, "
        "paridad restante y primera selección de modelos; finalmente integración "
        "Windows/restore/carga/QA/adopción. Seguridad y recuperación necesarias "
        "para producción siguen siendo condiciones de entrega.", "",
        "## Lista completa de resultados base", "",
        "A continuación están los53resultados existentes con su avance acreditado, "
        "contexto y cierre. Los280subpasos literales y evidencias están en el JSON "
        "maestro; los criterios que necesitan conciliación se señalan. "
        "«Sin crédito» no significa que no exista código.", "",
    ])
    for area in ledger["areas"]:
        lines.extend([f"### {area['id']} · {md(area['name'])}", ""])
        for item in requirements:
            if item["area"] != area["id"]:
                continue
            closed_display = f"{float(Fraction(item['closedPoints'])):.2f}".replace(".", ",")
            weight_display = f"{float(Fraction(str(item['weightPoints']))):.2f}".replace(".", ",")
            lines.extend([
                f"#### {item['id']} · {md(item['title'])}", "",
                f"- **Cierre acreditado:** {item['completedCheckpoints']}/"
                f"{item['totalCheckpoints']} subpasos; {closed_display}/"
                f"{weight_display} puntos. Estado:{item['state']}.",
                f"- **Lo que hay:** {md(item['currentContext'])}",
                f"- **{'Criterio conservado; no reabrir por este registro' if item['state'] == 'cerrado_acreditado' else 'Resultado que falta cerrar'}:** {md(item['closureCriterion'])}",
                "- **Fuentes:** " + "; ".join(
                    f"[{Path(path).name}]({doclink(path)})"
                    for path in item["contextEvidence"]
                ),
            ])
            if item["ledgerAlignmentRequired"]:
                lines.append("- **Conciliar redacción antes de acreditar:** "
                             + ", ".join(item["ledgerAlignmentRequired"])
                             + "; aplicar la decisión45días/exención global vigente.")
            lines.append("")
    lines.extend([
        "## Progreso y cierre de esta consolidación", "",
        f"**{points}/100 del cierre restante**, misma base "
        f"{ledger['baseline_id']},53resultados/280subpasos/23acreditados. "
        "**No es porcentaje global del producto.** Registrar pendientes, "
        "descargar modelos o regenerar esta hoja no suma implementación.", "",
        "El cierre de esta consolidación es documental: ninguna función, "
        "plantilla o prueba de producto se acredita por este registro. "
        "Los originales y los paquetes históricos se conservan.", "",
    ])
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(["ID RC10", "Área", "Acción", "Resultado responsable",
                     "Resultados relacionados", "Estado comparativo",
                     "Disposición", "Trabajo", "Añade peso"])
    for action in mappings:
        values = [action["offlineId"], action["area"], action["action"],
                  action["canonicalOwner"], ", ".join(action["relatedResults"]),
                  action["status"], action["decision"], action["workNeeded"], "No"]
        writer.writerow([
            "'" + str(x) if str(x).lstrip().startswith(("=", "+", "-", "@"))
            else str(x) for x in values
        ])
    human_report = "\n".join(lines)
    for before, after in [
        ("servidor10", "servidor 10"), ("candidata10", "candidata 10"),
        ("PostgreSQL17", "PostgreSQL 17"), ("Los10clientes", "Los 10 clientes"),
        ("mantiene53resultados", "mantiene 53 resultados"),
        ("53resultados", "53 resultados"), ("50con peso", "50 con peso"),
        ("y3controles", "y 3 controles"), ("280subpasos", "280 subpasos"),
        ("y23acreditados", "y 23 acreditados"), ("23acreditados", "23 acreditados"),
        ("no280funciones", "no 280 funciones"), ("Las302acciones", "Las 302 acciones"),
        ("las302acciones", "las 302 acciones"), ("302acciones", "302 acciones"),
        ("21formas", "21 formas"), ("otroWindows", "otro Windows"),
        ("carga10usuarios", "carga de 10 usuarios"),
        ("Primer100perfiles", "Primeros 100 perfiles"),
        ("100perfiles", "100 perfiles"), ("perfiles:12Sophos", "perfiles: 12 Sophos"),
        ("16Fortinet", "16 Fortinet"), ("12PaloAlto", "12 Palo Alto"),
        ("20Cisco", "20 Cisco"), ("12Aruba", "12 Aruba"), ("8Synology", "8 Synology"),
        ("8QNAP", "8 QNAP"), ("6racks", "6 racks"), ("6UPS/PDU", "6 UPS/PDU"),
        ("45días", "45 días"), ("gracia45", "gracia de 45 días"),
        ("política45", "política de 45 días"), ("frenteC-HW", "frente C-HW"),
        ("144racks", "144 racks"), ("195registros", "195 registros"),
        ("19tienen", "19 tienen"), ("100puntos", "100 puntos"),
        ("cierre restante9", "cierre restante 9"),
    ]:
        human_report = human_report.replace(before, after)
    outputs = {
        ROOT / "docs/REGISTRO-REQUISITOS-MAESTRO.json":
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        ROOT / "docs/HOJA-DE-RUTA-MAESTRA.md": human_report,
        ROOT / "docs/TRAZABILIDAD-RC10-MAESTRA.csv": "\ufeff" + stream.getvalue(),
    }
    return outputs, registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs, registry = build()
    if args.write:
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8", newline="")
    if args.check:
        for path, content in outputs.items():
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                raise ValueError("master_artifact_stale:" + path.name)
    print(json.dumps({
        "baseResults": len(registry["baseResults"]),
        "rc10Mapped": len(registry["rc10DetailMapping"]),
        "additionalEntriesByType": dict(collections.Counter(
            r["classification"] for r in registry["additionalRegister"]
        )),
        "closurePointsUnchanged": registry["metric"]["closedPoints"],
        "writesLedgerOrProduct": False,
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
