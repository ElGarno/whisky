"""Whisky Tasting Webapp - Haupteinstiegspunkt."""

import streamlit as st

st.set_page_config(
    page_title="Whisky Sammlung",
    page_icon="🥃",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Whisky Sammlung")

st.markdown("""
Willkommen bei deinem Whisky-Sammlungsmanager!

Nutze die Seitenleiste zur Navigation:
- **Whisky Registrieren** - Füge neue Flaschen per Fotoerkennung hinzu
- **Whisky Info** - Detaillierte Infos zu deinen Whiskies
- **Statistiken** - Erkunde deine Sammlungsanalysen
- **Verkostung** - Führe Verkostungen mit Freunden durch
""")

# Zeige Schnellstatistiken
from services import db

whiskies = db.get_all_whiskies()
stats = db.get_whisky_stats()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Flaschen gesamt", len(whiskies))
with col2:
    st.metric("Gesamtwert", f"{stats[1]:.0f} €" if stats[1] else "0 €")
with col3:
    avg_price = stats[4] if stats[4] else 0
    st.metric("Durchschnittspreis", f"{avg_price:.0f} €")
