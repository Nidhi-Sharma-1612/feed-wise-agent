import json
from pathlib import Path
import streamlit as st

_OVERRIDE_FILE = Path(__file__).parent.parent.parent / "output" / "config_overrides.json"


def _load_overrides() -> dict:
    if _OVERRIDE_FILE.exists():
        try:
            return json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_overrides(data: dict) -> None:
    _OVERRIDE_FILE.parent.mkdir(exist_ok=True)
    _OVERRIDE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def render():
    st.header("Configuration")
    st.caption("Adjust classification thresholds and priority mappings. Changes apply to the next pipeline run.")

    overrides = _load_overrides()

    st.subheader("Classification Settings")
    confidence_threshold = st.slider(
        "Minimum Confidence Threshold",
        min_value=0.0, max_value=1.0,
        value=float(overrides.get("confidence_threshold", 0.70)),
        step=0.05,
        help="Items with confidence below this will be flagged for manual review.",
    )

    st.subheader("Priority Rules")
    st.caption("Map (Category, Max Rating) → Priority. These control how tickets are prioritized.")

    priority_options = ["Critical", "High", "Medium", "Low"]

    col1, col2 = st.columns(2)
    with col1:
        bug_critical = st.selectbox("Bug, Rating ≤ 1 →", priority_options,
                                    index=priority_options.index(overrides.get("bug_critical", "Critical")))
        bug_high = st.selectbox("Bug, Rating ≤ 2 →", priority_options,
                                index=priority_options.index(overrides.get("bug_high", "High")))
        bug_medium = st.selectbox("Bug, Rating > 2 →", priority_options,
                                  index=priority_options.index(overrides.get("bug_medium", "Medium")))
    with col2:
        feature_priority = st.selectbox("Feature Request →", priority_options,
                                        index=priority_options.index(overrides.get("feature_priority", "Medium")))
        complaint_high = st.selectbox("Complaint, Rating ≤ 2 →", priority_options,
                                      index=priority_options.index(overrides.get("complaint_high", "High")))
        complaint_low = st.selectbox("Complaint, Rating > 2 →", priority_options,
                                     index=priority_options.index(overrides.get("complaint_low", "Low")))

    st.subheader("Model Settings")
    model = st.selectbox(
        "OpenAI Model",
        ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"].index(overrides.get("model", "gpt-4o-mini")),
    )

    if st.button("Save Configuration", type="primary"):
        new_overrides = {
            "confidence_threshold": confidence_threshold,
            "bug_critical": bug_critical,
            "bug_high": bug_high,
            "bug_medium": bug_medium,
            "feature_priority": feature_priority,
            "complaint_high": complaint_high,
            "complaint_low": complaint_low,
            "model": model,
        }
        _save_overrides(new_overrides)
        st.success("Configuration saved. These settings will apply to the next pipeline run.")

    if st.button("Reset to Defaults"):
        if _OVERRIDE_FILE.exists():
            _OVERRIDE_FILE.unlink()
        st.rerun()
