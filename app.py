import streamlit as st
import pandas as pd
import zipfile
import io
import os
from collections import defaultdict
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

st.set_page_config(page_title="UPS Splitter: Email or Download Per Main Reference")

# --- Password Protection ---
PASSWORD = "splitUPS20253"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("Enter password to access:", type="password")
    if pwd == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

st.title("UPS Splitter: Email or Download Per Main Reference")

uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type=["csv"])
email_address = st.text_input("Enter your email to receive ZIPs (optional)")

if uploaded_file:
    df = pd.read_csv(uploaded_file, dtype=str)
    if "Main Reference" not in df.columns or "Manifest Date" not in df.columns:
        st.error("CSV must contain 'Main Reference' and 'Manifest Date' columns.")
        st.stop()

    grouped = defaultdict(list)
    for _, row in df.iterrows():
        main_ref = row["Main Reference"]
        manifest = row["Manifest Date"]
        grouped[(main_ref, manifest)].append(row)

    results = []
    for (main_ref, manifest), rows in grouped.items():
        out_df = pd.DataFrame(rows)
        filename = f"{main_ref}_{manifest}.csv"
        buffer = io.StringIO()
        out_df.to_csv(buffer, index=False)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr(filename, buffer.getvalue())
        zip_buffer.seek(0)

        st.subheader(f"{main_ref} — {manifest}")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label=f"📥 Download ZIP",
                data=zip_buffer.getvalue(),
                file_name=f"{main_ref}_{manifest}.zip",
                mime="application/zip"
            )
        with col2:
            if email_address:
                send = st.button(f"📧 Send to {email_address}", key=f"{main_ref}_{manifest}")
                if send:
                    try:
                        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
                        encoded = base64.b64encode(zip_buffer.getvalue()).decode()
                        attachment = Attachment(
                            FileContent(encoded),
                            FileName(f"{main_ref}_{manifest}.zip"),
                            FileType("application/zip"),
                            Disposition("attachment")
                        )
                        message = Mail(
                            from_email="davidl@jjsolutions.com",
                            to_emails=email_address,
                            subject=f"UPS ZIP: {main_ref} | {manifest}",
                            plain_text_content="Your ZIP is attached."
                        )
                        message.attachment = attachment
                        response = sg.send(message)
                        st.success(f"Sent to {email_address} (Status {response.status_code})")
                    except Exception as e:
                        st.error(f"❌ Failed to send: {e}")
            else:
                st.info("Enter your email above to enable sending.")
