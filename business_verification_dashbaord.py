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
    """Cleans and formats phone numbers to a consistent '254...' format."""
    phone = str(phone).strip().replace(" ", "").replace("+", "").replace("-", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9: # Assumes 7xx xxx xxx format for local numbers
        return "254" + phone
    return phone

# -------------------- LOAD DATA --------------------
@st.cache_data(ttl=300) # Cache data for 5 minutes
def load_data(url):
    """
    Loads data from the specified URL, performs initial cleaning,
    and tags potential global duplicates.
    """
    try:
        df = pd.read_csv(url)
        if df.empty:
            return pd.DataFrame() # Return empty DataFrame if CSV is empty

        df.columns = df.columns.str.strip() # Strip whitespace from column names
        
        # Convert Timestamp to datetime, coercing errors to NaT
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        # Drop rows where Timestamp is NaT (if any, indicating invalid timestamp format)
        df.dropna(subset=['Timestamp'], inplace=True)

        df['County'] = df['County'].astype(str).str.strip().str.title()
        df['Verified ID Number'] = df['Verified ID Number'].astype(str).str.strip().str.upper()
        df['Verified Phone Number'] = df['Verified Phone Number'].astype(str).apply(clean_phone)

        # Tag global duplicates for informational display (not used for unique metrics calculation directly)
        df['Is Duplicate (Global)'] = df.duplicated(subset=['Verified ID Number', 'Verified Phone Number'], keep='first')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}. Please check the CSV URL and format.")
        return pd.DataFrame()

# -------------------- LOAD DATA & INITIAL CHECKS --------------------
df_raw = load_data(SHEET_CSV_URL)
if df_raw.empty:
    st.warning("⚠️ No data loaded or data is empty from the source. Check the URL or data availability.")
    st.stop()

# Ensure Timestamp column is datetime for filtering
if not pd.api.types.is_datetime64_any_dtype(df_raw['Timestamp']):
    st.error("Error: 'Timestamp' column is not in datetime format after loading.")
    st.stop()

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🗓️ Filters")

# Determine valid date range for the date input widget
min_available_date = df_raw['Timestamp'].min().date() if not df_raw['Timestamp'].empty else datetime(2025, 3, 1).date()
max_available_date = df_raw['Timestamp'].max().date() if not df_raw['Timestamp'].empty else (datetime.now() + timedelta(days=1)).date()

# Set a default start date (e.g., beginning of data or a reasonable default)
# Ensure default start date is not earlier than min_available_date
default_start_date = max(datetime(2025, 3, 1).date(), min_available_date) 
default_end_date = max_available_date # Default to the latest available date

date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(default_start_date, default_end_date), # Use actual available min/max if possible
    min_value=min_available_date,
    max_value=max_available_date
)

# Handle cases where only one date is selected
if len(date_range) == 2:
    start_date, end_date = date_range
elif len(date_range) == 1:
    start_date = end_date = date_range[0]
else: # Fallback if no date selected (shouldn't happen with default value)
    start_date = default_start_date
    end_date = default_end_date

filter_start_dt = datetime.combine(start_date, datetime.min.time())
filter_end_dt = datetime.combine(end_date, datetime.max.time())

counties = sorted(df_raw['County'].dropna().unique())
selected_counties = st.sidebar.multiselect(
    "Select Counties:",
    options=counties,
    default=counties # Default to all counties selected
)

# -------------------- FILTER DATA (This is your first filter step) --------------------
filtered_df = df_raw[
    (df_raw['Timestamp'] >= filter_start_dt) &
    (df_raw['Timestamp'] <= filter_end_dt) &
    (df_raw['County'].isin(selected_counties))
].copy() # Use .copy() to avoid SettingWithCopyWarning

# -------------------- DEDUPLE AFTER FILTERING (This is your "cleanup" step) --------------------
# Create a deduplicated version of the filtered_df for unique counts
# This aligns with: Filter -> Filter -> Deduplicate
deduplicated_filtered_df = filtered_df.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'], 
    keep='first'
).copy() # Use .copy() to avoid SettingWithCopyWarning

# -------------------- METRICS (FILTERED VIEW) --------------------
st.subheader("📈 High-Level Summary (Filtered View)")
total_filtered_rows = filtered_df.shape[0] # Total rows after initial filtering (includes local duplicates)
unique_filtered_rows = deduplicated_filtered_df.shape[0] # Unique rows after filtering AND then deduplicating
filtered_counties_covered = deduplicated_filtered_df['County'].nunique() # Unique counties with at least one unique submission in filter

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total Submissions (Filtered)", f"{total_filtered_rows:,}")
col2.metric("✅ Unique Submissions (Filtered)", f"{unique_filtered_rows:,}")
col3.metric("📍 Counties with Unique Submissions", filtered_counties_covered)
col4.metric("📊 Average Submissions/Day (Unique)", 
            f"{unique_filtered_rows / ((end_date - start_date).days + 1):,.2f}" if (end_date - start_date).days >= 0 else "0.00")

# -------------------- COUNTY BREAKDOWN (UNIQUE SUBMISSIONS - after filter & dedup) --------------------
st.subheader(f"📊 Unique Submissions by County ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
# Group by county using the deduplicated_filtered_df
unique_county_stats = deduplicated_filtered_df.groupby('County').size().reset_index(name='Unique Count')

if not unique_county_stats.empty:
    fig_bar = px.bar(
        unique_county_stats,
        x='County',
        y='Unique Count',
        title=f"Unique Submissions per County",
        height=450,
        text='Unique Count' # Display the count on bars
    )
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("🔢 Unique Submissions Per County Table")
    st.dataframe(unique_county_stats.sort_values(by='Unique Count', ascending=False).reset_index(drop=True))
else:
    st.info(f"ℹ️ No unique submissions for the selected date range in the selected counties to display county breakdown.")

# -------------------- PERFORMANCE TREND (UNIQUE SUBMISSIONS - after filter & dedup) --------------------
st.subheader(f"📈 Unique Submissions Over Time ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
# Group by timestamp (date part) using the deduplicated_filtered_df
daily_unique_stats = deduplicated_filtered_df.groupby(deduplicated_filtered_df['Timestamp'].dt.date).size().reset_index(name='Unique Submissions')
daily_unique_stats.columns = ['Date', 'Unique Submissions'] # Rename column for clarity

if not daily_unique_stats.empty:
    fig_line = px.line(
        daily_unique_stats,
        x='Date',
        y='Unique Submissions',
        title='Daily Unique Submissions Trend',
        markers=True
    )
    fig_line.update_layout(xaxis_title='Date', yaxis_title='Number of Unique Submissions')
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("ℹ️ No unique submission data available for the selected range to show trend over time.")

# -------------------- NO SUBMISSIONS ANALYSIS (Based on Unique Submissions) --------------------
st.subheader("🚫 Counties with No Unique Submissions (in filtered view)")
all_counties_47 = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta",
    "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi",
    "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
    "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
    "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru",
    "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma",
    "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi"
]

# Get the list of counties that *are* present in the unique filtered data
active_counties_in_filter = deduplicated_filtered_df['County'].unique().tolist()

# Filter `all_counties_47` to include only those selected in the sidebar
# This ensures we only report on counties the user *expected* to see data for.
relevant_all_counties = [c for c in all_counties_47 if c in selected_counties]

# Determine which of the relevant counties have no unique submissions
no_submission_counties = [county for county in relevant_all_counties if county not in active_counties_in_filter]

if no_submission_counties:
    st.error(f"🚫 The following selected counties have NO Unique Submissions in the current filter: {', '.join(sorted(no_submission_counties))} ({len(no_submission_counties)} total)")
else:
    if selected_counties: # Only show success if counties were actually selected
        st.success("✅ All selected counties have unique submissions in the current filter!")
    else:
        st.info("No counties selected in the sidebar filter to check for submissions.")


# -------------------- FULL ROWS (Including Duplicates relevant to filter) --------------------
st.subheader("🧾 Full Filtered Rows (Including Local Duplicates)")
st.caption("This table shows all submissions that match your date and county filters. The 'Is Duplicate (Global)' column indicates if it's a duplicate when considering the entire dataset.")

if not filtered_df.empty:
    # Optional: Sort by 'Is Duplicate (Global)' to easily see duplicates at the top/bottom
    st.dataframe(filtered_df.sort_values(by='Is Duplicate (Global)').reset_index(drop=True), use_container_width=True)
else:
    st.info("ℹ️ No data available for the selected filters to display full rows.")

# -------------------- DOWNLOAD BUTTON --------------------
@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to CSV format for download."""
    return df.to_csv(index=False).encode('utf-8')

if not filtered_df.empty:
    filtered_csv = convert_df_to_csv(filtered_df)
    st.download_button(
        label=f"📥 Download Filtered Data (Includes All Rows, Global Duplicate Tag)",
        data=filtered_csv,
        file_name=f"Business_Verification_Filtered_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv",
        mime='text/csv'
    )
    
if not deduplicated_filtered_df.empty:
    dedup_filtered_csv = convert_df_to_csv(deduplicated_filtered_df)
    st.download_button(
        label=f"⬇️ Download Unique Submissions (Filtered and Deduplicated)",
        data=dedup_filtered_csv,
        file_name=f"Business_Verification_Unique_Filtered_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv",
        mime='text/csv'
    )

st.success(f"✅ Dashboard updated dynamically as of {datetime.now().strftime('%B %d, %Y %H:%M:%S')}!")
st.info("Please refresh the page or wait 5 minutes for new data to load from the source.")
