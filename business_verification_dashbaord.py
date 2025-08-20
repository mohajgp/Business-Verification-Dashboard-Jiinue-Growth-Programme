import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="📍 KNCCI Jiinue Business Verification Dashboard",
    page_icon="📍",
    layout="wide"
)

st.title("📍 KNCCI Jiinue Business Verification Dashboard")

# -------------------- GOOGLE SHEET LOADING --------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/XXXXXXX/edit#gid=0"  # <-- replace with your sheet link

@st.cache_data(ttl=300)
def load_data():
    csv_url = SHEET_URL.replace("/edit#gid=", "/export?format=csv&gid=")
    df = pd.read_csv(csv_url)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Normalize phone and ID columns
    df["Verified Phone Number"] = df["Verified Phone Number"].astype(str).str.replace(r"\D", "", regex=True)
    df["Verified ID Number"] = df["Verified ID Number"].astype(str).str.strip()

    return df

df = load_data()

# -------------------- METRICS CALC --------------------
total_submissions = len(df)

# Manual dedup (Excel-style: just ID + Phone)
manual_dedup = df.drop_duplicates(subset=["Verified ID Number", "Verified Phone Number"]).shape[0]

# Strict dedup (Cleaned: normalize before dropping duplicates)
df_strict = df.copy()
df_strict["Verified Phone Number"] = df_strict["Verified Phone Number"].str.replace(r"^0", "254", regex=True)
strict_dedup = df_strict.drop_duplicates(subset=["Verified ID Number", "Verified Phone Number"]).shape[0]

# -------------------- DISPLAY --------------------
st.caption(f"Real-time view of business verifications by field officers - Stats as of {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📄 Total Submissions (Filtered)", f"{total_submissions:,}")
with col2:
    st.metric("📝 Manual Dedup (Excel-style)", f"{manual_dedup:,}")
with col3:
    st.metric("🧹 Strict Dedup (Cleaned)", f"{strict_dedup:,}")
