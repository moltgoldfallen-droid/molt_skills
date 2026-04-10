---
name: skillgraph
description: >
  Self-introspecting OpenClaw skill visualization dashboard that scans all installed
  skills, maps their dependencies, categories, versions, and metadata, then renders
  an interactive force-directed node graph served as a local web dashboard. Inspired
  by Muse's Skill Evolution Graph. Auto-generates from live SKILL.md files — no
  manual data entry. Includes category color-coding, dependency edges, version
  history timeline, skill detail panel, search/filter, and health status indicators.
  Served via Python HTTP on the Mac Mini, accessible via browser or Tailscale.
  Updates on demand or via daily cron. This skill should be used whenever the agent
  needs to visualize the skill ecosystem, audit installed skills, check skill health
  or dependencies, generate a skill inventory report, or provide a dashboard view
  of all active OpenClaw capabilities.
---

# SkillGraph — OpenClaw Skill Evolution Dashboard

## Purpose

You are a self-introspecting visualization agent. Your job is to scan every installed
OpenClaw skill across all known directories, extract structured metadata from each
SKILL.md, map the relationships between skills, and render an interactive
force-directed graph as a local web dashboard. This gives Keng a single visual
overview of his entire OpenClaw ecosystem — what's installed, what's active, what
depends on what, and what needs attention.

**Design Reference:** Muse's Skill Evolution Graph (技能演化) — dark theme, glowing
colored nodes sized by importance, category-based coloring, dependency edges,
detail panel on click, search/filter sidebar.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   SkillGraph Agent                     │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Step 1: DISCOVER                                 │ │
│  │  Scan all skill directories for SKILL.md files    │ │
│  │  Parse YAML frontmatter + markdown body           │ │
│  │  Extract: name, description, category, version,   │ │
│  │  tech stack, capabilities, gaps, dependencies     │ │
│  └──────────────────────┬───────────────────────────┘ │
│                         │                              │
│  ┌──────────────────────▼───────────────────────────┐ │
│  │  Step 2: ANALYZE                                  │ │
│  │  Map cross-skill dependencies (config references, │ │
│  │  import patterns, data flow declarations)         │ │
│  │  Classify into categories                         │ │
│  │  Calculate health score per skill                 │ │
│  │  Detect version from changelog or git             │ │
│  └──────────────────────┬───────────────────────────┘ │
│                         │                              │
│  ┌──────────────────────▼───────────────────────────┐ │
│  │  Step 3: GENERATE                                 │ │
│  │  Output graph_data.json (nodes + edges)           │ │
│  │  Render index.html with D3.js force-directed      │ │
│  │  graph, detail panel, search, filters             │ │
│  └──────────────────────┬───────────────────────────┘ │
│                         │                              │
│  ┌──────────────────────▼───────────────────────────┐ │
│  │  Step 4: SERVE                                    │ │
│  │  Python HTTP server on port 18800                 │ │
│  │  Accessible via localhost or Tailscale            │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## Step 1: Skill Discovery

Scan all known OpenClaw skill directories. Same discovery paths used by TechPulse
Daily's integration radar, extended with additional common locations.

```python
import os
import re
import yaml
import json
import hashlib
from pathlib import Path
from datetime import datetime

SKILL_DISCOVERY_PATHS = [
    Path("~/openclaw-projects/skills/"),
    Path("~/.openclaw/workspace/skills/"),
    Path("~/.openclaw/skills/"),
    Path("/mnt/skills/user/"),
    Path("/mnt/skills/private/"),
    Path("/mnt/skills/public/"),
    Path("/mnt/skills/examples/"),
]

# ─────────────────────────────────────────────
# CATEGORY DETECTION
# ─────────────────────────────────────────────
# Categories and their color assignments (matching Muse's palette)

CATEGORY_RULES = {
    "Knowledge & Research": {
        "color": "#4CAF50",       # Green
        "glow": "#81C784",
        "keywords": [
            "research", "knowledge", "news", "feed", "rss", "arxiv",
            "summary", "briefing", "intelligence", "analysis", "report",
            "documentation", "wiki", "search", "scraping",
        ],
    },
    "Automation": {
        "color": "#FF9800",       # Orange
        "glow": "#FFB74D",
        "keywords": [
            "automation", "cron", "scheduler", "workflow", "n8n",
            "pipeline", "bot", "trigger", "webhook", "sync",
            "backup", "deploy", "ci", "cd", "monitor",
        ],
    },
    "Finance": {
        "color": "#FFC107",       # Amber/Yellow
        "glow": "#FFD54F",
        "keywords": [
            "finance", "stock", "trading", "invest", "portfolio",
            "valuation", "dcf", "earnings", "SEC", "edgar",
            "market", "price", "dividend", "expense", "budget",
        ],
    },
    "Health & Wellness": {
        "color": "#E91E63",       # Pink
        "glow": "#F48FB1",
        "keywords": [
            "health", "fitness", "exercise", "habit", "wellness",
            "nutrition", "calorie", "sleep", "meditation", "martial",
            "pose", "biomechanics", "training", "coach",
        ],
    },
    "Security": {
        "color": "#F44336",       # Red
        "glow": "#EF9A9A",
        "keywords": [
            "security", "encryption", "password", "auth", "vault",
            "backup", "firewall", "vpn", "tailscale", "ssh",
        ],
    },
    "Communication": {
        "color": "#2196F3",       # Blue
        "glow": "#64B5F6",
        "keywords": [
            "telegram", "slack", "email", "gmail", "imessage",
            "notification", "message", "chat", "sms", "discord",
        ],
    },
    "Creative": {
        "color": "#9C27B0",       # Purple
        "glow": "#CE93D8",
        "keywords": [
            "image", "video", "audio", "music", "design",
            "generate", "creative", "art", "writing", "content",
        ],
    },
    "Productivity": {
        "color": "#00BCD4",       # Cyan
        "glow": "#4DD0E1",
        "keywords": [
            "productivity", "task", "todo", "calendar", "reminder",
            "planner", "time", "focus", "pomodoro", "note",
        ],
    },
    "Development": {
        "color": "#8BC34A",       # Light Green
        "glow": "#AED581",
        "keywords": [
            "code", "coding", "git", "github", "docker",
            "deploy", "test", "debug", "api", "sdk", "dev",
        ],
    },
    "System": {
        "color": "#607D8B",       # Blue Grey
        "glow": "#90A4AE",
        "keywords": [
            "system", "config", "setup", "install", "update",
            "gpu", "hardware", "server", "infrastructure",
        ],
    },
}


def discover_all_skills():
    """
    Scan all directories for SKILL.md files.
    Returns list of raw skill data dicts.
    """
    skills = []
    seen_ids = set()

    for base_path in SKILL_DISCOVERY_PATHS:
        expanded = base_path.expanduser()
        if not expanded.exists():
            continue

        # Direct children that are directories with SKILL.md
        for skill_dir in expanded.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            skill_id = skill_dir.name
            if skill_id in seen_ids:
                continue
            seen_ids.add(skill_id)

            skill_data = parse_skill(skill_file, skill_id, str(expanded))
            if skill_data:
                skills.append(skill_data)

    return skills


def parse_skill(skill_file, skill_id, source_dir):
    """
    Extract all metadata from a single SKILL.md.
    Returns a structured dict for the graph node.
    """
    content = skill_file.read_text(encoding='utf-8', errors='replace')
    stat = skill_file.stat()

    # ── YAML frontmatter ──
    frontmatter = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        try:
            frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            pass

    body = content[fm_match.end():] if fm_match else content

    name = frontmatter.get('name', skill_id)
    description = frontmatter.get('description', '')
    if isinstance(description, str):
        description = description.strip()[:300]
    else:
        description = str(description)[:300]

    # ── Extract metadata ──
    tech_stack = extract_tech_stack(body)
    capabilities = extract_list_section(body, [
        'capabilities', 'features', 'current.?capabilities',
    ])
    known_gaps = extract_list_section(body, [
        'known.?gaps', 'limitations', 'known.?issues', 'todo',
    ])
    version = extract_version(body, frontmatter)
    category = classify_category(name, description, body)
    dependencies = extract_dependencies(body, skill_id)
    cron_schedules = extract_cron_schedules(body)
    health = calculate_health(content, stat, capabilities, known_gaps)

    return {
        'id': skill_id,
        'name': name,
        'description': description,
        'category': category['name'],
        'color': category['color'],
        'glow': category['glow'],
        'version': version,
        'tech_stack': tech_stack,
        'capabilities': capabilities[:6],
        'known_gaps': known_gaps[:6],
        'dependencies': dependencies,
        'cron_schedules': cron_schedules,
        'health': health,
        'source_dir': source_dir,
        'file_size': stat.st_size,
        'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'line_count': content.count('\n'),
    }
```

### Helper Functions

```python
def extract_tech_stack(body):
    """Extract tech from pip install lines, imports, and platform keywords."""
    tech = set()
    for match in re.finditer(r'pip install\s+([^\n]+)', body):
        for pkg in match.group(1).split():
            if not pkg.startswith('-') and len(pkg) > 2:
                tech.add(pkg.split('==')[0].split('>=')[0].lower())
    for match in re.finditer(r'(?:from|import)\s+([\w.]+)', body):
        module = match.group(1).split('.')[0].lower()
        if module not in ('os', 'sys', 'json', 're', 'math', 'datetime', 'pathlib'):
            tech.add(module)
    return list(tech)[:15]


def extract_list_section(body, patterns):
    """Extract bullet-list items from sections matching given header patterns."""
    items = []
    for pat in patterns:
        regex = rf'(?:{pat})[:\s]*\n((?:\s*[-*•]\s*.+\n)+)'
        match = re.search(regex, body, re.IGNORECASE)
        if match:
            found = re.findall(r'[-*•]\s*(.+)', match.group(1))
            items.extend([i.strip().strip('"\'') for i in found[:8]])
            break
    return items


def extract_version(body, frontmatter):
    """Detect version from frontmatter, changelog headers, or filename patterns."""
    if 'version' in frontmatter:
        return str(frontmatter['version'])
    ver_match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', body[:2000])
    if ver_match:
        return ver_match.group(0)
    return "v1.0"


def classify_category(name, description, body):
    """Score each category by keyword hits, return the best match."""
    combined = (name + ' ' + description + ' ' + body[:3000]).lower()
    best_cat = "System"
    best_score = 0

    for cat_name, cat_info in CATEGORY_RULES.items():
        score = sum(1 for kw in cat_info['keywords'] if kw in combined)
        if score > best_score:
            best_score = score
            best_cat = cat_name

    cat = CATEGORY_RULES.get(best_cat, CATEGORY_RULES["System"])
    return {'name': best_cat, 'color': cat['color'], 'glow': cat['glow']}


def extract_dependencies(body, self_id):
    """
    Detect dependencies between skills by scanning for:
    - Explicit cross-project references (e.g., "read_from_value_radar")
    - Import-like references to other skill names
    - Data flow declarations ("feeds into", "pulls from")
    """
    deps = []
    # Pattern: read_from_{skill}, feed_to_{skill}
    for match in re.finditer(r'read_from_(\w+)|feed[s_]*(?:into|to)[\s_]*(\w+)', body, re.I):
        dep = (match.group(1) or match.group(2)).lower().replace('_', '-')
        if dep != self_id:
            deps.append(dep)

    # Pattern: "from {SkillName}" or "via {SkillName}" in prose
    known_skills = [
        'lifeos-mentor', 'value-radar', 'smartflow-trader',
        'form-sensei', 'techpulse-daily', 'skillgraph',
    ]
    body_lower = body.lower()
    for skill in known_skills:
        variants = [skill, skill.replace('-', '_'), skill.replace('-', ' ')]
        if any(v in body_lower for v in variants) and skill != self_id:
            if skill not in deps:
                deps.append(skill)

    return list(set(deps))


def extract_cron_schedules(body):
    """Find cron schedule definitions."""
    schedules = []
    for match in re.finditer(
        r'(?:cron|trigger|schedule)[^"]*?["\'](\d[\d\s*/,-]+)["\']',
        body, re.I
    ):
        schedules.append(match.group(1).strip())
    # Also match labeled cron entries
    for match in re.finditer(
        r'(\w[\w_]+):\s*["\'](\d[\d\s*/,-]+)["\']',
        body
    ):
        schedules.append(f"{match.group(1)}: {match.group(2)}")
    return schedules[:10]


def calculate_health(content, stat, capabilities, known_gaps):
    """
    Health score (0-100) based on:
    - File size (>500 bytes = has content)
    - Has capabilities defined
    - Has known_gaps defined (self-awareness = good)
    - Recent modification (< 30 days)
    - Has cron schedules (active, not dormant)
    """
    score = 0
    if stat.st_size > 500:
        score += 20
    if stat.st_size > 3000:
        score += 10
    if len(capabilities) >= 3:
        score += 20
    if len(known_gaps) >= 1:
        score += 15  # Self-awareness bonus
    days_old = (datetime.now().timestamp() - stat.st_mtime) / 86400
    if days_old < 7:
        score += 20
    elif days_old < 30:
        score += 10
    if 'cron' in content.lower() or 'schedule' in content.lower():
        score += 15

    return min(score, 100)
```

---

## Step 2: Generate Graph Data

```python
def generate_graph_data(skills):
    """
    Convert skill list into D3.js-compatible graph JSON.
    Nodes = skills, Edges = dependencies.
    """
    nodes = []
    edges = []
    skill_ids = {s['id'] for s in skills}

    for skill in skills:
        # Node size based on file size + capabilities count
        size = max(15, min(60, skill['file_size'] / 500 + len(skill['capabilities']) * 5))

        nodes.append({
            'id': skill['id'],
            'name': skill['name'],
            'description': skill['description'],
            'category': skill['category'],
            'color': skill['color'],
            'glow': skill['glow'],
            'version': skill['version'],
            'size': size,
            'tech_stack': skill['tech_stack'],
            'capabilities': skill['capabilities'],
            'known_gaps': skill['known_gaps'],
            'cron_schedules': skill['cron_schedules'],
            'health': skill['health'],
            'source_dir': skill['source_dir'],
            'last_modified': skill['last_modified'],
            'line_count': skill['line_count'],
        })

        # Edges from dependencies
        for dep in skill['dependencies']:
            if dep in skill_ids:
                edges.append({
                    'source': skill['id'],
                    'target': dep,
                    'type': 'dependency',
                })

    # Category summary for legend
    categories = {}
    for skill in skills:
        cat = skill['category']
        if cat not in categories:
            categories[cat] = {
                'name': cat,
                'color': skill['color'],
                'count': 0,
            }
        categories[cat]['count'] += 1

    return {
        'nodes': nodes,
        'edges': edges,
        'categories': list(categories.values()),
        'meta': {
            'total_skills': len(skills),
            'total_edges': len(edges),
            'generated_at': datetime.now().isoformat(),
            'scan_paths': [str(p) for p in SKILL_DISCOVERY_PATHS],
        },
    }
```

---

## Step 3: HTML Dashboard (D3.js Force-Directed Graph)

The dashboard is a single self-contained HTML file. No build step, no npm, no
frameworks — just HTML + CSS + D3.js loaded from CDN.

**Design Spec (matching Muse's aesthetic):**

- **Background:** Deep black (#0a0a0a) with subtle grid texture
- **Nodes:** Circular, colored by category, with outer glow effect
- **Node size:** Proportional to skill complexity (file size + capabilities)
- **Edges:** Thin curved lines with slight opacity, colored gradient between source/target
- **Hover:** Node scales up, glow intensifies, tooltip shows name + category
- **Click:** Opens right-side detail panel with full metadata
- **Left sidebar:** Skill list grouped by category, with search filter
- **Legend:** Category colors with counts
- **Physics:** D3 force simulation with collision detection, adjustable charge

```python
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦞 SkillGraph — OpenClaw Skill Evolution</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;600;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg-primary: #0a0a0a;
    --bg-secondary: #111111;
    --bg-panel: #161616;
    --bg-card: #1a1a1a;
    --border: #2a2a2a;
    --text-primary: #e0e0e0;
    --text-secondary: #888888;
    --text-muted: #555555;
    --accent: #ff6b35;
    --accent-glow: rgba(255, 107, 53, 0.3);
  }

  body {
    font-family: 'Outfit', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    overflow: hidden;
    height: 100vh;
    display: flex;
  }

  /* ── LEFT SIDEBAR ── */
  #sidebar {
    width: 260px;
    min-width: 260px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 16px 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  #sidebar h1 {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  #search-box {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    outline: none;
  }
  #search-box:focus { border-color: var(--accent); }
  #search-box::placeholder { color: var(--text-muted); }

  .category-group { margin-top: 4px; }
  .category-header {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    padding: 6px 0;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
  .category-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .category-count {
    margin-left: auto;
    font-size: 10px;
    color: var(--text-muted);
  }

  .skill-item {
    font-size: 13px;
    padding: 5px 8px 5px 20px;
    cursor: pointer;
    border-radius: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-secondary);
    transition: all 0.15s;
  }
  .skill-item:hover {
    background: var(--bg-card);
    color: var(--text-primary);
  }
  .skill-item.active {
    background: rgba(255, 107, 53, 0.15);
    color: var(--accent);
  }
  .skill-version {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text-muted);
    float: right;
  }

  /* ── MAIN GRAPH AREA ── */
  #graph-container {
    flex: 1;
    position: relative;
    overflow: hidden;
  }
  #graph-container svg { width: 100%; height: 100%; }

  /* Node glow filter — applied via SVG defs */
  .node-circle {
    cursor: pointer;
    transition: r 0.2s;
  }
  .node-circle:hover { filter: brightness(1.3); }
  .node-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    fill: var(--text-secondary);
    pointer-events: none;
    text-anchor: middle;
  }
  .edge-line {
    stroke-opacity: 0.25;
    fill: none;
  }
  .edge-line:hover { stroke-opacity: 0.6; }

  /* ── META BAR (bottom) ── */
  #meta-bar {
    position: absolute;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(22, 22, 22, 0.9);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    display: flex;
    gap: 24px;
    backdrop-filter: blur(8px);
  }
  #meta-bar span { color: var(--text-secondary); }

  /* ── RIGHT DETAIL PANEL ── */
  #detail-panel {
    width: 340px;
    min-width: 340px;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    overflow-y: auto;
    padding: 20px 16px;
    display: none;
    flex-direction: column;
    gap: 16px;
  }
  #detail-panel.open { display: flex; }

  #detail-close {
    position: absolute;
    top: 12px;
    right: 12px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 18px;
    cursor: pointer;
  }

  .detail-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .detail-name {
    font-size: 20px;
    font-weight: 700;
  }
  .detail-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
  }
  .detail-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
  }
  .health-bar {
    height: 6px;
    background: var(--bg-card);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 4px;
  }
  .health-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s;
  }

  .detail-section-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin-top: 8px;
  }
  .detail-description {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
  }
  .tag {
    display: inline-block;
    padding: 2px 8px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-secondary);
    margin: 2px 3px 2px 0;
  }
  .detail-list {
    list-style: none;
    padding: 0;
  }
  .detail-list li {
    font-size: 12px;
    color: var(--text-secondary);
    padding: 3px 0;
    border-bottom: 1px solid var(--border);
  }
  .detail-list li:last-child { border: none; }
  .detail-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
  }
</style>
</head>
<body>

<!-- LEFT SIDEBAR -->
<div id="sidebar">
  <h1>🦞 SkillGraph</h1>
  <input id="search-box" type="text" placeholder="Search skills...">
  <div id="skill-list"></div>
</div>

<!-- MAIN GRAPH -->
<div id="graph-container">
  <svg id="graph-svg"></svg>
  <div id="meta-bar">
    <div>Skills: <span id="meta-total">0</span></div>
    <div>Edges: <span id="meta-edges">0</span></div>
    <div>Categories: <span id="meta-cats">0</span></div>
    <div>Generated: <span id="meta-time">—</span></div>
  </div>
</div>

<!-- RIGHT DETAIL PANEL -->
<div id="detail-panel">
  <div id="detail-content"></div>
</div>

<script>
// ── GRAPH DATA (injected by Python at generation time) ──
const GRAPH_DATA = __GRAPH_DATA_JSON__;

// ── RENDER SIDEBAR ──
function renderSidebar(data) {
  const list = document.getElementById('skill-list');
  const grouped = {};
  data.nodes.forEach(n => {
    if (!grouped[n.category]) grouped[n.category] = [];
    grouped[n.category].push(n);
  });

  let html = '';
  Object.entries(grouped).sort((a, b) => b[1].length - a[1].length).forEach(([cat, skills]) => {
    const color = skills[0].color;
    html += '<div class="category-group">';
    html += '<div class="category-header">';
    html += '<span class="category-dot" style="background:' + color + '"></span>';
    html += cat;
    html += '<span class="category-count">(' + skills.length + ')</span>';
    html += '</div>';
    skills.sort((a, b) => a.name.localeCompare(b.name)).forEach(s => {
      html += '<div class="skill-item" data-id="' + s.id + '" onclick="selectNode(\'' + s.id + '\')">';
      html += s.name;
      html += '<span class="skill-version">' + s.version + '</span>';
      html += '</div>';
    });
    html += '</div>';
  });
  list.innerHTML = html;
}

// ── RENDER DETAIL PANEL ──
function showDetail(node) {
  const panel = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');
  panel.classList.add('open');

  const healthColor = node.health >= 70 ? '#4CAF50' : node.health >= 40 ? '#FF9800' : '#F44336';

  let html = '';
  html += '<div class="detail-header">';
  html += '<span class="category-dot" style="background:' + node.color + ';width:12px;height:12px"></span>';
  html += '<span class="detail-name">' + node.name + '</span>';
  html += '</div>';
  html += '<div class="detail-id">' + node.id + ' · ' + node.version + '</div>';
  html += '<div class="detail-badge" style="background:' + node.color + '22;color:' + node.color + '">' + node.category + '</div>';

  html += '<div class="detail-section-title">Health</div>';
  html += '<div class="health-bar"><div class="health-fill" style="width:' + node.health + '%;background:' + healthColor + '"></div></div>';
  html += '<div class="detail-meta">' + node.health + '/100</div>';

  html += '<div class="detail-section-title">Description</div>';
  html += '<div class="detail-description">' + node.description + '</div>';

  if (node.tech_stack.length) {
    html += '<div class="detail-section-title">Tech Stack</div>';
    html += '<div>' + node.tech_stack.map(t => '<span class="tag">' + t + '</span>').join('') + '</div>';
  }

  if (node.capabilities.length) {
    html += '<div class="detail-section-title">Capabilities</div>';
    html += '<ul class="detail-list">' + node.capabilities.map(c => '<li>✓ ' + c + '</li>').join('') + '</ul>';
  }

  if (node.known_gaps.length) {
    html += '<div class="detail-section-title">Known Gaps</div>';
    html += '<ul class="detail-list">' + node.known_gaps.map(g => '<li>⚠ ' + g + '</li>').join('') + '</ul>';
  }

  if (node.cron_schedules.length) {
    html += '<div class="detail-section-title">Cron Schedules</div>';
    html += '<ul class="detail-list">' + node.cron_schedules.map(c => '<li>⏰ ' + c + '</li>').join('') + '</ul>';
  }

  html += '<div class="detail-section-title">Meta</div>';
  html += '<div class="detail-meta">';
  html += 'Source: ' + node.source_dir + '<br>';
  html += 'Lines: ' + node.line_count + '<br>';
  html += 'Modified: ' + node.last_modified.split('T')[0] + '<br>';
  html += '</div>';

  html += '<button onclick="document.getElementById(\'detail-panel\').classList.remove(\'open\')" style="margin-top:12px;padding:6px 12px;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;color:var(--text-secondary);cursor:pointer;font-size:12px">Close Panel</button>';

  content.innerHTML = html;
}

// ── D3 FORCE GRAPH ──
function renderGraph(data) {
  const svg = d3.select('#graph-svg');
  const width = document.getElementById('graph-container').clientWidth;
  const height = document.getElementById('graph-container').clientHeight;

  svg.selectAll('*').remove();

  // Glow filter
  const defs = svg.append('defs');
  const filter = defs.append('filter').attr('id', 'glow');
  filter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
  const merge = filter.append('feMerge');
  merge.append('feMergeNode').attr('in', 'blur');
  merge.append('feMergeNode').attr('in', 'SourceGraphic');

  const g = svg.append('g');

  // Zoom
  const zoom = d3.zoom().scaleExtent([0.2, 5]).on('zoom', (e) => {
    g.attr('transform', e.transform);
  });
  svg.call(zoom);

  // Simulation
  const sim = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(data.edges).id(d => d.id).distance(120))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => d.size + 10));

  // Edges
  const links = g.selectAll('.edge-line')
    .data(data.edges).join('line')
    .attr('class', 'edge-line')
    .attr('stroke', '#333')
    .attr('stroke-width', 1.5);

  // Nodes
  const nodes = g.selectAll('.node-group')
    .data(data.nodes).join('g')
    .attr('class', 'node-group')
    .call(d3.drag()
      .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  // Glow circle (behind)
  nodes.append('circle')
    .attr('r', d => d.size + 6)
    .attr('fill', d => d.glow)
    .attr('opacity', 0.15)
    .attr('filter', 'url(#glow)');

  // Main circle
  nodes.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => d.size)
    .attr('fill', d => d.color)
    .attr('stroke', d => d.glow)
    .attr('stroke-width', 2)
    .on('click', (e, d) => { selectNode(d.id); });

  // Labels
  nodes.append('text')
    .attr('class', 'node-label')
    .attr('dy', d => d.size + 14)
    .text(d => d.name);

  // Tick
  sim.on('tick', () => {
    links
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    nodes.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
  });

  // Meta bar
  document.getElementById('meta-total').textContent = data.nodes.length;
  document.getElementById('meta-edges').textContent = data.edges.length;
  document.getElementById('meta-cats').textContent = data.categories.length;
  document.getElementById('meta-time').textContent = data.meta.generated_at.split('T')[0];

  window._graphNodes = data.nodes;
}

// ── SELECT NODE ──
function selectNode(id) {
  const node = window._graphNodes.find(n => n.id === id);
  if (node) showDetail(node);
  document.querySelectorAll('.skill-item').forEach(el => {
    el.classList.toggle('active', el.dataset.id === id);
  });
}

// ── SEARCH ──
document.getElementById('search-box').addEventListener('input', function() {
  const q = this.value.toLowerCase();
  document.querySelectorAll('.skill-item').forEach(el => {
    const name = el.textContent.toLowerCase();
    el.style.display = name.includes(q) ? '' : 'none';
  });
});

// ── INIT ──
renderSidebar(GRAPH_DATA);
renderGraph(GRAPH_DATA);
</script>
</body>
</html>
"""
```

---

## Step 4: Build & Serve

```python
import http.server
import threading

OUTPUT_DIR = Path("~/.openclaw/workspace/skillgraph/").expanduser()
SERVE_PORT = 18800

def build_dashboard():
    """
    Run full pipeline: discover → analyze → generate JSON → inject into HTML → write files.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Discover
    print("Scanning skills...")
    skills = discover_all_skills()
    print(f"  Found {len(skills)} skills")

    # Generate graph data
    graph_data = generate_graph_data(skills)

    # Write JSON (for API consumers / debugging)
    json_path = OUTPUT_DIR / "graph_data.json"
    with open(json_path, 'w') as f:
        json.dump(graph_data, f, indent=2, default=str)
    print(f"  Wrote {json_path}")

    # Inject into HTML and write
    html_content = DASHBOARD_HTML.replace(
        '__GRAPH_DATA_JSON__',
        json.dumps(graph_data, default=str)
    )
    html_path = OUTPUT_DIR / "index.html"
    with open(html_path, 'w') as f:
        f.write(html_content)
    print(f"  Wrote {html_path}")

    return html_path


def serve_dashboard():
    """Start a local HTTP server to serve the dashboard."""
    os.chdir(str(OUTPUT_DIR))
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(('0.0.0.0', SERVE_PORT), handler)
    print(f"SkillGraph dashboard: http://localhost:{SERVE_PORT}")
    print(f"  (Tailscale: http://ngs-mac-mini:{SERVE_PORT})")
    server.serve_forever()


def main():
    build_dashboard()
    serve_dashboard()


if __name__ == "__main__":
    main()
```

---

## Cron Job Specification

### CRON: Scheduled Graph Rebuild

**Trigger:** Configure the cron expression that fits your environment (for
example `0 4 * * *` if you prefer a pre-dawn refresh).

Runs before your daily automations so the dashboard is already up-to-date when
you check it.

**Execution:**
1. Run `discover_all_skills()` → scan all directories
2. Run `generate_graph_data()` → build nodes + edges
3. Write `graph_data.json` and `index.html` to output directory
4. HTTP server picks up new files automatically (it serves from the directory)
5. Log results to `logs/cron_execution.log`

**The HTTP server itself runs as a persistent background process** — started once
via `openclaw gateway` or a LaunchAgent, not restarted daily.

---

## Telegram Bot Commands

| Command | Action |
|---------|--------|
| `/graph` | Send dashboard URL (localhost + Tailscale link) |
| `/graph refresh` | Force rebuild the graph now |
| `/graph stats` | Send text summary: total skills, per-category counts, health scores |
| `/graph health` | List skills with health < 50 that need attention |
| `/graph search {term}` | Find skills matching a keyword |

---

## LaunchAgent (Auto-Start HTTP Server on Boot)

Create `~/Library/LaunchAgents/ai.openclaw.skillgraph.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.openclaw.skillgraph</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>http.server</string>
        <string>18800</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/ngkengyit/.openclaw/workspace/skillgraph</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/ngkengyit/.openclaw/logs/skillgraph.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/ngkengyit/.openclaw/logs/skillgraph-error.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/ai.openclaw.skillgraph.plist
```

---

## Error Recovery

| Failure | Response |
|---------|----------|
| SKILL.md has invalid YAML frontmatter | Skip frontmatter, parse body only, log warning |
| A discovery path doesn't exist | Skip silently, continue with others |
| D3.js CDN unreachable | Dashboard still loads from cached browser, graph won't render until CDN is back |
| HTTP server port 18800 in use | Try 18801, 18802, log which port was used |
| Zero skills discovered | Render empty graph with "No skills found" message, check paths |
| Graph data too large (>500 skills) | Cap at 200 most recently modified, paginate the rest |

---

## Config Section (add to shared/config.yaml)

```yaml
# ─────────────────────────────────────────────
# PROJECT 6: SKILLGRAPH
# ─────────────────────────────────────────────
skillgraph:
  enabled: true
  priority: 5

  output_dir: "~/.openclaw/workspace/skillgraph/"
  serve_port: 18800

  cron_schedules:
    daily_rebuild: "0 4 * * *"       # 04:00 SGT daily

  graph:
    max_nodes: 200
    physics_charge: -300
    physics_collision_radius: 10
    default_node_size: 20
    max_node_size: 60
```

---

## Implementation Dependencies

```bash
pip install pyyaml
# D3.js loaded from CDN in the HTML — no local install needed
# Python http.server is built-in — no install needed
```

This skill has **zero external dependencies** beyond PyYAML (which you already have).
