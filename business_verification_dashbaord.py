import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from openlocationcode import openlocationcode as olc  # pip install openlocationcode

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Business Verification Dashboard",
    page_icon="📍",
    layout="wide"
)

st.title("📍 KNCCI Jiinue Business Verification Dashboard")
st.caption("Real-time view of business verifications by field officers")

# -------------------- SETTINGS --------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zsxFO4Gix-NqRRt-LQWf_TzlJcUtMbHdCOmstTOaP_Q/export?format=csv"

# -------------------- FUNCTION TO LOAD DATA --------------------
@st.cache_data(ttl=300)
def load_data(url):
    with st.spinner("Loading data..."):
        df_raw = pd.read_csv(url)
        df_raw.columns = df_raw.columns.str.strip()

        # Clean Timestamp and County
        df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], errors='coerce')
        df_raw['County'] = (
            df_raw['County']
            .astype(str)
            .str.strip()
            .str.title()
            .str.replace("’", "'")
        )

        # Clean Geo Coordinates
        df_clean = df_raw.dropna(subset=['Geo-Coordinates']).copy()

        latitudes = []
        longitudes = []

        # Loop through each row & check whether it's lat/long or plus code
        for coord in df_clean['Geo-Coordinates']:
            coord = coord.strip()

            if ',' in coord:
                # Already lat,long
                parts = coord.split(',')
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                except ValueError:
                    lat, lon = None, None
            else:
                # Plus Code
                try:
                    decoded = olc.decode(coord)
                    lat = decoded.latitudeCenter
                    lon = decoded.longitudeCenter
                except Exception:
                    lat, lon = None, None

            latitudes.append(lat)
            longitudes.append(lon)

        df_clean['Latitude'] = latitudes
        df_clean['Longitude'] = longitudes
        df_clean = df_clean.dropna(subset=['Latitude', 'Longitude'])

        # Validate coordinates (Kenya region)
        df_clean = df_clean[
            (df_clean['Latitude'] >= -5) & (df_clean['Latitude'] <= 5) &
            (df_clean['Longitude'] >= 33) & (df_clean['Longitude'] <= 42)
        ]

    return df_raw, df_clean

# -------------------- LOAD DATA --------------------
df_raw, df_clean = load_data(SHEET_CSV_URL)

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("📅 Filter Submissions")

min_date = df_raw['Timestamp'].min()
max_date = df_raw['Timestamp'].max()

if pd.isna(min_date) or pd.isna(max_date):
    st.sidebar.warning("⚠️ No valid timestamp data available!")
    st.stop()

st.sidebar.markdown(f"🗓️ **Earliest Submission**: `{min_date.date()}`")
st.sidebar.markdown(f"🗓️ **Latest Submission**: `{max_date.date()}`")

date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date(),
    help="Select a date range where submissions exist."
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

counties = df_raw['County'].dropna().unique()
selected_counties = st.sidebar.multiselect(
    "Select Counties",
    options=sorted(counties),
    default=sorted(counties)
)

if st.sidebar.button("🔄 Reset Filters"):
    st.experimental_rerun()

# -------------------- FILTER DATA --------------------
filtered_raw = df_raw[
    (df_raw['Timestamp'].dt.date >= start_date) &
    (df_raw['Timestamp'].dt.date <= end_date) &
    (df_raw['County'].isin(selected_counties))
]

filtered_clean = df_clean[
    (df_clean['Timestamp'].dt.date >= start_date) &
    (df_clean['Timestamp'].dt.date <= end_date) &
    (df_clean['County'].isin(selected_counties))
]

# -------------------- SUMMARY METRICS --------------------
st.subheader("📈 Summary Metrics")

total_responses = df_raw.shape[0]
filtered_submissions = filtered_raw.shape[0]
counties_covered = filtered_raw['County'].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("✅ Total Submissions (ALL)", f"{total_responses:,}")
col2.metric("📊 Filtered Submissions", f"{filtered_submissions:,}")
col3.metric("📍 Counties Covered", counties_covered)

# -------------------- MAP --------------------
st.subheader("🗺️ Verified Business Locations Map")

if not filtered_clean.empty:
    fig_map = px.scatter_mapbox(
        filtered_clean,
        lat="Latitude",
        lon="Longitude",
        color="County",
        hover_name="Name of the Participant" if 'Name of the Participant' in df_raw.columns else None,
        hover_data={
            "Verified Phone Number": True,
            "Verified ID Number": True,
            "Latitude": False,
            "Longitude": False
        },
        zoom=6,
        height=600
    )
    fig_map.update_layout(mapbox_style="open-street-map")
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("⚠️ No geocoded data available for the selected filters.")

# -------------------- PER COUNTY STATS --------------------
st.subheader("📋 Submissions Per County - Weekly and March")

# Define weekly & monthly frames
today = pd.Timestamp.now().normalize()
week_start = today - pd.to_timedelta(today.weekday(), unit='D')

weekly_df = df_raw[df_raw['Timestamp'].dt.date >= week_start.date()]
march_df = df_raw[df_raw['Timestamp'].dt.month == 3]

# Group by county
weekly_counts = weekly_df.groupby('County').size().reset_index(name='Weekly Submissions')
march_counts = march_df.groupby('County').size().reset_index(name='March Submissions')

# Merge stats
county_stats = pd.DataFrame({'County': sorted(df_raw['County'].dropna().unique())})
county_stats = county_stats.merge(weekly_counts, on='County', how='left')
county_stats = county_stats.merge(march_counts, on='County', how='left')

# Fill NaN with 0
county_stats[['Weekly Submissions', 'March Submissions']] = county_stats[['Weekly Submissions', 'March Submissions']].fillna(0).astype(int)

# Display table
st.dataframe(county_stats, use_container_width=True)

# -------------------- NO SUBMISSIONS --------------------
st.subheader("🚫 Counties With NO Submissions (Week and March)")

all_counties = sorted(df_raw['County'].dropna().unique())

march_submitted_counties = march_df['County'].dropna().unique().tolist()
weekly_submitted_counties = weekly_df['County'].dropna().unique().tolist()

march_no_submissions = sorted([county for county in all_counties if county not in march_submitted_counties])
weekly_no_submissions = sorted([county for county in all_counties if county not in weekly_submitted_counties])

col1, col2 = st.columns(2)
with col1:
    st.warning("📆 No Submissions in March:")
    st.write(march_no_submissions if march_no_submissions else "✅ All counties submitted!")
with col2:
    st.warning("📅 No Submissions This Week:")
    st.write(weekly_no_submissions if weekly_no_submissions else "✅ All counties submitted!")

# -------------------- DATA TABLE --------------------
st.subheader("📄 Filtered Data Table (All Submissions)")

if not filtered_raw.empty:
    st.dataframe(filtered_raw)
else:
    st.info("ℹ️ No submissions found for the selected filters.")

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not filtered_raw.empty:
    csv_data = convert_df_to_csv(filtered_raw)

    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name=f"Business_Verifications_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime='text/csv'
    )

st.success("✅ Dashboard updated in real-time!")
