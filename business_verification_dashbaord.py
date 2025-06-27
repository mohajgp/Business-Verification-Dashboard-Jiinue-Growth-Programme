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
    # Normalize ID to handle potential .0 from Excel or mixed types
    df['Verified ID Number'] = df['Verified ID Number'].astype(str).str.strip()
    df['Verified ID Number'] = df['Verified ID Number'].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.', '').isdigit() else x).str.upper()
    df['Verified Phone Number'] = df['Verified Phone Number'].astype(str).apply(clean_phone)
    df['Is Duplicate'] = df.duplicated(subset=['Verified ID Number', 'Verified Phone Number'], keep='first')
    return df

# -------------------- LOAD DATA --------------------
df_raw = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded from the source. Check the URL or data availability.")
    st.stop()

# -------------------- COUNTY MASTER LIST (Used for reference, not direct filtering of display) --------------------
all_counties_47 = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta",
    "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi",
    "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
    "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
    "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru",
    "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma",
    "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
]

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filters")
# Set a reasonable default min_date if df_raw['Timestamp'] is empty or has NaT
default_min_date = df_raw['Timestamp'].min().date() if not df_raw['Timestamp'].empty and pd.notna(df_raw['Timestamp'].min()) else datetime(2023, 1, 1).date()
default_max_date = df_raw['Timestamp'].max().date() if not df_raw['Timestamp'].empty and pd.notna(df_raw['Timestamp'].max()) else datetime.now().date()

min_date_filter = st.sidebar.date_input(
    "Select Start Date:",
    value=default_min_date,
    min_value=datetime(2023, 1, 1).date(), # Absolute min to prevent errors
    max_value=default_max_date
)

max_date_filter = st.sidebar.date_input(
    "Select End Date:",
    value=default_max_date,
    min_value=min_date_filter, # End date cannot be before start date
    max_value=default_max_date
)

filter_start = datetime.combine(min_date_filter, datetime.min.time())
filter_end = datetime.combine(max_date_filter, datetime.max.time())

counties_in_data = sorted(df_raw['County'].dropna().unique())
selected_counties = st.sidebar.multiselect(
    "Select Counties:",
    options=counties_in_data,
    default=counties_in_data
)

# -------------------- FILTER DATA --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'] >= filter_start) &
    (df_raw['Timestamp'] <= filter_end) &
    (df_raw['County'].isin(selected_counties))
]

# Create unique_df *after* all filters are applied
unique_df = filtered_df.drop_duplicates(subset=['Verified ID Number', 'Verified Phone Number'])

# -------------------- METRICS (FILTERED VIEW) --------------------
st.subheader("📈 High-Level Summary (Filtered View)")
total_filtered_rows = filtered_df.shape[0]
unique_filtered_rows = unique_df.shape[0]
filtered_counties_covered = unique_df['County'].nunique() # Counties with unique submissions in the filtered set

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Rows (Before Deduplication)", f"{total_filtered_rows:,}")
col2.metric("✅ Unique Submissions", f"{unique_filtered_rows:,}")
col3.metric("📍 Counties Covered", filtered_counties_covered)
# This metric is redundant with col2, let's change it to something else if needed,
# or just remove it if 3 columns are enough. Keeping for now as per original.
col4.metric("📊 Unique Submissions in Range", f"{unique_filtered_rows:,}")

# -------------------- COUNTY BREAKDOWN (UNIQUE SUBMISSIONS, ONLY SELECTED COUNTIES) --------------------
st.subheader(f"📊 Unique Submissions by County (Filtered: {min_date_filter} to {max_date_filter})")

# Calculate unique submissions per county *within the filtered and unique data*
# This will only include counties that are both selected and have submissions
county_counts_filtered = unique_df['County'].value_counts().reset_index()
county_counts_filtered.columns = ['County', 'Count']
# Sort by count descending for the dataframe display and bar chart
filtered_county_stats_display = county_counts_filtered.sort_values(by='Count', ascending=False)


if not filtered_county_stats_display.empty:
    fig_bar = px.bar(
        filtered_county_stats_display, # Use the filtered stats
        x='County',
        y='Count',
        title=f"Unique Submissions per County (showing selected counties)",
        height=400,
        text=filtered_county_stats_display['Count'].apply(lambda x: f"{x:,}")
    )
    fig_bar.update_traces(textposition='auto')
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("ℹ️ No unique submissions for the selected counties and date range.")


st.subheader("🔢 Total Unique Submissions Per County (Table)")
if not filtered_county_stats_display.empty:
    st.dataframe(filtered_county_stats_display.reset_index(drop=True))
else:
    st.info("ℹ️ No unique submissions for the selected counties and date range to display in table.")


# -------------------- PERFORMANCE TREND --------------------
st.subheader(f"📈 Submissions Over Time ({min_date_filter} to {max_date_filter})")
daily_stats = unique_df.groupby(unique_df['Timestamp'].dt.date).size().reset_index(name='Submissions')

if not daily_stats.empty:
    fig_line = px.line(
        daily_stats,
        x='Timestamp',
        y='Submissions',
        title='Daily Unique Submissions Trend',
        markers=True
    )
    fig_line.update_layout(xaxis_title='Date', yaxis_title='Number of Submissions')
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("ℹ️ No submission data available for the selected range to show trend.")

# -------------------- NO SUBMISSIONS ANALYSIS (within selected counties) --------------------
st.subheader("🚫 Counties with No Unique Submissions (within selected filter)")
# Get counties that are selected in the filter but have 0 unique submissions
active_counties_with_submissions = unique_df['County'].unique().tolist()
no_submission_counties_in_filter = [
    county for county in selected_counties if county not in active_counties_with_submissions
]

if no_submission_counties_in_filter:
    st.error(f"🚫 Counties with NO Unique Submissions (in your current filter): {', '.join(no_submission_counties_in_filter)} ({len(no_submission_counties_in_filter)} total)")
else:
    st.success("✅ All selected counties have unique submissions!")

# -------------------- FULL ROWS WITH DUPLICATES --------------------
st.subheader("🧾 Full Filtered Rows (Including Duplicates)")
if not filtered_df.empty:
    st.dataframe(filtered_df.sort_values(by='Is Duplicate').reset_index(drop=True))
else:
    st.info("ℹ️ No data available for the selected filters.")

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not unique_df.empty:
    filtered_csv = convert_df_to_csv(unique_df)
    st.download_button(
        label=f"📥 Download Unique Submissions",
        data=filtered_csv,
        file_name=f"Business_Verification_Unique_{min_date_filter}_to_{max_date_filter}.csv",
        mime='text/csv'
    )
else:
    st.info("ℹ️ No unique submissions to download for the selected filters.")

st.success(f"✅ Dashboard updated dynamically as of {datetime.now().strftime('%B %d, %Y')}!")
