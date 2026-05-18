import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from config.settings import TICKETS_CSV, METRICS_CSV, EXPECTED_CSV


def _load_csv(path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def render():
    st.header("Analytics")

    tickets_df = _load_csv(TICKETS_CSV)
    metrics_df = _load_csv(METRICS_CSV)
    expected_df = _load_csv(EXPECTED_CSV)

    if tickets_df.empty:
        st.info("No data yet. Run the pipeline to see analytics.")
        return

    # --- Processing Metrics ---
    if not metrics_df.empty:
        st.subheader("Pipeline Run Metrics")
        latest = metrics_df.iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Processed", int(latest.get("total_processed", 0)))
        m2.metric("Tickets Created", int(latest.get("tickets_created", 0)))
        m3.metric("Quality Score", f"{float(latest.get('quality_score', 0)):.0f}/100")
        m4.metric("Processing Time", f"{float(latest.get('total_processing_time_s', 0)):.1f}s")

        if len(metrics_df) > 1:
            st.subheader("Run History")
            hist = metrics_df[["timestamp", "total_processed", "tickets_created", "quality_score"]].copy()
            hist["timestamp"] = pd.to_datetime(hist["timestamp"]).dt.strftime("%H:%M:%S")
            st.dataframe(hist, use_container_width=True, hide_index=True)

        st.divider()

    # --- Category Distribution ---
    st.subheader("Category Distribution")
    cat_counts = tickets_df["category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]

    fig_cat = px.bar(
        cat_counts, x="Category", y="Count",
        color="Category",
        color_discrete_map={
            "Bug": "#FF4B4B", "Feature Request": "#1E90FF",
            "Praise": "#4CAF50", "Complaint": "#FF8C00", "Spam": "#9E9E9E",
        },
        title="Tickets by Category",
    )
    st.plotly_chart(fig_cat, use_container_width=True)

    # --- Priority Distribution ---
    st.subheader("Priority Distribution")
    if "priority" in tickets_df.columns:
        pri_counts = tickets_df["priority"].value_counts().reset_index()
        pri_counts.columns = ["Priority", "Count"]
        fig_pri = px.pie(
            pri_counts, names="Priority", values="Count",
            color="Priority",
            color_discrete_map={
                "Critical": "#FF4B4B", "High": "#FF8C00",
                "Medium": "#FFD700", "Low": "#4CAF50",
            },
            title="Tickets by Priority",
        )
        st.plotly_chart(fig_pri, use_container_width=True)

    st.divider()

    # --- Accuracy vs Expected ---
    st.subheader("Classification Accuracy vs Expected")
    if expected_df.empty:
        st.info("expected_classifications.csv not found — cannot compute accuracy.")
        return

    if "source_id" not in tickets_df.columns or "category" not in tickets_df.columns:
        st.warning("Tickets file missing source_id or category column.")
        return

    merged = expected_df.merge(
        tickets_df[["source_id", "category"]].rename(columns={"category": "actual_category"}),
        on="source_id", how="left",
    )
    merged["match"] = merged["category"] == merged["actual_category"]
    matched = merged["match"].sum()
    total = len(merged)
    accuracy = matched / total * 100 if total > 0 else 0

    acc1, acc2, acc3 = st.columns(3)
    acc1.metric("Expected Items", total)
    acc2.metric("Correctly Classified", int(matched))
    acc3.metric("Accuracy", f"{accuracy:.1f}%")

    # Per-category accuracy
    if not merged.empty:
        per_cat = merged.groupby("category").agg(
            total=("match", "count"),
            correct=("match", "sum"),
        ).reset_index()
        per_cat["accuracy_%"] = (per_cat["correct"] / per_cat["total"] * 100).round(1)

        fig_acc = px.bar(
            per_cat, x="category", y="accuracy_%",
            color="category",
            title="Accuracy by Expected Category",
            labels={"accuracy_%": "Accuracy (%)", "category": "Category"},
            range_y=[0, 105],
        )
        fig_acc.add_hline(y=80, line_dash="dash", line_color="red",
                          annotation_text="80% target", annotation_position="top right")
        st.plotly_chart(fig_acc, use_container_width=True)

    # Show misclassified items
    with st.expander("Show Misclassified Items"):
        wrong = merged[~merged["match"]][["source_id", "source_type", "category", "actual_category"]]
        if wrong.empty:
            st.success("No misclassifications found!")
        else:
            wrong.columns = ["Source ID", "Type", "Expected", "Actual"]
            st.dataframe(wrong, use_container_width=True, hide_index=True)
