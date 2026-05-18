# FeedWise Agent — Intelligent User Feedback Analysis System

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

## Setup

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

## Usage

1. Open the app at `http://localhost:8501`
2. Click **▶ Run Full Pipeline** in the sidebar
3. View results in the **Dashboard** tab
4. Adjust thresholds in **Configuration**
5. Edit tickets in **Manual Override**
6. See accuracy metrics in **Analytics**

## Input Files (`data/`)

| File | Description |
|------|-------------|
| `app_store_reviews.csv` | 20 mock reviews (bugs, features, praise, complaints, spam) |
| `support_emails.csv` | 10 mock support emails with technical details |
| `expected_classifications.csv` | Ground truth for accuracy measurement |

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
├── tools/           # 10 tools (CSV I/O, classification, ticket creation)
├── crew/            # Crew assembly and pipeline runner
├── config/          # Settings, thresholds, priority rules
├── storage/         # Session persistence
├── ui/              # Streamlit app + 4 section pages
│   └── sections/    # Dashboard, Config, Override, Analytics
├── data/            # Input CSV files
└── output/          # Generated output files (created at runtime)
```

## Configuration

Edit `config/settings.py` or use the **Configuration** page in the UI to adjust:
- `CONFIDENCE_THRESHOLD` — minimum confidence for auto-classification (default: 0.70)
- `PRIORITY_RULES` — maps (category, rating) → priority level
- `OPENAI_MODEL` — default: `gpt-4o-mini`
