"""Whisky Tasting Webapp - Main Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="Whisky Collection",
    page_icon="🥃",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Whisky Collection")

st.markdown("""
Welcome to your whisky collection manager!

Use the sidebar to navigate:
- **Register Whisky** - Add new bottles via photo recognition
- **Whisky Info** - View detailed info about your whiskies
- **Statistics** - Explore your collection analytics
- **Tasting** - Run tasting sessions with friends
""")

# Show quick stats
from services import db

whiskies = db.get_all_whiskies()
stats = db.get_whisky_stats()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Bottles", len(whiskies))
with col2:
    st.metric("Total Value", f"${stats[1]:.0f}" if stats[1] else "$0")
with col3:
    avg_price = stats[4] if stats[4] else 0
    st.metric("Avg Price", f"${avg_price:.0f}")
