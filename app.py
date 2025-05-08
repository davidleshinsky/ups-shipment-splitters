
import streamlit as st
import pandas as pd
import io
import zipfile
import base64

PASSWORD = "splitUPS2025"

st.set_page_config(page_title="UPS Shipment File Splitter")

def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password to access the tool:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password to access the tool:", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

def process_file(uploaded_file):
    df = pd.read_csv(uploaded_file)
    if "Main Reference" not in df.columns or "Manifest Date" not in df.columns:
        st.error("CSV must contain 'Main Reference' and 'Manifest Date' columns.")
        return None

    grouped = df.groupby(["Main Reference", "Manifest Date"])
    output_zip = io.BytesIO()

    with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for (reference, date), group in grouped:
            name = f"{reference}_{str(date).replace('/', '-')}.csv"
            csv_bytes = group.to_csv(index=False).encode("utf-8")
            zf.writestr(name, csv_bytes)

    output_zip.seek(0)
    return output_zip

def main():
    if not check_password():
        return

    st.title("UPS Shipment File Splitter")
    uploaded_file = st.file_uploader("Upload UPS Tracking File (CSV)", type=["csv"])
    
    if uploaded_file:
        zip_bytes = process_file(uploaded_file)
        if zip_bytes:
            b64 = base64.b64encode(zip_bytes.read()).decode()
            href = f'<a href="data:application/zip;base64,{b64}" download="split_files.zip">📥 Download ZIP</a>'
            st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
