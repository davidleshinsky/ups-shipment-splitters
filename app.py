
import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile
import base64
import requests

# Password protection
PASSWORD = st.secrets["APP_PASSWORD"]
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    input_pwd = st.text_input("Enter password to access the tool:", type="password")
    if input_pwd == PASSWORD:
        st.session_state["authenticated"] = True
        st.experimental_rerun()
    else:
        st.stop()

st.title("UPS Shipment File Splitter")

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV or Excel)", type=["csv", "xlsx"])
email = st.text_input("Enter your email to receive the ZIP:")

def split_file(df):
    grouped = df.groupby(["Reference Number", "Manifest Date"])
    temp_dir = tempfile.mkdtemp()
    paths = []

    for (ref, date), group in grouped:
        file_name = f"{ref}_{str(date).replace('/', '-')}.csv"
        file_path = os.path.join(temp_dir, file_name)
        group.to_csv(file_path, index=False)
        paths.append(file_path)

    return paths, temp_dir

def zip_files(file_paths, zip_name="split_files.zip"):
    zip_path = os.path.join(tempfile.gettempdir(), zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in file_paths:
            zipf.write(file, os.path.basename(file))
    return zip_path

def send_email(to_email, zip_path):
    api_key = st.secrets["SENDGRID_API_KEY"]
    from_email = st.secrets["FROM_EMAIL"]

    with open(zip_path, "rb") as f:
        zip_data = base64.b64encode(f.read()).decode()

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": "Your split UPS shipment ZIP file",
            "content": [{
                "type": "text/plain",
                "value": "Attached is your processed UPS file as a ZIP."
            }],
            "attachments": [{
                "content": zip_data,
                "filename": os.path.basename(zip_path),
                "type": "application/zip",
                "disposition": "attachment"
            }]
        }
    )
    return response.status_code, response.text

if uploaded_file and email:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        file_paths, folder = split_file(df)
        zip_path = zip_files(file_paths)

        with open(zip_path, "rb") as f:
            st.download_button("Download ZIP", f, file_name="split_files.zip")

        if st.button("Send ZIP by Email"):
            status, result = send_email(email, zip_path)
            if status == 202:
                st.success("Email sent successfully.")
            else:
                st.error(f"Failed to send email: {status} {result}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
