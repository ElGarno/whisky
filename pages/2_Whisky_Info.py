"""View detailed information about whiskies."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai

st.set_page_config(page_title="Whisky Info", page_icon="📖", layout="wide")
st.title("Whisky Information")

# Get all whiskies
whiskies = db.get_all_whiskies()

if not whiskies:
    st.info("No whiskies in your collection yet. Add some on the Register page!")
    st.stop()

# Create selection options
whisky_options = {w[0]: f"{w[1]} ({w[3] or 'Unknown'})" for w in whiskies}

selected_id = st.selectbox(
    "Select a whisky",
    options=list(whisky_options.keys()),
    format_func=lambda x: whisky_options[x]
)

# Get selected whisky details
whisky = db.get_whisky(selected_id)

if whisky:
    # whisky: (id, name, year, distillery, distillery_id, price, current_fill_ml, bottle_size_ml, image_path, info_markdown)

    col1, col2 = st.columns([1, 2])

    with col1:
        # Show image if available
        if whisky[8]:  # image_path
            try:
                st.image(whisky[8], caption=whisky[1], width=250)
            except Exception:
                st.info("Image not available")
        else:
            st.info("No image")

        # Quick stats
        st.subheader("Details")
        st.write(f"**Distillery:** {whisky[3] or 'Unknown'}")
        if whisky[2]:  # year
            st.write(f"**Age:** {whisky[2]} years")
        if whisky[5]:  # price
            st.write(f"**Price:** ${whisky[5]:.2f}")

        # Fill level
        fill_pct = (whisky[6] / whisky[7]) * 100 if whisky[7] else 0
        st.write(f"**Fill Level:** {fill_pct:.0f}%")
        st.progress(fill_pct / 100)

    with col2:
        st.subheader(whisky[1])  # name

        # Show info markdown
        if whisky[9]:  # info_markdown
            st.markdown(whisky[9])
        else:
            st.info("No info generated yet.")

        # Regenerate button
        if st.button("Regenerate Info"):
            with st.spinner("Generating new info..."):
                try:
                    info = ai.generate_whisky_info(
                        whisky[1],  # name
                        whisky[3],  # distillery
                        whisky[2]   # year
                    )
                    db.update_whisky_info(selected_id, info)
                    st.success("Info regenerated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# Show all whiskies in a table
st.divider()
st.subheader("Collection Overview")

import pandas as pd

data = []
for w in whiskies:
    fill_pct = (w[5] / w[6]) * 100 if w[6] else 0
    data.append({
        "Name": w[1],
        "Distillery": w[3] or "Unknown",
        "Age": w[2] if w[2] else "NAS",
        "Price": f"${w[4]:.0f}" if w[4] else "-",
        "Fill": f"{fill_pct:.0f}%"
    })

df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True, hide_index=True)
