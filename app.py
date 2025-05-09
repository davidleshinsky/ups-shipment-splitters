
import streamlit as st
import pandas as pd
import zipfile
import io
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

# CONFIGURATION
PASSWORD = "splitUPS2025"
SENDER_EMAIL = "davidl@jjsolutions.com"
SENDGRID_API_KEY = st.secrets["SENDGRID_API_KEY"]

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

st.title("UPS Splitter: Email or Download Per Main Reference")

# Password protection
if not st.session_state.authenticated:
    password = st.text_input("Enter password to access:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.experimental_rerun()
    else:
        st.stop()

# File upload + email input
uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type="csv")
recipient_email = st.text_input("Your email address (for ZIPs):")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    required_cols = {"Main Reference", "Manifest Date"}
    if not required_cols.issubset(df.columns):
        st.error("CSV must contain 'Main Reference' and 'Manifest Date' columns.")
        st.stop()

    grouped = df.groupby(["Main Reference", "Manifest Date"])
    results = []

    for (main_ref, manifest_date), group in grouped:
        filename = f"{main_ref}_{manifest_date.replace('/', '-')}.csv"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr(filename, group.to_csv(index=False))
        zip_bytes = zip_buffer.getvalue()

        with st.expander(f"📦 {filename}"):
            st.download_button("⬇️ Download ZIP", data=zip_bytes, file_name=f"{filename}.zip", mime="application/zip")

            if recipient_email:
                if st.button(f"📧 Email ZIP for {main_ref}", key=filename):
                    try:
                        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
                        attachment = Attachment()
                        attachment.file_content = FileContent(base64.b64encode(zip_bytes).decode())
                        attachment.file_type = FileType("application/zip")
                        attachment.file_name = FileName(f"{filename}.zip")
                        attachment.disposition = Disposition("attachment")

                        message = Mail(
                            from_email=SENDER_EMAIL,
                            to_emails=recipient_email,
                            subject=f"UPS ZIP: {filename}",
                            plain_text_content="Your UPS ZIP file is attached.",
                        )
                        message.attachment = attachment
                        response = sg.send(message)

                        if response.status_code == 202:
                            st.success("✅ Email sent successfully.")
                        else:
                            st.error(f"❌ Email failed ({response.status_code}): {response.body}")

                    except Exception as e:
                        st.error(f"❌ Email error: {str(e)}")
