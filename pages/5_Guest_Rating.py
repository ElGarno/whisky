"""Gast-Bewertung - Vereinfachte Bewertungsseite für Gäste via QR-Code."""

import streamlit as st
import sys
from pathlib import Path
import qrcode
from io import BytesIO
import base64

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db
from services.auth import require_auth, show_logout_button

st.set_page_config(page_title="Gast-Bewertung", page_icon="🎫", layout="centered")

# URL-Parameter auslesen
query_params = st.query_params
whisky_id = query_params.get("whisky", None)

if whisky_id:
    # Guest mode - no auth required for rating via QR code
    pass
else:
    # Admin mode - require auth for QR code generation
    if not require_auth():
        st.stop()
    show_logout_button()

if whisky_id:
    # Gast-Modus: Bewertungsformular anzeigen
    try:
        whisky_id = int(whisky_id)
        whisky = db.get_whisky(whisky_id)

        if not whisky:
            st.error("Whisky nicht gefunden!")
            st.stop()

        # whisky: (id, name, year, distillery, distillery_id, price, fill_ml, bottle_size, image_path, info_markdown, quantity)
        st.title(f"🥃 {whisky[1]}")
        st.caption(f"{whisky[3] or 'Unbekannte Brennerei'}" + (f" • {whisky[2]} Jahre" if whisky[2] else ""))

        # Bild anzeigen wenn vorhanden
        if whisky[8]:
            image_path = Path(__file__).parent.parent / whisky[8]
            if image_path.exists():
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image(str(image_path), width=200)

        st.divider()

        # Durchschnittsbewertung anzeigen
        avg_rating = db.get_whisky_avg_rating(whisky_id)
        if avg_rating and avg_rating[1] > 0:
            st.metric("Durchschnittsbewertung", f"{avg_rating[0]}/10", f"{avg_rating[1]} Bewertungen")

        st.subheader("Deine Bewertung")

        with st.form("guest_rating_form"):
            guest_name = st.text_input(
                "Dein Name",
                placeholder="Max",
                help="Damit wir wissen, wer bewertet hat"
            )

            score = st.slider(
                "Bewertung",
                min_value=0.0,
                max_value=10.0,
                value=7.0,
                step=0.5,
                help="0 = Nicht trinkbar, 10 = Perfekt"
            )

            notes = st.text_area(
                "Notizen (optional)",
                placeholder="Was schmeckst du? Würdest du ihn wieder trinken?",
                height=100
            )

            submitted = st.form_submit_button("Bewertung abgeben", type="primary", use_container_width=True)

            if submitted:
                if not guest_name.strip():
                    st.error("Bitte gib deinen Namen ein!")
                else:
                    db.add_guest_rating(
                        whisky_id=whisky_id,
                        guest_name=guest_name.strip(),
                        score=score,
                        notes=notes.strip() if notes else None
                    )
                    st.success("🎉 Danke für deine Bewertung!")
                    st.balloons()

        # Bisherige Gast-Bewertungen
        guest_ratings = db.get_guest_ratings(whisky_id)
        if guest_ratings:
            st.divider()
            st.subheader("Andere Bewertungen")
            for rating in guest_ratings[:5]:  # Letzte 5 anzeigen
                name, score, notes, created = rating
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{name}**")
                        if notes:
                            st.caption(notes)
                    with col2:
                        st.write(f"**{score}/10**")

    except ValueError:
        st.error("Ungültige Whisky-ID!")
        st.stop()

else:
    # Admin-Modus: QR-Codes generieren
    st.title("🎫 Gast-Bewertungsmodus")
    st.write("Generiere QR-Codes für deine Flaschen, damit Gäste schnell bewerten können.")

    whiskies = db.get_all_whiskies()

    if not whiskies:
        st.info("Noch keine Whiskies in der Sammlung. Füge welche auf der Registrieren-Seite hinzu!")
        st.stop()

    st.divider()

    # Base URL für QR-Codes (kann angepasst werden)
    st.subheader("Einstellungen")
    default_url = "http://localhost:8501"
    base_url = st.text_input(
        "Basis-URL deiner App",
        value=default_url,
        help="Die URL unter der deine App erreichbar ist. Für lokale Nutzung: http://localhost:8501"
    )

    st.divider()
    st.subheader("QR-Codes für deine Whiskies")

    # Whisky auswählen
    selected_whisky_id = st.selectbox(
        "Whisky auswählen",
        options=[w[0] for w in whiskies],
        format_func=lambda x: next((f"{w[1]} ({w[3] or 'Unbekannt'})" for w in whiskies if w[0] == x), "")
    )

    if selected_whisky_id:
        whisky = next((w for w in whiskies if w[0] == selected_whisky_id), None)

        if whisky:
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"### {whisky[1]}")
                st.write(f"**Brennerei:** {whisky[3] or 'Unbekannt'}")
                if whisky[2]:
                    st.write(f"**Alter:** {whisky[2]} Jahre")

                # Durchschnittsbewertung
                avg_rating = db.get_whisky_avg_rating(whisky[0])
                if avg_rating and avg_rating[1] > 0:
                    st.metric("Bewertung", f"{avg_rating[0]}/10", f"{avg_rating[1]} Stimmen")

            with col2:
                # QR-Code generieren
                qr_url = f"{base_url}/Guest_Rating?whisky={whisky[0]}"

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_url)
                qr.make(fit=True)

                qr_img = qr.make_image(fill_color="black", back_color="white")

                # Bild in Base64 konvertieren
                buffer = BytesIO()
                qr_img.save(buffer, format="PNG")
                qr_base64 = base64.b64encode(buffer.getvalue()).decode()

                st.image(f"data:image/png;base64,{qr_base64}", width=200)
                st.caption("QR-Code scannen zum Bewerten")

                # Download-Button
                st.download_button(
                    label="QR-Code herunterladen",
                    data=buffer.getvalue(),
                    file_name=f"qr_{whisky[1].replace(' ', '_')}.png",
                    mime="image/png"
                )

            # Gast-Bewertungen anzeigen
            guest_ratings = db.get_guest_ratings(whisky[0])
            if guest_ratings:
                st.divider()
                st.subheader("Gast-Bewertungen")

                import pandas as pd
                df = pd.DataFrame([
                    {
                        "Gast": r[0],
                        "Punkte": r[1],
                        "Notizen": r[2] or "-",
                        "Datum": str(r[3])[:10] if r[3] else "-"
                    }
                    for r in guest_ratings
                ])
                st.dataframe(df, use_container_width=True, hide_index=True)

    # Alle QR-Codes auf einmal generieren
    st.divider()
    with st.expander("Alle QR-Codes auf einmal generieren"):
        st.write("Generiere QR-Codes für alle Whiskies in deiner Sammlung.")

        if st.button("Alle QR-Codes generieren", type="secondary"):
            cols = st.columns(3)

            for idx, whisky in enumerate(whiskies):
                qr_url = f"{base_url}/Guest_Rating?whisky={whisky[0]}"

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=6,
                    border=2,
                )
                qr.add_data(qr_url)
                qr.make(fit=True)

                qr_img = qr.make_image(fill_color="black", back_color="white")

                buffer = BytesIO()
                qr_img.save(buffer, format="PNG")
                qr_base64 = base64.b64encode(buffer.getvalue()).decode()

                with cols[idx % 3]:
                    st.image(f"data:image/png;base64,{qr_base64}", width=120)
                    st.caption(whisky[1][:20] + "..." if len(whisky[1]) > 20 else whisky[1])
