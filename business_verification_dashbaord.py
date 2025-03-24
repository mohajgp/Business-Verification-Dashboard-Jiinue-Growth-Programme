import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from openlocationcode import openlocationcode as olc

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

ALL_COUNTIES = [
    'Mombasa', 'Kwale', 'Kilifi', 'Tana River', 'Lamu', 'Taita Taveta', 'Garissa', 'Wajir',
    'Mandera', 'Marsabit', 'Isiolo', 'Meru', 'Tharaka Nithi', 'Embu', 'Kitui', 'Machakos',
    'Makueni', 'Nyandarua', 'Nyeri', 'Kirinyaga', 'Murang\'a', 'Kiambu', 'Turkana',
    'West Pokot', 'Samburu', 'Trans Nzoia', 'Uasin Gishu', 'Elgeyo Marakwet', 'Nandi',
    'Baringo', 'Laikipia', 'Nakuru', 'Narok', 'Kajiado', 'Kericho', 'Bomet', 'Kakamega',
    'Vihiga', 'Bungoma', 'Busia', 'Siaya', 'Kisumu', 'Homa Bay', 'Migori', 'Kisii', 'Nyamira',
    'Nairobi'
]

# -------------------- LOAD DATA FUNCTION --------------------
@st.cache_data(ttl=300)
def load_data(url):
    with st.spinner("Loading data..."):
        df_raw = pd.read_csv(url)
        df_raw.columns = df_raw.columns.str.strip()

        # Convert timestamp column
        df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df_raw['County'] = df_raw['County'].str.strip().str.title()

        # Clean data for geocoding
        df_clean = df_raw.dropna(subset=['Geo-Coordinates']).copy()

        latitudes = []
        longitudes = []

        for coord in df_clean['Geo-Coordinates']:
            coord = coord.strip()
            if ',' in coord:
                parts = coord.split(',')
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                except ValueError:
                    lat, lon = None, None
            else:
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

        # Validate coordinates within Kenya region
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
    max_value=max_date.date()
)

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

selected_counties = st.sidebar.multiselect(
    "Select Counties",
    options=sorted(df_raw['County'].dropna().unique()),
    default=sorted(df_raw['County'].dropna().unique())
)

if st.sidebar.button("🔄 Reset Filters"):
    st.experimental_rerun()

# -------------------- APPLY FILTERS --------------------
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

col1, col2, col3 = st.columns(3)
col1.metric("✅ Total Submissions (ALL)", f"{df_raw.shape[0]:,}")
col2.metric("📊 Filtered Submissions", f"{filtered_raw.shape[0]:,}")
col3.metric("📍 Counties Covered", filtered_raw['County'].nunique())

# -------------------- MARCH AND WEEKLY SUBMISSION ANALYSIS --------------------
st.subheader("📅 March and Weekly Submissions Analysis")

# Define March period
march_start = datetime(2025, 3, 1)
march_end = datetime(2025, 3, 31)

march_df = df_raw[
    (df_raw['Timestamp'] >= march_start) &
    (df_raw['Timestamp'] <= march_end)
]

# Define weekly period: 17th March to 23rd March (inclusive)
week_start = datetime(2025, 3, 17)
week_end = datetime(2025, 3, 23)

weekly_df = df_raw[
    (df_raw['Timestamp'] >= week_start) &
    (df_raw['Timestamp'] <= week_end)
]

# Submissions count per county
march_county_submissions = march_df['County'].value_counts().to_dict()
weekly_county_submissions = weekly_df['County'].value_counts().to_dict()

# Counties without submissions
counties_no_march = sorted(list(set(ALL_COUNTIES) - set(march_df['County'].dropna().unique())))
counties_no_week = sorted(list(set(ALL_COUNTIES) - set(weekly_df['County'].dropna().unique())))

# Display counties and counts
st.markdown("### 🚫 Counties with **NO** submissions in March 2025")
st.write(counties_no_march)

st.markdown("### 🚫 Counties with **NO** submissions during 17-23 March 2025")
st.write(counties_no_week)

# Display submission counts
st.markdown("### 📊 Submissions per County - March 2025")
st.dataframe(pd.DataFrame.from_dict(march_county_submissions, orient='index', columns=['Submissions']).sort_index())

st.markdown("### 📊 Submissions per County - 17-23 March 2025")
st.dataframe(pd.DataFrame.from_dict(weekly_county_submissions, orient='index', columns=['Submissions']).sort_index())

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

# -------------------- DATA TABLE & DOWNLOAD --------------------
st.subheader("📄 Filtered Data Table (All Submissions)")

if not filtered_raw.empty:
    st.dataframe(filtered_raw)
else:
    st.info("ℹ️ No submissions found for the selected filters.")

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
