import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Business Verification Dashboard",
    page_icon="📍",
    layout="wide"
)

st.title("📍 KNCCI Jiinue Business Verification Dashboard")
st.caption(f"Real-time view of business verifications by field officers - Stats as of {datetime.now().strftime('%B %d, %Y')}")

# -------------------- SETTINGS --------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zsxFO4Gix-NqRRt-LQWf_TzlJcUtMbHdCOmstTOaP_Q/export?format=csv"

# -------------------- FUNCTION TO LOAD DATA --------------------
@st.cache_data(ttl=300)
def load_data(url):
    with st.spinner("Loading data..."):
        try:
            df_raw = pd.read_csv(url)
            df_raw.columns = df_raw.columns.str.strip()

            # Debugging: Show first few raw timestamps
            st.sidebar.write("DEBUG: First 5 raw 'Timestamp' values:")
            st.sidebar.write(df_raw['Timestamp'].head().tolist())

            df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
            
            if df_raw['Timestamp'].isna().any():
                st.sidebar.write("DEBUG: Some timestamps failed to parse. Count of NaT:", df_raw['Timestamp'].isna().sum())
                st.sidebar.write("DEBUG: First 5 failed timestamps (if any):")
                st.sidebar.write(df_raw[df_raw['Timestamp'].isna()]['Timestamp'].head().tolist())

            st.sidebar.write("DEBUG: Timestamp range after parsing:")
            st.sidebar.write(f"Min: {df_raw['Timestamp'].min()}, Max: {df_raw['Timestamp'].max()}")

            df_raw['County'] = df_raw['County'].str.strip().str.title()

            # Process geo-coordinates
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
                    lat, lon = None, None  # Simplified: only handling lat,lon format for now
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
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame(), pd.DataFrame()

# -------------------- LOAD DATA --------------------
df_raw, df_clean = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded from the source. Check the URL or data availability.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("📅 Filters")
min_date = df_raw['Timestamp'].min().date()
max_date = df_raw['Timestamp'].max().date()

# Force min_date to March 2
filter_min_date = min(min_date, datetime(2025, 3, 2).date())

st.sidebar.markdown(f"🗓️ **Earliest Submission**: `{min_date}`")
st.sidebar.markdown(f"🗓️ **Latest Submission**: `{max_date}`")

# Date range filter
default_start = datetime(2025, 3, 2).date()
default_end = datetime(2025, 3, 24).date()

date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(default_start, default_end),
    min_value=filter_min_date,
    max_value=max_date,
    help="Choose start and end dates (ends at 12:00 on end date)."
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
else:
    start_date = end_date = date_range

filter_start = datetime.combine(start_date, datetime.min.time())  # 00:00:00
filter_end = datetime.combine(end_date, datetime.strptime("12:00:00", "%H:%M:%S").time())  # 12:00:00

# County filter
counties = sorted(df_raw['County'].dropna().unique())
selected_counties = st.sidebar.multiselect(
    "Select Counties:",
    options=counties,
    default=counties,
    help="Filter by specific counties."
)

# -------------------- FILTER DATA --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'] >= filter_start) &
    (df_raw['Timestamp'] <= filter_end) &
    (df_raw['County'].isin(selected_counties))
]

filtered_clean_df = df_clean[
    (df_clean['Timestamp'] >= filter_start) &
    (df_clean['Timestamp'] <= filter_end) &
    (df_clean['County'].isin(selected_counties))
]

# Check submissions after 12:00:00 today
today_noon = datetime(2025, 3, 24, 12, 0, 0)
after_noon_df = df_raw[df_raw['Timestamp'] > today_noon] if datetime.now().date() == datetime(2025, 3, 24).date() else pd.DataFrame()

# -------------------- HIGH-LEVEL SUMMARY --------------------
st.subheader("📈 High-Level Summary")
col1, col2, col3 = st.columns(3)
col1.metric("✅ Total Submissions (ALL)", f"{df_raw.shape[0]:,}")
col2.metric("📍 Total Counties Covered", df_raw['County'].nunique())
col3.metric("📊 Submissions in Range", f"{filtered_df.shape[0]:,}")

# Gap explanation
gap = df_raw.shape[0] - filtered_df.shape[0]
after_noon_count = after_noon_df.shape[0]
if gap > 0:
    if after_noon_count > 0 and datetime.now().date() == datetime(2025, 3, 24).date():
        st.info(f"ℹ️ {gap:,} submissions outside range. {after_noon_count:,} after {today_noon.strftime('%B %d, %Y')} 12:00 today.")
    else:
        st.info(f"ℹ️ {gap:,} submissions outside range (before {start_date.strftime('%B %d')} or after {end_date.strftime('%B %d')} 12:00).")

# -------------------- MAP VIEW --------------------
st.subheader("🗺️ Verification Locations")
if not filtered_clean_df.empty:
    fig_map = px.scatter_mapbox(
        filtered_clean_df,
        lat="Latitude",
        lon="Longitude",
        color="County",
        hover_name="County",
        hover_data={"Timestamp": True, "Latitude": False, "Longitude": False},
        zoom=5,
        height=500
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("⚠️ No geocoded data available for the selected filters.")

# -------------------- COUNTY BREAKDOWN --------------------
st.subheader(f"📊 Submissions by County ({start_date.strftime('%B %d, %Y')} 00:00 to {end_date.strftime('%B %d, %Y')} 12:00)")
filtered_county_stats = filtered_df.groupby('County').agg(
    Count=('Timestamp', 'size'),
    Timestamps=('Timestamp', lambda x: x.dt.strftime('%Y-%m-%d %H:%M:%S').tolist())
).reset_index()

if not filtered_county_stats.empty:
    fig_bar = px.bar(
        filtered_county_stats,
        x='County',
        y='Count',
        title=f"Submissions per County ({start_date.strftime('%B %d, %Y')} 00:00 to {end_date.strftime('%B %d, %Y')} 12:00)",
        height=400,
        text=filtered_county_stats['Count'].apply(lambda x: f"{x:,}")
    )
    fig_bar.update_traces(textposition='auto')
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info(f"ℹ️ No submissions for {start_date.strftime('%B %d, %Y')} 00:00 to {end_date.strftime('%B %d, %Y')} 12:00.")

# -------------------- DETAILED DATA --------------------
st.subheader("📋 Detailed Submissions")
if not filtered_county_stats.empty:
    st.dataframe(filtered_county_stats)
    if after_noon_count > 0 and datetime.now().date() == datetime(2025, 3, 24).date():
        st.write("📋 Submissions After Today 12:00:")
        after_noon_stats = after_noon_df.groupby('County').agg(
            Count=('Timestamp', 'size'),
            Timestamps=('Timestamp', lambda x: x.dt.strftime('%Y-%m-%d %H:%M:%S').tolist())
        ).reset_index()
        st.dataframe(after_noon_stats)
else:
    st.info("ℹ️ No detailed data for the selected filters.")

# -------------------- NO-WORK ANALYSIS --------------------
st.subheader("🚫 Counties with No Submissions")
all_counties_47 = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta",
    "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi",
    "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
    "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
    "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru",
    "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma",
    "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
]

active_counties = filtered_df['County'].unique().tolist()
no_work_counties = [county for county in all_counties_47 if county not in active_counties]

if no_work_counties:
    st.error(f"🚫 Counties with NO Submissions: {', '.join(no_work_counties)} ({len(no_work_counties)} total)")
else:
    st.success("✅ All counties have submissions!")

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not filtered_county_stats.empty:
    filtered_csv = convert_df_to_csv(filtered_county_stats)
    st.download_button(
        label=f"📥 Download Stats CSV ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
        data=filtered_csv,
        file_name=f"County_Stats_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.csv",
        mime='text/csv'
    )

st.success(f"✅ Dashboard updated dynamically as of {datetime.now().strftime('%B %d, %Y')}!")
