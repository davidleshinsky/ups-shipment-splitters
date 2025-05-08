import streamlit as st
import pandas as pd
import io
import zipfile
import base64
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

st.set_page_config(page_title="UPS Shipment File Splitter", layout="wide")
st.title("UPS Shipment File Splitter")

# Step 1: Password
password = st.text_input("Enter password to access the tool:", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.stop()

# Step 2: Upload File
uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV or Excel)", type=["csv", "xlsx"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ Failed to read file: {e}")
        st.stop()

    # Step 3: Detect Reference Column
    ref_col = next((col for col in df.columns if "reference" in col.lower()), None)
    if not ref_col:
        st.error("❌ Could not find a column with 'reference' in the header.")
        st.stop()

    df["Main Reference"] = df[ref_col].astype(str).str.split(",").str[0].str.strip()

    # Step 4: Create ZIP of grouped files
    zip_buffer = io.BytesIO()
    df["Manifest Date"] = pd.to_datetime(df.get("Manifest Date", pd.NaT), errors="coerce")
    df["Sheet Name"] = df["Main Reference"] + "_" + df["Manifest Date"].dt.strftime("%Y-%m-%d")
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for name, group in df.groupby("Sheet Name"):
            file_buffer = io.BytesIO()
            group.to_excel(file_buffer, index=False)
            zipf.writestr(f"{name}.xlsx", file_buffer.getvalue())
    zip_buffer.seek(0)

    # Step 5: Allow ZIP download
    st.download_button("📁 Download ZIP", zip_buffer.getvalue(), file_name="split_files.zip", mime="application/zip")

    # Step 6: Email option
    email = st.text_input("Enter your email to receive the ZIP:")
    if email and st.button("📤 Send ZIP by Email"):
        try:
            sg = sendgrid.SendGridAPIClient(api_key=st.secrets["SENDGRID_API_KEY"])
            message = Mail(
                from_email=st.secrets["FROM_EMAIL"],
                to_emails=email,
                subject="Your Split UPS Tracking Files",
                plain_text_content="Attached is your ZIP file containing the split UPS tracking data.",
            )
            encoded = base64.b64encode(zip_buffer.getvalue()).decode()
            attachment = Attachment(
                FileContent(encoded),
                FileName("split_files.zip"),
                FileType("application/zip"),
                Disposition("attachment"),
            )
            message.attachment = attachment
            sg.send(message)
            st.success("📨 Email sent successfully.")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")