import streamlit as st
import pandas as pd
import io
import zipfile
import base64
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import os

st.set_page_config(page_title="UPS Shipment File Splitter", layout="wide")
st.title("UPS Shipment File Splitter")

password = st.text_input("Enter password to access the tool:", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.stop()

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV or Excel)", type=["csv", "xlsx"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except:
        st.error("Failed to read file: 'Reference 1'")
        st.stop()

    # Extract main reference and manifest date
    df["Main Reference"] = df["Main Reference"].str.extract(r"([A-Z0-9]+)\s*-\s*([\d/]+)", expand=False)[0]
    df["Manifest Date"] = pd.to_datetime(df["Manifest Date"], errors="coerce")
    df["Sheet Name"] = df["Main Reference"].astype(str) + "_" + df["Manifest Date"].dt.strftime("%Y-%m-%d")

    # Group and export
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for name, group in df.groupby("Sheet Name"):
            file_buffer = io.BytesIO()
            group.to_excel(file_buffer, index=False)
            zipf.writestr(f"{name}.xlsx", file_buffer.getvalue())

    st.success("✅ File split successfully.")
    st.download_button("📁 Download ZIP", zip_buffer.getvalue(), file_name="split_files.zip", mime="application/zip")

    email = st.text_input("Enter your email to receive the ZIP:")
    if st.button("📤 Send ZIP by Email"):
        if email:
            try:
                sg = sendgrid.SendGridAPIClient(api_key=st.secrets["SENDGRID_API_KEY"])
                message = Mail(
                    from_email=st.secrets["FROM_EMAIL"],
                    to_emails=email,
                    subject="Split UPS File",
                    plain_text_content="Attached is your split UPS tracking file ZIP.",
                )
                encoded = base64.b64encode(zip_buffer.getvalue()).decode()
                attachment = Attachment(
                    FileContent(encoded),
                    FileName("split_files.zip"),
                    FileType("application/zip"),
                    Disposition("attachment"),
                )
                message.attachment = attachment
                response = sg.send(message)
                st.success("📨 Email sent successfully.")
            except Exception as e:
                st.error("❌ Failed to send email.")
        else:
            st.warning("⚠️ Please enter a valid email address.")