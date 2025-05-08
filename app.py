
import streamlit as st
import pandas as pd
import os
import tempfile
import zipfile
import requests

# Send email using SendGrid
def send_email(to_email, zip_path):
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("FROM_EMAIL")

    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    import base64
    encoded = base64.b64encode(zip_bytes).decode()

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
                "content": encoded,
                "filename": os.path.basename(zip_path),
                "type": "application/zip",
                "disposition": "attachment"
            }]
        }
    )
    return response.status_code, response.text

# Streamlit app UI
st.set_page_config(page_title="UPS Shipment File Splitter")
st.title("UPS Shipment File Splitter")

password = st.text_input("Enter password to access the tool:", type="password")
if password != "ups123":
    st.stop()

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV or Excel)", type=["csv", "xlsx"])
email = st.text_input("Enter your email to receive the ZIP:")

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith("xlsx") else pd.read_csv(uploaded_file)
    if "Main Reference" not in df.columns:
        st.error("Missing required column: Main Reference")
        st.stop()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        for ref, group in df.groupby("Main Reference"):
            out_path = temp_dir / f"{ref}.csv"
            group.to_csv(out_path, index=False)

        zip_path = temp_dir / "split_files.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in temp_dir.glob("*.csv"):
                zipf.write(file, arcname=file.name)

        st.download_button("Download ZIP", zip_path.read_bytes(), file_name="split_files.zip")

        if st.button("Send ZIP by Email"):
            if not email:
                st.error("Enter a valid email address.")
            else:
                code, msg = send_email(email, zip_path)
                if code == 202:
                    st.success("Email sent successfully!")
                else:
                    st.error(f"Failed to send email: {msg}")
