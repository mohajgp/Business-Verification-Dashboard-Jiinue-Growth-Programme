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

# Full list of counties in Kenya
ALL_COUNTIES = [
    'Mombasa', 'Kwale', 'Kilifi', 'Tana River', 'Lamu', 'Taita Taveta', 'Garissa', 'Wajir',
    'Mandera', 'Marsabit', 'Isiolo', 'Meru', 'Tharaka-Nithi', 'Embu', 'Kitui', 'Machakos',
    'Makueni', 'Nyandarua', 'Nyeri', 'Kirinyaga', "Murang'a", 'Kiambu', 'Turkana',
    'West Pokot', 'Samburu', 'Trans Nzoia', 'Uasin Gishu', 'Elgeyo Marakwet', 'Nandi',
    'Baringo', 'Laikipia', 'Nakuru', 'Narok', 'Kajiado', 'Kericho', 'Bomet', 'Kakamega',
    'Vihiga', 'Bungoma', 'Busia', 'Siaya', 'Kisumu', 'Homa Bay', 'Migori', 'Kisii', 'Nyamira',
    'Nairobi'
]

# -------------------- FUNCTION TO LOAD DATA --------------------
@st.cache_data(ttl=300)
def load_data(url):
    with st.spinner("Loading data..."):
        df_raw = pd.read_csv(url)
        df_raw.columns = df_raw.columns.str.strip()

        df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], errors='coerce')
        df_raw['County'] = df_raw['County'].str.strip().str.title()

        # Create clean copy with coordinates
        df_clean = df_raw.dropna(subset=['Geo-Coordinates']).copy()

        latitudes = []
        longitudes = []

        # Loop through each row & check whether it's lat/long or plus code
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

total_responses = df_raw.shape[0]
filtered_submissions = filtered_raw.shape[0]
counties_covered = filtered_raw['County'].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("✅ Total Submissions (ALL)", f"{total_responses:,}")
col2.metric("📊 Filtered Submissions", f"{filtered_submissions:,}")
col3.metric("📍 Counties Covered", counties_covered)

# -------------------- COUNTIES WITHOUT SUBMISSIONS --------------------
st.subheader("🚫 Counties Without Submissions")

counties_with_submissions = filtered_raw['County'].dropna().unique().tolist()

counties_without_submissions = sorted(list(set(ALL_COUNTIES) - set(counties_with_submissions)))

if counties_without_submissions:
    st.error(f"These counties have **NO submissions** for the selected filters ({len(counties_without_submissions)} counties):")
    st.write(counties_without_submissions)

    counties_no_work_df = pd.DataFrame({"Counties Without Submissions": counties_without_submissions})

    st.download_button(
        label="📥 Download No Submission Counties (CSV)",
        data=counties_no_work_df.to_csv(index=False).encode('utf-8'),
        file_name=f"No_Submissions_Counties_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime='text/csv'
    )
else:
    st.success("🎉 All counties have submissions for the selected filters!")

# -------------------- MARCH & WEEKLY SUBMISSION STATS WITH COUNTS --------------------
st.subheader("📅 March and Weekly Submissions Analysis (with Submission Counts)")

# === MARCH SUBMISSIONS ===
march_mask = (df_raw['Timestamp'].dt.month == 3) & (df_raw['Timestamp'].dt.year == 2024)
df_march = df_raw[march_mask]

march_counts = df_march.groupby('County').size().reindex(ALL_COUNTIES, fill_value=0).reset_index()
march_counts.columns = ['County', 'March Submissions']

counties_with_no_march_submissions = march_counts[march_counts['March Submissions'] == 0]['County'].tolist()

st.markdown(f"🚫 **Counties with NO submissions in March 2024 ({len(counties_with_no_march_submissions)} counties):** `{counties_with_no_march_submissions}`")

st.markdown("✅ **March 2024 Submission Counts by County:**")
st.dataframe(march_counts)

# === 17-24 MARCH SUBMISSIONS ===
start_week = datetime(2024, 3, 17).date()
end_week = datetime(2024, 3, 24).date()

week_mask = (df_raw['Timestamp'].dt.date >= start_week) & (df_raw['Timestamp'].dt.date <= end_week)
df_week = df_raw[week_mask]

week_counts = df_week.groupby('County').size().reindex(ALL_COUNTIES, fill_value=0).reset_index()
week_counts.columns = ['County', '17-24 March Submissions']

counties_with_no_week_submissions = week_counts[week_counts['17-24 March Submissions'] == 0]['County'].tolist()

st.markdown(f"🚫 **Counties with NO submissions during 17-24 March ({len(counties_with_no_week_submissions)} counties):** `{counties_with_no_week_submissions}`")

st.markdown("✅ **17-24 March Submission Counts by County:**")
st.dataframe(week_counts)

# -------------------- MAP OF VERIFIED BUSINESS LOCATIONS --------------------
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
