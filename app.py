
import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
from datetime import datetime

st.set_page_config(page_title="UPS Shipment File Splitter")

# Password protection
PASSWORD = "splitUPS2025"
with st.form("password_form"):
    pw = st.text_input("Enter password to access the tool:", type="password")
    submitted = st.form_submit_button("Submit")
    if not submitted or pw != PASSWORD:
        st.stop()

st.title("UPS Shipment File Splitter")
st.caption("Upload a UPS tracking CSV and download grouped shipments by Reference and Manifest Date.")

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    if "Reference Number(s)" not in df.columns or "Manifest Date" not in df.columns:
        st.error("CSV must contain 'Reference Number(s)' and 'Manifest Date' columns.")
        st.stop()

    # Extract main reference as first token before semicolon or whitespace
    df["Main Reference"] = df["Reference Number(s)"].str.extract(r"^([^;\s]+)")

    # Format Manifest Date if needed (e.g., from MM/DD/YYYY to MMDDYY)
    try:
        df["Manifest Date"] = pd.to_datetime(df["Manifest Date"]).dt.strftime("%m%d%y")
    except:
        pass  # Assume already formatted

    # Group and write to ZIP
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for (ref, date), group in df.groupby(["Main Reference", "Manifest Date"]):
            filename = f"{ref}_{date}.csv"
            csv_bytes = group.drop(columns=["Main Reference"]).to_csv(index=False).encode("utf-8")
            zipf.writestr(filename, csv_bytes)

    st.success("Done! Download your ZIP file below:")
    st.download_button("Download ZIP", zip_buffer.getvalue(), "split_shipments.zip", "application/zip")
