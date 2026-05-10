#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              AGENTIC DBT LIBRARIAN — DOCUMENTATION GAP FINDER              ║
║                                                                              ║
║  Phase 2: Scans manifest.json for missing descriptions and outputs           ║
║  a rich Markdown audit report (DOCS_AUDIT.md) with risk scoring.            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python gap_finder.py [--manifest PATH] [--output PATH] [--project NAME]

Examples:
    python gap_finder.py
    python gap_finder.py --manifest ./target/manifest.json --output DOCS_AUDIT.md
    python gap_finder.py --manifest ./sample_manifest.json --project my_dbt_project
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColumnGap:
    """Represents a single column with a missing description."""
    model_name: str
    column_name: str
    data_type: Optional[str] = None
    is_likely_pk: bool = False
    is_likely_fk: bool = False
    risk_level: str = "LOW"
    risk_reason: str = ""


@dataclass
class ModelGap:
    """Represents a model with documentation issues."""
    name: str
    unique_id: str
    path: str
    schema: Optional[str] = None
    database: Optional[str] = None
    materialization: str = "view"
    depends_on: list = field(default_factory=list)
    missing_model_description: bool = False
    missing_columns: list = field(default_factory=list)  # List[ColumnGap]
    total_columns: int = 0
    documented_columns: int = 0
    risk_score: int = 0  # 0-100
    risk_tier: str = "LOW"  # LOW / MEDIUM / HIGH / CRITICAL

    @property
    def coverage_pct(self) -> float:
        if self.total_columns == 0:
            return 0.0
        return round((self.documented_columns / self.total_columns) * 100, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Scoring Engine
# ─────────────────────────────────────────────────────────────────────────────

# Keywords that elevate risk — these columns likely flow into reports/BI tools
HIGH_VALUE_COLUMN_PATTERNS = [
    "revenue", "amount", "total", "mrr", "arr", "ltv", "price",
    "customer", "user_id", "account_id", "order_id", "transaction",
    "churn", "conversion", "profit", "margin", "cost",
    "pii", "email", "phone", "ssn", "address", "name",
    "status", "state", "tier", "segment", "type",
]

# Materialization risk weights
MATERIALIZATION_RISK = {
    "table": 30,
    "incremental": 40,
    "view": 10,
    "ephemeral": 5,
}

# Schema risk patterns — marts/core are consumer-facing
SCHEMA_RISK_PATTERNS = {
    "mart": 30, "marts": 30, "core": 25, "reporting": 35,
    "analytics": 20, "staging": 5, "stg": 5, "raw": 0,
    "intermediate": 10, "int": 10,
}


def is_likely_primary_key(col_name: str) -> bool:
    """Heuristically detect primary keys."""
    lower = col_name.lower()
    return lower in ("id", "pk") or lower.endswith("_id") and col_name.lower().startswith(
        tuple(["", "order", "customer", "user", "account", "product", "event"])
    ) or lower == col_name.lower().split("_")[0] + "_id"


def is_likely_foreign_key(col_name: str, model_name: str) -> bool:
    """Heuristically detect foreign keys (ends in _id but not the model's own PK)."""
    lower = col_name.lower()
    model_prefix = model_name.lower().replace("fct_", "").replace("dim_", "").replace("stg_", "")
    if lower.endswith("_id") and not lower.startswith(model_prefix[:4]):
        return True
    return False


def score_column_risk(col: ColumnGap) -> tuple[str, str, int]:
    """Returns (risk_level, risk_reason, score) for a column gap."""
    score = 0
    reasons = []
    lower_col = col.column_name.lower()

    if col.is_likely_pk:
        score += 40
        reasons.append("Primary Key — joins break without this being documented")
    if col.is_likely_fk:
        score += 25
        reasons.append("Foreign Key — referential integrity depends on this column")

    for pattern in HIGH_VALUE_COLUMN_PATTERNS:
        if pattern in lower_col:
            score += 20
            reasons.append(f"Business-critical keyword '{pattern}' detected")
            break

    if score >= 60:
        return "CRITICAL", "; ".join(reasons), score
    elif score >= 35:
        return "HIGH", "; ".join(reasons), score
    elif score >= 15:
        return "MEDIUM", "; ".join(reasons), score
    else:
        return "LOW", "Low-signal column — documentation still recommended", score


def score_model_risk(model: ModelGap) -> tuple[int, str]:
    """Compute an overall risk score (0–100) and tier for a model."""
    score = 0

    # Missing model-level description is baseline risk
    if model.missing_model_description:
        score += 20

    # Materialization risk
    score += MATERIALIZATION_RISK.get(model.materialization, 10)

    # Schema/layer risk
    schema_lower = (model.schema or "").lower()
    for pattern, weight in SCHEMA_RISK_PATTERNS.items():
        if pattern in schema_lower:
            score += weight
            break

    # Column coverage deficit
    missing_ratio = 1 - (model.documented_columns / max(model.total_columns, 1))
    score += int(missing_ratio * 30)

    # Critical column presence
    has_critical = any(c.risk_level == "CRITICAL" for c in model.missing_columns)
    has_high = any(c.risk_level == "HIGH" for c in model.missing_columns)
    if has_critical:
        score += 20
    elif has_high:
        score += 10

    score = min(score, 100)

    if score >= 75:
        tier = "CRITICAL"
    elif score >= 50:
        tier = "HIGH"
    elif score >= 25:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return score, tier


# ─────────────────────────────────────────────────────────────────────────────
# Manifest Parser
# ─────────────────────────────────────────────────────────────────────────────

def load_manifest(manifest_path: str) -> dict:
    """Load and validate the dbt manifest.json file."""
    path = Path(manifest_path)
    if not path.exists():
        print(f"[ERROR] manifest.json not found at: {manifest_path}")
        print("        Run `dbt compile` or `dbt run` first to generate it.")
        sys.exit(1)

    with open(path, "r") as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] manifest.json is not valid JSON: {e}")
            sys.exit(1)

    version = manifest.get("metadata", {}).get("dbt_schema_version", "unknown")
    print(f"[INFO] Loaded manifest.json (dbt schema version: {version})")
    return manifest


def analyze_manifest(manifest: dict, project_name: Optional[str] = None) -> list[ModelGap]:
    """
    Iterate through all model nodes and identify documentation gaps.
    Returns a list of ModelGap objects for models that have any gaps.
    """
    nodes = manifest.get("nodes", {})
    gaps: list[ModelGap] = []

    # Filter to only model nodes (skip tests, snapshots, seeds, analyses)
    model_nodes = {
        node_id: node
        for node_id, node in nodes.items()
        if node.get("resource_type") == "model"
        and (project_name is None or node.get("package_name") == project_name)
    }

    print(f"[INFO] Found {len(model_nodes)} model nodes to analyze.")

    for node_id, node in model_nodes.items():
        model_name = node.get("name", "unknown")
        model_description = (node.get("description") or "").strip()
        columns = node.get("columns", {})
        config = node.get("config", {})
        materialization = config.get("materialized", "view")
        schema = node.get("schema") or config.get("schema", "")
        database = node.get("database", "")
        path = node.get("original_file_path", "")
        depends_on = node.get("depends_on", {}).get("nodes", [])

        # Count documented columns
        total_cols = len(columns)
        documented_cols = sum(
            1 for col in columns.values()
            if (col.get("description") or "").strip()
        )

        missing_model_desc = not bool(model_description)
        missing_col_gaps: list[ColumnGap] = []

        # Check each column for missing descriptions
        for col_name, col_data in columns.items():
            col_desc = (col_data.get("description") or "").strip()
            if not col_desc:
                is_pk = is_likely_primary_key(col_name)
                is_fk = is_likely_foreign_key(col_name, model_name)
                col_gap = ColumnGap(
                    model_name=model_name,
                    column_name=col_name,
                    data_type=col_data.get("data_type"),
                    is_likely_pk=is_pk,
                    is_likely_fk=is_fk,
                )
                col_gap.risk_level, col_gap.risk_reason, _ = score_column_risk(col_gap)
                missing_col_gaps.append(col_gap)

        # Only report models with at least one gap
        if missing_model_desc or missing_col_gaps:
            model_gap = ModelGap(
                name=model_name,
                unique_id=node_id,
                path=path,
                schema=schema,
                database=database,
                materialization=materialization,
                depends_on=depends_on,
                missing_model_description=missing_model_desc,
                missing_columns=missing_col_gaps,
                total_columns=total_cols,
                documented_columns=documented_cols,
            )
            model_gap.risk_score, model_gap.risk_tier = score_model_risk(model_gap)
            gaps.append(model_gap)

    # Sort by risk score descending (most critical first)
    gaps.sort(key=lambda m: m.risk_score, reverse=True)
    return gaps


# ─────────────────────────────────────────────────────────────────────────────
# Report Generator
# ─────────────────────────────────────────────────────────────────────────────

RISK_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
}

COST_OF_IGNORANCE = {
    "CRITICAL": (
        "**Immediate business risk.** This model or column is likely used in "
        "executive dashboards, financial reports, or critical joins. Without documentation, "
        "any developer can misinterpret this data, leading to **incorrect revenue reporting, "
        "broken pipelines, or compliance violations**. Estimate: 4–16 hours of incident "
        "response time per misuse event."
    ),
    "HIGH": (
        "**Significant technical debt.** Missing documentation here will slow onboarding "
        "of new data engineers and create ambiguity in downstream BI tools. "
        "**Data consumers will make assumptions** that may propagate errors silently. "
        "Estimate: 2–8 hours of confusion or rework per quarter per analyst."
    ),
    "MEDIUM": (
        "**Moderate risk of misuse.** This column or model could be misunderstood in context. "
        "While not immediately breaking, undocumented fields **erode data trust** over time "
        "and make audits harder. Estimate: 1–3 hours of clarification overhead per quarter."
    ),
    "LOW": (
        "**Low immediate risk**, but contributes to documentation debt. "
        "Completing this documentation improves the overall data catalog quality and "
        "helps automated tooling (like this Librarian!) function better."
    ),
}


def generate_summary_stats(all_gaps: list[ModelGap], total_models: int) -> dict:
    """Compute summary statistics for the report header."""
    models_with_gaps = len(all_gaps)
    models_fully_documented = total_models - models_with_gaps
    total_missing_model_desc = sum(1 for g in all_gaps if g.missing_model_description)
    total_missing_cols = sum(len(g.missing_columns) for g in all_gaps)

    tier_counts = defaultdict(int)
    for g in all_gaps:
        tier_counts[g.risk_tier] += 1

    return {
        "total_models": total_models,
        "models_with_gaps": models_with_gaps,
        "models_fully_documented": models_fully_documented,
        "coverage_pct": round((models_fully_documented / max(total_models, 1)) * 100, 1),
        "total_missing_model_desc": total_missing_model_desc,
        "total_missing_cols": total_missing_cols,
        "tier_counts": dict(tier_counts),
    }


def render_markdown_report(
    gaps: list[ModelGap],
    stats: dict,
    manifest_path: str,
) -> str:
    """Render the full Markdown DOCS_AUDIT.md report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines.append("# 📚 dbt Documentation Audit Report — `DOCS_AUDIT.md`")
    lines.append("")
    lines.append(f"> Generated by **Agentic dbt Librarian** on `{now}`  ")
    lines.append(f"> Source: `{manifest_path}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Executive Summary ────────────────────────────────────────────────────
    lines.append("## 📊 Executive Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Models Scanned | **{stats['total_models']}** |")
    lines.append(f"| Models with Documentation Gaps | **{stats['models_with_gaps']}** |")
    lines.append(f"| Fully Documented Models | **{stats['models_fully_documented']}** |")
    lines.append(f"| Overall Documentation Coverage | **{stats['coverage_pct']}%** |")
    lines.append(f"| Missing Model Descriptions | **{stats['total_missing_model_desc']}** |")
    lines.append(f"| Missing Column Descriptions | **{stats['total_missing_cols']}** |")
    lines.append("")

    # Risk tier breakdown
    lines.append("### Risk Tier Distribution")
    lines.append("")
    lines.append("| Tier | Count | Meaning |")
    lines.append("|------|-------|---------|")
    tier_meta = [
        ("CRITICAL", "Immediate action required — financial or compliance risk"),
        ("HIGH", "Address this sprint — analytics accuracy risk"),
        ("MEDIUM", "Address this quarter — data trust risk"),
        ("LOW", "Address opportunistically — quality hygiene"),
    ]
    for tier, meaning in tier_meta:
        count = stats["tier_counts"].get(tier, 0)
        emoji = RISK_EMOJI[tier]
        lines.append(f"| {emoji} {tier} | {count} | {meaning} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not gaps:
        lines.append("## ✅ No Documentation Gaps Found!")
        lines.append("")
        lines.append("All models have descriptions for both the model and all columns.")
        lines.append("**Excellent data documentation hygiene!** 🎉")
        return "\n".join(lines)

    # ── Gap Details ──────────────────────────────────────────────────────────
    lines.append("## 🔍 Detailed Gap Analysis")
    lines.append("")
    lines.append(
        "> Models are sorted by **Risk Score** (highest first). "
        "Address CRITICAL items immediately."
    )
    lines.append("")

    for i, model in enumerate(gaps, 1):
        emoji = RISK_EMOJI[model.risk_tier]
        lines.append(
            f"### {i}. `{model.name}` {emoji} **{model.risk_tier}** "
            f"(Score: {model.risk_score}/100)"
        )
        lines.append("")

        # Model metadata table
        lines.append("| Property | Value |")
        lines.append("|----------|-------|")
        lines.append(f"| **File Path** | `{model.path}` |")
        lines.append(f"| **Schema** | `{model.database}.{model.schema}` |")
        lines.append(f"| **Materialization** | `{model.materialization}` |")
        lines.append(f"| **Column Coverage** | {model.documented_columns}/{model.total_columns} ({model.coverage_pct}%) |")
        lines.append(f"| **Upstream Models** | {len(model.depends_on)} |")
        lines.append("")

        # Model description gap
        if model.missing_model_description:
            lines.append("#### ❌ Missing: Model-Level Description")
            lines.append("")
            lines.append(
                "> The model itself has no description. Every consumer of this model "
                "— from BI tools to new engineers — will have zero context about its purpose."
            )
            lines.append("")

        # Column gaps
        if model.missing_columns:
            lines.append(f"#### ❌ Missing Column Descriptions ({len(model.missing_columns)} columns)")
            lines.append("")
            lines.append("| Column | Data Type | Likely Role | Risk | Reason |")
            lines.append("|--------|-----------|-------------|------|--------|")

            for col in sorted(model.missing_columns, key=lambda c: c.risk_level):
                role = "🔑 Primary Key" if col.is_likely_pk else "🔗 Foreign Key" if col.is_likely_fk else "📊 Metric/Attribute"
                dtype_str = f"`{col.data_type}`" if col.data_type else "*(unknown)*"
                col_emoji = RISK_EMOJI[col.risk_level]
                lines.append(
                    f"| `{col.column_name}` | {dtype_str} | {role} "
                    f"| {col_emoji} {col.risk_level} | {col.risk_reason} |"
                )
            lines.append("")

        # Cost of Ignorance box
        lines.append(f"#### 💸 Cost of Ignorance — `{model.risk_tier}` Risk")
        lines.append("")
        lines.append(f"> {COST_OF_IGNORANCE[model.risk_tier]}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # ── Action Plan ──────────────────────────────────────────────────────────
    lines.append("## 🚀 Recommended Action Plan")
    lines.append("")
    lines.append(
        "Use the **Agentic dbt Librarian** n8n workflow to automatically generate "
        "schema.yml patches for these models. Prioritize in this order:"
    )
    lines.append("")
    lines.append("```")
    lines.append("PRIORITY 1 (This Week)   → All CRITICAL models")
    lines.append("PRIORITY 2 (This Sprint) → All HIGH models")
    lines.append("PRIORITY 3 (This Quarter)→ All MEDIUM models")
    lines.append("PRIORITY 4 (Backlog)     → All LOW models")
    lines.append("```")
    lines.append("")
    lines.append("### Quick Fix: Run the AI Agent on Top-Priority Models")
    lines.append("")
    lines.append("```bash")
    lines.append("# Trigger the n8n workflow for each critical model:")
    if gaps:
        critical_models = [g for g in gaps if g.risk_tier == "CRITICAL"]
        for m in critical_models[:5]:
            lines.append(f"curl -X POST $N8N_WEBHOOK_URL -d '{{\"model\": \"{m.name}\"}}'")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by the Agentic dbt Librarian. Do not edit manually.*")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Agentic dbt Librarian — Documentation Gap Finder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gap_finder.py
  python gap_finder.py --manifest ./target/manifest.json
  python gap_finder.py --manifest ./target/manifest.json --output DOCS_AUDIT.md
  python gap_finder.py --manifest ./sample_manifest.json --project jaffle_shop
        """,
    )
    parser.add_argument(
        "--manifest",
        default="./target/manifest.json",
        help="Path to dbt manifest.json (default: ./target/manifest.json)",
    )
    parser.add_argument(
        "--output",
        default="DOCS_AUDIT.md",
        help="Output path for the audit report (default: DOCS_AUDIT.md)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Filter to a specific dbt project name (optional)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  AGENTIC DBT LIBRARIAN — Documentation Gap Finder")
    print("=" * 70)
    print()

    # Load manifest
    manifest = load_manifest(args.manifest)

    # Count total models for stats
    all_model_nodes = {
        nid: n for nid, n in manifest.get("nodes", {}).items()
        if n.get("resource_type") == "model"
        and (args.project is None or n.get("package_name") == args.project)
    }
    total_models = len(all_model_nodes)

    # Analyze
    print(f"[INFO] Analyzing documentation gaps...")
    gaps = analyze_manifest(manifest, args.project)
    stats = generate_summary_stats(gaps, total_models)

    # Print summary to console
    print()
    print(f"  ✅ Fully Documented : {stats['models_fully_documented']}/{total_models} models")
    print(f"  ❌ Models with Gaps : {stats['models_with_gaps']}")
    print(f"  📊 Coverage         : {stats['coverage_pct']}%")
    print()

    tier_counts = stats["tier_counts"]
    if tier_counts.get("CRITICAL", 0):
        print(f"  🔴 CRITICAL : {tier_counts['CRITICAL']} models — Address immediately!")
    if tier_counts.get("HIGH", 0):
        print(f"  🟠 HIGH     : {tier_counts['HIGH']} models")
    if tier_counts.get("MEDIUM", 0):
        print(f"  🟡 MEDIUM   : {tier_counts['MEDIUM']} models")
    if tier_counts.get("LOW", 0):
        print(f"  🟢 LOW      : {tier_counts['LOW']} models")

    print()

    # Generate report
    report = render_markdown_report(gaps, stats, args.manifest)

    # Write output
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(f"[SUCCESS] Audit report written to: {output_path.resolve()}")
    print()
    print("  Open DOCS_AUDIT.md to view the full report with risk scores,")
    print("  cost-of-ignorance analysis, and prioritized action plan.")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
