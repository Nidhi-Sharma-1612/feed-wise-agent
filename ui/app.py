import sys
import os

# Make project root importable when running from ui/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import streamlit as st
from ui.sections import dashboard_page, config_page, override_page, analytics_page
from storage.session_store import save_run_result, get_last_run

st.set_page_config(
    page_title="FeedWise Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
with st.sidebar:
    st.title("🔍 FeedWise Agent")
    st.caption("Intelligent User Feedback Analysis")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Dashboard", "Configuration", "Manual Override", "Analytics"],
        index=0,
    )

    st.divider()
    st.subheader("Run Pipeline")

    if st.button("▶ Run Full Pipeline", type="primary", use_container_width=True):
        with st.spinner("Running multi-agent pipeline... This may take a few minutes."):
            from crew.feedback_crew import run_pipeline
            result = run_pipeline()
            save_run_result(result)
            st.session_state["last_result"] = result
        if result["success"]:
            st.success(f"Pipeline complete in {result['elapsed_seconds']}s")
        else:
            st.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")

    last = get_last_run()
    if last:
        status = "✅ Success" if last.get("success") else "❌ Failed"
        st.caption(f"Last run: {status} ({last.get('elapsed_seconds', '?')}s)")

    st.divider()
    st.caption("Capstone Project — Agentic AI Certification")

# --- Main content ---
if page == "Dashboard":
    dashboard_page.render()
elif page == "Configuration":
    config_page.render()
elif page == "Manual Override":
    override_page.render()
elif page == "Analytics":
    analytics_page.render()
