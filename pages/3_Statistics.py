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
from services import db, ai
from services.auth import require_auth, show_logout_button

st.set_page_config(page_title="Statistiken", page_icon="📊", layout="wide")

if not require_auth():
    st.stop()
show_logout_button()

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

    # Cocktail-Vorschläge für fast leere Flaschen
    st.divider()
    st.subheader("🍹 Cocktail-Ideen für fast leere Flaschen")
    st.write("Bevor du die letzten Tropfen wegschüttest...")

    for whisky in whiskies:
        # whisky: (id, name, year, distillery, price, fill_ml, bottle_size, image_path, info_markdown, quantity)
        if whisky[6] and whisky[5]:
            fill_pct = whisky[5] / whisky[6] * 100
            if fill_pct < 25:
                with st.expander(f"🥃 {whisky[1]} ({whisky[5]}ml übrig)"):
                    if st.button(f"Cocktails vorschlagen", key=f"cocktail_{whisky[0]}"):
                        with st.spinner("Suche passende Cocktails..."):
                            try:
                                suggestions = ai.suggest_cocktails(
                                    whisky[1],
                                    whisky[3] or "Unbekannt",
                                    whisky[5]
                                )

                                st.info(suggestions['message'])

                                for cocktail in suggestions['cocktails']:
                                    st.write(f"### 🍸 {cocktail['name']}")
                                    st.write(cocktail['description'])
                                    st.write("**Zutaten:**")
                                    for ingredient in cocktail['ingredients']:
                                        st.write(f"- {ingredient}")
                                    st.caption(f"Benötigt: {cocktail['ml_needed']}ml Whisky")
                                    st.divider()

                                st.success(f"💡 Oder doch lieber pur? {suggestions['neat_suggestion']}")

                            except Exception as e:
                                st.error(f"Fehler: {e}")
else:
    st.success("Alle Flaschen haben noch genug Inhalt!")

# Collection Health Score
st.divider()
st.subheader("🏥 Sammlungs-Gesundheitscheck")
st.write("Wie ausgewogen ist deine Whisky-Sammlung?")

if st.button("Sammlung analysieren", type="primary"):
    whiskies_with_regions = db.get_whiskies_with_regions()

    whisky_data = [
        {
            "name": w[1],
            "distillery": w[2],
            "region": w[3],
            "year": w[4],
            "price": float(w[5]) if w[5] else 0,
            "fill_pct": float(w[6]) if w[6] else 100
        }
        for w in whiskies_with_regions
    ]

    stats_dict = {
        "total_bottles": stats[0],
        "total_value": float(stats[1]) if stats[1] else 0,
        "avg_price": float(stats[4]) if stats[4] else 0
    }

    with st.spinner("Analysiere deine Sammlung..."):
        try:
            health = ai.analyze_collection_health(whisky_data, stats_dict)

            # Health Score Anzeige
            col1, col2 = st.columns([1, 2])

            with col1:
                score = health['health_score']
                color = "#22c55e" if score >= 70 else "#eab308" if score >= 40 else "#ef4444"

                st.markdown(f"""
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 4em; font-weight: bold; color: {color};">{score}</div>
                    <div style="font-size: 1.2em; color: #888;">von 100 Punkten</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # Breakdown als Balkendiagramm
                breakdown = health['score_breakdown']
                categories = ['Vielfalt', 'Wert', 'Füllstände', 'Altersspanne']
                values = [
                    breakdown.get('diversity', 0),
                    breakdown.get('value', 0),
                    breakdown.get('fill_levels', 0),
                    breakdown.get('age_range', 0)
                ]

                fig = go.Figure(go.Bar(
                    x=values,
                    y=categories,
                    orientation='h',
                    marker_color=['#3b82f6', '#22c55e', '#eab308', '#8b5cf6'],
                    text=values,
                    textposition='outside'
                ))
                fig.update_layout(
                    xaxis_range=[0, 100],
                    height=200,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)

            # Stärken und Schwächen
            col1, col2 = st.columns(2)

            with col1:
                st.write("### ✅ Stärken")
                for strength in health.get('strengths', []):
                    st.write(f"- {strength}")

            with col2:
                st.write("### ⚠️ Lücken")
                for gap in health.get('gaps', []):
                    st.write(f"- {gap}")

            # Empfehlungen
            st.divider()
            st.write("### 🛒 Empfehlungen für deine Sammlung")

            for rec in health.get('recommendations', []):
                col1, col2, col3 = st.columns([2, 3, 1])
                with col1:
                    st.write(f"**{rec['whisky']}**")
                with col2:
                    st.write(rec['reason'])
                with col3:
                    st.write(rec['price_range'])

        except Exception as e:
            st.error(f"Fehler bei der Analyse: {e}")

# Participant Analytics
st.divider()
st.subheader("👥 Teilnehmer-Statistiken")

participant_analytics = db.get_participant_analytics()

if not participant_analytics:
    st.info("Noch keine Bewertungsdaten vorhanden. Führe erst eine Verkostung durch!")
else:
    # Übersichtstabelle
    df_participants = pd.DataFrame([
        {
            "Teilnehmer": p[0],
            "Bewertungen": p[1],
            "Ø Punkte": p[2],
            "Min": p[3],
            "Max": p[4],
            "Std.Abw.": p[5] if p[5] else 0
        }
        for p in participant_analytics
    ])

    st.dataframe(df_participants, use_container_width=True, hide_index=True)

    # Insights
    if len(participant_analytics) >= 2:
        st.write("### 📊 Erkenntnisse")

        # Finde den strengsten und großzügigsten Bewerter
        sorted_by_avg = sorted(participant_analytics, key=lambda x: x[2])
        strictest = sorted_by_avg[0]
        generous = sorted_by_avg[-1]

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Strengster Bewerter",
                strictest[0],
                f"Ø {strictest[2]} Punkte",
                delta_color="inverse"
            )

        with col2:
            st.metric(
                "Großzügigster Bewerter",
                generous[0],
                f"Ø {generous[2]} Punkte"
            )

        # Finde den konstantesten Bewerter (niedrigste Standardabweichung)
        with_stddev = [p for p in participant_analytics if p[5] is not None and p[5] > 0]
        if with_stddev:
            most_consistent = min(with_stddev, key=lambda x: x[5])
            most_varied = max(with_stddev, key=lambda x: x[5])

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Konstantester Bewerter",
                    most_consistent[0],
                    f"Std.Abw.: {most_consistent[5]}"
                )

            with col2:
                st.metric(
                    "Variabelster Bewerter",
                    most_varied[0],
                    f"Std.Abw.: {most_varied[5]}"
                )

    # Detailansicht pro Teilnehmer
    st.write("### 🔍 Detailansicht")

    all_participants = db.get_all_participants()
    selected_participant = st.selectbox("Teilnehmer auswählen", all_participants)

    if selected_participant:
        participant_ratings = db.get_participant_ratings(selected_participant)

        if participant_ratings:
            df_ratings = pd.DataFrame([
                {
                    "Whisky": r[0],
                    "Brennerei": r[1] or "-",
                    "Punkte": r[2],
                    "Notizen": r[3] or "-",
                    "Verkostung": r[4],
                    "Datum": str(r[5])
                }
                for r in participant_ratings
            ])

            st.dataframe(df_ratings, use_container_width=True, hide_index=True)

            # Geschmacksprofil generieren
            if st.button(f"🧬 Geschmacksprofil für {selected_participant} generieren"):
                ratings_for_ai = [
                    {
                        "whisky_name": r[0],
                        "distillery": r[1],
                        "score": float(r[2]),
                        "notes": r[3]
                    }
                    for r in participant_ratings
                ]

                with st.spinner("Analysiere Geschmacksprofil..."):
                    try:
                        fingerprint = ai.generate_flavor_fingerprint(
                            ratings_for_ai,
                            selected_participant
                        )

                        st.write(f"## {fingerprint['profile_name']}")
                        st.write(fingerprint['description'])

                        # Radar Chart
                        prefs = fingerprint['preferences']
                        categories = ['Torf', 'Frucht', 'Süße', 'Würze', 'Maritim', 'Sherry']
                        values = [
                            prefs.get('peat', 0),
                            prefs.get('fruit', 0),
                            prefs.get('sweet', 0),
                            prefs.get('spice', 0),
                            prefs.get('maritime', 0),
                            prefs.get('sherry', 0)
                        ]

                        fig = go.Figure(data=go.Scatterpolar(
                            r=values + [values[0]],
                            theta=categories + [categories[0]],
                            fill='toself',
                            fillcolor='rgba(212, 175, 55, 0.3)',
                            line=dict(color='#d4af37', width=2)
                        ))

                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(visible=True, range=[0, 100])
                            ),
                            showlegend=False,
                            height=350
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Bevorzugte Regionen:**")
                            for region in fingerprint.get('favorite_regions', []):
                                st.write(f"- {region}")

                        with col2:
                            st.write("**Empfehlungen:**")
                            for rec in fingerprint.get('recommendations', []):
                                st.write(f"- {rec}")

                    except Exception as e:
                        st.error(f"Fehler: {e}")
