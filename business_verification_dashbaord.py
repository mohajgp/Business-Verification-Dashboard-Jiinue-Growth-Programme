import streamlit as st
import pandas as pd
from datetime import datetime

# CONFIG
st.set_page_config(page_title="KNCCI Mentorship Submissions", layout="wide")
st.title("📋 KNCCI Mentorship Submissions Dashboard")
st.markdown("Analyze submissions for **March 2025** and **Week 17-23 March 2025**.")

# LOAD DATA
sheet_id = '1zsxFO4Gix-NqRRt-LQWf_TzlJcUtMbHdCOmstTOaP_Q'
gid = '1224059157'

csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'

@st.cache_data
def load_data():
    df = pd.read_csv(csv_url)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce', dayfirst=True)
    df['County'] = df['County'].astype(str).str.strip()
    return df

df_raw = load_data()

# FILTER DATES
march_start = datetime(2025, 3, 1)
march_end = datetime(2025, 3, 31)

week_start = datetime(2025, 3, 17)
week_end = datetime(2025, 3, 23)

march_df = df_raw[(df_raw['Timestamp'] >= march_start) & (df_raw['Timestamp'] <= march_end)]
weekly_df = df_raw[(df_raw['Timestamp'] >= week_start) & (df_raw['Timestamp'] <= week_end)]

# ALL COUNTIES
all_counties = [
    'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo Marakwet', 'Embu', 'Garissa',
    'Homa Bay', 'Isiolo', 'Kajiado', 'Kakamega', 'Kericho', 'Kiambu', 'Kilifi',
    'Kirinyaga', 'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia', 'Lamu', 'Machakos',
    'Makueni', 'Mandera', 'Marsabit', 'Meru', 'Migori', 'Mombasa', "Murang'a",
    'Nairobi', 'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua', 'Nyeri',
    'Samburu', 'Siaya', 'Taita Taveta', 'Tana River', 'Tharaka Nithi', 'Trans Nzoia',
    'Turkana', 'Uasin Gishu', 'Vihiga', 'Wajir', 'West Pokot'
]

march_submitted = march_df['County'].unique().tolist()
weekly_submitted = weekly_df['County'].unique().tolist()

march_no_submissions = sorted([county for county in all_counties if county not in march_submitted])
weekly_no_submissions = sorted([county for county in all_counties if county not in weekly_submitted])

march_counts = march_df['County'].value_counts().sort_index()
weekly_counts = weekly_df['County'].value_counts().sort_index()

# DISPLAY RESULTS
st.header("🚫 Counties with NO Submissions")

col1, col2 = st.columns(2)

with col1:
    st.subheader("March 2025")
    st.write(march_no_submissions)
    st.metric("Count", len(march_no_submissions))

with col2:
    st.subheader("Week 17-23 March 2025")
    st.write(weekly_no_submissions)
    st.metric("Count", len(weekly_no_submissions))

# SUBMISSIONS COUNTS
st.header("📊 Submissions Per County")

col3, col4 = st.columns(2)

with col3:
    st.subheader("March 2025 Submissions")
    st.dataframe(march_counts)

with col4:
    st.subheader("17-23 March 2025 Submissions")
    st.dataframe(weekly_counts)

# DOWNLOAD OPTIONS
st.header("⬇️ Download Reports")

march_csv = march_df.to_csv(index=False).encode('utf-8')
weekly_csv = weekly_df.to_csv(index=False).encode('utf-8')

st.download_button("Download March Submissions CSV", march_csv, "march_submissions.csv", "text/csv")
st.download_button("Download Weekly Submissions CSV", weekly_csv, "weekly_submissions.csv", "text/csv")

st.caption("KNCCI Mentorship Dashboard • March 2025 Analysis")
