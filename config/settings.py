from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

REVIEWS_CSV = DATA_DIR / "app_store_reviews.csv"
EMAILS_CSV = DATA_DIR / "support_emails.csv"
EXPECTED_CSV = DATA_DIR / "expected_classifications.csv"

TICKETS_CSV = OUTPUT_DIR / "generated_tickets.csv"
PROCESSING_LOG_CSV = OUTPUT_DIR / "processing_log.csv"
METRICS_CSV = OUTPUT_DIR / "metrics.csv"

CATEGORIES = ["Bug", "Feature Request", "Praise", "Complaint", "Spam"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]

CONFIDENCE_THRESHOLD = 0.70

# (category, max_rating) -> priority; rating=None means any rating (for emails)
PRIORITY_RULES = {
    ("Bug", 1): "Critical",
    ("Bug", 2): "High",
    ("Bug", 5): "Medium",
    ("Feature Request", 5): "Medium",
    ("Complaint", 2): "High",
    ("Complaint", 5): "Low",
    ("Praise", 5): "Low",
    ("Spam", 5): "Low",
}

TICKETS_COLUMNS = [
    "ticket_id", "source_id", "source_type", "title", "category", "priority",
    "description", "technical_details", "platform", "app_version",
    "created_at", "status", "confidence_score",
]

PROCESSING_LOG_COLUMNS = [
    "timestamp", "source_id", "source_type", "agent", "action",
    "input_category", "output_category", "confidence", "notes", "processing_time_ms",
]

METRICS_COLUMNS = [
    "run_id", "timestamp", "total_processed", "bugs", "features", "praise",
    "complaints", "spam", "tickets_created", "quality_score",
    "accuracy_vs_expected", "avg_confidence", "total_processing_time_s",
]
