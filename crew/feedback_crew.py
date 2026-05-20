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

# chromadb import hook — crewai 1.x imports chromadb throughout its core.
# chromadb's pydantic v1 Settings breaks on Python 3.14 + uv.
# We install a meta-path finder that intercepts ALL chromadb imports and
# returns smart stub modules. We don't use RAG so stubs never run real code.
try:
    from chromadb.config import Settings as _test_settings  # noqa: F401
except Exception:
    # Remove ALL partial chromadb entries left behind by the failed import.
    # Without this, Python sees chromadb in sys.modules as a non-package
    # module (no __path__) and refuses to import chromadb.config from our hook.
    for _k in list(sys.modules.keys()):
        if _k == "chromadb" or _k.startswith("chromadb."):
            del sys.modules[_k]
    import importlib.machinery

    # pydantic-v2-compatible Settings stub so crewai can build ChromaDBConfig
    try:
        from pydantic_core import core_schema as _core_schema

        class _Settings:
            def __init__(self, **kwargs: object) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

            @classmethod
            def __get_pydantic_core_schema__(
                cls, _source: object, _handler: object
            ) -> object:
                return _core_schema.any_schema()

    except Exception:
        class _Settings:  # type: ignore[no-redef]
            def __init__(self, **kwargs: object) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

    class _ChromaStubModule(types.ModuleType):
        """A stub chromadb module whose attributes auto-return stubs."""

        def __getattr__(self, name: str) -> object:
            # Classes (CamelCase) → return a no-op class
            if name and name[0].isupper():
                if name == "Settings":
                    setattr(self, name, _Settings)
                    return _Settings
                stub_cls = type(name, (), {
                    "__init__": lambda self, *a, **kw: None,
                    "__call__": lambda self, *a, **kw: [],
                    "__class_getitem__": classmethod(lambda cls, *a: cls),
                })
                setattr(self, name, stub_cls)
                return stub_cls
            # Constants / strings
            if name in ("DEFAULT_DATABASE", "DEFAULT_TENANT"):
                return f"default_{name.split('_')[-1].lower()}"
            return None

    class _ChromaStubLoader:
        def create_module(self, spec: object) -> None:
            return None

        def exec_module(self, module: types.ModuleType) -> None:
            module.__class__ = _ChromaStubModule

    class _ChromaFinder:
        def find_spec(
            self,
            name: str,
            path: object = None,
            target: object = None,
        ) -> object:
            if name.startswith("chromadb"):
                return importlib.machinery.ModuleSpec(
                    name, _ChromaStubLoader(), is_package=True
                )
            return None

    sys.meta_path.insert(0, _ChromaFinder())

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
