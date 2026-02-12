import streamlit as st
import diyepw
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="AMY EPW Generator", page_icon="🌤️")

def generate_epw_cloud(wmo_number, year, temp_dir):
    try:
        diyepw.create_amy_epw_files_for_years_and_wmos(
            [int(year)],
            [int(wmo_number)],
            max_records_to_interpolate=100,
            max_records_to_impute=50,
            max_missing_amy_rows=50,
            allow_downloads=True,
            amy_epw_dir=temp_dir,
        )
        return True
    except Exception as e:
        st.error(f"Processing Error: {e}")
        return False

st.title("🌤️ AMY EPW Weather Generator")
st.info("This tool fetches real-world weather data from NOAA for building energy simulations.")

with st.form("epw_form"):
    col1, col2 = st.columns(2)
    with col1:
        wmo_code = st.text_input("WMO Number", placeholder="e.g., 722950")
    with col2:
        target_year = st.number_input("Year", min_value=1901, max_value=2025, value=2024)
    
    submit_button = st.form_submit_button("Generate & Prepare Download")

if submit_button:
    if not wmo_code:
        st.warning("Please enter a WMO number.")
    else:
        # Create a temporary directory that works on any OS (Linux/Windows/Cloud)
        with tempfile.TemporaryDirectory() as tmpdirname:
            with st.status("Downloading from NOAA... this may take a minute.", expanded=True) as status:
                success = generate_epw_cloud(wmo_code, target_year, tmpdirname)
                
                if success:
                    # Find the generated file in the temp folder
                    generated_files = list(Path(tmpdirname).glob("*.epw"))
                    
                    if generated_files:
                        status.update(label="Success!", state="complete", expanded=False)
                        target_file = generated_files[0]
                        
                        with open(target_file, "rb") as f:
                            st.download_button(
                                label="📥 Download EPW File",
                                data=f,
                                file_name=target_file.name,
                                mime="text/plain",
                                use_container_width=True
                            )
                    else:
                        status.update(label="File not found after processing.", state="error")
                else:
                    status.update(label="Generation Failed", state="error")