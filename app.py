
import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile

# --- SETTINGS ---
REQUIRED_PASSWORD = "splitUPS2025"
REQUIRED_COLUMNS = ["Reference Number(s)", "Manifest Date"]

# --- AUTHENTICATION ---
st.set_page_config(page_title="UPS Splitter", layout="wide")
st.title("📦 UPS Shipment File Splitter")

password = st.text_input("Enter password to access the tool:", type="password")
if password != REQUIRED_PASSWORD:
    st.warning("Please enter the correct password to continue.")
    st.stop()

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    # --- AUTO-CLEAN HEADERS ---
    df.columns = [col.strip() for col in df.columns]
    col_map = {col: col for col in df.columns}

    # Auto-correct fuzzy matches
    for col in df.columns:
        if "reference" in col.lower():
            col_map[col] = "Reference Number(s)"
        if "manifest" in col.lower():
            col_map[col] = "Manifest Date"

    df.rename(columns=col_map, inplace=True)

    # --- VALIDATE COLUMNS ---
    if not all(c in df.columns for c in REQUIRED_COLUMNS):
        st.error("Missing required columns: Reference Number(s) and Manifest Date")
        st.stop()

    # --- CLEAN & SPLIT ---
    df["Main Reference"] = df["Reference Number(s)"].str.extract(r"^([A-Z]+\d+)", expand=False)
    df["Manifest Date"] = pd.to_datetime(df["Manifest Date"]).dt.strftime("%Y-%m-%d")
    df["Sheet Name"] = df["Main Reference"] + "_" + df["Manifest Date"]

    output = BytesIO()
    with zipfile.ZipFile(output, "w") as zip_buffer:
        for name, group in df.groupby("Sheet Name"):
            buffer = BytesIO()
            group.to_excel(buffer, index=False)
            zip_buffer.writestr(f"{name}.xlsx", buffer.getvalue())

    st.success("✅ Your files are ready to download!")
    st.download_button("📥 Download ZIP", output.getvalue(), file_name="UPS_Shipments_Split.zip")
