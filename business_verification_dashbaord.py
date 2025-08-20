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

# -------------------- HELPER FUNCTIONS --------------------
def clean_phone(phone):
    """Normalize Kenyan phone numbers into 2547XXXXXXXX format."""
    if pd.isna(phone):
        return None
    phone = str(phone).strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("07") and len(phone) == 10:
        phone = "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone
    elif phone.startswith("01") and len(phone) == 10:
        phone = "254" + phone[1:]
    elif phone.startswith("1") and len(phone) == 9:
        phone = "254" + phone
    return phone

# -------------------- LOAD DATA --------------------
@st.cache_data(ttl=300)
def load_data():
    # replace this with your actual Google Sheet CSV export link
    url = "https://docs.google.com/spreadsheets/d/1b_zSo-YNG47zEfAThmJBgEoypTq36IMT/export?format=csv"
    df = pd.read_csv(url)

    # parse timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    return df

df_raw = load_data()

# -------------------- FILTER CONTROLS --------------------
st.sidebar.header("🔎 Filters")

counties = df_raw['County'].dropna().unique().tolist()
selected_counties = st.sidebar.multiselect("Select Counties", counties, default=counties)

start_date = st.sidebar.date_input("Start Date", df_raw['Timestamp'].min().date())
end_date = st.sidebar.date_input("End Date", df_raw['Timestamp'].max().date())

# filter
filtered_df = df_raw[
    (df_raw['County'].isin(selected_counties)) &
    (df_raw['Timestamp'].dt.date >= start_date) &
    (df_raw['Timestamp'].dt.date <= end_date)
].copy()

# -------------------- DEDUPLICATION METHODS --------------------
# Manual dedup (Excel-style: raw ID + Phone as typed)
manual_dedup_df = filtered_df.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'], keep='first'
).copy()

# Strict dedup (cleaned ID + normalized phone)
strict_dedup_df = filtered_df.copy()
strict_dedup_df['Verified ID Number'] = strict_dedup_df['Verified ID Number'].astype(str).str.strip().str.upper()
strict_dedup_df['Verified Phone Number'] = strict_dedup_df['Verified Phone Number'].astype(str).apply(clean_phone)
strict_dedup_df = strict_dedup_df.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'], keep='first'
).copy()

# -------------------- METRICS --------------------
st.caption(f"Real-time view of business verifications by field officers - Stats as of {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")

st.subheader("📈 High-Level Summary (Filtered View)")
total_filtered_rows = filtered_df.shape[0]
manual_unique_rows = manual_dedup_df.shape[0]
strict_unique_rows = strict_dedup_df.shape[0]
filtered_counties_covered = strict_dedup_df['County'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Submissions (Filtered)", f"{total_filtered_rows:,}")
col2.metric("📝 Manual Dedup (Excel-style)", f"{manual_unique_rows:,}")
col3.metric("🧹 Strict Dedup (Cleaned)", f"{strict_unique_rows:,}")
col4.metric("📍 Counties with Unique Submissions", filtered_counties_covered)

st.caption(
    f"ℹ️ Manual dedup gave **{manual_unique_rows:,}**, strict cleaning gave **{strict_unique_rows:,}**. "
    f"Difference = **{manual_unique_rows - strict_unique_rows:,}** rows removed due to hidden characters or phone formatting."
)

# -------------------- TIME ANALYSIS --------------------
st.subheader("📅 Unique Submissions Per Month (Global Deduplication)")
monthly_uniques = strict_dedup_df.groupby(strict_dedup_df['Timestamp'].dt.to_period('M')).size().reset_index(name="Unique Count")
monthly_uniques['Timestamp'] = monthly_uniques['Timestamp'].astype(str)

fig_monthly = px.bar(monthly_uniques, x="Timestamp", y="Unique Count", text="Unique Count")
fig_monthly.update_traces(textposition="outside")
st.plotly_chart(fig_monthly, use_container_width=True)

# -------------------- COUNTY STATS --------------------
st.subheader("📊 Monthly & County Stats (Global Deduplication)")
county_monthly = strict_dedup_df.groupby(
    [strict_dedup_df['County'], strict_dedup_df['Timestamp'].dt.to_period('M')]
).size().reset_index(name="Unique Count")
county_monthly['Timestamp'] = county_monthly['Timestamp'].astype(str)

st.dataframe(county_monthly)

# -------------------- DOWNLOADS --------------------
st.subheader("⬇️ Download Cleaned Data")
col1, col2 = st.columns(2)
col1.download_button(
    "📥 Download Manual Dedup (Excel-style)",
    manual_dedup_df.to_csv(index=False).encode("utf-8"),
    "manual_dedup.csv",
    "text/csv"
)
col2.download_button(
    "📥 Download Strict Dedup (Cleaned)",
    strict_dedup_df.to_csv(index=False).encode("utf-8"),
    "strict_dedup.csv",
    "text/csv"
)
