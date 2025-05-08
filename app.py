import streamlit as st
import pandas as pd
import re
import zipfile
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from io import BytesIO

st.set_page_config(page_title="UPS Shipment File Splitter", layout="wide")
st.title("📦 UPS Shipment File Splitter")

password = st.text_input("Enter password to access the tool:", type="password")
if password != "upsplit":
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

    df["Main Reference"] = df["Reference"].str.extract(r"(\w{2,}-\d{2,})")
    df["Manifest Date"] = pd.to_datetime(df["Manifest Date"]).dt.strftime('%Y-%m-%d')
    grouped = df.groupby(["Main Reference", "Manifest Date"])

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for (ref, date), group in grouped:
            filename = f"{ref}_{date}.xlsx"
            buffer = BytesIO()
            group.to_excel(buffer, index=False)
            zipf.writestr(filename, buffer.getvalue())

    st.success("✅ File split successfully.")
    st.download_button("📥 Download ZIP", zip_buffer.getvalue(), file_name="split_shipments.zip")

    to_email = st.text_input("Or enter your email to receive it:")
    if to_email and st.button("✉️ Send ZIP by Email"):
        try:
            sg = sendgrid.SendGridAPIClient(api_key=st.secrets["SENDGRID_API_KEY"])
            from_email = Email("david@jjsolutions.com")
            to = To(to_email)
            content = Content("text/plain", "Your UPS shipment files are attached.")
            mail = Mail(from_email, to, "Your Split UPS Files", content)
            
            zip_buffer.seek(0)
            mail.add_attachment(zip_buffer.getvalue(), 'application/zip', 'split_shipments.zip', 'attachment')
            response = sg.send(mail)

            if response.status_code in [200, 202]:
                st.success("✅ Email sent successfully.")
            else:
                st.error(f"❌ Email failed. Status code: {response.status_code}")
        except Exception as e:
            st.error(f"❌ SendGrid error: {e}")