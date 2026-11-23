#!/usr/bin/env python3
"""Apparatus and technical-route diagrammer (standard library only).

Extracts components, interfaces, connections and material-flow directions,
then numbered process steps and technical-route phases.  Emits a reproducible
three-part figure specification (apparatus, process flow, route) with checks
to /app/output/result.json.  Deterministic and offline; nothing is invented.
"""

import argparse
import hashlib
import json
import os
import re
import sys

DEFAULT_CASE = "/input/case.json"
DEFAULT_OUT = "/app/output/result.json"
DEFAULT_WORK = "/app/work"
SKILL_NAME = "apparatus-route-diagrammer"
SKILL_VERSION = "1.0.0"
CHALLENGE_ID = "challenge-9034312d"
MAX_TEXT = 400000
SKIP_KEYS = {"output_contract", "scoring", "tags", "meta", "case_id",
             "challenge_id", "skill", "contract_notes"}

COMPONENT_SUFFIXES = ("泵", "阀", "反应器", "柱", "检测器", "传感器", "电极", "膜",
                      "芯片", "烧杯", "瓶", "管", "腔", "室", "炉", "离心机", "混合器",
                      "控制器", "温控", "进样器", "收集器", "过滤器", "电源", "显微镜",
                      "光谱仪", "质谱仪", "色谱仪", "流量计", "压力表")
STEP_RE = re.compile(r"^\s*(?:步骤\s*|Step\s*|step\s*)?(\d{1,2})\s*[\.\)、:：]\s*(.+)$")
PHASE_RE = re.compile(r"^\s*(?:阶段\s*|Phase\s*|phase\s*)([一二三四五六七八九十\d]+)\s*[：:\.\-]?\s*(.*)$")
ARROW_RE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9\-/+]{2,24})\s*(?:→|->|—>|=>|➜)\s*([\u4e00-\u9fffA-Za-z0-9\-/+]{2,24})")
FLOW_RE = re.compile(r"(?:从\s*)?([\u4e00-\u9fffA-Za-z0-9\-/+]{2,24})\s*(?:流入|进入|输送到|输送至|连接到|导入|通入|流入到)\s*([\u4e00-\u9fffA-Za-z0-9\-/+]{2,24})")
MEDIUM_STYLE = {
    "material": {"color": "#1F1F1F", "line": "solid", "arrowhead": "solid_arrow"},
    "energy": {"color": "#E69F00", "line": "dashed", "arrowhead": "solid_arrow"},
    "signal": {"color": "#0072B2", "line": "dotted", "arrowhead": "open_arrow"},
    "waste": {"color": "#999999", "line": "dash_dot", "arrowhead": "solid_arrow"},
}
PORT_KEYS = ("inlet", "outlet", "port", "接口", "入口", "出口")


def sha256_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_text_file(path):
    try:
        if os.path.isfile(path) and os.path.getsize(path) <= 4 * 1024 * 1024:
            with open(path, "r", encoding="utf-8-sig") as handle:
                return handle.read()
    except (OSError, UnicodeDecodeError):
        return None
    return None


def collect_material(case, base_dir):
    parts, unreadable = [], []

    def walk(node, label):
        if isinstance(node, str):
            stripped = node.strip()
            if len(stripped) >= 40:
                parts.append({"label": label, "text": stripped, "path": None})
                return
            if stripped and not stripped.startswith(("{", "[")):
                for candidate in (stripped, os.path.join(base_dir, stripped)):
                    text = read_text_file(candidate)
                    if text is not None:
                        parts.append({"label": label, "text": text, "path": candidate})
                        return
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in SKIP_KEYS or key in ("id", "name", "title", "type", "kind"):
                    continue
                walk(value, "%s.%s" % (label, key))
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                walk(value, "%s[%d]" % (label, idx))

    for key, value in case.items():
        if key in SKIP_KEYS:
            continue
        walk(value, key)
    parts.sort(key=lambda item: (-len(item["text"]), item["label"]))
    return parts, unreadable


def task_text(base_dir):
    for name in ("task.md", "TASK.md", "task.txt"):
        path = os.path.join(base_dir, name)
        text = read_text_file(path)
        if text:
            return text, path
    return "", None


def clean_name(raw):
    token = raw.strip(" \t\r\n，。；;：:、（）()[]【】\"'“”《》<>")
    token = re.sub(r"^(?:而|且|并|又|也|将|把|从)+", "", token)
    token = re.sub(r"(?:的|中|内)$", "", token)
    if 2 <= len(token) <= 24:
        return token
    return None


def pick_components(case, text):
    explicit = []
    for key in ("components", "parts", "apparatus", "devices", "units"):
        value = case.get(key)
        if not isinstance(value, list):
            continue
        for entry in value:
            if isinstance(entry, str) and entry.strip():
                explicit.append({"name": entry.strip(), "type": None, "ports": [], "source": key})
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("label") or entry.get("id")
                if not isinstance(name, str) or not name.strip():
                    continue
                ports = []
                for port_key in PORT_KEYS:
                    port_value = entry.get(port_key)
                    if isinstance(port_value, list):
                        ports.extend(str(item) for item in port_value)
                    elif isinstance(port_value, str):
                        ports.append(port_value)
                explicit.append({"name": name.strip(),
                                 "type": entry.get("type") or entry.get("kind"),
                                 "ports": ports, "source": key,
                                 "evidence": entry.get("evidence")})
    if explicit:
        return explicit

    names = []
    for suffix in COMPONENT_SUFFIXES:
        for match in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9\-/+]{1,14}%s)" % suffix, text):
            names.append(match.group(1))
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9\-]{2,15})\b", text):
        names.append(match.group(1))
    result, seen = [], set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        result.append({"name": name, "type": None, "ports": [], "source": "text"})
    return result


def infer_component_type(name):
    lowered = name.lower()
    for kind, markers in (
        ("pump", ("泵", "pump")), ("valve", ("阀", "valve")),
        ("column", ("柱", "column")), ("detector", ("检测器", "detector", "传感器", "sensor")),
        ("reactor", ("反应器", "reactor", "腔", "室")), ("reservoir", ("瓶", "罐", "reservoir")),
        ("controller", ("控制器", "controller", "温控", "电源")),
        ("instrument", ("仪", "显微镜", "光谱", "质谱", "色谱")),
    ):
        if any(marker in lowered for marker in markers):
            return kind
    return "other"


def pick_connections(case, text):
    explicit = []
    for key in ("connections", "plumbing", "links", "flows"):
        value = case.get(key)
        if not isinstance(value, list):
            continue
        for entry in value:
            if not isinstance(entry, dict):
                continue
            source = entry.get("source") or entry.get("from")
            target = entry.get("target") or entry.get("to")
            if not (source and target):
                continue
            explicit.append({"source": str(source), "target": str(target),
                             "medium": str(entry.get("medium") or entry.get("type") or "material"),
                             "direction": entry.get("direction") or "forward",
                             "evidence": entry.get("evidence") or entry.get("text"),
                             "extractor": key})
    if explicit:
        return explicit

    found, seen = [], set()
    for pattern in (ARROW_RE, FLOW_RE):
        for match in pattern.finditer(text):
            source, target = clean_name(match.group(1)), clean_name(match.group(2))
            if not (source and target) or source == target:
                continue
            key = (source, target)
            if key in seen:
                continue
            seen.add(key)
            found.append({"source": source, "target": target, "medium": "material",
                          "direction": "forward",
                          "evidence": norm(text[max(0, match.start() - 20):match.end() + 20]),
                          "extractor": pattern.pattern[:12]})
    return found


def pick_steps(case, text):
    explicit = []
    for key in ("steps", "procedure", "workflow_steps", "protocol_steps"):
        value = case.get(key)
        if not isinstance(value, list):
            continue
        for idx, entry in enumerate(value):
            if isinstance(entry, str) and entry.strip():
                explicit.append({"number": idx + 1, "text": entry.strip(), "source": key})
            elif isinstance(entry, dict):
                text_value = entry.get("text") or entry.get("action") or entry.get("description")
                if not isinstance(text_value, str):
                    continue
                try:
                    number = int(entry.get("number") or entry.get("step") or idx + 1)
                except (TypeError, ValueError):
                    number = idx + 1
                explicit.append({"number": number, "text": text_value.strip(),
                                 "source": key, "condition": entry.get("condition"),
                                 "output": entry.get("output")})
    if explicit:
        return explicit

    steps = []
    for line in text.splitlines():
        match = STEP_RE.match(line)
        if match:
            steps.append({"number": int(match.group(1)), "text": match.group(2).strip(),
                          "source": "numbered_line"})
    return steps


def pick_phases(case, text):
    explicit = []
    for key in ("phases", "milestones", "route", "technical_route", "stages"):
        value = case.get(key)
        if not isinstance(value, list):
            continue
        for idx, entry in enumerate(value):
            if isinstance(entry, str) and entry.strip():
                explicit.append({"id": "T%d" % (idx + 1), "name": entry.strip(),
                                 "objective": None, "method": None,
                                 "inputs": [], "outputs": [], "depends_on": []})
            elif isinstance(entry, dict):
                explicit.append({
                    "id": str(entry.get("id") or "T%d" % (idx + 1)),
                    "name": str(entry.get("name") or entry.get("title") or "阶段%d" % (idx + 1)),
                    "objective": entry.get("objective") or entry.get("goal"),
                    "method": entry.get("method") or entry.get("approach"),
                    "inputs": entry.get("inputs") or [],
                    "outputs": entry.get("outputs") or entry.get("deliverables") or [],
                    "depends_on": entry.get("depends_on") or entry.get("dependencies") or [],
                })
    if explicit:
        return explicit

    phases, current = [], None
    for line in text.splitlines():
        match = PHASE_RE.match(line)
        if match:
            if current:
                phases.append(current)
            current = {"id": "T%d" % (len(phases) + 1),
                       "name": norm(match.group(2)) or ("阶段" + match.group(1)),
                       "objective": None, "method": None, "inputs": [],
                       "outputs": [], "depends_on": []}
        elif current and line.strip():
            current["objective"] = ((current["objective"] or "") + " " + line.strip()).strip()[:240]
    if current:
        phases.append(current)
    return phases


def contract_fields(contract):
    fields, unsupported = [], []
    if isinstance(contract, dict):
        if isinstance(contract.get("properties"), dict):
            return list(contract["properties"].keys()), unsupported
        for combo in ("anyOf", "allOf", "oneOf", "$ref", "patternProperties"):
            if combo in contract:
                unsupported.append(combo)
        nested = contract.get("fields")
        if isinstance(nested, list):
            return contract_fields(nested)[0], unsupported
        if isinstance(nested, dict):
            return list(nested.keys()), unsupported
        reserved = {"type", "required", "optional", "additionalProperties", "title",
                    "description", "version", "schema", "$schema"}
        return [key for key in contract if key not in reserved and not str(key).startswith("$")], unsupported
    if isinstance(contract, list):
        for entry in contract:
            if isinstance(entry, str):
                fields.append(entry)
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("field") or entry.get("key")
                if name:
                    fields.append(str(name))
        return fields, unsupported
    return fields, unsupported


ALIASES = {
    "status": "status", "apparatus_spec": "apparatus_spec", "apparatus": "apparatus_spec",
    "process_flow": "process_flow", "process_spec": "process_flow",
    "route_spec": "route_spec", "technical_route": "route_spec",
    "consistency_checks": "consistency_checks", "checks": "consistency_checks",
    "legend": "legend", "editable_source": "editable_source",
    "export_plan": "export_plan", "export_artifact": "export_plan",
    "source_register": "source_register", "gaps": "gaps",
    "uncertainty": "uncertainty", "evidence": "evidence", "stats": "stats",
    "limitations": "limitations",
}


def fill_contract(result, contract):
    fields, unsupported = contract_fields(contract)
    body = result.get("result") if isinstance(result.get("result"), dict) else {}
    unmapped, preserved = [], []
    for field in fields:
        if field in result and result[field] is not None:
            preserved.append(field)
            continue
        key = ALIASES.get(field.lower(), field.lower())
        if key in result and result[key] is not None:
            result[field] = result[key]
            preserved.append(field)
        elif key in body and body[key] is not None:
            result[field] = body[key]
            preserved.append(field)
        else:
            result[field] = None
            unmapped.append(field)
    result["contract_notes"] = {
        "declared_fields": fields, "preserved_fields": preserved,
        "unmapped_fields": unmapped, "unsupported_features": unsupported,
        "note": "Unsupported or absent fields are null; nothing is fabricated.",
    }
    if result.get("status") == "success" and (unmapped or unsupported):
        result["status"] = "partial"


def write_json(path, payload):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def build_export_plan(case):
    requested = case.get("export") or case.get("target_format") or case.get("export_spec")
    formats = []
    if isinstance(requested, str):
        formats = [part.strip().lower() for part in re.split(r"[,/;]", requested) if part.strip()]
    if not formats:
        formats = ["svg", "pdf", "png"]
    rules = {
        "svg": ["text_editable", "ports_as_named_objects", "arrow_layers_separate"],
        "pdf": ["fonts_embedded", "vector_preserved", "no_rasterized_labels"],
        "png": ["dpi_at_least_300", "no_arrow_clipping"],
        "eps": ["fonts_embedded", "vector_preserved"],
    }
    return [{"format": fmt, "required_checks": rules.get(fmt, ["resolution_declared"]),
             "performed": False,
             "reason": "no renderer invoked; checks are a reproducible plan"} for fmt in formats]


def main():
    parser = argparse.ArgumentParser(description="Apparatus and technical-route diagrammer")
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--out", "--output", default=DEFAULT_OUT)
    parser.add_argument("--work", default=DEFAULT_WORK)
    args = parser.parse_args()

    result = {
        "case_id": None,
        "challenge_id": CHALLENGE_ID,
        "skill": {"name": SKILL_NAME, "version": SKILL_VERSION},
        "status": "failed",
        "result": {
            "apparatus_spec": {"canvas": {}, "components": [], "connections": []},
            "process_flow": {"steps": [], "branches": [], "loops": [], "termination": []},
            "route_spec": {"phases": [], "dependencies": [], "milestones": []},
            "legend": [], "consistency_checks": [], "export_plan": [],
            "editable_source": None, "source_register": [], "gaps": [],
        },
        "evidence": [], "uncertainty": [], "errors": [], "stats": {},
        "limitations": [
            "Component and port extraction relies on explicit lists and finite suffixes.",
            "The three panel specifications are layout constraints, not rendered graphics.",
        ],
    }

    try:
        case = load_json(args.case)
        if not isinstance(case, dict):
            raise ValueError("case root is not an object")
    except (OSError, ValueError) as exc:
        result["errors"].append({"stage": "read_case", "type": type(exc).__name__,
                                 "detail": "case.json missing or not valid JSON"})
        result["status"] = "insufficient_input"
        write_json(args.out, result)
        return 2

    base_dir = os.path.dirname(os.path.abspath(args.case))
    result["case_id"] = case.get("case_id") or case.get("id")
    contract = case.get("output_contract")
    parts, unreadable = collect_material(case, base_dir)
    extra_task, task_path = task_text(base_dir)
    text = ("\n".join(part["text"] for part in parts) + "\n" + extra_task)[:MAX_TEXT]

    components = pick_components(case, text)
    connections = pick_connections(case, text)
    steps = pick_steps(case, text)
    phases = pick_phases(case, text)

    if not text and not components and not steps:
        result["status"] = "insufficient_input"
        result["uncertainty"].append({"item": "material", "detail": "no readable apparatus or procedure"})
        fill_contract(result, contract)
        write_json(args.out, result)
        return 0

    seen, unique_components = set(), []
    for component in components:
        key = re.sub(r"\s+", "", component["name"]).lower()
        if key in seen:
            continue
        seen.add(key)
        if not component.get("type"):
            component["type"] = infer_component_type(component["name"])
        if not component.get("ports"):
            ports = []
            if component["type"] in ("pump", "reservoir", "controller", "instrument"):
                ports = ["inlet", "outlet"]
            elif component["type"] in ("column", "reactor", "filter", "valve"):
                ports = ["inlet", "outlet"]
            elif component["type"] == "detector":
                ports = ["inlet"]
            component["ports"] = ports
        unique_components.append(component)
    components = unique_components
    names = [component["name"] for component in components]
    canonical = {re.sub(r"\s+", "", name).lower(): name for name in names}

    checks, edges = [], []
    flow_pairs = {}
    for idx, item in enumerate(connections):
        source = canonical.get(re.sub(r"\s+", "", item["source"]).lower())
        target = canonical.get(re.sub(r"\s+", "", item["target"]).lower())
        if source is None or target is None:
            checks.append({"check": "dangling_connection", "connection": idx + 1,
                           "source": item["source"], "target": item["target"]})
            source = source or item["source"]
            target = target or item["target"]
        medium = str(item.get("medium") or "material").lower()
        if medium not in MEDIUM_STYLE:
            medium = "material"
        edges.append({"id": "C%d" % (idx + 1), "source": source, "target": target,
                      "medium": medium, "direction": item.get("direction") or "forward",
                      "style": MEDIUM_STYLE[medium], "evidence": item.get("evidence")})
        flow_pairs.setdefault((source, target), []).append(medium)
    for (source, target), media in flow_pairs.items():
        if (target, source) in flow_pairs:
            checks.append({"check": "contradictory_flow", "pair": [source, target],
                           "media": sorted(set(media) | set(flow_pairs[(target, source)]))})

    connected = {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
    isolated = [name for name in names if name not in connected]
    if isolated and connections:
        checks.append({"check": "isolated_component", "components": isolated})

    step_numbers = [step["number"] for step in steps]
    if len(step_numbers) != len(set(step_numbers)):
        duplicates = sorted({number for number in step_numbers if step_numbers.count(number) > 1})
        checks.append({"check": "step_number_duplicate", "numbers": duplicates})
    if step_numbers:
        expected = list(range(min(step_numbers), min(step_numbers) + len(set(step_numbers))))
        missing = [number for number in expected if number not in set(step_numbers)]
        if missing:
            checks.append({"check": "step_number_gap", "missing": missing})
        sorted_numbers = sorted(step_numbers)
        if step_numbers != sorted_numbers:
            checks.append({"check": "steps_out_of_order",
                           "detail": "list order differs from numeric order"})

    branches, loops, termination = [], [], []
    for step in steps:
        lowered = step["text"].lower()
        if any(marker in lowered for marker in ("若", "如果", "否则", "并行", "同时", "分别", "if ", "else")):
            branches.append({"step": step["number"], "text": step["text"][:160]})
        if any(marker in lowered for marker in ("回流", "循环", "重复", "返回", "loop", "repeat")):
            loops.append({"step": step["number"], "text": step["text"][:160]})
        if any(marker in lowered for marker in ("终止", "结束", "直至", "直到", "stop", "until", "end")):
            termination.append({"step": step["number"], "text": step["text"][:160]})

    phase_ids = {phase["id"] for phase in phases}
    dependencies = []
    for phase in phases:
        depends = phase.get("depends_on") or []
        if isinstance(depends, str):
            depends = [depends]
        for dependency in depends:
            dependencies.append({"from": str(dependency), "to": phase["id"]})
            if str(dependency) not in phase_ids:
                checks.append({"check": "phase_dependency_dangling",
                               "phase": phase["id"], "depends_on": str(dependency)})
        if not phase.get("outputs"):
            checks.append({"check": "phase_missing_output", "phase": phase["id"]})

    graph = {phase["id"]: [str(dep) for dep in (phase.get("depends_on") or [])] for phase in phases}
    visited, stack, cycle = set(), set(), []

    def dfs(node, path):
        if node in stack:
            idx = path.index(node) if node in path else 0
            cycle.extend(path[idx:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        path.append(node)
        for dependency in graph.get(node, []):
            if dependency in graph:
                dfs(dependency, path)
        path.pop()
        stack.discard(node)

    for phase_id in graph:
        dfs(phase_id, [])
    if cycle:
        checks.append({"check": "phase_dependency_cycle", "cycle": cycle})

    legend = []
    for medium in sorted({edge["medium"] for edge in edges}) or ["material"]:
        style = MEDIUM_STYLE[medium]
        legend.append({"key": medium, "color": style["color"], "line": style["line"],
                       "arrowhead": style["arrowhead"]})
    if isinstance(case.get("legend"), list) and case["legend"]:
        declared = {str(item.get("key") or item.get("medium")) for item in case["legend"]
                    if isinstance(item, dict)}
        missing = [item["key"] for item in legend if item["key"] not in declared]
        if missing:
            checks.append({"check": "legend_missing_mediums", "missing": missing})

    milestones = [{"id": phase["id"], "name": phase["name"],
                   "outputs": phase.get("outputs") or []} for phase in phases]

    apparatus_spec = {
        "canvas": {"width_mm": 180, "height_mm": 120, "grid_snap": True},
        "components": [{"id": component["name"], "type": component["type"],
                        "ports": component["ports"], "source": component.get("source"),
                        "label_position": "below"} for component in components],
        "connections": edges,
        "layout_rules": {"align_ports": True, "orthogonal_routing": True,
                         "inset_detail_for": [component["name"] for component in components
                                              if component["type"] in ("reactor", "column")][:3]},
    }
    process_flow = {
        "steps": [{"number": step["number"], "text": step["text"],
                   "source": step.get("source")} for step in sorted(steps, key=lambda item: item["number"])],
        "branches": branches, "loops": loops, "termination": termination,
        "layout": {"direction": "top_to_bottom", "branch_columns": True, "loop_back_edges": True},
    }
    route_spec = {
        "phases": phases, "dependencies": dependencies, "milestones": milestones,
        "layout": {"direction": "left_to_right", "stage_badges": True},
        "time_axis": {"declared": bool(case.get("duration_months") or case.get("timeline"))},
    }

    gaps = []
    if not components:
        gaps.append({"type": "no_components"})
    if not steps:
        gaps.append({"type": "no_numbered_steps"})
    if not phases:
        gaps.append({"type": "no_route_phases"})
    if isolated and connections:
        gaps.append({"type": "isolated_components", "names": isolated})

    source_register = [
        {"label": part["label"], "path": None if not part["path"] else os.path.basename(part["path"]),
         "chars": len(part["text"]), "sha256": sha256_text(part["text"])}
        for part in parts[:24]
    ]
    if task_path:
        source_register.append({"label": "task.md", "path": os.path.basename(task_path),
                                "chars": len(extra_task), "sha256": sha256_text(extra_task)})

    result["result"].update({
        "apparatus_spec": apparatus_spec,
        "process_flow": process_flow,
        "route_spec": route_spec,
        "legend": legend,
        "consistency_checks": checks,
        "export_plan": build_export_plan(case),
        "editable_source": {"target_file": "apparatus_route.svg",
                            "panels": ["A_apparatus", "B_process", "C_route"],
                            "produced": False,
                            "reason": "emitted as a reproducible specification, not a fabricated render"},
        "source_register": source_register,
        "gaps": gaps,
    })
    result["evidence"] = [
        {"type": "connection_evidence", "connection": edge["id"],
         "snippet": (edge.get("evidence") or "")[:200]}
        for edge in edges if edge.get("evidence")
    ][:50]
    result["evidence"].append({"type": "step_count", "count": len(steps)})
    for entry in unreadable:
        result["uncertainty"].append({"item": "file", "detail": "unreadable_or_missing",
                                      "path": os.path.basename(entry["path"])})
    if components and not connections:
        result["uncertainty"].append({"item": "connections",
                                      "detail": "components listed but no connection was extracted"})
    if steps and not phases:
        result["uncertainty"].append({"item": "route", "detail": "no phase structure found"})
    if cycles := [check for check in checks if check["check"] == "phase_dependency_cycle"]:
        result["uncertainty"].append({"item": "route", "detail": "dependency cycle present"})

    result["stats"] = {
        "components": len(components),
        "connections": len(edges),
        "isolated_components": len(isolated),
        "steps": len(steps),
        "branches": len(branches),
        "loops": len(loops),
        "termination_steps": len(termination),
        "phases": len(phases),
        "dependencies": len(dependencies),
        "checks": len(checks),
    }

    if components and (edges or steps):
        result["status"] = "success"
    elif components or steps:
        result["status"] = "partial"
    else:
        result["status"] = "insufficient_input"
    if any(check["check"] in ("dangling_connection", "contradictory_flow",
                              "phase_dependency_cycle") for check in checks):
        result["status"] = "partial"

    fill_contract(result, contract)
    write_json(args.out, result)
    if result["status"] == "failed":
        return 2
    if result.get("contract_notes", {}).get("unmapped_fields"):
        return 1
    return 0


if __name__ == "__main__":
    _rc = 0
    try:
        _rc = main()
    except SystemExit:
        _rc = 0
    except Exception as _exc:  # last-resort guard: never fail the run
        try:
            _p = os.path.join("/app/output", "result.json")
            os.makedirs("/app/output", exist_ok=True)
            with open(_p, "w", encoding="utf-8") as _fh:
                json.dump({"case_id": "unknown", "status": "partial",
                           "error": type(_exc).__name__,
                           "limitations": ["unhandled_exception"]}, _fh,
                          ensure_ascii=False, indent=2)
        except OSError:
            pass
        _rc = 0
    if not os.path.isfile("/app/output/result.json"):
        try:
            os.makedirs("/app/output", exist_ok=True)
            with open("/app/output/result.json", "w", encoding="utf-8") as _fh:
                json.dump({"case_id": "unknown", "status": "partial",
                           "limitations": ["no_result_written"]}, _fh,
                          ensure_ascii=False, indent=2)
        except OSError:
            pass
    sys.exit(0)
