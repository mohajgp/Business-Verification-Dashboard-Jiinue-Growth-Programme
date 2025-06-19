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
st.caption(f"Updated as of {datetime.now().strftime('%B %d, %Y')}")

# -------------------- SETTINGS --------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zsxFO4Gix-NqRRt-LQWf_TzlJcUtMbHdCOmstTOaP_Q/export?format=csv"

# -------------------- PHONE NORMALIZATION --------------------
def clean_phone(phone):
    phone = str(phone).strip().replace(" ", "").replace("+", "").replace("-", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("7"):
        return "254" + phone
    return phone

# -------------------- LOAD & CLEAN DATA --------------------
@st.cache_data(ttl=300)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df['County'] = df['County'].str.strip().str.title()
    df['Verified ID Number'] = df['Verified ID Number'].astype(str).str.strip().str.upper()
    df['Verified Phone Number'] = df['Verified Phone Number'].astype(str).apply(clean_phone)
    df['Date'] = df['Timestamp'].dt.date
    return df

# -------------------- LOAD DATA --------------------
df = load_data(SHEET_CSV_URL)
total_rows_before = df.shape[0]

# -------------------- DATE SELECTION --------------------
unique_dates = sorted(df['Date'].dropna().unique())
selected_date = st.sidebar.selectbox("📅 Select Date", options=unique_dates, index=len(unique_dates)-1)

# -------------------- FILTER THEN DEDUPLICATE --------------------
df_selected = df[df['Date'] == selected_date].copy()
rows_before_dedup = df_selected.shape[0]
df_selected = df_selected.drop_duplicates(subset=['Verified ID Number', 'Verified Phone Number'])
rows_after_dedup = df_selected.shape[0]

# -------------------- METRICS --------------------
st.subheader("🔍 Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Rows (All Time)", f"{total_rows_before:,}")
col2.metric("📅 Rows on " + str(selected_date), f"{rows_before_dedup:,}")
col3.metric("✅ Unique on Selected Date", f"{rows_after_dedup:,}")
col4.metric("📍 Counties on Selected Date", df_selected['County'].nunique())

# -------------------- COUNTY BREAKDOWN --------------------
st.subheader(f"📊 Submissions by County on {selected_date}")
county_stats = df_selected.groupby('County').size().reset_index(name='Count')

if not county_stats.empty:
    fig = px.bar(
        county_stats,
        x='County',
        y='Count',
        title='County Breakdown',
        text='Count',
        height=400
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(county_stats.sort_values(by='Count', ascending=False))
else:
    st.info("No data for the selected date.")

# -------------------- DOWNLOAD --------------------
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

if not df_selected.empty:
    st.download_button(
        label="📥 Download CSV",
        data=convert_df(df_selected),
        file_name=f"Business_Verifications_{selected_date}.csv",
        mime="text/csv"
    )
