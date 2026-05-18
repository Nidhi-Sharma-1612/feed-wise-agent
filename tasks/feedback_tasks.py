from crewai import Task
from agents.feedback_agents import (
    csv_reader_agent,
    feedback_classifier_agent,
    bug_analysis_agent,
    feature_extractor_agent,
    ticket_creator_agent,
    quality_critic_agent,
)
from config.settings import REVIEWS_CSV, EMAILS_CSV


read_feedback_task = Task(
    description=(
        "Read all user feedback from the two CSV files:\n"
        f"  - App store reviews: {REVIEWS_CSV}\n"
        f"  - Support emails: {EMAILS_CSV}\n\n"
        "Use the 'Read App Store Reviews CSV' tool with filepath='default', "
        "then the 'Read Support Emails CSV' tool with filepath='default'. "
        "Combine both result lists into a single unified JSON array. "
        "Each item must have: source_id, source_type, text, platform, rating, "
        "user_name, date, app_version. "
        "Return the full combined JSON array as your final answer."
    ),
    expected_output=(
        "A JSON array containing all feedback items (reviews + emails) "
        "with normalized fields: source_id, source_type, text, platform, rating, "
        "user_name, date, app_version. Example: "
        '[{"source_id": "R001", "source_type": "review", "text": "...", ...}, ...]'
    ),
    agent=csv_reader_agent,
)

classify_feedback_task = Task(
    description=(
        "You will receive a JSON array of feedback items from the previous task.\n\n"
        "For EACH item in the array, call the 'Classify Feedback Item' tool. "
        "Pass a JSON string as input, e.g.: "
        '\'{"text": "<item text>", "rating": "<item rating>"}\'. '
        "Add the returned 'category' and 'confidence' fields to each item. "
        "Return the complete updated JSON array with classification results added to every item."
    ),
    expected_output=(
        "The same JSON array with two new fields added to each item: "
        "'category' (one of: Bug, Feature Request, Praise, Complaint, Spam) "
        "and 'confidence' (float 0.0-1.0). "
        'Example: [{"source_id": "R001", ..., "category": "Bug", "confidence": 0.85}, ...]'
    ),
    agent=feedback_classifier_agent,
    context=[read_feedback_task],
)

analyze_bugs_task = Task(
    description=(
        "You will receive the classified feedback JSON array from the previous task.\n\n"
        "Filter to items where category == 'Bug'. "
        "For each bug item, call the 'Extract Bug Details' tool. "
        "Pass a JSON string as input, e.g.: "
        '\'{"text": "<bug text>", "platform": "<platform>", "app_version": "<version>"}\'. '
        "Add a 'bug_details' field to each bug item containing the returned JSON. "
        "Return ONLY the bug items (with bug_details added) as a JSON array. "
        "If there are no bugs, return an empty array []."
    ),
    expected_output=(
        "A JSON array of bug items only, each with an added 'bug_details' object containing: "
        "device, os_version, app_version, steps_to_reproduce, severity, affected_feature. "
        'Example: [{"source_id": "R001", "category": "Bug", "bug_details": {...}}, ...]'
    ),
    agent=bug_analysis_agent,
    context=[classify_feedback_task],
)

extract_features_task = Task(
    description=(
        "You will receive the classified feedback JSON array from the classification task.\n\n"
        "Filter to items where category == 'Feature Request'. "
        "For each feature item, call the 'Extract Feature Details' tool with the item's 'text' field. "
        "Add a 'feature_details' field to each feature item containing the returned JSON. "
        "Return ONLY the feature request items (with feature_details added) as a JSON array. "
        "If there are no feature requests, return an empty array []."
    ),
    expected_output=(
        "A JSON array of feature request items only, each with an added 'feature_details' object: "
        "feature_name, user_impact, demand_estimate, use_case. "
        'Example: [{"source_id": "R006", "category": "Feature Request", "feature_details": {...}}, ...]'
    ),
    agent=feature_extractor_agent,
    context=[classify_feedback_task],
)

create_tickets_task = Task(
    description=(
        "You have the classified feedback array from classify_feedback_task "
        "(all 30 items with 'category' and 'confidence' fields).\n\n"
        "Call the 'Create All Tickets From Classified Feedback' tool ONCE.\n"
        "Pass the COMPLETE classified JSON array exactly as returned by classify_feedback_task.\n"
        "Do NOT truncate or filter — include ALL items (reviews AND emails).\n\n"
        "The tool internally handles bug/feature enrichment, priority assignment, "
        "deduplication, and writes generated_tickets.csv and processing_log.csv.\n\n"
        "Return the JSON summary that the tool returns."
    ),
    expected_output=(
        "JSON: {tickets_created: <int>, skipped_spam: <int>, "
        "categories: {Bug: N, Feature Request: N, Complaint: N, Praise: N}}. "
        "Expect approximately 26 tickets and 4 spam skipped from 30 total items."
    ),
    agent=ticket_creator_agent,
    context=[classify_feedback_task, analyze_bugs_task, extract_features_task],
)

quality_review_task = Task(
    description=(
        "You are the Quality Reviewer. Your job is to review all generated tickets and write metrics.\n\n"
        "Step 1: Call 'Read Generated Tickets CSV' with input 'read' to load all tickets.\n\n"
        "Step 2: For each ticket in the list, call 'Review Ticket Quality' with the ticket "
        "as a JSON string. Collect all quality scores.\n\n"
        "Step 3: Compute the average quality_score across all tickets.\n\n"
        "Step 4: Call 'Write Metrics CSV' with a JSON string containing:\n"
        '  {"quality_score": <avg score>, "total_processing_time_s": <seconds>}\n'
        "The tool will auto-compute category counts and accuracy from the CSV files.\n\n"
        "Step 5: Call 'Write Processing Log Entry' with a JSON string for the final summary:\n"
        '  {"source_id": "SUMMARY", "source_type": "system", "agent": "Quality Reviewer",\n'
        '   "action": "quality_review_complete", "confidence": <avg_score/100>,\n'
        '   "notes": "<N> tickets reviewed, avg quality <score>/100"}\n\n'
        "Step 6: Return a human-readable quality report."
    ),
    expected_output=(
        "A quality report with: total tickets reviewed, average quality score, "
        "category breakdown, flagged issues, accuracy vs expected, and confirmation "
        "that metrics.csv and processing_log.csv were updated."
    ),
    agent=quality_critic_agent,
    context=[create_tickets_task],
)
