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

# -------------------- UNIQUE PER MONTH (GLOBAL-DEDUP MATCHING DOWNLOAD) --------------------
st.subheader("📅 Unique Submissions Per Month (Global Deduplication – matches download)")

deduplicated_filtered_df['Month'] = deduplicated_filtered_df['Timestamp'].dt.to_period('M')
monthly_uniques = (
    deduplicated_filtered_df
    .groupby('Month')
    .size()
    .reset_index(name='Unique Submissions This Month')
)
monthly_uniques['Month'] = monthly_uniques['Month'].astype(str)

if not monthly_uniques.empty:
    st.dataframe(monthly_uniques, use_container_width=True)
    sum_of_monthly_uniques = monthly_uniques['Unique Submissions This Month'].sum()
    st.info(
        f"ℹ️ Sum of monthly uniques (filtered dedup): **{sum_of_monthly_uniques:,}**, "
        f"and global unique across all data is: **{global_unique:,}**."
    )
else:
    st.info("ℹ️ No monthly data for selected filters.")

# -------------------- GLOBAL DEDUP → MONTHLY + COUNTY --------------------
st.subheader("📊 Monthly & County Stats (Global Deduplication)")

deduplicated_global_df = df_raw.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'], keep='first'
).copy()
deduplicated_global_df['Month'] = deduplicated_global_df['Timestamp'].dt.to_period('M')

monthly_county_stats = (
    deduplicated_global_df
    .groupby(['Month', 'County'])
    .size()
    .reset_index(name='Unique Participants')
    .sort_values(['Month', 'County'])
)
monthly_county_stats['Month'] = monthly_county_stats['Month'].astype(str)

if not monthly_county_stats.empty:
    st.dataframe(monthly_county_stats, use_container_width=True)
else:
    st.info("ℹ️ No data for monthly & county breakdown.")

# Optional Heatmap
heatmap_data = monthly_county_stats.pivot(index='County', columns='Month', values='Unique Participants').fillna(0)
if not heatmap_data.empty:
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Month", y="County", color="Participants"),
        text_auto=True,
        aspect="auto",
        title="Unique Participants by County and Month (Global Dedup)"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# -------------------- COUNTY BREAKDOWN (Filtered) --------------------
st.subheader(f"📊 Unique Submissions by County ({start_date} to {end_date})")
unique_county_stats = deduplicated_filtered_df.groupby('County').size().reset_index(name='Unique Count')

if not unique_county_stats.empty:
    fig_bar = px.bar(unique_county_stats, x='County', y='Unique Count', title='Unique Submissions per County',
                     height=450, text='Unique Count')
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(unique_county_stats.sort_values(by='Unique Count', ascending=False).reset_index(drop=True))
else:
    st.info("ℹ️ No unique submissions for selected filters.")

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


