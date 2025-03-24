import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------- Example Constants --------------------
ALL_COUNTIES = [
    'Mombasa', 'Kwale', 'Kilifi', 'Tana River', 'Lamu', 'Taita Taveta', 'Garissa', 'Wajir',
    'Mandera', 'Marsabit', 'Isiolo', 'Meru', 'Tharaka Nithi', 'Embu', 'Kitui', 'Machakos',
    'Makueni', 'Nyandarua', 'Nyeri', 'Kirinyaga', "Murang'a", 'Kiambu', 'Turkana',
    'West Pokot', 'Samburu', 'Trans Nzoia', 'Uasin Gishu', 'Elgeyo Marakwet', 'Nandi',
    'Baringo', 'Laikipia', 'Nakuru', 'Narok', 'Kajiado', 'Kericho', 'Bomet', 'Kakamega',
    'Vihiga', 'Bungoma', 'Busia', 'Siaya', 'Kisumu', 'Homa Bay', 'Migori', 'Kisii', 'Nyamira',
    'Nairobi'
]

# Sample df_raw is assumed to be loaded and 'Timestamp' is already a datetime type
# Assuming you already have df_raw loaded. Example:
# df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], errors='coerce')
# df_raw['County'] = df_raw['County'].str.strip().str.title()

# -------------------- DATE RANGES --------------------
march_start = datetime(2025, 3, 1)
march_end = datetime(2025, 3, 31)

week_start = datetime(2025, 3, 17)
week_end = datetime(2025, 3, 23)

# -------------------- FILTER DATA --------------------
march_df = df_raw[
    (df_raw['Timestamp'] >= march_start) &
    (df_raw['Timestamp'] <= march_end)
].copy()

weekly_df = df_raw[
    (df_raw['Timestamp'] >= week_start) &
    (df_raw['Timestamp'] <= week_end)
].copy()

# -------------------- CLEAN COUNTY NAMES --------------------
# Ensure consistent case and no leading/trailing spaces
march_df['County'] = march_df['County'].str.strip().str.title()
weekly_df['County'] = weekly_df['County'].str.strip().str.title()

# -------------------- SUBMISSION COUNTS --------------------
march_counts = march_df['County'].value_counts().to_dict()
weekly_counts = weekly_df['County'].value_counts().to_dict()

# -------------------- FIND COUNTIES WITH NO SUBMISSIONS --------------------
march_no_submissions = sorted([
    county for county in ALL_COUNTIES if county not in march_counts
])

weekly_no_submissions = sorted([
    county for county in ALL_COUNTIES if county not in weekly_counts
])

# -------------------- DISPLAY STATS --------------------
st.subheader("📅 March and Weekly Submissions Analysis")

# 🚫 Counties with NO submissions in March 2025
st.markdown("🚫 **Counties with NO submissions in March 2025:**")
if march_no_submissions:
    st.error(march_no_submissions)
else:
    st.success("🎉 All counties have submissions in March 2025!")

# 🚫 Counties with NO submissions in 17-23 March 2025
st.markdown("🚫 **Counties with NO submissions during 17-23 March 2025:**")
if weekly_no_submissions:
    st.error(weekly_no_submissions)
else:
    st.success("🎉 All counties have submissions during 17-23 March 2025!")

# -------------------- SUBMISSION COUNTS DISPLAY --------------------
# March Counts
st.markdown("📊 **Submissions per County - March 2025**")
march_counts_df = pd.DataFrame(list(march_counts.items()), columns=['County', 'Submissions']).sort_values(by='County')
st.dataframe(march_counts_df)

# Weekly Counts
st.markdown("📊 **Submissions per County - 17-23 March 2025**")
weekly_counts_df = pd.DataFrame(list(weekly_counts.items()), columns=['County', 'Submissions']).sort_values(by='County')
st.dataframe(weekly_counts_df)

# Optional: download buttons
st.download_button(
    "📥 Download March Submissions Count",
    march_counts_df.to_csv(index=False).encode('utf-8'),
    file_name='March_Submissions_2025.csv',
    mime='text/csv'
)

st.download_button(
    "📥 Download Weekly Submissions Count",
    weekly_counts_df.to_csv(index=False).encode('utf-8'),
    file_name='Weekly_Submissions_17_23_March_2025.csv',
    mime='text/csv'
)
