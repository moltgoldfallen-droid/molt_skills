#!/usr/bin/env python3
"""SkillGraph builder.

Scans SKILL.md files, generates graph_data.json + index.html,
and stores them under ~/.openclaw/workspace/skillgraph.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "skillgraph"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_JSON = OUTPUT_DIR / "graph_data.json"
GRAPH_HTML = OUTPUT_DIR / "index.html"
TEMPLATE_PATH = Path(__file__).with_name("template.html")

SKILL_DISCOVERY_PATHS = [
    Path("~/openclaw-projects/skills/").expanduser(),
    Path("~/.openclaw/workspace/skills/").expanduser(),
    Path("~/.openclaw/skills/").expanduser(),
    Path("/mnt/skills/user/").expanduser(),
    Path("/mnt/skills/private/").expanduser(),
    Path("/mnt/skills/public/").expanduser(),
    Path("/mnt/skills/examples/").expanduser(),
]

CATEGORY_RULES = {
    "Knowledge & Research": {
        "color": "#4CAF50",
        "glow": "#81C784",
        "keywords": [
            "research",
            "knowledge",
            "news",
            "feed",
            "rss",
            "arxiv",
            "summary",
            "briefing",
            "intelligence",
            "analysis",
            "report",
            "documentation",
            "wiki",
            "search",
            "scraping",
        ],
    },
    "Automation": {
        "color": "#FF9800",
        "glow": "#FFB74D",
        "keywords": [
            "automation",
            "cron",
            "scheduler",
            "workflow",
            "n8n",
            "pipeline",
            "bot",
            "trigger",
            "webhook",
            "sync",
            "backup",
            "deploy",
            "ci",
            "cd",
            "monitor",
        ],
    },
    "Finance": {
        "color": "#FFC107",
        "glow": "#FFD54F",
        "keywords": [
            "finance",
            "stock",
            "trading",
            "invest",
            "portfolio",
            "valuation",
            "dcf",
            "earnings",
            "sec",
            "edgar",
            "market",
            "price",
            "dividend",
            "expense",
            "budget",
        ],
    },
    "Health & Wellness": {
        "color": "#E91E63",
        "glow": "#F48FB1",
        "keywords": [
            "health",
            "fitness",
            "exercise",
            "habit",
            "wellness",
            "nutrition",
            "calorie",
            "sleep",
            "meditation",
            "martial",
            "pose",
            "biomechanics",
            "training",
            "coach",
        ],
    },
    "Security": {
        "color": "#F44336",
        "glow": "#EF9A9A",
        "keywords": [
            "security",
            "encryption",
            "password",
            "auth",
            "vault",
            "backup",
            "firewall",
            "vpn",
            "tailscale",
            "ssh",
        ],
    },
    "Communication": {
        "color": "#2196F3",
        "glow": "#64B5F6",
        "keywords": [
            "telegram",
            "slack",
            "email",
            "gmail",
            "imessage",
            "notification",
            "message",
            "chat",
            "sms",
            "discord",
        ],
    },
    "Creative": {
        "color": "#9C27B0",
        "glow": "#CE93D8",
        "keywords": [
            "image",
            "video",
            "audio",
            "music",
            "design",
            "generate",
            "creative",
            "art",
            "writing",
            "content",
        ],
    },
    "Productivity": {
        "color": "#00BCD4",
        "glow": "#4DD0E1",
        "keywords": [
            "productivity",
            "task",
            "todo",
            "calendar",
            "reminder",
            "planner",
            "time",
            "focus",
            "pomodoro",
            "note",
        ],
    },
    "Development": {
        "color": "#8BC34A",
        "glow": "#AED581",
        "keywords": [
            "code",
            "coding",
            "git",
            "github",
            "docker",
            "deploy",
            "test",
            "debug",
            "api",
            "sdk",
            "dev",
        ],
    },
    "System": {
        "color": "#607D8B",
        "glow": "#90A4AE",
        "keywords": [
            "system",
            "config",
            "setup",
            "install",
            "update",
            "gpu",
            "hardware",
            "server",
            "infrastructure",
        ],
    },
}


def load_template() -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing template.html at {TEMPLATE_PATH}")
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def extract_frontmatter(content: str) -> (Dict, str):
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        body = content[match.end():]
        return frontmatter, body
    return {}, content


def extract_list(body: str, patterns: List[str], limit: int = 8) -> List[str]:
    for pattern in patterns:
        regex = rf"(?:{pattern})[:\s]*\n((?:\s*[-*•]\s*.+\n)+)"
        match = re.search(regex, body, re.IGNORECASE)
        if match:
            items = re.findall(r"[-*•]\s*(.+)", match.group(1))
            return [i.strip().strip('"\'') for i in items[:limit]]
    return []


def classify(name: str, description: str, body: str) -> Dict[str, str]:
    combined = (name + " " + description + " " + body[:3000]).lower()
    best = ("System", 0)
    for cat, info in CATEGORY_RULES.items():
        score = sum(1 for kw in info["keywords"] if kw in combined)
        if score > best[1]:
            best = (cat, score)
    cat = CATEGORY_RULES.get(best[0], CATEGORY_RULES["System"])
    return {"name": best[0], "color": cat["color"], "glow": cat["glow"]}


def extract_version(frontmatter: Dict, body: str) -> str:
    if "version" in frontmatter:
        return str(frontmatter["version"])
    match = re.search(r"v(\d+\.\d+(?:\.\d+)?)", body[:2000])
    return match.group(0) if match else "v1.0"


def extract_crons(body: str) -> List[str]:
    crons = []
    for match in re.finditer(r"(?:cron|schedule)[^\"']*?['\"](\d[\d\s*/,-]+)['\"]", body, re.IGNORECASE):
        crons.append(match.group(1))
    for match in re.finditer(r"(\w[\w_]+):\s*['\"](\d[\d\s*/,-]+)['\"]", body):
        crons.append(f"{match.group(1)}: {match.group(2)}")
    return crons[:10]


def extract_tech(body: str) -> List[str]:
    tech = set()
    for match in re.finditer(r"pip install\s+([^\n]+)", body):
        for pkg in match.group(1).split():
            if not pkg.startswith("-"):
                tech.add(pkg.split("==")[0].split(">=")[0].lower())
    for match in re.finditer(r"(?:from|import)\s+([\w.]+)", body):
        module = match.group(1).split(".")[0].lower()
        if module not in {"os", "sys", "json", "re", "math", "datetime", "pathlib"}:
            tech.add(module)
    return list(tech)[:15]


def extract_dependencies(body: str, self_id: str) -> List[str]:
    deps = set()
    for match in re.finditer(r"read_from_(\w+)|feed(?:s|ing)?[_\s]*(?:into|to)[_\s]*(\w+)", body, re.IGNORECASE):
        dep = (match.group(1) or match.group(2) or "").lower().replace("_", "-")
        if dep and dep != self_id:
            deps.add(dep)
    known = [p.name for path in SKILL_DISCOVERY_PATHS if path.exists() for p in path.iterdir() if p.is_dir()]
    body_lower = body.lower()
    for skill in known:
        for variant in [skill, skill.replace("-", "_"), skill.replace("-", " ")]:
            if variant and variant in body_lower and skill != self_id:
                deps.add(skill)
    return sorted(deps)


def calc_health(content: str, stat, capabilities: List[str], gaps: List[str]) -> int:
    score = 0
    size = stat.st_size
    if size > 500:
        score += 20
    if size > 3000:
        score += 10
    if len(capabilities) >= 3:
        score += 20
    if gaps:
        score += 15
    days_old = (datetime.now().timestamp() - stat.st_mtime) / 86400
    if days_old < 7:
        score += 20
    elif days_old < 30:
        score += 10
    if "cron" in content.lower() or "schedule" in content.lower():
        score += 15
    return min(score, 100)


def parse_skill(skill_file: Path, skill_id: str, source_dir: str) -> Optional[Dict]:
    content = read_file(skill_file)
    if content is None:
        return None
    frontmatter, body = extract_frontmatter(content)
    stat = skill_file.stat()

    name = frontmatter.get("name", skill_id)
    description = frontmatter.get("description", "")
    if isinstance(description, str):
        description = description.strip()[:300]
    else:
        description = str(description)[:300]

    category = classify(name, description, body)
    tech = extract_tech(body)
    capabilities = extract_list(body, ["capabilities", "features", "current.?capabilities"])
    gaps = extract_list(body, ["known.?gaps", "limitations", "known.?issues", "todo"])
    deps = extract_dependencies(body, skill_id)
    crons = extract_crons(body)
    version = extract_version(frontmatter, body)
    health = calc_health(content, stat, capabilities, gaps)

    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "category": category["name"],
        "color": category["color"],
        "glow": category["glow"],
        "version": version,
        "tech_stack": tech,
        "capabilities": capabilities[:6],
        "known_gaps": gaps[:6],
        "dependencies": deps,
        "cron_schedules": crons,
        "health": health,
        "source_dir": source_dir,
        "file_size": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "line_count": content.count("\n"),
    }


def discover_skills() -> List[Dict]:
    skills: List[Dict] = []
    seen = set()
    for base in SKILL_DISCOVERY_PATHS:
        if not base.exists():
            continue
        for child in base.iterdir():
            if not child.is_dir():
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.exists():
                continue
            skill_id = child.name
            if skill_id in seen:
                continue
            parsed = parse_skill(skill_file, skill_id, str(base))
            if parsed:
                skills.append(parsed)
                seen.add(skill_id)
    return skills


def generate_graph(skills: List[Dict]) -> Dict:
    ids = {s["id"] for s in skills}
    nodes = []
    edges = []
    for skill in skills:
        size = max(15, min(60, skill["file_size"] / 500 + len(skill["capabilities"]) * 5))
        node = dict(skill)
        node["size"] = size
        nodes.append(node)
        for dep in skill["dependencies"]:
            if dep in ids:
                edges.append({"source": skill["id"], "target": dep, "type": "dependency"})
    categories: Dict[str, Dict] = {}
    for skill in skills:
        cat = skill["category"]
        if cat not in categories:
            categories[cat] = {"name": cat, "color": skill["color"], "count": 0}
        categories[cat]["count"] += 1
    return {
        "nodes": nodes,
        "edges": edges,
        "categories": list(categories.values()),
        "meta": {
            "total_skills": len(nodes),
            "total_edges": len(edges),
            "generated_at": datetime.now().isoformat(),
            "scan_paths": [str(p) for p in SKILL_DISCOVERY_PATHS],
        },
    }


def build_dashboard():
    template = load_template()
    skills = discover_skills()
    graph = generate_graph(skills)
    GRAPH_JSON.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    html = template.replace("__GRAPH_DATA_JSON__", json.dumps(graph))
    GRAPH_HTML.write_text(html, encoding="utf-8")
    print(f"Generated graph for {len(skills)} skills -> {GRAPH_HTML}")


if __name__ == "__main__":
    try:
        build_dashboard()
    except KeyboardInterrupt:
        sys.exit(1)
