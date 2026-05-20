import os
import sys
import time
import types
import importlib.metadata

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")

# Fix Windows charmap encoding for CrewAI emoji output
encoding = getattr(sys.stdout, "encoding", None)
if isinstance(encoding, str) and encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# pkg_resources shim — some crewai versions import pkg_resources in telemetry,
# but Python 3.14 + uv don't expose it even when setuptools is installed.
try:
    import pkg_resources  # noqa: F401
except ImportError:
    _shim = types.ModuleType("pkg_resources")

    def _get_distribution(name: str):
        try:
            version = importlib.metadata.version(name)
        except Exception:
            version = "0.0.0"
        return types.SimpleNamespace(version=version)

    _shim.get_distribution = _get_distribution
    _shim.require = lambda *_args, **_kwargs: None
    _shim.resource_string = lambda *_args, **_kwargs: b""
    sys.modules["pkg_resources"] = _shim

# chromadb blocker — crewai 1.x tries to import chromadb for RAG/knowledge features.
# chromadb uses pydantic v1 internally which breaks on Python 3.14.
# Blocking it here forces crewai to use its MissingChromaDBConfig fallback.
# We don't use RAG features so this has no functional impact.
try:
    import chromadb  # noqa: F401
except Exception:
    for _mod in [k for k in sys.modules if k.startswith("chromadb")]:
        sys.modules[_mod] = None  # type: ignore[assignment]
    sys.modules.setdefault("chromadb", None)  # type: ignore[assignment]

from crewai import Crew, Process
from agents.feedback_agents import (
    csv_reader_agent,
    feedback_classifier_agent,
    bug_analysis_agent,
    feature_extractor_agent,
    ticket_creator_agent,
    quality_critic_agent,
)
from tasks.feedback_tasks import (
    read_feedback_task,
    classify_feedback_task,
    analyze_bugs_task,
    extract_features_task,
    create_tickets_task,
    quality_review_task,
)
from config.settings import TICKETS_CSV, PROCESSING_LOG_CSV, METRICS_CSV, OUTPUT_DIR


def build_crew() -> Crew:
    return Crew(
        agents=[
            csv_reader_agent,
            feedback_classifier_agent,
            bug_analysis_agent,
            feature_extractor_agent,
            ticket_creator_agent,
            quality_critic_agent,
        ],
        tasks=[
            read_feedback_task,
            classify_feedback_task,
            analyze_bugs_task,
            extract_features_task,
            create_tickets_task,
            quality_review_task,
        ],
        process=Process.sequential,
        verbose=True,
    )


def run_pipeline() -> dict:
    """Run the full feedback analysis pipeline.

    Returns dict with keys: success, quality_report, output_files, elapsed_seconds.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    for csv_path in [TICKETS_CSV, PROCESSING_LOG_CSV, METRICS_CSV]:
        if csv_path.exists():
            csv_path.unlink()

    crew = build_crew()
    start = time.time()
    try:
        crew_output = crew.kickoff()
        elapsed = round(time.time() - start, 1)
        return {
            "success": True,
            "quality_report": str(crew_output),
            "output_files": {
                "tickets": str(TICKETS_CSV),
                "processing_log": str(PROCESSING_LOG_CSV),
                "metrics": str(METRICS_CSV),
            },
            "elapsed_seconds": elapsed,
        }
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        return {
            "success": False,
            "error": str(e),
            "output_files": {},
            "elapsed_seconds": elapsed,
        }


if __name__ == "__main__":
    run_result = run_pipeline()
    print("\n=== PIPELINE RESULT ===")
    print(f"Success: {run_result['success']}")
    print(f"Elapsed: {run_result['elapsed_seconds']}s")
    if run_result.get("quality_report"):
        print("\nQuality Report:")
        print(run_result["quality_report"])
    if run_result.get("error"):
        print(f"Error: {run_result['error']}")
