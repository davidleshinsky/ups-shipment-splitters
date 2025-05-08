import streamlit as st
import pandas as pd
import zipfile
import os
import shutil
import sendgrid
from sendgrid.helpers.mail import Mail
from io import BytesIO

# Streamlit config
st.set_page_config(page_title="UPS Shipment File Splitter", layout="centered")
st.title("UPS Shipment File Splitter")
st.caption("Upload UPS Tracking File (CSV or Excel)")

# Password gate
password = st.text_input("Enter password to access the tool:", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.stop()

# File upload
uploaded_file = st.file_uploader("Upload file here", type=["csv", "xlsx"])
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
        df['Main Ref'] = df['Reference 1'].str.extract(r'((?:\d{5,}-)?\d{4,})')
        groups = df.groupby(['Main Ref', 'Manifest Date'])

        output_zip = BytesIO()
        with zipfile.ZipFile(output_zip, "w") as zf:
            for (ref, date), group in groups:
                name = f"{ref}_{str(date)}.csv".replace("/", "-")
                buffer = BytesIO()
                group.to_csv(buffer, index=False)
                zf.writestr(name, buffer.getvalue())
        output_zip.seek(0)

        st.success("File split successfully.")
        st.download_button("Download ZIP", output_zip, file_name="split_files.zip")

        # Email option
        email = st.text_input("Or enter your email to receive it:")
        if st.button("Send ZIP by Email"):
            if email:
                sg = sendgrid.SendGridAPIClient(api_key=st.secrets["SENDGRID_API_KEY"])
                message = Mail(
                    from_email=st.secrets["FROM_EMAIL"],
                    to_emails=email,
                    subject="Your Split UPS File",
                    plain_text_content="Attached is your split UPS tracking file ZIP.",
                )
                message.add_attachment(
                    output_zip.getvalue(),
                    file_type="application/zip",
                    file_name="split_files.zip"
                )
                try:
                    sg.send(message)
                    st.success("Email sent successfully.")
                except Exception as e:
                    st.error(f"Failed to send email. {e}")
            else:
                st.warning("Please enter a valid email address.")
    except Exception as e:
        st.error(f"Failed to read file: {e}")
