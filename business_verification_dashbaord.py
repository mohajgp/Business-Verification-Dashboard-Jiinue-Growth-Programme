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
        df['Gender'] = df['Gender'].astype(str).str.strip().str.title()
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
        df['Is Duplicate (Global)'] = df.duplicated(subset=['Verified ID Number', 'Verified Phone Number'], keep='first')
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df_raw = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filters")
min_date = df_raw['Timestamp'].min().date()
max_date = df_raw['Timestamp'].max().date()
default_start_date = max(datetime(2025, 3, 1).date(), min_date)
default_end_date = max_date

date_range = st.sidebar.date_input("Select Date Range:", value=(default_start_date, default_end_date),
                                   min_value=min_date, max_value=max_date)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

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

deduplicated_df = filtered_df.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'], keep='first'
).copy()

# -------------------- METRICS --------------------
st.subheader("📈 High-Level Summary (Filtered View)")
total_filtered_rows = filtered_df.shape[0]
unique_filtered_rows = deduplicated_df.shape[0]
filtered_counties_covered = deduplicated_df['County'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Submissions (Filtered)", f"{total_filtered_rows:,}")
col2.metric("✅ Unique Submissions", f"{unique_filtered_rows:,}")
col3.metric("📍 Counties with Unique Submissions", filtered_counties_covered)
col4.metric("📊 Avg Unique Submissions/Day",
            f"{unique_filtered_rows / ((end_date - start_date).days + 1):,.2f}" if (end_date - start_date).days >= 0 else "0.00")

# -------------------- AGE & GENDER CATEGORIES --------------------
st.subheader("👥 Age & Gender Breakdown (Unique Records)")

def categorize(row):
    try:
        age = int(row['Age'])
    except:
        return "Unknown"
    gender = str(row['Gender']).lower()
    if 18 <= age <= 35:
        if gender == "male":
            return "Young male (18–35)"
        elif gender == "female":
            return "Young female (18–35)"
    elif age > 35:
        if gender == "male":
            return "Male above 35"
        elif gender == "female":
            return "Female above 35"
    return "Unknown"

deduplicated_df['Category'] = deduplicated_df.apply(categorize, axis=1)
cat_counts = deduplicated_df['Category'].value_counts()

cols = st.columns(5)
cols[0].metric("👨 Young Males", cat_counts.get('Young male (18–35)', 0))
cols[1].metric("👩 Young Females", cat_counts.get('Young female (18–35)', 0))
cols[2].metric("👨‍🦳 Males >35", cat_counts.get('Male above 35', 0))
cols[3].metric("👩‍🦳 Females >35", cat_counts.get('Female above 35', 0))
cols[4].metric("❓ Unknown", cat_counts.get('Unknown', 0))

# -------------------- COUNTY CHART --------------------
st.subheader("📊 Unique Submissions by County")
county_stats = deduplicated_df.groupby('County').size().reset_index(name='Unique Count')

if not county_stats.empty:
    fig_bar = px.bar(county_stats, x='County', y='Unique Count', text='Unique Count', height=450,
                     title=f"Unique Submissions per County ({start_date} to {end_date})")
    fig_bar.update_traces(texttemplate='%{text}', textposition='outside')
    fig_bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(county_stats.sort_values(by='Unique Count', ascending=False).reset_index(drop=True))
else:
    st.info("ℹ️ No unique submissions for selected filters.")

# -------------------- DAILY TREND --------------------
st.subheader("📈 Unique Submissions Over Time")
daily_stats = deduplicated_df.groupby(deduplicated_df['Timestamp'].dt.date).size().reset_index(name='Unique Submissions')

if not daily_stats.empty:
    fig_line = px.line(daily_stats, x='Timestamp', y='Unique Submissions', markers=True,
                       title='Daily Unique Submissions Trend')
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("ℹ️ No daily trend data for selected filters.")

# -------------------- FULL ROWS --------------------
st.subheader("🧾 Filtered Data (With Global Duplicate Tags)")
st.dataframe(filtered_df.sort_values(by='Is Duplicate (Global)').reset_index(drop=True), use_container_width=True)

# -------------------- DOWNLOAD BUTTONS --------------------
@st.cache_data
def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

st.download_button("📥 Download All Filtered Rows", data=to_csv(filtered_df),
                   file_name=f"All_Filtered_{start_date}_{end_date}.csv", mime='text/csv')

st.download_button("⬇️ Download Unique Submissions", data=to_csv(deduplicated_df),
                   file_name=f"Unique_Filtered_{start_date}_{end_date}.csv", mime='text/csv')

st.success(f"✅ Dashboard updated at {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")
