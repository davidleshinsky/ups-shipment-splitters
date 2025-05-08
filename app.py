
import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import base64

st.set_page_config(page_title="UPS Shipment File Splitter", layout="wide")

# Session-based password protection
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
st.title("UPS Shipment File Splitter")

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type="csv")
email = st.text_input("Enter your email to receive the ZIP (optional):")

if uploaded_file:
    df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    if "Reference Number(s)" not in df.columns or "Manifest Date" not in df.columns:
        st.error("CSV must contain 'Reference Number(s)' and 'Manifest Date' columns.")
        st.stop()

    df["Main Reference"] = df["Reference Number(s)"].str.extract(r"^([^;\s]+)")
    try:
        df["Manifest Date"] = pd.to_datetime(df["Manifest Date"]).dt.strftime("%m%d%y")
    except:
        pass

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for (ref, date), group in df.groupby(["Main Reference", "Manifest Date"]):
            filename = f"{ref}_{date}.csv"
            csv_bytes = group.drop(columns=["Main Reference"]).to_csv(index=False).encode("utf-8")
            zipf.writestr(filename, csv_bytes)
    zip_buffer.seek(0)

    st.download_button("📥 Download ZIP", zip_buffer.getvalue(), file_name="split_shipments.zip")

    if email and st.button("📤 Send ZIP by Email"):
        import requests
        from_email = st.secrets["FROM_EMAIL"]
        api_key = st.secrets["SENDGRID_API_KEY"]
        encoded_file = base64.b64encode(zip_buffer.read()).decode()

        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [{"to": [{"email": email}]}],
                "from": {"email": from_email},
                "subject": "Your UPS Split ZIP File",
                "content": [{"type": "text/plain", "value": "Please find your split shipment ZIP attached."}],
                "attachments": [{
                    "content": encoded_file,
                    "filename": "split_shipments.zip",
                    "type": "application/zip",
                    "disposition": "attachment"
                }]
            }
        )
        if response.status_code == 202:
            st.success("✅ Email sent successfully!")
        else:
            st.error(f"❌ Failed to send email. {response.status_code}: {response.text}")
