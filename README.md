<div align="center">

# 📚 Agentic dbt Librarian

**An AI-powered autonomous documentation engine for dbt projects.**  
Detects undocumented models via GitHub webhook → fetches SQL + lineage context → generates business-context `schema.yml` via Gemini AI → opens a Pull Request for human review.

[![Documentation Audit](https://github.com/utxarshh/agentic-dbt-librarian/actions/workflows/docs_audit.yml/badge.svg)](https://github.com/utxarshh/agentic-dbt-librarian/actions/workflows/docs_audit.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![dbt](https://img.shields.io/badge/dbt-1.7%2B-orange?logo=dbt&logoColor=white)](https://docs.getdbt.com)
[![n8n](https://img.shields.io/badge/n8n-workflow-red?logo=n8n&logoColor=white)](https://n8n.io)

</div>

---

## 🤔 The Problem

> Every dbt project eventually drowns in undocumented models.

When a data engineer pushes `fct_orders.sql`, no one writes the `schema.yml` for it.  
Weeks later, a BI analyst asks: *"What does `net_revenue` actually mean — is it before or after returns?"*  
No one knows. Dashboards become untrustworthy. Onboarding takes weeks instead of days.

**The Agentic dbt Librarian fixes this automatically.**

---

## ✨ How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Developer pushes a commit containing a *.sql model file    │
│     to the GitHub repository                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │  GitHub Webhook (push event)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. n8n Workflow Triggers                                       │
│     ├── Fetches the raw .sql file from GitHub API              │
│     ├── Fetches manifest.json for lineage context              │
│     └── Assembles structured prompt context                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │  Gemini AI (Impact Prompting)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. AI Agent Generates schema.yml                              │
│     Every description answers three questions:                  │
│     • What is it?  (technical definition)                      │
│     • Why does it exist?  (business purpose)                   │
│     • What breaks if it's wrong?  (downstream risk)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │  GitHub API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Pull Request Created on new branch                         │
│     docs/ai-schema-{model}-{timestamp}                         │
│     Human data engineer reviews and merges                     │
└─────────────────────────────────────────────────────────────────┘
```

### 🤖 Bonus: Autonomous CI Audit

Every push to `main` automatically runs the **Documentation Gap Finder**, commits a fresh `DOCS_AUDIT.md` with risk scores, and **opens a GitHub Issue** if critical models are found undocumented.

---

## 📊 Current Documentation Coverage

> Auto-generated from `target/manifest.json` by the CI pipeline.

See [`gap_finder/DOCS_AUDIT.md`](gap_finder/DOCS_AUDIT.md) for the full risk-scored audit.

| Model | Layer | Risk | Coverage |
|-------|-------|------|----------|
| `stg_customers` | staging | 🟢 LOW | Mostly documented |
| `stg_orders` | staging | 🟡 MEDIUM | Partially documented |
| `stg_products` | staging | 🔴 CRITICAL | Undocumented |
| `dim_customers` | marts | 🔴 CRITICAL | Undocumented |
| `fct_orders` | marts | 🔴 CRITICAL | Undocumented |
| `rpt_monthly_revenue` | reporting | 🔴 CRITICAL | Undocumented |

**This is the exact scenario the Librarian is designed to solve.**

---

## 🏗️ Project Structure

```
agentic-dbt-librarian/
│
├── 📁 models/                        # dbt project models
│   ├── staging/
│   │   ├── stg_customers.sql         # Raw CRM data staging
│   │   ├── stg_orders.sql            # Raw orders staging
│   │   ├── stg_products.sql          # Product catalog staging
│   │   └── schema.yml                # Partial docs (shows the gap)
│   ├── marts/
│   │   ├── dim_customers.sql         # Customer dimension w/ LTV + segment
│   │   ├── fct_orders.sql            # Central orders fact table
│   │   └── schema.yml                # Mostly undocumented (Librarian input)
│   └── reporting/
│       ├── rpt_monthly_revenue.sql   # Monthly revenue KPIs + return rate
│       └── schema.yml                # Fully undocumented (highest risk)
│
├── 📁 gap_finder/
│   ├── gap_finder.py                 # Documentation gap scanner (590 lines)
│   ├── sample_manifest.json          # Sample data for local testing
│   └── DOCS_AUDIT.md                 # ← Auto-generated by CI on every push
│
├── 📁 n8n/
│   └── agentic_dbt_librarian.json    # Import-ready n8n workflow (12 nodes)
│
├── 📁 prompts/
│   └── system_prompt.md              # Impact Prompting AI agent instructions
│
├── 📁 docs/
│   ├── architecture.md               # Full system design + metadata strategy
│   └── sample_ai_output.md           # Example of what the AI generates
│
├── 📁 .github/
│   ├── workflows/
│   │   └── docs_audit.yml            # CI: auto-audit + issue creation
│   └── PULL_REQUEST_TEMPLATE.md      # Template for AI-generated doc PRs
│
├── 🌐 dashboard.html                 # Local governance dashboard (no deps)
├── dbt_project.yml                   # dbt project configuration
├── Makefile                          # Developer convenience commands
├── requirements.txt                  # Python dependencies (pyyaml)
└── target/manifest.json              # dbt compiled manifest (6 models)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- n8n (local or cloud)
- GitHub Personal Access Token (repo scope)
- Google Gemini API key ([Get one free](https://aistudio.google.com/apikey))
- ngrok (for local webhook testing)

### 1. Clone & Install

```bash
git clone https://github.com/utxarshh/agentic-dbt-librarian.git
cd agentic-dbt-librarian
make install
```

### 2. Run the Documentation Gap Finder

```bash
# Against the included sample manifest:
make audit

# Against your real dbt project:
make audit MANIFEST=/path/to/your/project/target/manifest.json
```

Open `gap_finder/DOCS_AUDIT.md` to see the risk-scored audit.

### 3. Launch the Governance Dashboard

```bash
make serve
# Open: http://localhost:8080/dashboard.html
```

### 4. Set Up the n8n Automation

1. Start n8n: `npx n8n`
2. Open [http://localhost:5678](http://localhost:5678)
3. **Credentials** → Create two:
   - `GitHub API` — your PAT with `repo` scope
   - `Google Gemini(PaLM) Api` — your AI Studio key
4. **Import** `n8n/agentic_dbt_librarian.json`
5. **Activate** the workflow
6. Start ngrok: `ngrok http 5678`
7. Add the ngrok webhook URL to your GitHub repo (Settings → Webhooks → push events)

### 5. Trigger the Librarian

```bash
echo "-- trigger" >> models/marts/fct_orders.sql
git add . && git commit -m "docs: trigger librarian for fct_orders" && git push
```

A PR will appear in your repo with AI-generated `schema.yml` within ~30 seconds.

---

## 🎯 Sample AI Output

The Librarian generates descriptions like this (see [`docs/sample_ai_output.md`](docs/sample_ai_output.md)):

```yaml
- name: net_revenue
  description: >
    The recognized revenue contribution of this order in USD.
    Equals amount when status is 'completed' or 'shipped'; 0 for all
    other statuses including 'returned' and 'cancelled'. This is the
    primary revenue metric used in executive dashboards and MRR reporting.
    Do not sum amount directly — always use net_revenue for P&L calculations.
```

Not just *what* it is — but *why* it exists and *what breaks if you get it wrong*.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | [n8n](https://n8n.io) (self-hosted) |
| **AI Model** | Google Gemini 2.0 Flash (via AI Studio free tier) |
| **Trigger** | GitHub Webhooks (push events) |
| **Gap Finder** | Python 3.10+ (zero non-stdlib deps) |
| **Dashboard** | Vanilla HTML/JS/CSS (zero deps, single file) |
| **CI/CD** | GitHub Actions |
| **Tunneling** | ngrok (local dev) |

---

## 🏛️ Governance Controls

| Control | Mechanism |
|---------|-----------|
| **Human-in-the-loop** | All AI output goes through a GitHub PR — no auto-merge |
| **Description locking** | Existing non-empty descriptions are preserved via manifest context |
| **Schema validation** | YAML parser + required key checks before PR creation |
| **Audit trail** | Git history records every AI-generated change |
| **Gap reporting** | GitHub Actions auto-commits `DOCS_AUDIT.md` weekly |
| **Alerting** | GitHub Issues auto-created when CRITICAL gaps are detected |

---

## 📐 Architecture Deep Dive

See [`docs/architecture.md`](docs/architecture.md) for:
- Full context assembly layer (SQL + manifest.json + catalog.json)
- Lineage-aware prompt construction pseudocode
- Metadata strategy for `manifest.json` vs `catalog.json`
- Governance control implementation details

---

## 🤝 Contributing

```bash
# Run the audit before opening a PR
make audit

# Run the dashboard locally
make serve
```

PRs welcome. Please include updated `DOCS_AUDIT.md` if you add new models.

---

<div align="center">

Built with 🤖 + ❤️ for data teams who hate writing YAML.

</div>
