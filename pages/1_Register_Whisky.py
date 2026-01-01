"""Register a new whisky via photo recognition."""

import streamlit as st
from PIL import Image
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai

st.set_page_config(page_title="Register Whisky", page_icon="📸")
st.title("Register Whisky")

# Initialize session state
if "recognition_result" not in st.session_state:
    st.session_state.recognition_result = None
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

# Photo upload
st.subheader("Upload a photo of your whisky bottle")

uploaded_file = st.file_uploader(
    "Take a photo or upload an image",
    type=["jpg", "jpeg", "png"],
    help="Make sure the label is clearly visible"
)

if uploaded_file is not None:
    # Display the image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded image", width=300)

    # Store image bytes
    uploaded_file.seek(0)
    st.session_state.uploaded_image = uploaded_file.read()

    # Analyze button
    if st.button("Analyze with AI", type="primary"):
        with st.spinner("Analyzing image..."):
            try:
                result = ai.analyze_whisky_photo(st.session_state.uploaded_image)
                st.session_state.recognition_result = result
                st.success("Analysis complete!")
            except Exception as e:
                st.error(f"Error analyzing image: {e}")

# Show recognition results and edit form
if st.session_state.recognition_result:
    result = st.session_state.recognition_result

    st.subheader("Recognition Results")
    st.info(f"Confidence: {result.get('confidence', 0) * 100:.0f}%")

    # Editable form
    with st.form("whisky_form"):
        name = st.text_input("Whisky Name", value=result.get("name", ""))
        distillery = st.text_input("Distillery", value=result.get("distillery", ""))
        year = st.number_input(
            "Age (years)",
            min_value=0,
            max_value=100,
            value=result.get("year") or 0,
            help="Enter 0 if no age statement"
        )

        # Fill level
        fill_options = {
            "full": "Full (100%)",
            "three_quarters": "3/4 Full (75%)",
            "half": "Half (50%)",
            "quarter": "1/4 Full (25%)",
            "near_empty": "Near Empty (<10%)"
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
            "Fill Level",
            options=list(fill_options.keys()),
            format_func=lambda x: fill_options[x],
            index=list(fill_options.keys()).index(detected_fill) if detected_fill in fill_options else 0
        )

        price = st.number_input(
            "Price ($)",
            min_value=0.0,
            step=1.0,
            help="Optional: Enter the purchase price"
        )

        submitted = st.form_submit_button("Save Whisky", type="primary")

        if submitted:
            if not name or not distillery:
                st.error("Please enter both name and distillery")
            else:
                # Get or create distillery
                distillery_id = db.get_or_create_distillery(distillery)

                # Save image to assets
                image_path = None
                if st.session_state.uploaded_image:
                    assets_dir = Path(__file__).parent.parent / "assets" / "whisky_images"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    image_filename = f"{name.lower().replace(' ', '_')}.jpg"
                    image_path = str(assets_dir / image_filename)

                    img = Image.open(io.BytesIO(st.session_state.uploaded_image))
                    img.save(image_path, "JPEG", quality=85)

                # Add whisky to database
                whisky_id = db.add_whisky(
                    name=name,
                    year=year if year > 0 else None,
                    distillery_id=distillery_id,
                    price=price if price > 0 else None,
                    current_fill_ml=fill_ml_map[fill_level],
                    image_path=image_path
                )

                st.success(f"Saved {name}!")

                # Generate info in background
                with st.spinner("Generating whisky info..."):
                    try:
                        info = ai.generate_whisky_info(name, distillery, year if year > 0 else None)
                        db.update_whisky_info(whisky_id, info)

                        # Try to get distillery location
                        location = ai.get_distillery_location(distillery)
                        if location:
                            db.update_distillery_location(
                                distillery_id,
                                location["latitude"],
                                location["longitude"]
                            )
                            # Update region/country
                            conn = db.get_connection()
                            conn.execute("""
                                UPDATE distilleries
                                SET region = ?, country = ?
                                WHERE id = ?
                            """, [location.get("region"), location.get("country"), distillery_id])
                            conn.close()

                        st.success("Info generated! Check the Whisky Info page.")
                    except Exception as e:
                        st.warning(f"Could not generate info: {e}")

                # Clear session state
                st.session_state.recognition_result = None
                st.session_state.uploaded_image = None
                st.rerun()

# Manual entry option
st.divider()
st.subheader("Or add manually")

with st.expander("Manual Entry Form"):
    with st.form("manual_form"):
        m_name = st.text_input("Whisky Name")
        m_distillery = st.text_input("Distillery")
        m_year = st.number_input("Age (years)", min_value=0, max_value=100, value=0)
        m_price = st.number_input("Price ($)", min_value=0.0, step=1.0)
        m_fill = st.slider("Fill Level (%)", min_value=0, max_value=100, value=100)

        if st.form_submit_button("Add Whisky"):
            if not m_name or not m_distillery:
                st.error("Please enter both name and distillery")
            else:
                distillery_id = db.get_or_create_distillery(m_distillery)
                whisky_id = db.add_whisky(
                    name=m_name,
                    year=m_year if m_year > 0 else None,
                    distillery_id=distillery_id,
                    price=m_price if m_price > 0 else None,
                    current_fill_ml=int(700 * m_fill / 100)
                )

                # Generate info
                with st.spinner("Generating info..."):
                    try:
                        info = ai.generate_whisky_info(m_name, m_distillery, m_year if m_year > 0 else None)
                        db.update_whisky_info(whisky_id, info)

                        location = ai.get_distillery_location(m_distillery)
                        if location:
                            db.update_distillery_location(distillery_id, location["latitude"], location["longitude"])
                    except Exception as e:
                        st.warning(f"Could not generate info: {e}")

                st.success(f"Added {m_name}!")
                st.rerun()
