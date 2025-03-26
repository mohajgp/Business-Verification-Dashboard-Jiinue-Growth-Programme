import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

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

            df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
            df_raw['County'] = df_raw['County'].str.strip().str.title()

            return df_raw
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()

# -------------------- LOAD DATA --------------------
df_raw = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded from the source. Check the URL or data availability.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("📅 Filters")

# Date filter: From March 1st to a day after today
min_date = datetime(2025, 3, 1).date()
max_date = (datetime.now() + timedelta(days=1)).date()

st.sidebar.markdown(f"🗓️ **Earliest Submission**: `{min_date}`")
st.sidebar.markdown(f"🗓️ **Latest Submission**: `{max_date}`")

# Date range selection
date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)
filter_start = datetime.combine(start_date, datetime.min.time())
filter_end = datetime.combine(end_date, datetime.max.time())

# County filter
counties = sorted(df_raw['County'].dropna().unique())
selected_counties = st.sidebar.multiselect(
    "Select Counties:",
    options=counties,
    default=counties
)

# -------------------- FILTER DATA --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'] >= filter_start) &
    (df_raw['Timestamp'] <= filter_end) &
    (df_raw['County'].isin(selected_counties))
]

# -------------------- HIGH-LEVEL SUMMARY --------------------
st.subheader("📈 High-Level Summary")
col1, col2, col3 = st.columns(3)
col1.metric("✅ Total Submissions (ALL)", f"{df_raw.shape[0]:,}")
col2.metric("📍 Total Counties Covered", df_raw['County'].nunique())
col3.metric("📊 Submissions in Range", f"{filtered_df.shape[0]:,}")

# -------------------- COUNTY BREAKDOWN --------------------
st.subheader(f"📊 Submissions by County ({start_date} to {end_date})")
filtered_county_stats = filtered_df.groupby('County').size().reset_index(name='Count')

if not filtered_county_stats.empty:
    fig_bar = px.bar(
        filtered_county_stats,
        x='County',
        y='Count',
        title=f"Submissions per County ({start_date} to {end_date})",
        height=400,
        text=filtered_county_stats['Count'].apply(lambda x: f"{x:,}")
    )
    fig_bar.update_traces(textposition='auto')
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info(f"ℹ️ No submissions for the selected date range.")

# -------------------- NO SUBMISSIONS ANALYSIS --------------------
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
no_submission_counties = [county for county in all_counties_47 if county not in active_counties]

if no_submission_counties:
    st.error(f"🚫 Counties with NO Submissions: {', '.join(no_submission_counties)} ({len(no_submission_counties)} total)")
else:
    st.success("✅ All counties have submissions!")

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not filtered_county_stats.empty:
    filtered_csv = convert_df_to_csv(filtered_county_stats)
    st.download_button(
        label=f"📥 Download Stats CSV ({start_date} to {end_date})",
        data=filtered_csv,
        file_name=f"County_Stats_{start_date}_to_{end_date}.csv",
        mime='text/csv'
    )

st.success(f"✅ Dashboard updated dynamically as of {datetime.now().strftime('%B %d, %Y')}!")
