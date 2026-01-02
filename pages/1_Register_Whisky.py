"""Registriere einen neuen Whisky per Fotoerkennung."""

import streamlit as st
from PIL import Image
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai

st.set_page_config(page_title="Whisky Registrieren", page_icon="📸")
st.title("Whisky Registrieren")

# Session State initialisieren
if "recognition_result" not in st.session_state:
    st.session_state.recognition_result = None
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "estimated_price" not in st.session_state:
    st.session_state.estimated_price = None

# Foto-Upload
st.subheader("Lade ein Foto deiner Whisky-Flasche hoch")

uploaded_file = st.file_uploader(
    "Mache ein Foto oder lade ein Bild hoch",
    type=["jpg", "jpeg", "png"],
    help="Stelle sicher, dass das Etikett gut sichtbar ist"
)

if uploaded_file is not None:
    # Bild anzeigen
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladenes Bild", width=300)

    # Bild-Bytes speichern
    uploaded_file.seek(0)
    st.session_state.uploaded_image = uploaded_file.read()

    # Analyse-Button
    if st.button("Mit KI analysieren", type="primary"):
        with st.spinner("Analysiere Bild..."):
            try:
                result = ai.analyze_whisky_photo(st.session_state.uploaded_image)
                st.session_state.recognition_result = result
                st.success("Analyse abgeschlossen!")

                # Preisschätzung abrufen
                with st.spinner("Ermittle Marktpreis..."):
                    try:
                        price_info = ai.estimate_whisky_price(
                            result.get("name", ""),
                            result.get("distillery", ""),
                            result.get("year")
                        )
                        st.session_state.estimated_price = price_info
                    except Exception:
                        st.session_state.estimated_price = None

            except Exception as e:
                st.error(f"Fehler bei der Bildanalyse: {e}")

# Erkennungsergebnisse und Bearbeitungsformular anzeigen
if st.session_state.recognition_result:
    result = st.session_state.recognition_result

    st.subheader("Erkennungsergebnisse")
    st.info(f"Konfidenz: {result.get('confidence', 0) * 100:.0f}%")

    # Preisschätzung anzeigen falls verfügbar
    if st.session_state.estimated_price:
        price_info = st.session_state.estimated_price
        st.success(
            f"💰 **Geschätzter Marktpreis:** {price_info.get('price_eur', 0):.0f} € "
            f"(Spanne: {price_info.get('price_range_min', 0):.0f} - {price_info.get('price_range_max', 0):.0f} €)"
        )
        if price_info.get('source_info'):
            st.caption(f"ℹ️ {price_info.get('source_info')}")

    # Bearbeitbares Formular
    with st.form("whisky_form"):
        name = st.text_input("Whisky Name", value=result.get("name", ""))
        distillery = st.text_input("Brennerei", value=result.get("distillery", ""))
        year = st.number_input(
            "Alter (Jahre)",
            min_value=0,
            max_value=100,
            value=result.get("year") or 0,
            help="Gib 0 ein wenn keine Altersangabe"
        )

        # Füllstand
        fill_options = {
            "full": "Voll (100%)",
            "three_quarters": "3/4 Voll (75%)",
            "half": "Halb (50%)",
            "quarter": "1/4 Voll (25%)",
            "near_empty": "Fast leer (<10%)"
        }
        fill_ml_map = {
            "full": 700,
            "three_quarters": 525,
            "half": 350,
            "quarter": 175,
            "near_empty": 50
        }

        detected_fill = result.get("fill_level", "full")
        fill_level = st.selectbox(
            "Füllstand",
            options=list(fill_options.keys()),
            format_func=lambda x: fill_options[x],
            index=list(fill_options.keys()).index(detected_fill) if detected_fill in fill_options else 0
        )

        # Geschätzten Preis als Standardwert verwenden
        default_price = 0.0
        if st.session_state.estimated_price:
            default_price = float(st.session_state.estimated_price.get('price_eur', 0))

        price = st.number_input(
            "Preis (€)",
            min_value=0.0,
            value=default_price,
            step=1.0,
            help="Geschätzter Marktpreis vorausgefüllt - kannst du anpassen"
        )

        quantity = st.number_input(
            "Anzahl (Flaschen)",
            min_value=1,
            max_value=100,
            value=1,
            help="Anzahl der Flaschen dieses Whiskys"
        )

        submitted = st.form_submit_button("Whisky speichern", type="primary")

        if submitted:
            if not name or not distillery:
                st.error("Bitte gib sowohl Name als auch Brennerei ein")
            else:
                # Brennerei abrufen oder erstellen
                distillery_id = db.get_or_create_distillery(distillery)

                # Bild in Assets speichern
                image_path = None
                if st.session_state.uploaded_image:
                    assets_dir = Path(__file__).parent.parent / "assets" / "whisky_images"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    image_filename = f"{name.lower().replace(' ', '_')}.jpg"
                    image_path = str(assets_dir / image_filename)

                    img = Image.open(io.BytesIO(st.session_state.uploaded_image))
                    img.save(image_path, "JPEG", quality=85)

                # Whisky zur Datenbank hinzufügen
                whisky_id = db.add_whisky(
                    name=name,
                    year=year if year > 0 else None,
                    distillery_id=distillery_id,
                    price=price if price > 0 else None,
                    quantity=quantity,
                    current_fill_ml=fill_ml_map[fill_level],
                    image_path=image_path
                )

                st.success(f"{name} gespeichert!")

                # Info im Hintergrund generieren
                with st.spinner("Generiere Whisky-Informationen..."):
                    try:
                        info = ai.generate_whisky_info(name, distillery, year if year > 0 else None)
                        db.update_whisky_info(whisky_id, info)

                        # Versuche Brennerei-Standort zu ermitteln
                        location = ai.get_distillery_location(distillery)
                        if location:
                            db.update_distillery_location(
                                distillery_id,
                                location["latitude"],
                                location["longitude"]
                            )
                            # Region/Land aktualisieren
                            conn = db.get_connection()
                            conn.execute("""
                                UPDATE distilleries
                                SET region = ?, country = ?
                                WHERE id = ?
                            """, [location.get("region"), location.get("country"), distillery_id])
                            conn.close()

                        st.success("Infos generiert! Schau auf der Whisky Info Seite nach.")
                    except Exception as e:
                        st.warning(f"Konnte Infos nicht generieren: {e}")

                # Session State zurücksetzen
                st.session_state.recognition_result = None
                st.session_state.uploaded_image = None
                st.session_state.estimated_price = None
                st.rerun()

# Manuelle Eingabe Option
st.divider()
st.subheader("Oder manuell hinzufügen")

with st.expander("Manuelles Eingabeformular"):
    with st.form("manual_form"):
        m_name = st.text_input("Whisky Name")
        m_distillery = st.text_input("Brennerei")
        m_year = st.number_input("Alter (Jahre)", min_value=0, max_value=100, value=0)
        m_price = st.number_input("Preis (€)", min_value=0.0, step=1.0)
        m_quantity = st.number_input("Anzahl (Flaschen)", min_value=1, max_value=100, value=1)
        m_fill = st.slider("Füllstand (%)", min_value=0, max_value=100, value=100)

        if st.form_submit_button("Whisky hinzufügen"):
            if not m_name or not m_distillery:
                st.error("Bitte gib sowohl Name als auch Brennerei ein")
            else:
                distillery_id = db.get_or_create_distillery(m_distillery)
                whisky_id = db.add_whisky(
                    name=m_name,
                    year=m_year if m_year > 0 else None,
                    distillery_id=distillery_id,
                    price=m_price if m_price > 0 else None,
                    quantity=m_quantity,
                    current_fill_ml=int(700 * m_fill / 100)
                )

                # Infos generieren
                with st.spinner("Generiere Infos..."):
                    try:
                        info = ai.generate_whisky_info(m_name, m_distillery, m_year if m_year > 0 else None)
                        db.update_whisky_info(whisky_id, info)

                        location = ai.get_distillery_location(m_distillery)
                        if location:
                            db.update_distillery_location(distillery_id, location["latitude"], location["longitude"])
                    except Exception as e:
                        st.warning(f"Konnte Infos nicht generieren: {e}")

                st.success(f"{m_name} hinzugefügt!")
                st.rerun()
