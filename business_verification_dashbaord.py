import streamlit as st
import pandas as pd

st.set_page_config(page_title="Deduplication Checker", page_icon="📑", layout="wide")
st.title("📑 Business Verification Deduplication Checker")

# Google Sheet (make sure it's shared as "Anyone with link")
sheet_url = "https://docs.google.com/spreadsheets/d/1zsxFO4Gix-NqRRt-LQWf_TzlJcUtMbHdCOmstTOaP_Q/export?format=csv"

# Force engine to avoid error
df = pd.read_excel(sheet_url, engine="openpyxl")

# --- Dedup logic ---
df = df.reset_index(drop=True)

df_excel_style = df.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'],
    keep='first'
)

df_norm = df.copy()
df_norm['Verified Phone Number'] = df_norm['Verified Phone Number'].astype(str).str.replace(r'\D', '', regex=True)
df_norm['Verified Phone Number'] = df_norm['Verified Phone Number'].str.replace(r'^(?:0|254)?', '254', regex=True)
df_norm['Verified ID Number'] = df_norm['Verified ID Number'].astype(str).str.strip().str.upper()

df_strict = df_norm.drop_duplicates(
    subset=['Verified ID Number', 'Verified Phone Number'],
    keep='first'
)

# Show metrics
col1, col2, col3 = st.columns(3)
col1.metric("📄 Total Submissions (Filtered)", f"{len(df):,}")
col2.metric("📝 Manual Dedup (Excel-style)", f"{len(df_excel_style):,}")
col3.metric("🧹 Strict Dedup (Cleaned)", f"{len(df_strict):,}")
