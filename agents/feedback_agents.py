from crewai import Agent, LLM
from config.settings import OPENAI_MODEL
from tools.csv_tools import read_reviews_csv, read_emails_csv
from tools.classification_tools import classify_feedback_item, extract_bug_details, extract_feature_details
from tools.ticket_tools import (
    create_ticket, write_tickets_csv, write_processing_log,
    write_metrics_csv, review_ticket, read_tickets_csv,
    create_all_tickets,
)

_llm = LLM(model=f"openai/{OPENAI_MODEL}", temperature=0.1)


csv_reader_agent = Agent(
    role="CSV Data Reader",
    goal=(
        "Read and parse all user feedback from CSV files (app store reviews and support emails), "
        "normalize the data into a unified JSON list, and return it for downstream processing."
    ),
    backstory=(
        "You are a data ingestion specialist who expertly reads raw CSV files, "
        "handles missing values, and produces clean, structured JSON output. "
        "You always validate the data and report any anomalies."
    ),
    tools=[read_reviews_csv, read_emails_csv],
    llm=_llm,
    verbose=True,
    allow_delegation=False,
)

feedback_classifier_agent = Agent(
    role="Feedback Classifier",
    goal=(
        "Classify each feedback item into exactly one category: "
        "Bug, Feature Request, Praise, Complaint, or Spam. "
        "Assign a confidence score (0.0–1.0) to each classification."
    ),
    backstory=(
        "You are an NLP expert specializing in user feedback analysis for SaaS products. "
        "You have classified thousands of app reviews and support emails. "
        "You use keyword signals, sentiment cues, and context to make accurate classifications."
    ),
    tools=[classify_feedback_item],
    llm=_llm,
    verbose=True,
    allow_delegation=False,
)

bug_analysis_agent = Agent(
    role="Bug Analyst",
    goal=(
        "For every item classified as a Bug, extract technical details including: "
        "device, OS version, app version, steps to reproduce, affected feature, and severity. "
        "Assign severity as Critical, High, Medium, or Low based on impact."
    ),
    backstory=(
        "You are a senior QA engineer who has triaged hundreds of bug reports. "
        "You know exactly what information engineering teams need to reproduce and fix bugs. "
        "You are systematic and thorough in extracting technical context from user descriptions."
    ),
    tools=[extract_bug_details],
    llm=_llm,
    verbose=True,
    allow_delegation=False,
)

feature_extractor_agent = Agent(
    role="Feature Analyst",
    goal=(
        "For every item classified as a Feature Request, identify the feature name, "
        "estimate user impact (High/Medium/Low), estimate demand, and describe the use case."
    ),
    backstory=(
        "You are a product manager with deep experience turning user feedback into actionable feature specs. "
        "You understand user needs and can estimate impact and demand from the language users use. "
        "You focus on clarity and actionability in your feature analysis."
    ),
    tools=[extract_feature_details],
    llm=_llm,
    verbose=True,
    allow_delegation=False,
)

ticket_creator_agent = Agent(
    role="Ticket Creator",
    goal=(
        "Generate a structured, well-formatted ticket for every feedback item "
        "(excluding Spam and Praise which only need a brief log entry). "
        "Write all tickets to the output CSV file. "
        "Each ticket must have a clear title, description, category, priority, and technical details for bugs."
    ),
    backstory=(
        "You are an experienced project manager who has created thousands of engineering tickets. "
        "You know how to write clear, actionable titles and descriptions that engineers can act on immediately. "
        "You prioritize correctly based on severity and user impact."
    ),
    tools=[create_all_tickets, write_metrics_csv],
    llm=_llm,
    verbose=True,
    allow_delegation=False,
)

quality_critic_agent = Agent(
    role="Quality Reviewer",
    goal=(
        "Review all generated tickets for completeness, correctness, and consistency. "
        "Flag any tickets with missing fields, incorrect priorities, or unclear descriptions. "
        "Compute quality metrics and write the final processing log and metrics CSV."
    ),
    backstory=(
        "You are a meticulous quality assurance specialist who reviews engineering artifacts "
        "before they go into the backlog. You enforce standards and catch issues early. "
        "You generate clear quality reports and actionable metrics for the team."
    ),
    tools=[read_tickets_csv, review_ticket, write_processing_log, write_metrics_csv],
    llm=_llm,
    verbose=True,
    allow_delegation=False,
)
