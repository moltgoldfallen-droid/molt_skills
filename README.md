## What Is This?

SkillGraph is an OpenClaw skill that **visualizes your entire skill ecosystem** as an interactive force-directed node graph — inspired by [Muse's Skill Evolution Graph (技能演化)](https://muse.ai).

It automatically scans every installed OpenClaw skill, extracts metadata from each `SKILL.md`, maps cross-skill dependencies, and renders a dark-themed interactive dashboard served locally on your machine.

**No manual data entry.** Install a new skill → the graph picks it up on the next rebuild.

<p align="center">
  <img src="assets/skillgraph-screenshot.png" alt="SkillGraph Dashboard" width="900">
</p>

---

## Features

**🔍 Auto-Discovery**
Scans multiple skill directories (local projects, OpenClaw defaults, community skills, user/private/public) and finds every `SKILL.md` automatically.

**🎨 10-Category Color-Coding**
Auto-classifies skills into categories by content analysis — no manual tagging required.

| Category | Color | Category | Color |
|----------|-------|----------|-------|
| Knowledge & Research | 🟢 Green | Security | 🔴 Red |
| Automation | 🟠 Orange | Communication | 🔵 Blue |
| Finance | 🟡 Amber | Creative | 🟣 Purple |
| Health & Wellness | 🩷 Pink | Productivity | 🩵 Cyan |
| Development | 🟩 Light Green | System | ⚪ Grey |

**🔗 Dependency Mapping**
Detects cross-skill relationships by parsing `read_from_*` patterns, data flow declarations, and skill name references. Renders as edges between nodes.

**📊 Health Scoring (0–100)**
Each skill gets a health score based on content depth, documented capabilities, self-awareness (known gaps), modification recency, and active scheduling.

**🖱️ Interactive Dashboard**
- D3.js force-directed graph with drag, zoom, and pan
- Left sidebar: searchable skill list grouped by category
- Right panel: full detail view on click (description, tech stack, capabilities, gaps, metadata)
- Bottom meta bar: total skills, edges, categories, generation timestamp

**📱 Telegram Integration**
`/graph` commands for quick access, forced refresh, stats, and health alerts.

**🏠 Fully Local & Private**
Served via Python's built-in HTTP server. No cloud, no npm, no build step, no data leaves your machine.

---

## Demo

```
┌─────────────────┬──────────────────────────────────┬──────────────────┐
│  LEFT SIDEBAR   │       FORCE-DIRECTED GRAPH       │  DETAIL PANEL    │
│                 │                                    │                  │
│  🔍 Search...   │     ●──────●                      │  📦 Skill Name   │
│                 │    /        \      ●               │  v2.1            │
│  CATEGORY A (3) │   ●    ●────●    / \              │  ────────────    │
│  • Skill One    │    \  / \      ●    ●             │  Health: 85/100  │
│  • Skill Two    │     ●    ●──●                     │  Category: ...   │
│  • Skill Three  │          |                         │  Tech: python,   │
│                 │          ●                        │  pandas, ...     │
│  CATEGORY B (2) │                                    │  Capabilities:   │
│  • Skill Four   │                                    │  • Feature A     │
│  • Skill Five   │   Skills: 12  Edges: 8             │  • Feature B     │
│                 │   Categories: 5                    │  Known Gaps:     │
│  ...            │   Generated: 2026-04-10            │  • Gap X         │
└─────────────────┴──────────────────────────────────┴──────────────────┘
```

---

## Installation

### Prerequisites

- [OpenClaw](https://openclaws.io) 2026.4 or later
- Python 3.10+
- PyYAML (`pip install pyyaml`)

### Quick Start

```bash
# Clone into your OpenClaw skills directory
cd ~/.openclaw/workspace/skills/
git clone https://github.com/YOUR_USERNAME/skillgraph.git

# Build the dashboard
cd skillgraph
python build.py

# Open in browser
open http://localhost:18800
```

### Auto-Start on Boot (macOS)

```bash
cat > ~/Library/LaunchAgents/ai.openclaw.skillgraph.plist << 'EOF'
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
    <string>PATH_TO_SKILLGRAPH_OUTPUT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/ai.openclaw.skillgraph.plist
```

Replace `PATH_TO_SKILLGRAPH_OUTPUT` with your actual output directory (e.g., `~/.openclaw/workspace/skillgraph`).

### Remote Access

If your machine runs [Tailscale](https://tailscale.com), access the dashboard from any device on your tailnet:

```
http://your-machine-name:18800
```

---

## How It Works

```
SKILL.md files            SkillGraph               Browser
across all dirs
                    ┌─────────────────────┐
  ┌──────┐         │  1. DISCOVER         │
  │SKILL │────────▶│  Scan directories    │
  │ .md  │         │  Parse YAML + body   │
  └──────┘         │                      │
  ┌──────┐         │  2. ANALYZE          │
  │SKILL │────────▶│  Map dependencies    │
  │ .md  │         │  Classify categories │
  └──────┘         │  Score health        │
  ┌──────┐         │                      │       ┌──────────┐
  │SKILL │────────▶│  3. GENERATE         │──────▶│ index.   │
  │ .md  │         │  graph_data.json     │       │  html    │
  └──────┘         │  index.html (D3.js)  │       └────┬─────┘
     ...           │                      │            │
                   │  4. SERVE            │            ▼
                   │  localhost:18800     │◀──── 🖥️ Dashboard
                   └─────────────────────┘
```

### What Gets Extracted From Each SKILL.md

| Source | Extracted |
|--------|-----------|
| YAML frontmatter | name, description, version |
| `pip install` / `import` lines | tech stack |
| Bullet lists under capability headers | current capabilities |
| "Known gaps" / "Limitations" sections | known gaps |
| Cross-references to other skills | dependency edges |
| Cron expressions | schedule information |
| File stats | size, modification date, line count |

### Discovery Paths

SkillGraph scans these directories by default:

```
~/openclaw-projects/skills/
~/.openclaw/workspace/skills/
~/.openclaw/skills/
/mnt/skills/user/
/mnt/skills/private/
/mnt/skills/public/
/mnt/skills/examples/
```

Add custom paths in the config or directly in `build.py`.

### Health Score Breakdown

| Factor | Points |
|--------|--------|
| File has content (>500 bytes) | +20 |
| Substantial content (>3KB) | +10 |
| 3+ capabilities defined | +20 |
| Known gaps documented | +15 |
| Modified in last 7 days | +20 |
| Modified in last 30 days | +10 |
| Has cron/schedule definitions | +15 |
| **Maximum** | **100** |

---

## Configuration

Add to your OpenClaw `config.yaml`:

```yaml
skillgraph:
  enabled: true
  output_dir: "~/.openclaw/workspace/skillgraph/"
  serve_port: 18800

  graph:
    max_nodes: 200
    physics_charge: -300
    physics_collision_radius: 10
    default_node_size: 20
    max_node_size: 60
```

---

## Telegram Commands

| Command | Action |
|---------|--------|
| `/graph` | Send dashboard URL |
| `/graph refresh` | Force rebuild the graph |
| `/graph stats` | Text summary of skill counts and categories |
| `/graph health` | List skills with health score below 50 |
| `/graph search {term}` | Find skills matching a keyword |

---

## Making Your Skills Graph-Friendly

SkillGraph works with any `SKILL.md`, but richer metadata produces richer nodes. To get the best visualization:

1. **Add YAML frontmatter** with `name` and `description`
2. **Document capabilities** as bullet lists under a "Capabilities" or "Features" header
3. **Document known gaps** under "Known Gaps" or "Limitations"
4. **Declare dependencies** using `read_from_{skill_name}` patterns or explicit references
5. **Include `pip install` lines** so the tech stack is auto-detected

---

## Tech Stack

| Component | Role |
|-----------|------|
| Python 3.10+ | Discovery, parsing, generation, HTTP server |
| PyYAML | SKILL.md frontmatter parsing |
| D3.js v7 | Force-directed graph (CDN) |
| JetBrains Mono | Monospace typography (Google Fonts) |
| Outfit | UI typography (Google Fonts) |

**Zero local dependencies** beyond PyYAML. No npm, no build tools, no frameworks.

---

## Project Structure

```
skillgraph/
├── SKILL.md           # OpenClaw skill definition
├── build.py           # Discovery + analysis + HTML generation
├── template.html      # Dashboard HTML/CSS/JS template
├── graph_data.json    # Generated (auto-created by build)
├── index.html         # Generated (auto-created by build)
├── assets/
│   ├── skillgraph-banner.png
│   └── skillgraph-screenshot.png
└── README.md
```

---

## Roadmap

- [ ] Live reload via WebSocket
- [ ] Version timeline (git log integration per skill)
- [ ] Skill creation wizard (right-click → "New Skill")
- [ ] Visual cluster grouping for connected skills
- [ ] PNG/SVG graph export
- [ ] ClawHub published vs. local-only indicators
- [ ] Overlay cron execution times and error rates

---

## Contributing

PRs welcome. Keep it zero-dependency and framework-free.

---

## License

MIT

---

<p align="center">
  Built with 🦞 for the OpenClaw community
</p>
