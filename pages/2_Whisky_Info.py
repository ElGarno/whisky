"""Detaillierte Informationen zu Whiskies anzeigen."""

import streamlit as st
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai

st.set_page_config(page_title="Whisky Info", page_icon="📖", layout="wide")
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
