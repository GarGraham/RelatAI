"""Streamlit prototype entrypoint for RelatAI."""

import streamlit as st

st.set_page_config(page_title="RelatAI", layout="wide")

st.title("RelatAI Prototype")
st.markdown(
    """
    Upload a dataset to explore automatic correlation insights.
    This prototype will connect to the backend API in future milestones.
    """
)

uploaded_file = st.file_uploader("Upload CSV, Parquet, or Excel", type=["csv", "parquet", "xlsx"])
if uploaded_file:
    st.success(f"Received file: {uploaded_file.name}")
    st.info("Backend integration will be implemented in upcoming milestones.")
