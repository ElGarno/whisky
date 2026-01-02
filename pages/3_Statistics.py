"""Statistiken und Analysen für die Whisky-Sammlung."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db

st.set_page_config(page_title="Statistiken", page_icon="📊", layout="wide")
st.title("Sammlungsstatistiken")

# Daten abrufen
whiskies = db.get_all_whiskies()
stats = db.get_whisky_stats()

if not whiskies:
    st.info("Noch keine Whiskies in deiner Sammlung. Füge welche auf der Registrieren-Seite hinzu!")
    st.stop()

# Übersichts-Metriken
st.subheader("Übersicht")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Flaschen gesamt", stats[0])
with col2:
    st.metric("Gesamtwert", f"{stats[1]:.0f} €" if stats[1] else "0 €")
with col3:
    st.metric("Durchschnittspreis", f"{stats[4]:.0f} €" if stats[4] else "0 €")
with col4:
    price_range = f"{stats[2]:.0f} € - {stats[3]:.0f} €" if stats[2] else "-"
    st.metric("Preisspanne", price_range)

st.divider()

# Zwei-Spalten-Layout
col_left, col_right = st.columns(2)

with col_left:
    # Altersverteilung
    st.subheader("Altersverteilung")
    age_data = db.get_age_distribution()

    if age_data:
        df_age = pd.DataFrame(age_data, columns=["Jahr", "Anzahl"])
        fig = px.bar(
            df_age,
            x="Jahr",
            y="Anzahl",
            title="Whiskies nach Altersangabe",
            labels={"Jahr": "Alter (Jahre)", "Anzahl": "Anzahl Flaschen"}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Altersdaten verfügbar")

    # Füllstände
    st.subheader("Füllstände")
    fill_data = db.get_fill_levels()

    if fill_data:
        df_fill = pd.DataFrame(fill_data, columns=["Name", "Aktuell ML", "Flaschen ML", "Füllstand %"])

        # Farbcodierung nach Füllstand
        colors = []
        for pct in df_fill["Füllstand %"]:
            if pct >= 75:
                colors.append("#22c55e")  # grün
            elif pct >= 50:
                colors.append("#eab308")  # gelb
            elif pct >= 25:
                colors.append("#f97316")  # orange
            else:
                colors.append("#ef4444")  # rot

        fig = go.Figure(go.Bar(
            x=df_fill["Füllstand %"],
            y=df_fill["Name"],
            orientation='h',
            marker_color=colors,
            text=df_fill["Füllstand %"].apply(lambda x: f"{x:.0f}%"),
            textposition='outside'
        ))
        fig.update_layout(
            title="Flaschen-Füllstände",
            xaxis_title="Füllstand %",
            yaxis_title="",
            height=max(300, len(fill_data) * 40)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Füllstanddaten verfügbar")

with col_right:
    # Preisverteilung
    st.subheader("Preisverteilung")

    prices = [w[4] for w in whiskies if w[4]]
    if prices:
        fig = px.histogram(
            x=prices,
            nbins=10,
            title="Preisverteilung",
            labels={"x": "Preis (€)", "y": "Anzahl"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Preisdaten verfügbar")

    # Nach Brennerei
    st.subheader("Nach Brennerei")

    distillery_counts = {}
    for w in whiskies:
        dist = w[3] or "Unbekannt"
        distillery_counts[dist] = distillery_counts.get(dist, 0) + 1

    if distillery_counts:
        df_dist = pd.DataFrame([
            {"Brennerei": k, "Anzahl": v}
            for k, v in sorted(distillery_counts.items(), key=lambda x: -x[1])
        ])

        fig = px.pie(
            df_dist,
            names="Brennerei",
            values="Anzahl",
            title="Flaschen nach Brennerei"
        )
        st.plotly_chart(fig, use_container_width=True)

# Karte
st.divider()
st.subheader("Brennerei-Karte")

distilleries = db.get_all_distilleries()

if distilleries:
    # Karte zentriert auf Schottland (Standard)
    m = folium.Map(location=[56.5, -4.5], zoom_start=5)

    for d in distilleries:
        # d: (id, name, region, country, latitude, longitude, logo_path)
        if d[4] and d[5]:  # lat und lng
            # Zähle Whiskies von dieser Brennerei
            count = sum(1 for w in whiskies if w[3] == d[1])

            popup_text = f"""
            <b>{d[1]}</b><br>
            Region: {d[2] or 'Unbekannt'}<br>
            Land: {d[3] or 'Unbekannt'}<br>
            Flaschen: {count}
            """

            folium.Marker(
                location=[d[4], d[5]],
                popup=folium.Popup(popup_text, max_width=200),
                tooltip=d[1],
                icon=folium.Icon(color='red', icon='glass', prefix='fa')
            ).add_to(m)

    st_folium(m, width=None, height=500, use_container_width=True)
else:
    st.info("Noch keine Brennerei-Standorte verfügbar. Füge Whiskies hinzu um die Karte zu füllen!")

# Warnung bei niedrigem Füllstand
st.divider()
st.subheader("Bald leer")

low_bottles = [
    (w[1], w[5] / w[6] * 100 if w[6] else 0)
    for w in whiskies
    if w[6] and (w[5] / w[6] * 100) < 25
]

if low_bottles:
    st.warning(f"{len(low_bottles)} Flasche(n) fast leer!")
    for name, pct in sorted(low_bottles, key=lambda x: x[1]):
        st.write(f"- **{name}**: {pct:.0f}% verbleibend")
else:
    st.success("Alle Flaschen haben noch genug Inhalt!")
