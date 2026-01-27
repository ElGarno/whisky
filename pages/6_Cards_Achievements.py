"""Cards & Achievements page - Collect whisky cards and unlock achievements."""

import streamlit as st
from PIL import Image
import io

from services import db
from services import barcode as barcode_service

st.set_page_config(page_title="Karten & Achievements", page_icon="🃏", layout="wide")

st.title("🃏 Karten & Achievements")

# User selection
all_participants = db.get_all_participants()
if not all_participants:
    st.info("Noch keine Teilnehmer vorhanden. Nimm an einem Tasting teil, um Karten freizuschalten!")
    st.stop()

user_name = st.selectbox("Wähle deinen Namen", all_participants)

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["🃏 Meine Karten", "🏆 Achievements", "📷 Whisky scannen"])

# ============================================
# Tab 1: My Cards
# ============================================
with tab1:
    st.header("Meine Whisky-Sammlung")

    # Get user card stats
    stats = db.get_user_card_stats(user_name)
    cards = db.get_user_cards(user_name)

    # Stats overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Gesammelte Karten", stats['total'])
    with col2:
        pct = (stats['total'] / stats['all_whiskies'] * 100) if stats['all_whiskies'] > 0 else 0
        st.metric("Fortschritt", f"{pct:.1f}%")
    with col3:
        legendary = stats['by_rarity'].get('legendary', 0)
        epic = stats['by_rarity'].get('epic', 0)
        st.metric("Legendär / Episch", f"{legendary} / {epic}")
    with col4:
        rare = stats['by_rarity'].get('rare', 0)
        common = stats['by_rarity'].get('common', 0)
        st.metric("Selten / Gewöhnlich", f"{rare} / {common}")

    st.divider()

    # Rarity colors and badges
    RARITY_COLORS = {
        'legendary': '#FFD700',  # Gold
        'epic': '#9B30FF',       # Purple
        'rare': '#1E90FF',       # Blue
        'common': '#808080'      # Gray
    }
    RARITY_NAMES = {
        'legendary': '✨ Legendär',
        'epic': '💜 Episch',
        'rare': '💙 Selten',
        'common': '⬜ Gewöhnlich'
    }

    if not cards:
        st.info("Du hast noch keine Karten gesammelt. Probiere Whiskys und bewerte sie, um Karten freizuschalten!")
    else:
        # Filter by rarity
        rarity_filter = st.multiselect(
            "Nach Seltenheit filtern",
            options=['legendary', 'epic', 'rare', 'common'],
            format_func=lambda x: RARITY_NAMES.get(x, x),
            default=['legendary', 'epic', 'rare', 'common']
        )

        filtered_cards = [c for c in cards if c[2] in rarity_filter]

        # Display cards in a grid
        cols = st.columns(4)
        for i, card in enumerate(filtered_cards):
            card_id, whisky_id, rarity, unlocked_at, whisky_name, distillery, region, year, image_path = card

            with cols[i % 4]:
                # Card container with colored border
                border_color = RARITY_COLORS.get(rarity, '#808080')
                st.markdown(f"""
                <div style="
                    border: 3px solid {border_color};
                    border-radius: 10px;
                    padding: 10px;
                    margin-bottom: 10px;
                    background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(0,0,0,0.1));
                    box-shadow: 0 0 10px {border_color}40;
                ">
                    <div style="text-align: center; font-size: 0.8em; color: {border_color}; font-weight: bold;">
                        {RARITY_NAMES.get(rarity, rarity)}
                    </div>
                    <h4 style="margin: 5px 0; text-align: center;">{whisky_name}</h4>
                    <p style="text-align: center; color: #888; margin: 0;">
                        {distillery or 'Unbekannt'}<br/>
                        {region or ''} {f'• {year}' if year else ''}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                # Show image if available
                if image_path:
                    try:
                        st.image(image_path, use_container_width=True)
                    except:
                        pass

# ============================================
# Tab 2: Achievements
# ============================================
with tab2:
    st.header("Achievements")

    # Check for new achievements
    if st.button("🔄 Achievements aktualisieren"):
        newly_unlocked = db.check_and_unlock_achievements(user_name)
        if newly_unlocked:
            st.balloons()
            for ach in newly_unlocked:
                st.success(f"🎉 Achievement freigeschaltet: {ach['icon']} {ach['name']} (+{ach['points']} Punkte)")

    # Total points
    total_points = db.get_user_total_points(user_name)
    st.metric("Gesamtpunkte", f"🏅 {total_points}")

    st.divider()

    # Get all achievements with progress
    achievements = db.get_user_achievement_progress(user_name)

    # Group by category
    categories = {}
    for ach in achievements:
        cat = ach[5]  # category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ach)

    CATEGORY_NAMES = {
        'beginner': '🌱 Anfänger',
        'collector': '📚 Sammler',
        'region': '🗺️ Regionen',
        'diversity': '🌍 Vielfalt',
        'time': '⏰ Zeitbasiert',
        'special': '⭐ Speziell'
    }

    for cat, achs in categories.items():
        with st.expander(f"{CATEGORY_NAMES.get(cat, cat)} ({len([a for a in achs if a[10]])} / {len(achs)})", expanded=True):
            for ach in achs:
                ach_id, code, name, desc, icon, category, req_type, req_value, req_extra, points, unlocked_at, progress = ach

                col1, col2, col3 = st.columns([1, 4, 2])

                with col1:
                    if unlocked_at:
                        st.markdown(f"<span style='font-size: 2em;'>{icon}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='font-size: 2em; opacity: 0.3;'>{icon}</span>", unsafe_allow_html=True)

                with col2:
                    if unlocked_at:
                        st.markdown(f"**{name}** ✅")
                        st.caption(desc)
                    else:
                        st.markdown(f"**{name}**")
                        st.caption(desc)
                        # Progress bar
                        progress_pct = min(progress / req_value, 1.0) if req_value > 0 else 0
                        st.progress(progress_pct, text=f"{progress} / {req_value}")

                with col3:
                    st.markdown(f"**+{points}** Punkte")
                    if unlocked_at:
                        st.caption(f"Freigeschaltet: {str(unlocked_at)[:10]}")

# ============================================
# Tab 3: Scan Whisky
# ============================================
with tab3:
    st.header("📷 Whisky scannen & bewerten")

    if not barcode_service.is_available():
        st.warning("Barcode-Scanning ist nicht verfügbar. Bitte installiere `pyzbar` und `libzbar0`.")
        st.code("pip install pyzbar\nsudo apt-get install libzbar0", language="bash")
    else:
        st.info("Scanne den Barcode einer Whisky-Flasche, um ihn zu identifizieren und zu bewerten.")

        # Camera input
        camera_image = st.camera_input("Barcode fotografieren")

        # Or file upload
        uploaded_file = st.file_uploader("Oder Bild hochladen", type=['jpg', 'jpeg', 'png'])

        image_source = camera_image or uploaded_file

        if image_source:
            # Decode barcode
            image = Image.open(image_source)
            st.image(image, caption="Aufgenommenes Bild", width=300)

            barcodes = barcode_service.decode_barcode(image)

            if not barcodes:
                st.warning("Kein Barcode erkannt. Bitte versuche es erneut mit besserer Beleuchtung.")
            else:
                ean = barcode_service.get_ean_barcode(barcodes)
                st.success(f"Barcode erkannt: **{ean}**")

                # Look up whisky
                whisky = db.get_whisky_by_barcode(ean)

                if whisky:
                    whisky_id, whisky_name, year, distillery = whisky[0], whisky[1], whisky[2], whisky[3]
                    st.success(f"Whisky gefunden: **{whisky_name}** ({distillery}, {year})")

                    # Rating form
                    st.subheader("Bewertung abgeben")

                    score = st.slider("Bewertung", 0.0, 10.0, 7.0, 0.5)
                    notes = st.text_area("Notizen (optional)")

                    if st.button("💾 Bewertung speichern & Karte freischalten"):
                        # Add guest rating (tasting_id = 0)
                        db.add_guest_rating(whisky_id, user_name, score, notes)

                        # Unlock card
                        card_id, is_new, rarity = db.unlock_card(user_name, whisky_id)

                        if is_new:
                            st.balloons()
                            st.success(f"🎴 Neue Karte freigeschaltet: **{whisky_name}** ({rarity.upper()})")
                        else:
                            st.info(f"Du hattest diese Karte bereits: **{whisky_name}**")

                        # Check achievements
                        newly_unlocked = db.check_and_unlock_achievements(user_name)
                        for ach in newly_unlocked:
                            st.success(f"🏆 Achievement freigeschaltet: {ach['icon']} {ach['name']}")

                        st.rerun()
                else:
                    st.warning("Dieser Barcode ist noch nicht in der Datenbank registriert.")

                    # Option to link to existing whisky
                    st.subheader("Barcode einem Whisky zuordnen")

                    all_whiskies = db.get_all_whiskies()
                    if all_whiskies:
                        whisky_options = {f"{w[1]} ({w[3]}, {w[2]})": w[0] for w in all_whiskies}
                        selected_whisky = st.selectbox("Whisky auswählen", options=list(whisky_options.keys()))

                        if st.button("Barcode zuordnen"):
                            whisky_id = whisky_options[selected_whisky]
                            db.add_whisky_barcode(ean, whisky_id)
                            st.success(f"Barcode {ean} wurde {selected_whisky} zugeordnet!")
                            st.rerun()
                    else:
                        st.info("Noch keine Whiskys in der Datenbank. Registriere zuerst einen Whisky.")

    st.divider()

    # Manual barcode entry
    st.subheader("🔢 Barcode manuell eingeben")
    manual_barcode = st.text_input("EAN/Barcode eingeben")

    if manual_barcode:
        whisky = db.get_whisky_by_barcode(manual_barcode)

        if whisky:
            whisky_id, whisky_name, year, distillery = whisky[0], whisky[1], whisky[2], whisky[3]
            st.success(f"Whisky gefunden: **{whisky_name}** ({distillery}, {year})")

            score = st.slider("Bewertung", 0.0, 10.0, 7.0, 0.5, key="manual_score")
            notes = st.text_area("Notizen (optional)", key="manual_notes")

            if st.button("💾 Bewertung speichern", key="manual_save"):
                db.add_guest_rating(whisky_id, user_name, score, notes)
                card_id, is_new, rarity = db.unlock_card(user_name, whisky_id)

                if is_new:
                    st.balloons()
                    st.success(f"🎴 Neue Karte freigeschaltet: **{whisky_name}** ({rarity.upper()})")

                newly_unlocked = db.check_and_unlock_achievements(user_name)
                for ach in newly_unlocked:
                    st.success(f"🏆 Achievement: {ach['icon']} {ach['name']}")

                st.rerun()
        else:
            st.info("Barcode nicht in der Datenbank gefunden.")
