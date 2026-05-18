import csv
import json
import uuid
from datetime import datetime
from crewai.tools import tool
from config.settings import (
    TICKETS_CSV, PROCESSING_LOG_CSV, METRICS_CSV,
    TICKETS_COLUMNS, PROCESSING_LOG_COLUMNS, METRICS_COLUMNS,
    PRIORITY_RULES,
)


def _make_ticket(source_id, source_type, category, title, description,
                 priority, technical_details="", platform="",
                 app_version="", confidence_score="0.0"):
    return {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:6].upper()}",
        "source_id": source_id,
        "source_type": source_type,
        "title": title,
        "category": category,
        "priority": priority,
        "description": description,
        "technical_details": technical_details,
        "platform": platform,
        "app_version": app_version,
        "created_at": datetime.utcnow().isoformat(),
        "status": "Open",
        "confidence_score": str(confidence_score),
    }


def _ensure_csv(path, columns):
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()


@tool("Create All Tickets From Classified Feedback")
def create_all_tickets(classified_json: str) -> str:
    """
    Create tickets for ALL non-spam feedback items and write them to CSV.
    Internally handles bug detail extraction and feature analysis — no extra merging needed.

    Input: a JSON array string of classified feedback items. Each item must have:
      source_id, source_type, category, confidence, text, platform, rating, app_version.

    This tool processes every category:
      Bug → extracts severity/device/steps internally, sets priority from severity
      Feature Request → extracts feature name/impact internally, priority = Medium
      Complaint → priority High if rating<=2 else Low
      Praise → priority Low
      Spam → skipped (no ticket created)

    Example input (the full array from the classify task):
      [{"source_id": "R001", "source_type": "review", "category": "Bug",
        "confidence": 0.99, "text": "App crashes...", "platform": "Google Play",
        "rating": "1", "app_version": "3.0.1"}, ...]

    Returns JSON: {tickets_created, skipped_spam, categories: {Bug, Feature Request, Complaint, Praise}}
    """
    from tools.classification_tools import extract_bug_details, extract_feature_details

    try:
        classified = json.loads(classified_json)
        if isinstance(classified, dict):
            classified = classified.get("classified", [])
    except Exception as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    # Dedup guard — skip source_ids already processed (tickets OR spam log entries)
    existing_ids = set()
    try:
        import pandas as pd
        if TICKETS_CSV.exists():
            existing_ids.update(pd.read_csv(TICKETS_CSV)["source_id"].astype(str).tolist())
        if PROCESSING_LOG_CSV.exists():
            log_df = pd.read_csv(PROCESSING_LOG_CSV)
            existing_ids.update(log_df["source_id"].astype(str).tolist())
    except Exception:
        pass

    bug_map = {}
    feat_map = {}

    tickets = []
    log_entries = []
    skipped_spam = 0

    for item in classified:
        sid = item.get("source_id", "")
        stype = item.get("source_type", "")
        category = item.get("category", "")
        confidence = item.get("confidence", 0.0)
        text = item.get("text", "")
        platform = item.get("platform", "")
        app_version = item.get("app_version", "")
        rating = item.get("rating", "")
        short_text = text[:80].replace("\n", " ")

        # Skip duplicates
        if sid in existing_ids:
            continue

        if category == "Spam":
            skipped_spam += 1
            log_entries.append({
                "source_id": sid, "source_type": stype, "agent": "Ticket Creator",
                "action": "skipped_spam", "input_category": category,
                "output_category": "Spam", "confidence": confidence,
                "notes": "Spam item skipped", "processing_time_ms": 0,
            })
            continue

        if category == "Bug":
            # Extract bug details internally via Python function call
            try:
                bug_input = json.dumps({"text": text, "platform": platform, "app_version": app_version})
                bd = json.loads(extract_bug_details.func(bug_input))
            except Exception:
                bd = {}
            severity = bd.get("severity", "Medium")
            priority = severity if severity in ["Critical", "High", "Medium", "Low"] else "Medium"
            tech = json.dumps(bd) if bd else ""
            title = f"[BUG] {short_text[:60]}"
            ticket = _make_ticket(sid, stype, category, title, text,
                                  priority, tech, platform, app_version, confidence)

        elif category == "Feature Request":
            # Extract feature details internally
            try:
                fd = json.loads(extract_feature_details.func(text))
            except Exception:
                fd = {}
            feature_name = fd.get("feature_name", short_text[:40])
            tech = json.dumps(fd) if fd else ""
            title = f"[FEATURE] {feature_name}"
            ticket = _make_ticket(sid, stype, category, title, text,
                                  "Medium", tech, platform, app_version, confidence)

        elif category == "Complaint":
            try:
                r = int(float(rating))
            except (ValueError, TypeError):
                r = 3
            priority = "High" if r <= 2 else "Low"
            title = f"[COMPLAINT] {short_text[:60]}"
            ticket = _make_ticket(sid, stype, category, title, text,
                                  priority, "", platform, app_version, confidence)

        elif category == "Praise":
            title = f"[PRAISE] {short_text[:60]}"
            ticket = _make_ticket(sid, stype, category, title, text,
                                  "Low", "", platform, app_version, confidence)

        else:
            title = f"[{category.upper()}] {short_text[:60]}"
            ticket = _make_ticket(sid, stype, category, title, text,
                                  "Low", "", platform, app_version, confidence)

        tickets.append(ticket)
        log_entries.append({
            "source_id": sid, "source_type": stype, "agent": "Ticket Creator",
            "action": "ticket_created", "input_category": category,
            "output_category": category, "confidence": confidence,
            "notes": f"Ticket {ticket['ticket_id']} created", "processing_time_ms": 0,
        })

    # Write tickets
    _ensure_csv(TICKETS_CSV, TICKETS_COLUMNS)
    with open(TICKETS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TICKETS_COLUMNS, extrasaction="ignore")
        for t in tickets:
            writer.writerow(t)

    # Write processing log
    _ensure_csv(PROCESSING_LOG_CSV, PROCESSING_LOG_COLUMNS)
    now = datetime.utcnow().isoformat()
    with open(PROCESSING_LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PROCESSING_LOG_COLUMNS, extrasaction="ignore")
        for entry in log_entries:
            entry["timestamp"] = now
            writer.writerow(entry)

    summary = {
        "tickets_created": len(tickets),
        "skipped_spam": skipped_spam,
        "items": [t["ticket_id"] for t in tickets],
        "categories": {
            "Bug": sum(1 for t in tickets if t["category"] == "Bug"),
            "Feature Request": sum(1 for t in tickets if t["category"] == "Feature Request"),
            "Complaint": sum(1 for t in tickets if t["category"] == "Complaint"),
            "Praise": sum(1 for t in tickets if t["category"] == "Praise"),
        }
    }
    return json.dumps(summary)


def _derive_priority(category: str, rating: str) -> str:
    try:
        r = int(float(rating))
    except (ValueError, TypeError):
        r = 3
    for (cat, max_r), priority in PRIORITY_RULES.items():
        if cat == category and r <= max_r:
            return priority
    return "Low"


@tool("Create Ticket")
def create_ticket(ticket_data_json: str) -> str:
    """
    Generate a structured ticket with a unique ticket_id and return it as JSON.
    Does NOT write to CSV — use 'Write Tickets to CSV' for that.

    Input: a JSON string with keys:
      source_id (str), source_type (str), category (str), title (str),
      description (str), priority (str, one of Critical/High/Medium/Low),
      technical_details (str, optional), platform (str, optional),
      app_version (str, optional), confidence_score (str, optional).

    Example input:
      {"source_id": "R001", "source_type": "review", "category": "Bug",
       "title": "[BUG] App crashes on calendar", "description": "...",
       "priority": "Critical", "technical_details": "Device: iPhone 13"}
    """
    try:
        data = json.loads(ticket_data_json)
    except Exception:
        return json.dumps({"error": f"Invalid JSON input: {ticket_data_json[:200]}"})

    ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "source_id": str(data.get("source_id", "")),
        "source_type": str(data.get("source_type", "")),
        "title": str(data.get("title", "")),
        "category": str(data.get("category", "")),
        "priority": str(data.get("priority", "Medium")),
        "description": str(data.get("description", "")),
        "technical_details": str(data.get("technical_details", "")),
        "platform": str(data.get("platform", "")),
        "app_version": str(data.get("app_version", "")),
        "created_at": datetime.utcnow().isoformat(),
        "status": "Open",
        "confidence_score": str(data.get("confidence_score", "0.0")),
    }
    return json.dumps(ticket)


@tool("Write Tickets to CSV")
def write_tickets_csv(tickets_json: str) -> str:
    """
    Write a list of ticket dicts (JSON array string) to output/generated_tickets.csv.
    Creates the file with headers if it doesn't exist. Returns confirmation message.
    """
    _ensure_csv(TICKETS_CSV, TICKETS_COLUMNS)
    try:
        tickets = json.loads(tickets_json)
        if isinstance(tickets, dict):
            tickets = [tickets]
        with open(TICKETS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=TICKETS_COLUMNS, extrasaction="ignore")
            for t in tickets:
                writer.writerow(t)
        return f"Written {len(tickets)} ticket(s) to {TICKETS_CSV}"
    except Exception as e:
        return f"Error writing tickets: {e}"


@tool("Write Processing Log Entry")
def write_processing_log(log_entry_json: str) -> str:
    """
    Append a log entry dict (JSON string) to output/processing_log.csv.
    Required fields: source_id, source_type, agent, action, confidence.
    Optional: input_category, output_category, notes, processing_time_ms.
    """
    _ensure_csv(PROCESSING_LOG_CSV, PROCESSING_LOG_COLUMNS)
    try:
        entry = json.loads(log_entry_json)
        if isinstance(entry, list):
            entries = entry
        else:
            entries = [entry]
        for e in entries:
            e.setdefault("timestamp", datetime.utcnow().isoformat())
        with open(PROCESSING_LOG_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PROCESSING_LOG_COLUMNS, extrasaction="ignore")
            for e in entries:
                writer.writerow(e)
        return f"Logged {len(entries)} entr(ies) to {PROCESSING_LOG_CSV}"
    except Exception as e:
        return f"Error writing log: {e}"


@tool("Read Generated Tickets CSV")
def read_tickets_csv(action: str) -> str:
    """
    Read the generated_tickets.csv output file and return its contents as a JSON array.
    Use this to review what tickets have been created so far.
    Pass action="read" to load the tickets.
    """
    if not TICKETS_CSV.exists():
        return json.dumps([])
    try:
        import pandas as pd
        df = pd.read_csv(TICKETS_CSV).fillna("")
        return df.to_json(orient="records")
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Write Metrics CSV")
def write_metrics_csv(metrics_json: str) -> str:
    """
    Compute and write a metrics row to output/metrics.csv.
    Auto-reads generated_tickets.csv to compute real category counts.

    Input: a JSON string with any subset of these keys (all optional, will be auto-computed if missing):
      quality_score (float), accuracy_vs_expected (float), avg_confidence (float),
      total_processing_time_s (float)

    Example: {"quality_score": 85.5, "total_processing_time_s": 210.0}
    """
    _ensure_csv(METRICS_CSV, METRICS_COLUMNS)
    try:
        overrides = json.loads(metrics_json) if metrics_json.strip() else {}
    except Exception:
        overrides = {}

    # Auto-compute from generated_tickets.csv
    computed = {
        "total_processed": 0, "bugs": 0, "features": 0,
        "praise": 0, "complaints": 0, "spam": 0, "tickets_created": 0,
    }
    if TICKETS_CSV.exists():
        try:
            import pandas as pd
            df = pd.read_csv(TICKETS_CSV).fillna("")
            computed["tickets_created"] = len(df)
            computed["total_processed"] = len(df)
            cat_counts = df["category"].value_counts().to_dict()
            computed["bugs"] = int(cat_counts.get("Bug", 0))
            computed["features"] = int(cat_counts.get("Feature Request", 0))
            computed["praise"] = int(cat_counts.get("Praise", 0))
            computed["complaints"] = int(cat_counts.get("Complaint", 0))
            computed["spam"] = int(cat_counts.get("Spam", 0))
            if "confidence_score" in df.columns:
                conf_vals = pd.to_numeric(df["confidence_score"], errors="coerce").dropna()
                computed["avg_confidence"] = round(float(conf_vals.mean()), 3) if len(conf_vals) else 0
        except Exception:
            pass

    # Compute accuracy vs expected if both files exist
    accuracy = 0.0
    if TICKETS_CSV.exists():
        try:
            from config.settings import EXPECTED_CSV
            import pandas as pd
            if EXPECTED_CSV.exists():
                tickets = pd.read_csv(TICKETS_CSV).fillna("")
                expected = pd.read_csv(EXPECTED_CSV).fillna("")
                merged = expected.merge(
                    tickets[["source_id", "category"]].rename(columns={"category": "actual"}),
                    on="source_id", how="left"
                )
                merged["match"] = merged["category"] == merged["actual"]
                accuracy = round(merged["match"].sum() / len(merged) * 100, 1) if len(merged) else 0
        except Exception:
            pass

    # Auto-compute quality score by reviewing all tickets internally
    auto_quality = 0.0
    if TICKETS_CSV.exists():
        try:
            import pandas as pd
            tdf = pd.read_csv(TICKETS_CSV).fillna("")
            scores = []
            for _, row in tdf.iterrows():
                result = json.loads(review_ticket.func(row.to_json()))
                scores.append(result.get("quality_score", 0))
            auto_quality = round(sum(scores) / len(scores), 2) if scores else 0.0
        except Exception:
            auto_quality = overrides.get("quality_score", 0)

    metrics = {
        **computed,
        "quality_score": overrides.get("quality_score", auto_quality),
        "accuracy_vs_expected": accuracy,
        "avg_confidence": computed.get("avg_confidence", overrides.get("avg_confidence", 0)),
        "total_processing_time_s": overrides.get("total_processing_time_s", 0),
        "run_id": uuid.uuid4().hex[:8],
        "timestamp": datetime.utcnow().isoformat(),
    }
    metrics.update({k: v for k, v in overrides.items() if k in METRICS_COLUMNS})

    try:
        with open(METRICS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_COLUMNS, extrasaction="ignore")
            writer.writerow(metrics)
        return (
            f"Metrics written: {metrics['tickets_created']} tickets, "
            f"{metrics['bugs']} bugs, {metrics['features']} features, "
            f"{metrics['complaints']} complaints, {metrics['praise']} praise, "
            f"accuracy={metrics['accuracy_vs_expected']}%"
        )
    except Exception as e:
        return f"Error writing metrics: {e}"


@tool("Review Ticket Quality")
def review_ticket(ticket_json: str) -> str:
    """
    Review a ticket dict (JSON string) for completeness and correctness.
    Returns JSON with: quality_score (0-100), issues (list), approved (bool).
    """
    required_fields = ["ticket_id", "source_id", "title", "category", "priority", "description"]
    try:
        ticket = json.loads(ticket_json)
        issues = []
        for field in required_fields:
            if not ticket.get(field, "").strip():
                issues.append(f"Missing required field: {field}")

        if ticket.get("category") == "Bug" and not ticket.get("technical_details", "").strip():
            issues.append("Bug ticket missing technical_details")

        title = ticket.get("title", "")
        if len(title) < 10:
            issues.append("Title too short (< 10 chars)")
        if len(title) > 120:
            issues.append("Title too long (> 120 chars)")

        if ticket.get("priority") not in ["Critical", "High", "Medium", "Low"]:
            issues.append(f"Invalid priority: {ticket.get('priority')}")

        quality_score = max(0, 100 - len(issues) * 20)
        return json.dumps({
            "ticket_id": ticket.get("ticket_id", ""),
            "quality_score": quality_score,
            "issues": issues,
            "approved": quality_score >= 60,
        })
    except Exception as e:
        return json.dumps({"error": str(e), "quality_score": 0, "issues": [str(e)], "approved": False})
