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
st.caption(f"Real-time view of business verifications by field officers - Stats as of {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")

# -------------------- SETTINGS --------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zsxFO4Gix-NqRRt-LQWf_TzlJcUtMbHdCOmstTOaP_Q/export?format=csv"

# -------------------- PHONE CLEANING FUNCTION --------------------
def clean_phone(phone):
    phone = str(phone).strip().replace(" ", "").replace("+", "").replace("-", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        return "254" + phone
    return phone

# -------------------- LOAD DATA --------------------
@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url)
        if df.empty:
            return pd.DataFrame()
        df.columns = df.columns.str.strip()
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df.dropna(subset=['Timestamp'], inplace=True)
        df['County'] = df['County'].astype(str).str.strip().str.title()
        df['Verified ID Number'] = df['Verified ID Number'].astype(str).str.strip().str.upper()
        df['Verified Phone Number'] = df['Verified Phone Number'].astype(str).apply(clean_phone)
        df['Is Duplicate (Global)'] = df.duplicated(subset=['Verified ID Number', 'Verified Phone Number'], keep='first')
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# -------------------- LOAD DATA --------------------
df_raw = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded.")
    st.stop()

# -------------------- GLOBAL METRICS (Sidebar) --------------------
st.sidebar.markdown("### 📊 Global Summary (Before Filters)")
global_total = df_raw.shape[0]
global_unique = df_raw.drop_duplicates(subset=['Verified ID Number', 'Verified Phone Number']).shape[0]
global_duplicates = global_total - global_unique

st.sidebar.metric("📄 Total Rows", f"{global_total:,}")
st.sidebar.metric("✅ Unique Across All", f"{global_unique:,}")
st.sidebar.metric("🧯 Global Duplicates", f"{global_duplicates:,}")

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filters")
min_available_date = df_raw['Timestamp'].min().date()
max_available_date = df_raw['Timestamp'].max().date()
default_start_date = max(datetime(2025, 3, 1).date(), min_available_date)
default_end_date = max_available_date

date_range = st.sidebar.date_input("Select Date Range:", value=(default_start_date, default_end_date),
                                   min_value=min_available_date, max_value=max_available_date)

if len(date_range) == 2:
    start_date, end_date = date_range
elif len(date_range) == 1:
    start_date = end_date = date_range[0]
else:
    start_date = default_start_date
    end_date = default_end_date

filter_start_dt = datetime.combine(start_date, datetime.min.time())
filter_end_dt = datetime.combine(end_date, datetime.max.time())

counties = sorted(df_raw['County'].dropna().unique())
selected_counties = st.sidebar.multiselect("Select Counties:", options=counties, default=counties)

# -------------------- FILTER DATA --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'] >= filter_start_dt) &
    (df_raw['Timestamp'] <= filter_end_dt) &
    (df_raw['County'].isin(selected_counties))
].copy()

# -------------------- DEDUPLICATE FILTERED DATA --------------------
deduplicated_filtered_df = filtered_df.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'], keep='first'
).copy()

# -------------------- FILTERED METRICS --------------------
st.subheader("📈 High-Level Summary (Filtered View)")
total_filtered_rows = filtered_df.shape[0]
unique_filtered_rows = deduplicated_filtered_df.shape[0]
filtered_counties_covered = deduplicated_filtered_df['County'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Submissions (Filtered)", f"{total_filtered_rows:,}")
col2.metric("✅ Unique After Cleaning (Filtered)", f"{unique_filtered_rows:,}")
col3.metric("📍 Counties with Unique Submissions", filtered_counties_covered)
col4.metric("📊 Avg Submissions/Day (Unique)",
            f"{unique_filtered_rows / ((end_date - start_date).days + 1):,.2f}" if (end_date - start_date).days >= 0 else "0.00")

st.info(
    "ℹ️ **Note:** Sum of monthly unique counts may exceed global unique count because participants can appear in multiple months."
)

# -------------------- UNIQUE PER MONTH --------------------
st.subheader("📅 Unique Submissions Per Month (Filtered View)")
monthly_uniques = (
    filtered_df.drop_duplicates(
        subset=['Verified ID Number', 'Verified Phone Number', filtered_df['Timestamp'].dt.to_period('M')]
    )
    .groupby(filtered_df['Timestamp'].dt.to_period('M'))
    .size()
    .reset_index(name='Unique Submissions This Month')
    .rename(columns={'Timestamp': 'Month'})
)

if not monthly_uniques.empty:
    monthly_uniques['Month'] = monthly_uniques['Month'].astype(str)
    st.dataframe(monthly_uniques, use_container_width=True)
else:
    st.info("ℹ️ No monthly data for selected filters.")

# -------------------- COUNTY BREAKDOWN --------------------
st.subheader(f"📊 Unique Submissions by County ({start_date} to {end_date})")
unique_county_stats = deduplicated_filtered_df.groupby('County').size().reset_index(name='Unique Count')

if not unique_county_stats.empty:
    fig_bar = px.bar(unique_county_stats, x='County', y='Unique Count', title='Unique Submissions per County',
                     height=450, text='Unique Count')
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("🔢 Unique Submissions Per County Table")
    st.dataframe(unique_county_stats.sort_values(by='Unique Count', ascending=False).reset_index(drop=True))
else:
    st.info("ℹ️ No unique submissions for selected filters.")

# -------------------- NO SUBMISSION COUNTIES --------------------
st.subheader("🚫 Counties with No Unique Submissions (Filtered View)")
all_counties_47 = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta", "Garissa", "Wajir", "Mandera", "Marsabit",
    "Isiolo", "Meru", "Tharaka Nithi", "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
    "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia", "Uasin Gishu", "Elgeyo Marakwet",
    "Nandi", "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga",
    "Bungoma", "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
]
active_counties_in_filter = deduplicated_filtered_df['County'].unique().tolist()
relevant_all_counties = [c for c in all_counties_47 if c in selected_counties]
no_submission_counties = [c for c in relevant_all_counties if c not in active_counties_in_filter]

if no_submission_counties:
    st.error(f"🚫 No unique submissions from: {', '.join(sorted(no_submission_counties))} ({len(no_submission_counties)} total)")
else:
    if selected_counties:
        st.success("✅ All selected counties have unique submissions.")
    else:
        st.info("No counties selected.")

# -------------------- FULL ROWS DISPLAY --------------------
st.subheader("🧾 Full Filtered Rows (With Global Duplicate Tags)")
st.caption("This includes duplicates for reference. Use global tag to assess redundancy.")

if not filtered_df.empty:
    st.dataframe(filtered_df.sort_values(by='Is Duplicate (Global)').reset_index(drop=True), use_container_width=True)
else:
    st.info("ℹ️ No filtered data to display.")

# -------------------- DOWNLOAD BUTTONS --------------------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if not filtered_df.empty:
    st.download_button("📥 Download All Filtered Rows", data=convert_df_to_csv(filtered_df),
                       file_name=f"All_Filtered_{start_date}_{end_date}.csv", mime='text/csv')

if not deduplicated_filtered_df.empty:
    st.download_button("⬇️ Download Unique Submissions", data=convert_df_to_csv(deduplicated_filtered_df),
                       file_name=f"Unique_Filtered_{start_date}_{end_date}.csv", mime='text/csv')

st.success(f"✅ Dashboard updated dynamically at {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")
