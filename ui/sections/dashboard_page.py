import pandas as pd
import streamlit as st
from config.settings import TICKETS_CSV, CATEGORIES, PRIORITIES


PRIORITY_COLORS = {
    "Critical": "#FF4B4B",
    "High": "#FF8C00",
    "Medium": "#FFD700",
    "Low": "#4CAF50",
}

CATEGORY_COLORS = {
    "Bug": "#FF4B4B",
    "Feature Request": "#1E90FF",
    "Praise": "#4CAF50",
    "Complaint": "#FF8C00",
    "Spam": "#9E9E9E",
}


def _priority_badge(priority: str) -> str:
    color = PRIORITY_COLORS.get(priority, "#9E9E9E")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600">{priority}</span>'


def _category_badge(cat: str) -> str:
    color = CATEGORY_COLORS.get(cat, "#9E9E9E")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600">{cat}</span>'


def render():
    st.header("Dashboard")

    if not TICKETS_CSV.exists():
        st.info("No tickets yet. Run the pipeline from the sidebar to generate tickets.")
        return

    df = pd.read_csv(TICKETS_CSV)
    if df.empty:
        st.info("Tickets file is empty. Run the pipeline to generate tickets.")
        return

    # Summary stats
    total = len(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Tickets", total)
    col2.metric("Bugs", len(df[df["category"] == "Bug"]))
    col3.metric("Features", len(df[df["category"] == "Feature Request"]))
    col4.metric("Complaints", len(df[df["category"] == "Complaint"]))
    col5.metric("Praise", len(df[df["category"] == "Praise"]))

    st.divider()

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        cat_filter = st.multiselect("Filter by Category", CATEGORIES, default=CATEGORIES)
    with filter_col2:
        pri_filter = st.multiselect("Filter by Priority", PRIORITIES, default=PRIORITIES)
    with filter_col3:
        sort_by = st.selectbox("Sort by", ["created_at", "priority", "category", "ticket_id"])

    filtered = df[df["category"].isin(cat_filter) & df["priority"].isin(pri_filter)]

    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    if sort_by == "priority":
        filtered = filtered.copy()
        filtered["_sort"] = filtered["priority"].map(priority_order)
        filtered = filtered.sort_values("_sort").drop(columns=["_sort"])
    else:
        filtered = filtered.sort_values(sort_by, ascending=False)

    st.subheader(f"Tickets ({len(filtered)})")

    display_cols = ["ticket_id", "source_id", "source_type", "title", "category", "priority", "status", "created_at"]
    available = [c for c in display_cols if c in filtered.columns]
    st.dataframe(filtered[available], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Category Breakdown")
    cat_counts = df["category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    st.bar_chart(cat_counts.set_index("Category"))
