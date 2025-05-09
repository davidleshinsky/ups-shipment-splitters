
import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import requests
import re

st.set_page_config(page_title="UPS Shipment Splitter by Main Reference", layout="wide")

# Password protection
def check_password():
    def password_entered():
        if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password:", type="password", key="password_input", on_change=password_entered)
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password:", type="password", key="password_input", on_change=password_entered)
        st.error("❌ Incorrect password")
        st.stop()

check_password()
st.title("UPS Splitter: Email Each Main Reference Group Separately")

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type="csv")
email = st.text_input("Enter your email to receive all individual reference files:")

if uploaded_file and email:
    df = pd.read_csv(uploaded_file, dtype=str).fillna("")

    if "Reference Number(s)" not in df.columns:
        st.error("CSV must contain 'Reference Number(s)' column.")
        st.stop()

    # Extract main reference (everything before first dash or pipe)
    def extract_main_reference(ref):
        if pd.isna(ref):
            return None
        parts = re.split(r"[-|]", str(ref))
        return parts[0] if parts else None

    df["Main Reference"] = df["Reference Number(s)"].apply(extract_main_reference)

    from_email = "davidl@jjsolutions.com"
    api_key = st.secrets["SENDGRID_API_KEY"]
    status_log = []

    for ref, group in df.groupby("Main Reference"):
        file_name = f"{ref}.csv"
        csv_bytes = group.drop(columns=["Main Reference"]).to_csv(index=False).encode("utf-8")
        encoded_file = base64.b64encode(csv_bytes).decode()

        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [{"to": [{"email": email}]}],
                "from": {"email": from_email},
                "subject": f"UPS Shipment File: {ref}",
                "content": [{
                    "type": "text/plain",
                    "value": f"Attached is the CSV for Main Reference: {ref}"
                }],
                "attachments": [{
                    "content": encoded_file,
                    "filename": file_name,
                    "type": "text/csv",
                    "disposition": "attachment"
                }]
            }
        )

        if response.status_code == 202:
            status_log.append(f"✅ Sent: {file_name}")
        else:
            status_log.append(f"❌ Failed: {file_name} ({response.status_code}) {response.text}")

    st.markdown("### Email Results:")
    for msg in status_log:
        st.markdown(f"- {msg}")
