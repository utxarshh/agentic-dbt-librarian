# 📚 Agentic dbt Librarian

> An intelligent, AI-powered documentation and governance system for Snowflake/dbt stacks. Automatically generates `schema.yml` files, identifies documentation gaps, and orchestrates everything through n8n workflows.

---

## Architecture Overview

```
GitHub Commit (.sql file)
        │
        ▼
  n8n Workflow Trigger
        │
        ├── Fetch SQL from GitHub
        │
        ├── Load manifest.json + catalog.json (Lineage Context)
        │
        ├── AI Agent (LLM) ──► System Prompt (Impact Prompting)
        │       │
        │       └── Returns: dbt schema.yml block
        │
        ├── YAML Response Parser (validation + clean-up)
        │
        └── GitHub API ──► Create Pull Request with schema.yml
```

## Project Structure

```
.
├── README.md                       # This file
├── gap_finder/
│   ├── gap_finder.py               # Phase 2: Documentation Gap Finder
│   └── sample_manifest.json        # Sample manifest for local testing
├── n8n/
│   └── agentic_dbt_librarian.json  # Phase 3: n8n Workflow (import-ready)
├── prompts/
│   └── system_prompt.md            # Phase 4: AI Agent System Prompt
├── docs/
│   └── architecture.md             # Phase 1: Full architecture & metadata strategy
└── sprint0/
    └── SPRINT_0_GUIDE.md           # Phase 5: Sprint 0 implementation guide
```

## Quick Start (Sprint 0)

See [`sprint0/SPRINT_0_GUIDE.md`](./sprint0/SPRINT_0_GUIDE.md) for the 3-step guide to get the MVP running locally within the hour.

## Components

| Phase | File | Purpose |
|-------|------|---------|
| 1 | `docs/architecture.md` | System design & metadata strategy |
| 2 | `gap_finder/gap_finder.py` | Identifies missing docs, outputs `DOCS_AUDIT.md` |
| 3 | `n8n/agentic_dbt_librarian.json` | n8n workflow (GitHub → AI → PR) |
| 4 | `prompts/system_prompt.md` | Impact-first AI Agent system prompt |
| 5 | `sprint0/SPRINT_0_GUIDE.md` | Local MVP setup in ~1 hour |
