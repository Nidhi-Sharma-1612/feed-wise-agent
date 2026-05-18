import json
import pandas as pd
from crewai.tools import tool
from config.settings import REVIEWS_CSV, EMAILS_CSV


@tool("Read App Store Reviews CSV")
def read_reviews_csv(filepath: str) -> str:
    """
    Read the app_store_reviews.csv file and return a JSON list of review dicts.
    Each dict contains: source_id, source_type, text, platform, rating, user_name, date, app_version.
    Pass filepath as the path to the CSV, or pass "default" to use the configured data path.
    """
    path = str(REVIEWS_CSV) if not filepath or filepath.strip().lower() == "default" else filepath
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        records = df.fillna("").to_dict(orient="records")
        unified = []
        for r in records:
            unified.append({
                "source_id": str(r.get("review_id", "")),
                "source_type": "review",
                "text": str(r.get("review_text", "")),
                "platform": str(r.get("platform", "")),
                "rating": str(r.get("rating", "")),
                "user_name": str(r.get("user_name", "")),
                "date": str(r.get("date", "")),
                "app_version": str(r.get("app_version", "")),
            })
        return json.dumps(unified, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Read Support Emails CSV")
def read_emails_csv(filepath: str) -> str:
    """
    Read the support_emails.csv file and return a JSON list of email dicts.
    Each dict contains: source_id, source_type, text, platform, rating, user_name, date, app_version.
    Pass filepath as the path to the CSV, or pass "default" to use the configured data path.
    """
    path = str(EMAILS_CSV) if not filepath or filepath.strip().lower() == "default" else filepath
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        records = df.fillna("").to_dict(orient="records")
        unified = []
        for r in records:
            body = str(r.get("body", ""))
            subject = str(r.get("subject", ""))
            unified.append({
                "source_id": str(r.get("email_id", "")),
                "source_type": "email",
                "text": f"Subject: {subject}\n\n{body}",
                "platform": "email",
                "rating": "",
                "user_name": str(r.get("sender_email", "")),
                "date": str(r.get("timestamp", "")),
                "app_version": "",
                "subject": subject,
                "priority_hint": str(r.get("priority", "")),
            })
        return json.dumps(unified, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
