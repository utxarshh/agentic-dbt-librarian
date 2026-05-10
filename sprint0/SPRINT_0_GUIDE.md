# Phase 5: Sprint 0 Guide — MVP in ~1 Hour

> Get the full Agentic dbt Librarian running locally from scratch in 3 steps.

---

## Prerequisites Checklist

Before starting, confirm you have:
- [ ] Python 3.10+
- [ ] n8n installed (Docker or npm)
- [ ] A GitHub repo with a dbt project (or use the sample files here)
- [ ] An OpenAI API key (GPT-4o access)
- [ ] A GitHub Personal Access Token (with `repo` scope)

---

## Step 1: Run the Gap Finder (10 minutes)

This immediately tells you where your documentation debt is.

### 1a. Point it at your real manifest

```bash
cd "Agentic dbt Librarian/gap_finder"

# If you have a real dbt project:
python gap_finder.py --manifest /path/to/your/dbt/project/target/manifest.json

# If you don't have a dbt project yet, use the included sample:
python gap_finder.py --manifest ./sample_manifest.json --project jaffle_shop
```

### 1b. Read the output

```bash
open DOCS_AUDIT.md   # macOS
# or
cat DOCS_AUDIT.md
```

**What you'll see:**
- A risk-scored list of every model and column missing documentation
- "Cost of Ignorance" analysis explaining the business risk
- A prioritized action plan (CRITICAL → HIGH → MEDIUM → LOW)

### 1c. Generate your real manifest (if needed)

```bash
# In your dbt project directory:
dbt compile          # Generates target/manifest.json
dbt docs generate    # Generates target/catalog.json (optional but recommended)
```

---

## Step 2: Import the n8n Workflow (20 minutes)

### 2a. Start n8n

```bash
# Option A: Docker (recommended)
docker run -it --rm \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=admin \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Option B: npm
npx n8n
```

Open: http://localhost:5678

### 2b. Add Credentials

In n8n Settings → Credentials, create:

**GitHub API credential:**
- Type: `GitHub API`
- Name: `GitHub API`
- Personal Access Token: your GitHub PAT (needs `repo` scope)

**OpenAI API credential:**
- Type: `OpenAI API`
- Name: `OpenAI API`
- API Key: your OpenAI key

### 2c. Import the Workflow

1. In n8n, click **Import from File**
2. Select `n8n/agentic_dbt_librarian.json`
3. The full 12-node workflow loads automatically
4. Click **Save**

### 2d. Activate & Get Webhook URL

1. Toggle the workflow to **Active**
2. Click on the **GitHub Webhook Trigger** node
3. Copy the **Webhook URL** (looks like: `https://your-n8n.domain/webhook/dbt-librarian-trigger`)

### 2e. Register the Webhook in GitHub

In your GitHub repo → Settings → Webhooks → Add webhook:
- **Payload URL**: paste your n8n webhook URL
- **Content type**: `application/json`
- **Events**: Select `Push events`
- Click **Add webhook**

---

## Step 3: Test End-to-End (30 minutes)

### 3a. Make a test commit

```bash
# In your dbt project, create or modify any .sql model file
echo "-- test change" >> models/marts/fct_orders.sql
git add .
git commit -m "test: trigger agentic dbt librarian"
git push origin main
```

### 3b. Watch the workflow run

In n8n → Executions tab, you'll see the workflow fire. Each node turns green as it completes:

```
✅ GitHub Webhook Trigger
✅ Parse Push Event & Filter SQL Files
✅ Skip if No SQL Files
✅ Fetch SQL File from GitHub
✅ Fetch manifest.json from GitHub
✅ Build Lineage-Aware Agent Context
✅ AI Agent — Generate schema.yml
✅ YAML Response Parser & Validator
✅ YAML Valid?
✅ Get Branch SHA
✅ Create PR Branch
✅ Commit schema.yml to Branch
✅ Create Pull Request
✅ Success Response
```

### 3c. Review the Pull Request

Go to your GitHub repo → Pull Requests. You'll find a new PR:

```
🤖 [AI Docs] schema.yml for `fct_orders`
```

The PR contains:
- A fully generated `schema.yml` with business-context descriptions
- A checklist for human review
- A reminder that AI descriptions are a starting point

**Review, edit if needed, and merge!**

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Workflow doesn't trigger | Check GitHub webhook delivery log (Settings → Webhooks → Recent Deliveries) |
| `manifest.json` not found | n8n needs read access to the repo; ensure the GitHub PAT has `repo` scope |
| AI returns invalid YAML | Check the raw response in n8n execution log; reduce `temperature` to 0.1 |
| PR creation fails | Ensure PAT has `repo` write scope, not just read |
| Gap finder shows no models | Verify `--project` matches your `dbt_project.yml` `name:` field |

---

## What's Next (Post-Sprint 0)

| Enhancement | Effort | Value |
|-------------|--------|-------|
| Add Slack notification when PR is opened | 30 min | High — keeps team aware |
| Schedule weekly gap finder run | 1 hour | High — continuous monitoring |
| Add `dbt test` suggestions to AI output | 2 hours | High — data quality |
| Connect catalog.json for column type enrichment | 2 hours | High — better descriptions |
| Add model-tier classification (mart vs staging) | 1 hour | Medium — smarter prompting |
| Deploy n8n to cloud (Railway/Render) | 2 hours | High — remove local dependency |
