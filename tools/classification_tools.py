import json
import re
from crewai.tools import tool

BUG_KEYWORDS = [
    "crash", "crashes", "crashing", "freeze", "freezes", "frozen", "hang",
    "not working", "broken", "error", "bug", "fail", "fails", "failure",
    "can't login", "cannot login", "can't sync", "not syncing", "sync issue",
    "data loss", "disappeared", "missing data", "notification", "won't open",
    "stuck", "loading forever", "spinner", "blank screen",
]
FEATURE_KEYWORDS = [
    "please add", "would love", "feature request", "suggestion", "suggest",
    "missing", "would be great", "could you add", "integration", "export",
    "dark mode", "calendar sync", "recurring", "pomodoro", "widget",
    "would like to see", "add support", "add the ability",
]
PRAISE_KEYWORDS = [
    "amazing", "excellent", "love", "great", "fantastic", "perfect",
    "best app", "highly recommend", "awesome", "wonderful", "brilliant",
    "well done", "thank you", "saved my", "transformed",
]
COMPLAINT_KEYWORDS = [
    "too expensive", "overpriced", "slow", "poor customer service",
    "no response", "disappointed", "unacceptable", "cancel", "refund",
    "worst", "terrible", "horrible", "awful", "bad experience",
]
SPAM_KEYWORDS = [
    "click here", "win a", "free iphone", "guaranteed returns", "buy now",
    "limited offer", "visit www", "crypto", "weight loss", "congratulations",
    "forward this", "act now", "www.", ".example.com",
]


def _score(text_lower: str, keywords: list) -> int:
    return sum(1 for kw in keywords if kw in text_lower)


@tool("Classify Feedback Item")
def classify_feedback_item(feedback_json: str) -> str:
    """
    Classify a single feedback item as Bug, Feature Request, Praise, Complaint, or Spam.
    Returns JSON with keys: category, confidence, reasoning.

    Input: a JSON string with keys:
      text (str, required) - the feedback text to classify,
      rating (str, optional) - star rating 1-5, used as tiebreaker

    Example: {"text": "App crashes when I open calendar", "rating": "1"}
    """
    try:
        data = json.loads(feedback_json)
        text = data.get("text", "")
        rating = data.get("rating", "")
    except Exception:
        text = feedback_json
        rating = ""

    text_lower = text.lower()
    scores = {
        "Bug": _score(text_lower, BUG_KEYWORDS),
        "Feature Request": _score(text_lower, FEATURE_KEYWORDS),
        "Praise": _score(text_lower, PRAISE_KEYWORDS),
        "Complaint": _score(text_lower, COMPLAINT_KEYWORDS),
        "Spam": _score(text_lower, SPAM_KEYWORDS),
    }

    total = sum(scores.values()) or 1
    top_category = max(scores, key=scores.get)
    top_score = scores[top_category]

    # Rating tiebreaker when no keywords match or scores are tied
    if top_score == 0:
        try:
            r = int(rating)
            if r <= 2:
                top_category = "Complaint"
            elif r >= 4:
                top_category = "Praise"
            else:
                top_category = "Complaint"
        except (ValueError, TypeError):
            top_category = "Complaint"
        confidence = 0.50
    else:
        confidence = round(min(top_score / total + 0.3, 0.99), 2)

    # Spam overrides everything if spam score is highest
    if scores["Spam"] >= 2 and scores["Spam"] >= top_score:
        top_category = "Spam"
        confidence = round(min(scores["Spam"] / total + 0.3, 0.99), 2)

    matched = [kw for kw in BUG_KEYWORDS + FEATURE_KEYWORDS + PRAISE_KEYWORDS
               + COMPLAINT_KEYWORDS + SPAM_KEYWORDS if kw in text_lower]

    return json.dumps({
        "category": top_category,
        "confidence": confidence,
        "reasoning": f"Keyword matches: {matched[:5]}. Scores: {scores}",
    })


@tool("Extract Bug Details")
def extract_bug_details(bug_report_json: str) -> str:
    """
    Extract technical details from a bug report.
    Returns JSON with: device, os_version, app_version, steps_to_reproduce, severity, affected_feature.

    Input: a JSON string with keys:
      text (str, required) - the bug report text,
      platform (str, optional) - e.g. "Google Play" or "email",
      app_version (str, optional) - e.g. "3.0.1"

    Example: {"text": "App crashes on calendar...", "platform": "App Store", "app_version": "3.0.1"}
    """
    try:
        data = json.loads(bug_report_json)
        text = data.get("text", "")
        platform = data.get("platform", "")
        app_version = data.get("app_version", "")
    except Exception:
        text = bug_report_json
        platform = ""
        app_version = ""

    text_lower = text.lower()

    # Severity heuristics
    critical_signals = ["data loss", "disappeared", "all tasks", "crash", "cannot login", "can't login"]
    high_signals = ["freeze", "not working", "broken", "sync", "notification"]
    severity = "Medium"
    if any(s in text_lower for s in critical_signals):
        severity = "Critical"
    elif any(s in text_lower for s in high_signals):
        severity = "High"

    # Device extraction (simple pattern)
    device_match = re.search(
        r"(iphone\s?\d+\s?(?:pro|plus|max)?|samsung galaxy\s?\w+|pixel\s?\d+|oneplus\s?\d+|galaxy note\s?\d+)",
        text_lower
    )
    device = device_match.group(0).title() if device_match else platform or "Unknown"

    # OS version
    os_match = re.search(r"(ios\s?\d+[\.\d]*|android\s?\d+[\.\d]*)", text_lower)
    os_version = os_match.group(0).title() if os_match else "Unknown"

    # Steps extraction
    steps_match = re.findall(r"\d+\.\s+(.+?)(?=\n\d+\.|\n\n|$)", text, re.MULTILINE)
    steps = steps_match[:5] if steps_match else ["See description"]

    # Affected feature
    feature_map = {
        "calendar": "Calendar View", "login": "Authentication", "sync": "Data Sync",
        "notification": "Push Notifications", "task": "Task Management",
        "offline": "Offline Mode",
    }
    affected = "General"
    for kw, feat in feature_map.items():
        if kw in text_lower:
            affected = feat
            break

    return json.dumps({
        "device": device,
        "os_version": os_version,
        "app_version": app_version,
        "steps_to_reproduce": steps,
        "severity": severity,
        "affected_feature": affected,
    })


@tool("Extract Feature Details")
def extract_feature_details(text: str) -> str:
    """
    Extract feature request details from feedback text.
    Returns JSON with: feature_name, user_impact, demand_estimate, use_case.
    """
    text_lower = text.lower()

    feature_map = {
        "dark mode": ("Dark Mode", "High", "Reduces eye strain in low-light usage"),
        "google calendar": ("Google Calendar Integration", "High", "Unified task and event management"),
        "export": ("Task Export (PDF/Excel)", "Medium", "Team sharing and reporting"),
        "pomodoro": ("Pomodoro Timer", "Medium", "Time management within the app"),
        "recurring": ("Recurring Tasks", "High", "Automation for repetitive tasks"),
        "widget": ("Home Screen Widget", "Medium", "Quick access to tasks"),
        "offline": ("Offline Mode", "High", "Work without internet connection"),
        "collaboration": ("Team Collaboration", "High", "Multi-user workspace"),
    }

    feature_name = "General Improvement"
    user_impact = "Low"
    use_case = text[:100] + "..."

    for kw, (name, impact, case) in feature_map.items():
        if kw in text_lower:
            feature_name = name
            user_impact = impact
            use_case = case
            break

    demand_estimate = "Medium (1 user request)"
    if any(w in text_lower for w in ["many", "team", "everyone", "lot of", "highly requested"]):
        demand_estimate = "High (multiple users)"

    return json.dumps({
        "feature_name": feature_name,
        "user_impact": user_impact,
        "demand_estimate": demand_estimate,
        "use_case": use_case,
    })
