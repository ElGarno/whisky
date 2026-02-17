"""Detaillierte Informationen zu Whiskies anzeigen."""

import streamlit as st
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai
from services import barcode as barcode_service
from services.auth import require_auth, show_logout_button

st.set_page_config(page_title="Whisky Info", page_icon="📖", layout="wide")

if not require_auth():
    st.stop()
show_logout_button()

st.title("Whisky Informationen")

# Alle Whiskies abrufen
whiskies = db.get_all_whiskies()

if not whiskies:
    st.info("Noch keine Whiskies in deiner Sammlung. Füge welche auf der Registrieren-Seite hinzu!")
    st.stop()

# Auswahloptionen erstellen
whisky_options = {w[0]: f"{w[1]} ({w[3] or 'Unbekannt'})" for w in whiskies}

selected_id = st.selectbox(
    "Wähle einen Whisky",
    options=list(whisky_options.keys()),
    format_func=lambda x: whisky_options[x]
)

# Ausgewählte Whisky-Details abrufen
whisky = db.get_whisky(selected_id)

if whisky:
    # whisky: (id, name, year, distillery, distillery_id, price, current_fill_ml, bottle_size_ml, image_path, info_markdown, quantity)

    col1, col2 = st.columns([1, 2])

    with col1:
        # Bild anzeigen falls verfügbar
        if whisky[8]:  # image_path
            try:
                st.image(whisky[8], caption=whisky[1], width=250)
                # Bild-Rotation Buttons
                rot_left, rot_right = st.columns(2)
                with rot_left:
                    if st.button("↶ Links", key="rot_left"):
                        img = Image.open(whisky[8])
                        img = img.rotate(90, expand=True)
                        img.save(whisky[8])
                        st.rerun()
                with rot_right:
                    if st.button("↷ Rechts", key="rot_right"):
                        img = Image.open(whisky[8])
                        img = img.rotate(-90, expand=True)
                        img.save(whisky[8])
                        st.rerun()
            except Exception:
                st.info("Bild nicht verfügbar")
        else:
            st.info("Kein Bild")

        # Schnellinfos
        st.subheader("Details")
        st.write(f"**Brennerei:** {whisky[3] or 'Unbekannt'}")
        if whisky[2]:  # year
            st.write(f"**Alter:** {whisky[2]} Jahre")
        if whisky[5]:  # price
            st.write(f"**Preis:** {whisky[5]:.2f} €")
        st.write(f"**Anzahl:** {whisky[10]} Flasche(n)")

        # Füllstand
        fill_pct = (whisky[6] / whisky[7]) * 100 if whisky[7] else 0
        st.write(f"**Füllstand:** {fill_pct:.0f}%")
        st.progress(fill_pct / 100)

        # Bearbeiten-Bereich
        with st.expander("Whisky bearbeiten"):
            with st.form("edit_form"):
                new_quantity = st.number_input(
                    "Anzahl (Flaschen)",
                    min_value=1,
                    max_value=100,
                    value=int(whisky[10])
                )
                new_fill = st.slider(
                    "Füllstand (%)",
                    min_value=0,
                    max_value=100,
                    value=int(fill_pct)
                )
                new_price = st.number_input(
                    "Preis (€)",
                    min_value=0.0,
                    value=float(whisky[5]) if whisky[5] else 0.0,
                    step=1.0
                )

                col_save, col_delete = st.columns(2)
                with col_save:
                    if st.form_submit_button("Änderungen speichern"):
                        fill_ml = int(whisky[7] * new_fill / 100)
                        db.update_whisky(
                            selected_id,
                            price=new_price if new_price > 0 else None,
                            fill_ml=fill_ml,
                            quantity=new_quantity
                        )
                        st.success("Aktualisiert!")
                        st.rerun()

                with col_delete:
                    if st.form_submit_button("Whisky löschen", type="secondary"):
                        db.delete_whisky(selected_id)
                        st.success("Gelöscht!")
                        st.rerun()

        # Barcode verwalten
        with st.expander("Barcode verwalten"):
            current_barcode = db.get_whisky_barcode(selected_id)

            if current_barcode:
                st.success(f"Aktueller Barcode: **{current_barcode}**")
                if st.button("Barcode entfernen", key="remove_barcode"):
                    db.delete_whisky_barcode(selected_id)
                    st.success("Barcode entfernt!")
                    st.rerun()
            else:
                st.info("Kein Barcode hinterlegt.")

            st.divider()
            st.write("**Barcode hinzufügen/ändern:**")

            # Tab für Kamera oder manuelle Eingabe
            barcode_tab1, barcode_tab2 = st.tabs(["Kamera", "Manuell"])

            with barcode_tab1:
                if not barcode_service.is_available():
                    st.warning("Barcode-Scanning nicht verfügbar. Installiere `pyzbar`.")
                    st.code("pip install pyzbar", language="bash")
                else:
                    camera_image = st.camera_input("Barcode fotografieren", key="barcode_cam")

                    if camera_image:
                        image = Image.open(camera_image)
                        barcodes = barcode_service.decode_barcode(image)

                        if barcodes:
                            ean = barcode_service.get_ean_barcode(barcodes)
                            if ean:
                                st.success(f"Erkannt: **{ean}**")
                                if st.button("Barcode speichern", key="save_scanned"):
                                    db.add_whisky_barcode(ean, selected_id)
                                    st.success("Barcode gespeichert!")
                                    st.rerun()
                        else:
                            st.warning("Kein Barcode erkannt. Versuche bessere Beleuchtung.")

            with barcode_tab2:
                manual_barcode = st.text_input(
                    "EAN/Barcode eingeben",
                    placeholder="5012345678901",
                    key="manual_barcode"
                )
                if manual_barcode:
                    if st.button("Barcode speichern", key="save_manual"):
                        db.add_whisky_barcode(manual_barcode, selected_id)
                        st.success(f"Barcode {manual_barcode} gespeichert!")
                        st.rerun()

        # Bewertungen verwalten
        with st.expander("Bewertungen verwalten"):
            avg_rating = db.get_whisky_avg_rating(selected_id)
            guest_ratings = db.get_guest_ratings(selected_id)

            if avg_rating and avg_rating[1] > 0:
                st.metric("Durchschnitt", f"{avg_rating[0]}/10", f"{avg_rating[1]} Bewertungen")

                # Session state for delete confirmation
                if "confirm_delete_ratings" not in st.session_state:
                    st.session_state.confirm_delete_ratings = None

                st.divider()

                # Delete guest ratings only
                guest_count = len(guest_ratings) if guest_ratings else 0
                if guest_count > 0:
                    if st.session_state.confirm_delete_ratings == f"guest_{selected_id}":
                        st.warning(f"Wirklich {guest_count} Gast-Bewertungen löschen?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Ja, löschen", key="confirm_del_guest"):
                                count = db.delete_whisky_guest_ratings(selected_id)
                                st.session_state.confirm_delete_ratings = None
                                st.success(f"{count} Gast-Bewertungen gelöscht!")
                                st.rerun()
                        with col_no:
                            if st.button("Abbrechen", key="cancel_del_guest"):
                                st.session_state.confirm_delete_ratings = None
                                st.rerun()
                    else:
                        if st.button(f"Gast-Bewertungen löschen ({guest_count})", key="del_guest"):
                            st.session_state.confirm_delete_ratings = f"guest_{selected_id}"
                            st.rerun()

                # Delete all ratings
                if st.session_state.confirm_delete_ratings == f"all_{selected_id}":
                    st.warning(f"Wirklich ALLE {avg_rating[1]} Bewertungen löschen?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Ja, alle löschen", key="confirm_del_all", type="primary"):
                            count = db.delete_whisky_ratings(selected_id)
                            st.session_state.confirm_delete_ratings = None
                            st.success(f"{count} Bewertungen gelöscht!")
                            st.rerun()
                    with col_no:
                        if st.button("Abbrechen", key="cancel_del_all"):
                            st.session_state.confirm_delete_ratings = None
                            st.rerun()
                else:
                    if st.button(f"Alle Bewertungen löschen ({avg_rating[1]})", key="del_all"):
                        st.session_state.confirm_delete_ratings = f"all_{selected_id}"
                        st.rerun()
            else:
                st.info("Keine Bewertungen vorhanden.")

    with col2:
        st.subheader(whisky[1])  # name

        # Info Markdown anzeigen
        if whisky[9]:  # info_markdown
            st.markdown(whisky[9])
        else:
            st.info("Noch keine Infos generiert.")

        # Neu generieren Button
        if st.button("Infos neu generieren"):
            with st.spinner("Generiere neue Infos..."):
                try:
                    info = ai.generate_whisky_info(
                        whisky[1],  # name
                        whisky[3],  # distillery
                        whisky[2]   # year
                    )
                    db.update_whisky_info(selected_id, info)
                    st.success("Infos neu generiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

# Alle Whiskies in einer Tabelle anzeigen
st.divider()
st.subheader("Sammlungsübersicht")

import pandas as pd

data = []
for w in whiskies:
    # w: (id, name, year, distillery, price, current_fill_ml, bottle_size_ml, image_path, info_markdown, quantity)
    fill_pct = (w[5] / w[6]) * 100 if w[6] else 0
    data.append({
        "Name": w[1],
        "Brennerei": w[3] or "Unbekannt",
        "Alter": w[2] if w[2] else "NAS",
        "Anz.": w[9],
        "Preis": f"{w[4]:.0f} €" if w[4] else "-",
        "Füllstand": f"{fill_pct:.0f}%"
    })

df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True, hide_index=True)
