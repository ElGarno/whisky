"""Whisky-Verkostung Verwaltung."""

import streamlit as st
import sys
from pathlib import Path
import qrcode
from io import BytesIO
import base64
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai
from services.auth import require_auth, show_logout_button

st.set_page_config(page_title="Verkostung", page_icon="🍷", layout="wide")

if not require_auth():
    st.stop()
show_logout_button()

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
# Random selection state
if "random_selection_result" not in st.session_state:
    st.session_state.random_selection_result = None
if "random_count" not in st.session_state:
    st.session_state.random_count = 4

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

        # Create whisky lookup for display
        whisky_options = {w[0]: f"{w[1]} ({w[3] or 'Unbekannt'})" for w in whiskies}

        # Tabbed selection interface
        selection_tab1, selection_tab2 = st.tabs(["Zufällige Auswahl", "Manuelle Auswahl"])

        with selection_tab1:
            st.write("Lass die KI eine vielfältige Auswahl für dich treffen!")

            # Check if manual selection has modified the state
            if st.session_state.random_selection_result:
                random_ids = set(st.session_state.random_selection_result['selected_whisky_ids'])
                current_ids = set(st.session_state.selected_whiskies)

                if random_ids != current_ids:
                    # Selection was manually modified, clear random result
                    st.session_state.random_selection_result = None

            # Calculate max whiskies
            max_available = len(whiskies)
            if max_available < 2:
                st.warning("Nicht genug Whiskies verfügbar! Füge mindestens 2 hinzu.")
            else:
                col1, col2 = st.columns([2, 1])

                with col1:
                    num_whiskies = st.number_input(
                        "Anzahl Whiskies",
                        min_value=2,
                        max_value=min(10, max_available),
                        value=min(st.session_state.random_count, max_available),
                        help="Wähle zwischen 2 und 10 Whiskies"
                    )
                    st.session_state.random_count = num_whiskies

                with col2:
                    st.write("")  # Spacing
                    num_participants = len(st.session_state.participants) if st.session_state.participants else 1
                    if num_participants > 5:
                        st.caption("Fast leere Flaschen werden ausgeschlossen")

                # Buttons row
                btn_col1, btn_col2 = st.columns(2)

                with btn_col1:
                    if st.button("KI-Auswahl starten", type="primary", use_container_width=True):
                        num_participants = len(st.session_state.participants) if st.session_state.participants else 1
                        eligible = db.get_whiskies_for_random_selection(num_participants)

                        if len(eligible) < num_whiskies:
                            st.error(f"Nur {len(eligible)} Whiskies verfügbar, aber {num_whiskies} angefragt!")
                        else:
                            eligible_dicts = [
                                {"id": w[0], "name": w[1], "year": w[2], "distillery": w[3]}
                                for w in eligible
                            ]

                            with st.spinner("KI wählt vielfältige Whiskies aus..."):
                                try:
                                    result = ai.select_random_whiskies(eligible_dicts, num_whiskies)
                                    st.session_state.random_selection_result = result
                                    st.session_state.selected_whiskies = result['selected_whisky_ids']
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler: {e}")

                with btn_col2:
                    if st.session_state.random_selection_result:
                        if st.button("Neu würfeln", use_container_width=True):
                            num_participants = len(st.session_state.participants) if st.session_state.participants else 1
                            eligible = db.get_whiskies_for_random_selection(num_participants)
                            eligible_dicts = [
                                {"id": w[0], "name": w[1], "year": w[2], "distillery": w[3]}
                                for w in eligible
                            ]

                            with st.spinner("Würfle neu..."):
                                try:
                                    result = ai.select_random_whiskies(eligible_dicts, num_whiskies)
                                    st.session_state.random_selection_result = result
                                    st.session_state.selected_whiskies = result['selected_whisky_ids']
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler: {e}")

                # Display current random selection
                if st.session_state.random_selection_result:
                    result = st.session_state.random_selection_result
                    st.success(f"{len(result['selected_whisky_ids'])} Whiskies ausgewählt")

                    st.write("**Ausgewählte Whiskies:**")
                    for i, name in enumerate(result['selected_whisky_names'], 1):
                        profile = result['profiles'].get(name, "")
                        st.write(f"{i}. **{name}** - _{profile}_")

                    with st.expander("Warum diese Auswahl?"):
                        st.write(result['diversity_explanation'])

        with selection_tab2:
            st.write("Wähle Whiskies manuell aus der Liste.")

            selected_ids = st.multiselect(
                "Wähle Whiskies für die Verkostung",
                options=list(whisky_options.keys()),
                format_func=lambda x: whisky_options[x],
                default=st.session_state.selected_whiskies,
                key="manual_selection"
            )
            # Update state when manual selection changes
            if selected_ids != st.session_state.selected_whiskies:
                st.session_state.selected_whiskies = selected_ids
                st.session_state.random_selection_result = None  # Clear random result

        # Reference to selected IDs for later steps
        selected_ids = st.session_state.selected_whiskies

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
                    st.session_state.random_selection_result = None

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
        # Helper function for QR code generation
        def generate_qr_base64(url: str, size: int = 10) -> str:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()

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

        # Extras: Einladung und Soundscape
        extra_col1, extra_col2 = st.columns(2)

        with extra_col1:
            with st.expander("🎫 Einladungskarte generieren"):
                host_name = st.text_input("Gastgeber-Name (optional)", key="invitation_host")
                base_url = st.text_input("App-URL", value="http://localhost:8501", key="invitation_url")

                if st.button("Einladung erstellen", key="gen_invitation"):
                    tasting_whisky_names = [db.get_whisky(wid)[1] for wid in whisky_ids if db.get_whisky(wid)]

                    with st.spinner("Erstelle Einladung..."):
                        try:
                            invitation = ai.generate_tasting_invitation(
                                tasting_name=tasting_name,
                                date=str(active_tasting[2]),
                                whiskies=tasting_whisky_names,
                                host_name=host_name if host_name else None
                            )

                            # Einladungskarte anzeigen
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                                        padding: 30px; border-radius: 15px; text-align: center;
                                        border: 2px solid #d4af37; margin: 10px 0;">
                                <h2 style="color: #d4af37; margin-bottom: 10px;">{invitation['title']}</h2>
                                <p style="color: #888; font-style: italic;">{invitation['subtitle']}</p>
                                <hr style="border-color: #d4af37; margin: 20px 0;">
                                <p style="color: #fff;">{invitation['body_text']}</p>
                                <p style="color: #d4af37; margin-top: 15px;">🥃 {invitation['whisky_preview']}</p>
                                <hr style="border-color: #d4af37; margin: 20px 0;">
                                <p style="color: #d4af37; font-size: 1.2em;">{invitation['footer']}</p>
                            </div>
                            """, unsafe_allow_html=True)

                            # QR-Code für die Einladung
                            qr_data = f"{base_url}/Tasting"
                            qr_b64 = generate_qr_base64(qr_data, size=6)
                            st.image(f"data:image/png;base64,{qr_b64}", width=120)
                            st.caption("QR-Code zur Verkostungsseite")

                        except Exception as e:
                            st.error(f"Fehler: {e}")

        with extra_col2:
            with st.expander("🎵 Soundscape-Empfehlungen"):
                if st.button("Atmosphäre vorschlagen", key="gen_soundscape"):
                    tasting_whisky_info = [
                        {
                            "name": db.get_whisky(wid)[1],
                            "distillery": db.get_whisky(wid)[3],
                            "region": None  # We'd need to fetch this from distillery
                        }
                        for wid in whisky_ids if db.get_whisky(wid)
                    ]

                    with st.spinner("Analysiere Whiskies für passende Atmosphäre..."):
                        try:
                            soundscape = ai.suggest_soundscape(tasting_whisky_info)

                            st.write(f"**Stimmung:** {soundscape['mood']}")

                            st.write("**Ambient Sounds:**")
                            for sound in soundscape['ambient_sounds']:
                                st.write(f"- 🔊 {sound}")

                            st.write("**Spotify-Suchen:**")
                            for search in soundscape['spotify_searches']:
                                spotify_url = f"https://open.spotify.com/search/{search.replace(' ', '%20')}"
                                st.markdown(f"- 🎵 [{search}]({spotify_url})")

                            st.info(f"💡 {soundscape['fun_fact']}")

                        except Exception as e:
                            st.error(f"Fehler: {e}")

        st.divider()

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

                    # Flavor Fingerprint für Teilnehmer
                    st.divider()
                    st.write("**🧬 Geschmacksprofile der Teilnehmer:**")

                    participants_in_tasting = list(set([r[3] for r in ratings]))

                    for participant in participants_in_tasting:
                        participant_ratings = [
                            {
                                "whisky_name": r[2],
                                "distillery": None,  # We'd need to fetch this
                                "score": float(r[4]),
                                "notes": r[5]
                            }
                            for r in ratings if r[3] == participant
                        ]

                        with st.expander(f"🎯 Profil: {participant}"):
                            if st.button(f"Geschmacksprofil analysieren", key=f"fp_{tasting[0]}_{participant}"):
                                with st.spinner(f"Analysiere {participant}'s Geschmack..."):
                                    try:
                                        fingerprint = ai.generate_flavor_fingerprint(
                                            participant_ratings,
                                            participant
                                        )

                                        st.write(f"### {fingerprint['profile_name']}")
                                        st.write(fingerprint['description'])

                                        # Radar Chart für Präferenzen
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
                                            r=values + [values[0]],  # Close the polygon
                                            theta=categories + [categories[0]],
                                            fill='toself',
                                            fillcolor='rgba(212, 175, 55, 0.3)',
                                            line=dict(color='#d4af37', width=2)
                                        ))

                                        fig.update_layout(
                                            polar=dict(
                                                radialaxis=dict(
                                                    visible=True,
                                                    range=[0, 100]
                                                )
                                            ),
                                            showlegend=False,
                                            height=300
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
