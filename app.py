
import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import requests

st.set_page_config(page_title="UPS Split & Email per Reference", layout="wide")

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
st.title("UPS Splitter: Email Each Reference Separately")

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type="csv")
email = st.text_input("Enter your email to receive all individual reference files:")

if uploaded_file and email:
    df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    if "Reference Number(s)" not in df.columns or "Manifest Date" not in df.columns:
        st.error("CSV must contain 'Reference Number(s)' and 'Manifest Date' columns.")
        st.stop()

    df["Main Reference"] = df["Reference Number(s)"].str.extract(r"^([^;\s]+)")
    try:
        df["Manifest Date"] = pd.to_datetime(df["Manifest Date"]).dt.strftime("%m%d%y")
    except:
        pass

    from_email = "davidl@jjsolutions.com"
    api_key = st.secrets["SENDGRID_API_KEY"]

    status_log = []

    for (ref, date), group in df.groupby(["Main Reference", "Manifest Date"]):
        file_name = f"{ref}_{date}.csv"
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
                    "value": f"Attached is the CSV for Reference {ref} dated {date}."
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
            status_log.append(f"✅ {file_name} sent.")
        else:
            status_log.append(f"❌ {file_name} failed ({response.status_code}): {response.text}")

    st.markdown("### Email Results:")
    for msg in status_log:
        st.markdown(f"- {msg}")
