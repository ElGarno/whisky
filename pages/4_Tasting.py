"""Whisky-Verkostung Verwaltung."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai

st.set_page_config(page_title="Verkostung", page_icon="🍷", layout="wide")
st.title("Whisky Verkostung")

# Session State initialisieren
if "tasting_step" not in st.session_state:
    st.session_state.tasting_step = "select"  # select, order, rate, summary
if "selected_whiskies" not in st.session_state:
    st.session_state.selected_whiskies = []
if "participants" not in st.session_state:
    st.session_state.participants = []
if "suggested_orders" not in st.session_state:
    st.session_state.suggested_orders = None
if "chosen_order" not in st.session_state:
    st.session_state.chosen_order = None

# Whiskies abrufen
whiskies = db.get_all_whiskies()

# Auf aktive Verkostung prüfen
active_tasting = db.get_active_tasting()

# Tab-Navigation
tab1, tab2, tab3 = st.tabs(["Neue Verkostung", "Aktive Verkostung", "Vergangene Verkostungen"])

with tab1:
    if active_tasting:
        st.warning("Du hast eine aktive Verkostung. Schließe sie ab oder schau im Tab 'Aktive Verkostung' nach.")
    elif not whiskies:
        st.info("Füge zuerst Whiskies auf der Registrieren-Seite hinzu!")
    else:
        st.subheader("Neue Verkostung erstellen")

        # Schritt 1: Whiskies auswählen
        st.write("**Schritt 1: Whiskies auswählen**")

        whisky_options = {w[0]: f"{w[1]} ({w[3] or 'Unbekannt'})" for w in whiskies}
        selected_ids = st.multiselect(
            "Wähle Whiskies für die Verkostung",
            options=list(whisky_options.keys()),
            format_func=lambda x: whisky_options[x],
            default=st.session_state.selected_whiskies
        )
        st.session_state.selected_whiskies = selected_ids

        # Schritt 2: Teilnehmer hinzufügen
        st.write("**Schritt 2: Teilnehmer hinzufügen**")
        participants_input = st.text_input(
            "Teilnehmernamen eingeben (kommagetrennt)",
            value=", ".join(st.session_state.participants),
            placeholder="Max, Anna, Peter"
        )
        if participants_input:
            st.session_state.participants = [p.strip() for p in participants_input.split(",") if p.strip()]

        # Schritt 3: KI-Vorschläge holen
        if len(selected_ids) >= 2 and st.session_state.participants:
            st.write("**Schritt 3: Verkostungsreihenfolge**")

            if st.button("KI-Vorschläge holen"):
                selected_whiskies = [
                    {"id": w[0], "name": w[1], "distillery": w[3], "year": w[2]}
                    for w in whiskies if w[0] in selected_ids
                ]

                with st.spinner("Hole KI-Vorschläge..."):
                    try:
                        suggestions = ai.suggest_tasting_order(selected_whiskies)
                        st.session_state.suggested_orders = suggestions
                    except Exception as e:
                        st.error(f"Fehler: {e}")

            # Vorschläge anzeigen
            if st.session_state.suggested_orders:
                for i, order in enumerate(st.session_state.suggested_orders):
                    with st.expander(f"Option {i+1}: {order['order_name']}", expanded=i==0):
                        st.write("**Reihenfolge:**")
                        for j, name in enumerate(order['whisky_names'], 1):
                            st.write(f"{j}. {name}")
                        st.write("**Begründung:**", order['explanation'])

                        if st.button(f"Diese Reihenfolge verwenden", key=f"use_order_{i}"):
                            st.session_state.chosen_order = order
                            st.success("Reihenfolge ausgewählt!")

            # Verkostung starten Button
            if st.session_state.chosen_order:
                tasting_name = st.text_input("Name der Verkostung", value="Whisky Verkostung")

                if st.button("Verkostung starten", type="primary"):
                    # Whisky-Namen zurück zu IDs mappen in Reihenfolge
                    ordered_ids = []
                    name_to_id = {w[1]: w[0] for w in whiskies}
                    for name in st.session_state.chosen_order['whisky_names']:
                        if name in name_to_id:
                            ordered_ids.append(name_to_id[name])

                    tasting_id = db.create_tasting(
                        name=tasting_name,
                        whisky_ids=ordered_ids,
                        participants=st.session_state.participants,
                        order_explanation=st.session_state.chosen_order['explanation']
                    )

                    # Session State zurücksetzen
                    st.session_state.selected_whiskies = []
                    st.session_state.participants = []
                    st.session_state.suggested_orders = None
                    st.session_state.chosen_order = None

                    st.success(f"Verkostung '{tasting_name}' erstellt!")
                    st.rerun()

        elif len(selected_ids) < 2:
            st.info("Wähle mindestens 2 Whiskies aus")
        elif not st.session_state.participants:
            st.info("Füge mindestens einen Teilnehmer hinzu")

with tab2:
    if not active_tasting:
        st.info("Keine aktive Verkostung. Erstelle eine im Tab 'Neue Verkostung'!")
    else:
        # active_tasting: (id, name, date, whisky_ids, participants, order_explanation, summary_markdown)
        tasting_id = active_tasting[0]
        tasting_name = active_tasting[1]
        whisky_ids = active_tasting[3]
        participants = active_tasting[4]
        order_explanation = active_tasting[5]

        st.subheader(f"Aktiv: {tasting_name}")
        st.write(f"**Datum:** {active_tasting[2]}")
        st.write(f"**Teilnehmer:** {', '.join(participants)}")

        if order_explanation:
            with st.expander("Erklärung zur Reihenfolge"):
                st.write(order_explanation)

        # Whiskies in Reihenfolge abrufen
        tasting_whiskies = [db.get_whisky(wid) for wid in whisky_ids]
        existing_ratings = db.get_tasting_ratings(tasting_id)

        # Bewertungsformular
        st.subheader("Bewertungen eingeben")

        for whisky in tasting_whiskies:
            if not whisky:
                continue

            st.write(f"### {whisky[1]}")  # name

            for participant in participants:
                # Prüfen ob Bewertung existiert
                has_rating = db.get_rating_exists(tasting_id, whisky[0], participant)

                if has_rating:
                    st.write(f"✅ {participant}: Bereits bewertet")
                else:
                    col1, col2, col3 = st.columns([2, 3, 2])

                    with col1:
                        st.write(f"**{participant}**")

                    with col2:
                        score = st.slider(
                            "Punktzahl",
                            min_value=0.0,
                            max_value=10.0,
                            value=5.0,
                            step=0.5,
                            key=f"score_{whisky[0]}_{participant}",
                            label_visibility="collapsed"
                        )

                    with col3:
                        if st.button("Speichern", key=f"save_{whisky[0]}_{participant}"):
                            notes = st.session_state.get(f"notes_{whisky[0]}_{participant}", "")
                            db.add_rating(tasting_id, whisky[0], participant, score, notes)
                            st.success("Gespeichert!")
                            st.rerun()

                    notes = st.text_input(
                        "Notizen (optional)",
                        key=f"notes_{whisky[0]}_{participant}",
                        label_visibility="collapsed",
                        placeholder="Verkostungsnotizen..."
                    )

            st.divider()

        # Prüfen ob alle Bewertungen abgeschlossen
        total_ratings_needed = len(whisky_ids) * len(participants)
        current_ratings = len(existing_ratings)

        st.write(f"**Fortschritt:** {current_ratings}/{total_ratings_needed} Bewertungen")
        st.progress(current_ratings / total_ratings_needed if total_ratings_needed > 0 else 0)

        if current_ratings == total_ratings_needed:
            st.success("Alle Bewertungen abgeschlossen!")

            if st.button("Zusammenfassung generieren & Verkostung abschließen", type="primary"):
                with st.spinner("Generiere KI-Zusammenfassung..."):
                    try:
                        # Bewertungsdaten vorbereiten
                        ratings_data = [
                            {
                                "participant": r[3],  # participant_name
                                "whisky": r[2],       # whisky_name
                                "score": float(r[4]), # score
                                "notes": r[5]         # notes
                            }
                            for r in existing_ratings
                        ]

                        whisky_names = [w[1] for w in tasting_whiskies if w]

                        summary = ai.generate_tasting_summary(
                            ratings_data,
                            whisky_names,
                            list(participants)
                        )

                        db.complete_tasting(tasting_id, summary)
                        st.success("Verkostung abgeschlossen!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Fehler beim Generieren der Zusammenfassung: {e}")

with tab3:
    st.subheader("Vergangene Verkostungen")

    all_tastings = db.get_all_tastings()
    completed_tastings = [t for t in all_tastings if t[5] == 'completed']

    if not completed_tastings:
        st.info("Noch keine abgeschlossenen Verkostungen.")
    else:
        for tasting in completed_tastings:
            # tasting: (id, name, date, whisky_ids, participants, status, summary_markdown)
            with st.expander(f"{tasting[1]} - {tasting[2]}"):
                st.write(f"**Teilnehmer:** {', '.join(tasting[4])}")
                st.write(f"**Whiskies:** {len(tasting[3])}")

                if tasting[6]:  # summary_markdown
                    st.divider()
                    st.markdown(tasting[6])

                # Bewertungen anzeigen
                ratings = db.get_tasting_ratings(tasting[0])
                if ratings:
                    st.divider()
                    st.write("**Alle Bewertungen:**")

                    import pandas as pd
                    df = pd.DataFrame([
                        {"Whisky": r[2], "Teilnehmer": r[3], "Punkte": r[4], "Notizen": r[5] or ""}
                        for r in ratings
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)
