"""Statistics and analytics for the whisky collection."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import db

st.set_page_config(page_title="Statistics", page_icon="📊", layout="wide")
st.title("Collection Statistics")

# Get data
whiskies = db.get_all_whiskies()
stats = db.get_whisky_stats()

if not whiskies:
    st.info("No whiskies in your collection yet. Add some on the Register page!")
    st.stop()

# Top metrics
st.subheader("Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Bottles", stats[0])
with col2:
    st.metric("Total Value", f"${stats[1]:.0f}" if stats[1] else "$0")
with col3:
    st.metric("Avg Price", f"${stats[4]:.0f}" if stats[4] else "$0")
with col4:
    price_range = f"${stats[2]:.0f} - ${stats[3]:.0f}" if stats[2] else "-"
    st.metric("Price Range", price_range)

st.divider()

# Two column layout
col_left, col_right = st.columns(2)

with col_left:
    # Age distribution
    st.subheader("Age Distribution")
    age_data = db.get_age_distribution()

    if age_data:
        df_age = pd.DataFrame(age_data, columns=["Year", "Count"])
        fig = px.bar(
            df_age,
            x="Year",
            y="Count",
            title="Whiskies by Age Statement",
            labels={"Year": "Age (Years)", "Count": "Number of Bottles"}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No age data available")

    # Fill levels
    st.subheader("Fill Levels")
    fill_data = db.get_fill_levels()

    if fill_data:
        df_fill = pd.DataFrame(fill_data, columns=["Name", "Current ML", "Bottle ML", "Fill %"])

        # Color code by fill level
        colors = []
        for pct in df_fill["Fill %"]:
            if pct >= 75:
                colors.append("#22c55e")  # green
            elif pct >= 50:
                colors.append("#eab308")  # yellow
            elif pct >= 25:
                colors.append("#f97316")  # orange
            else:
                colors.append("#ef4444")  # red

        fig = go.Figure(go.Bar(
            x=df_fill["Fill %"],
            y=df_fill["Name"],
            orientation='h',
            marker_color=colors,
            text=df_fill["Fill %"].apply(lambda x: f"{x:.0f}%"),
            textposition='outside'
        ))
        fig.update_layout(
            title="Bottle Fill Levels",
            xaxis_title="Fill %",
            yaxis_title="",
            height=max(300, len(fill_data) * 40)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No fill data available")

with col_right:
    # Price distribution
    st.subheader("Price Distribution")

    prices = [w[4] for w in whiskies if w[4]]
    if prices:
        fig = px.histogram(
            x=prices,
            nbins=10,
            title="Price Distribution",
            labels={"x": "Price ($)", "y": "Count"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No price data available")

    # Distillery breakdown
    st.subheader("By Distillery")

    distillery_counts = {}
    for w in whiskies:
        dist = w[3] or "Unknown"
        distillery_counts[dist] = distillery_counts.get(dist, 0) + 1

    if distillery_counts:
        df_dist = pd.DataFrame([
            {"Distillery": k, "Count": v}
            for k, v in sorted(distillery_counts.items(), key=lambda x: -x[1])
        ])

        fig = px.pie(
            df_dist,
            names="Distillery",
            values="Count",
            title="Bottles by Distillery"
        )
        st.plotly_chart(fig, use_container_width=True)

# Map
st.divider()
st.subheader("Distillery Map")

distilleries = db.get_all_distilleries()

if distilleries:
    # Create map centered on Scotland by default
    m = folium.Map(location=[56.5, -4.5], zoom_start=5)

    for d in distilleries:
        # d: (id, name, region, country, latitude, longitude, logo_path)
        if d[4] and d[5]:  # lat and lng
            # Count whiskies from this distillery
            count = sum(1 for w in whiskies if w[3] == d[1])

            popup_text = f"""
            <b>{d[1]}</b><br>
            Region: {d[2] or 'Unknown'}<br>
            Country: {d[3] or 'Unknown'}<br>
            Bottles: {count}
            """

            folium.Marker(
                location=[d[4], d[5]],
                popup=folium.Popup(popup_text, max_width=200),
                tooltip=d[1],
                icon=folium.Icon(color='red', icon='glass', prefix='fa')
            ).add_to(m)

    st_folium(m, width=None, height=500, use_container_width=True)
else:
    st.info("No distillery locations available yet. Add whiskies to populate the map!")

# Running low alert
st.divider()
st.subheader("Running Low")

low_bottles = [
    (w[1], w[5] / w[6] * 100 if w[6] else 0)
    for w in whiskies
    if w[6] and (w[5] / w[6] * 100) < 25
]

if low_bottles:
    st.warning(f"{len(low_bottles)} bottle(s) running low!")
    for name, pct in sorted(low_bottles, key=lambda x: x[1]):
        st.write(f"- **{name}**: {pct:.0f}% remaining")
else:
    st.success("All bottles have plenty remaining!")
