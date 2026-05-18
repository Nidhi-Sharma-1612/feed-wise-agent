import pandas as pd
import streamlit as st
from config.settings import TICKETS_CSV, CATEGORIES, PRIORITIES


def render():
    st.header("Manual Override")
    st.caption("Edit generated tickets inline. Changes are saved back to generated_tickets.csv.")

    if not TICKETS_CSV.exists():
        st.info("No tickets file found. Run the pipeline first.")
        return

    df = pd.read_csv(TICKETS_CSV)
    if df.empty:
        st.info("No tickets to display. Run the pipeline to generate tickets.")
        return

    st.subheader(f"Edit Tickets ({len(df)} total)")

    editable_cols = ["title", "category", "priority", "status", "description", "technical_details"]
    available_editable = [c for c in editable_cols if c in df.columns]

    column_config = {
        "category": st.column_config.SelectboxColumn("Category", options=CATEGORIES, required=True),
        "priority": st.column_config.SelectboxColumn("Priority", options=PRIORITIES, required=True),
        "status": st.column_config.SelectboxColumn(
            "Status", options=["Open", "In Progress", "Resolved", "Closed", "Rejected"], required=True
        ),
        "title": st.column_config.TextColumn("Title", max_chars=120),
        "description": st.column_config.TextColumn("Description"),
        "technical_details": st.column_config.TextColumn("Technical Details"),
    }

    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Save Changes", type="primary"):
            edited_df.to_csv(TICKETS_CSV, index=False)
            st.success("Tickets saved successfully.")

    with col2:
        if st.button("Approve All Open"):
            edited_df.loc[edited_df["status"] == "Open", "status"] = "In Progress"
            edited_df.to_csv(TICKETS_CSV, index=False)
            st.success("All Open tickets set to In Progress.")
            st.rerun()

    st.divider()
    st.subheader("Bulk Actions")

    col_a, col_b = st.columns(2)
    with col_a:
        filter_cat = st.selectbox("Filter by Category", ["All"] + CATEGORIES)
    with col_b:
        new_status = st.selectbox("Set Status", ["Open", "In Progress", "Resolved", "Closed", "Rejected"])

    if st.button("Apply Status to Filtered"):
        mask = edited_df["category"] == filter_cat if filter_cat != "All" else pd.Series([True] * len(edited_df))
        edited_df.loc[mask, "status"] = new_status
        edited_df.to_csv(TICKETS_CSV, index=False)
        st.success(f"Updated {mask.sum()} tickets to '{new_status}'.")
        st.rerun()
