
import streamlit as st
import base64
import pandas as pd
import os
import zipfile
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

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
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        st.stop()

    reference_col = "Reference Number(s)"
    if reference_col not in df.columns:
        st.error(f"Missing column '{reference_col}' in file.")
        st.stop()

    output_dir = "split_files"
    os.makedirs(output_dir, exist_ok=True)

    for ref, group in df.groupby(reference_col):
        filename = f"{ref}.csv".replace("/", "_").replace("\\", "_")
        group.to_csv(os.path.join(output_dir, filename), index=False)

    zip_filename = "split_files.zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        for f in os.listdir(output_dir):
            zipf.write(os.path.join(output_dir, f), arcname=f)

    with open(zip_filename, "rb") as f:
        st.download_button("Download ZIP", f.read(), file_name=zip_filename, mime="application/zip")

    email = st.text_input("Enter your email to receive the ZIP:")
    if email and st.button("Send ZIP by Email"):
        try:
            message = Mail(
                from_email=st.secrets["FROM_EMAIL"],
                to_emails=email,
                subject="Your UPS Shipment Split Files",
                plain_text_content="Attached is your ZIP file containing split shipment data."
            )
            with open(zip_filename, "rb") as f:
                data = f.read()
            encoded_file = base64.b64encode(data).decode()
            attached_file = Attachment(
                FileContent(encoded_file),
                FileName(zip_filename),
                FileType("application/zip"),
                Disposition("attachment")
            )
            message.attachment = attached_file
            sg = SendGridAPIClient(st.secrets["SENDGRID_API_KEY"])
            sg.send(message)
            st.success("Email sent successfully.")
        except Exception as e:
            st.error(f"Failed to send email: {e}")
