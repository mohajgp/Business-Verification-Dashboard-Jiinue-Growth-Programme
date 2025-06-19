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

# -------------------- PHONE CLEANING FUNCTION --------------------
def clean_phone(phone):
    phone = str(phone).strip().replace(" ", "").replace("+", "").replace("-", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("7"):
        return "254" + phone
    return phone

# -------------------- LOAD AND TAG DUPLICATES --------------------
@st.cache_data(ttl=300)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df['County'] = df['County'].str.strip().str.title()
    df['Verified ID Number'] = df['Verified ID Number'].astype(str).str.strip().str.upper()
    df['Verified Phone Number'] = df['Verified Phone Number'].astype(str).apply(clean_phone)
    df['Is Duplicate'] = df.duplicated(subset=['Verified ID Number', 'Verified Phone Number'], keep='first')
    return df

# -------------------- LOAD DATA --------------------
df_raw = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded from the source. Check the URL or data availability.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filters")
min_date = datetime(2025, 3, 1).date()
max_date = (datetime.now() + timedelta(days=1)).date()
date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)
filter_start = datetime.combine(start_date, datetime.min.time())
filter_end = datetime.combine(end_date, datetime.max.time())

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

# -------------------- METRICS (FILTERED VIEW) --------------------
st.subheader("📈 High-Level Summary (Filtered View)")
total_filtered_rows = filtered_df.shape[0]
unique_filtered_rows = filtered_df.drop_duplicates(subset=['Verified ID Number', 'Verified Phone Number']).shape[0]
filtered_counties = filtered_df['County'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Rows (Before Deduplication)", f"{total_filtered_rows:,}")
col2.metric("✅ Unique Submissions", f"{unique_filtered_rows:,}")
col3.metric("📍 Total Counties Covered", filtered_counties)
col4.metric("📊 Submissions in Range", f"{total_filtered_rows:,}")

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

    st.subheader("🔢 Total Submissions Per County")
    st.dataframe(filtered_county_stats.sort_values(by='Count', ascending=False).reset_index(drop=True))
else:
    st.info(f"ℹ️ No submissions for the selected date range.")

# -------------------- PERFORMANCE TREND --------------------
st.subheader(f"📈 Submissions Over Time ({start_date} to {end_date})")
daily_stats = filtered_df.groupby(filtered_df['Timestamp'].dt.date).size().reset_index(name='Submissions')

if not daily_stats.empty:
    fig_line = px.line(
        daily_stats,
        x='Timestamp',
        y='Submissions',
        title='Daily Submissions Trend',
        markers=True
    )
    fig_line.update_layout(xaxis_title='Date', yaxis_title='Number of Submissions')
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("ℹ️ No submission data available for the selected range to show trend.")

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

# -------------------- FULL ROWS WITH DUPLICATES --------------------
st.subheader("🧾 Full Filtered Rows (Including Duplicates)")
st.dataframe(filtered_df.sort_values(by='Is Duplicate').reset_index(drop=True))

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not filtered_df.empty:
    filtered_csv = convert_df_to_csv(filtered_df)
    st.download_button(
        label=f"📥 Download Filtered Data (With Duplicates)",
        data=filtered_csv,
        file_name=f"Business_Verification_Filtered_{start_date}_to_{end_date}.csv",
        mime='text/csv'
    )

st.success(f"✅ Dashboard updated dynamically as of {datetime.now().strftime('%B %d, %Y')}!")
