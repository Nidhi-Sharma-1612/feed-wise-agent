# FeedWise Agent — Intelligent User Feedback Analysis System

**Live Demo:** https://nidhi-sharma-1612-feed-wise-agent-uiapp-ct9s1g.streamlit.app

Capstone project for the Agentic AI Certification course.  
Automates triaging of app store reviews and support emails using a **6-agent CrewAI pipeline**.

## Architecture

| Agent | Role |
|-------|------|
| CSV Reader Agent | Reads and parses app_store_reviews.csv + support_emails.csv |
| Feedback Classifier Agent | Classifies each item: Bug / Feature Request / Praise / Complaint / Spam |
| Bug Analysis Agent | Extracts device, OS, severity, and steps to reproduce for bugs |
| Feature Extractor Agent | Identifies feature name, impact, and demand for feature requests |
| Ticket Creator Agent | Generates structured tickets and writes to generated_tickets.csv |
| Quality Critic Agent | Reviews ticket completeness, computes metrics, writes metrics.csv |

## Performance (Last Run)

| Metric | Result |
|--------|--------|
| Total feedback items | 30 (20 reviews + 10 emails) |
| Tickets generated | 27 (3 spam skipped) |
| Classification accuracy | **80%** vs expected |
| Quality score | **100 / 100** |
| Avg confidence | 0.95 |
| Pipeline runtime (local) | ~6–7 min |
| Pipeline runtime (Streamlit Cloud) | ~10 min |

## Local Setup

```bash
# 1. Clone / navigate to project
cd feed-wise-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY

# 4. Launch the Streamlit UI
streamlit run ui/app.py
```

## Streamlit Cloud Deployment

1. Push the repo to GitHub (all files including `runtime.txt` and `requirements.txt`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Set **Main file path** to `ui/app.py`
4. Add `OPENAI_API_KEY` in **Secrets** (Settings → Secrets)
5. Deploy — the app handles Python 3.14 compatibility automatically

> **Note:** The pipeline takes ~10 min on Streamlit Cloud due to shared compute.
> The chromadb import hook in `crew/feedback_crew.py` resolves pydantic v1
> incompatibilities with Python 3.14 transparently.

## Usage

1. Open the app at `http://localhost:8501`
2. Click **▶ Run Full Pipeline** in the sidebar
3. View results in the **Dashboard** tab
4. Adjust thresholds in **Configuration**
5. Edit tickets in **Manual Override**
6. See accuracy metrics in **Analytics**

## Input Files (`data/`)

| File | Rows | Description |
|------|------|-------------|
| `app_store_reviews.csv` | 20 | Mock reviews: bugs, features, praise, complaints, spam |
| `support_emails.csv` | 10 | Mock support emails with device/OS/steps details |
| `expected_classifications.csv` | 30 | Ground truth for accuracy measurement |

## Output Files (`output/`)

| File | Description |
|------|-------------|
| `generated_tickets.csv` | Structured tickets with priority, category, technical details |
| `processing_log.csv` | Per-item processing history and agent decisions |
| `metrics.csv` | Run metrics: counts, quality score, accuracy vs expected |

## Project Structure

```
feed-wise-agent/
├── agents/          # 6 CrewAI agent definitions
├── tasks/           # 6 sequential task definitions
├── tools/           # 12 tools (CSV I/O, classification, ticket creation)
├── crew/            # Crew assembly, pipeline runner, Python 3.14 compatibility shims
├── config/          # Settings, thresholds, priority rules
├── storage/         # Session persistence
├── ui/              # Streamlit app + 4 section pages
│   └── sections/    # Dashboard, Config, Override, Analytics
├── data/            # Input CSV files
├── output/          # Generated output files (created at runtime)
├── runtime.txt      # Python 3.11 pin for Streamlit Cloud
└── requirements.txt # Pinned dependencies
```

## Configuration

Edit `config/settings.py` or use the **Configuration** page in the UI to adjust:
- `CONFIDENCE_THRESHOLD` — minimum confidence for auto-classification (default: 0.70)
- `PRIORITY_RULES` — maps (category, rating) → priority level
- `OPENAI_MODEL` — default: `gpt-4o-mini`

## Dependencies

| Package | Purpose |
|---------|---------|
| `crewai>=1.0.0` | Multi-agent orchestration framework |
| `langchain-openai` | OpenAI LLM integration for agents |
| `streamlit` | Web UI |
| `pandas` | CSV reading and data manipulation |
| `plotly` | Analytics charts |
| `pydantic>=2.0.0` | Data validation |
| `setuptools` | pkg_resources compatibility shim |
