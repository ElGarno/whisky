"""Whisky tasting session management."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db, ai

st.set_page_config(page_title="Tasting", page_icon="🍷", layout="wide")
st.title("Whisky Tasting")

# Initialize session state
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

# Get whiskies
whiskies = db.get_all_whiskies()

# Check for active tasting
active_tasting = db.get_active_tasting()

# Tab navigation
tab1, tab2, tab3 = st.tabs(["New Tasting", "Active Tasting", "Past Tastings"])

with tab1:
    if active_tasting:
        st.warning("You have an active tasting. Complete or view it in the Active Tasting tab.")
    elif not whiskies:
        st.info("Add some whiskies first on the Register page!")
    else:
        st.subheader("Create New Tasting")

        # Step 1: Select whiskies
        st.write("**Step 1: Select Whiskies**")

        whisky_options = {w[0]: f"{w[1]} ({w[3] or 'Unknown'})" for w in whiskies}
        selected_ids = st.multiselect(
            "Choose whiskies for the tasting",
            options=list(whisky_options.keys()),
            format_func=lambda x: whisky_options[x],
            default=st.session_state.selected_whiskies
        )
        st.session_state.selected_whiskies = selected_ids

        # Step 2: Add participants
        st.write("**Step 2: Add Participants**")
        participants_input = st.text_input(
            "Enter participant names (comma-separated)",
            value=", ".join(st.session_state.participants),
            placeholder="John, Jane, Bob"
        )
        if participants_input:
            st.session_state.participants = [p.strip() for p in participants_input.split(",") if p.strip()]

        # Step 3: Get AI suggestions
        if len(selected_ids) >= 2 and st.session_state.participants:
            st.write("**Step 3: Tasting Order**")

            if st.button("Get AI Suggestions"):
                selected_whiskies = [
                    {"id": w[0], "name": w[1], "distillery": w[3], "year": w[2]}
                    for w in whiskies if w[0] in selected_ids
                ]

                with st.spinner("Getting AI suggestions..."):
                    try:
                        suggestions = ai.suggest_tasting_order(selected_whiskies)
                        st.session_state.suggested_orders = suggestions
                    except Exception as e:
                        st.error(f"Error: {e}")

            # Show suggestions
            if st.session_state.suggested_orders:
                for i, order in enumerate(st.session_state.suggested_orders):
                    with st.expander(f"Option {i+1}: {order['order_name']}", expanded=i==0):
                        st.write("**Order:**")
                        for j, name in enumerate(order['whisky_names'], 1):
                            st.write(f"{j}. {name}")
                        st.write("**Why:**", order['explanation'])

                        if st.button(f"Use this order", key=f"use_order_{i}"):
                            st.session_state.chosen_order = order
                            st.success("Order selected!")

            # Create tasting button
            if st.session_state.chosen_order:
                tasting_name = st.text_input("Tasting name", value="Whisky Tasting")

                if st.button("Start Tasting", type="primary"):
                    # Map whisky names back to IDs in order
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

                    # Reset session state
                    st.session_state.selected_whiskies = []
                    st.session_state.participants = []
                    st.session_state.suggested_orders = None
                    st.session_state.chosen_order = None

                    st.success(f"Tasting '{tasting_name}' created!")
                    st.rerun()

        elif len(selected_ids) < 2:
            st.info("Select at least 2 whiskies")
        elif not st.session_state.participants:
            st.info("Add at least one participant")

with tab2:
    if not active_tasting:
        st.info("No active tasting. Create one in the New Tasting tab!")
    else:
        # active_tasting: (id, name, date, whisky_ids, participants, order_explanation, summary_markdown)
        tasting_id = active_tasting[0]
        tasting_name = active_tasting[1]
        whisky_ids = active_tasting[3]
        participants = active_tasting[4]
        order_explanation = active_tasting[5]

        st.subheader(f"Active: {tasting_name}")
        st.write(f"**Date:** {active_tasting[2]}")
        st.write(f"**Participants:** {', '.join(participants)}")

        if order_explanation:
            with st.expander("Tasting Order Explanation"):
                st.write(order_explanation)

        # Get whiskies in order
        tasting_whiskies = [db.get_whisky(wid) for wid in whisky_ids]
        existing_ratings = db.get_tasting_ratings(tasting_id)

        # Rating form
        st.subheader("Enter Ratings")

        for whisky in tasting_whiskies:
            if not whisky:
                continue

            st.write(f"### {whisky[1]}")  # name

            for participant in participants:
                # Check if rating exists
                has_rating = db.get_rating_exists(tasting_id, whisky[0], participant)

                if has_rating:
                    st.write(f"✅ {participant}: Already rated")
                else:
                    col1, col2, col3 = st.columns([2, 3, 2])

                    with col1:
                        st.write(f"**{participant}**")

                    with col2:
                        score = st.slider(
                            "Score",
                            min_value=0.0,
                            max_value=10.0,
                            value=5.0,
                            step=0.5,
                            key=f"score_{whisky[0]}_{participant}",
                            label_visibility="collapsed"
                        )

                    with col3:
                        if st.button("Save", key=f"save_{whisky[0]}_{participant}"):
                            notes = st.session_state.get(f"notes_{whisky[0]}_{participant}", "")
                            db.add_rating(tasting_id, whisky[0], participant, score, notes)
                            st.success("Saved!")
                            st.rerun()

                    notes = st.text_input(
                        "Notes (optional)",
                        key=f"notes_{whisky[0]}_{participant}",
                        label_visibility="collapsed",
                        placeholder="Tasting notes..."
                    )

            st.divider()

        # Check if all ratings complete
        total_ratings_needed = len(whisky_ids) * len(participants)
        current_ratings = len(existing_ratings)

        st.write(f"**Progress:** {current_ratings}/{total_ratings_needed} ratings")
        st.progress(current_ratings / total_ratings_needed if total_ratings_needed > 0 else 0)

        if current_ratings == total_ratings_needed:
            st.success("All ratings complete!")

            if st.button("Generate Summary & Complete Tasting", type="primary"):
                with st.spinner("Generating AI summary..."):
                    try:
                        # Prepare ratings data
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
                        st.success("Tasting completed!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error generating summary: {e}")

with tab3:
    st.subheader("Past Tastings")

    all_tastings = db.get_all_tastings()
    completed_tastings = [t for t in all_tastings if t[5] == 'completed']

    if not completed_tastings:
        st.info("No completed tastings yet.")
    else:
        for tasting in completed_tastings:
            # tasting: (id, name, date, whisky_ids, participants, status, summary_markdown)
            with st.expander(f"{tasting[1]} - {tasting[2]}"):
                st.write(f"**Participants:** {', '.join(tasting[4])}")
                st.write(f"**Whiskies:** {len(tasting[3])}")

                if tasting[6]:  # summary_markdown
                    st.divider()
                    st.markdown(tasting[6])

                # Show ratings
                ratings = db.get_tasting_ratings(tasting[0])
                if ratings:
                    st.divider()
                    st.write("**All Ratings:**")

                    import pandas as pd
                    df = pd.DataFrame([
                        {"Whisky": r[2], "Participant": r[3], "Score": r[4], "Notes": r[5] or ""}
                        for r in ratings
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)
