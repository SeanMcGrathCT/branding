import streamlit as st
import pandas as pd
import base64
from datetime import datetime
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, storage
import json
import cairosvg

# Initialize Firebase
if not firebase_admin._apps:
    firebase_credentials = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred, {
        'storageBucket': f"{firebase_credentials['project_id']}.appspot.com"
    })

def upload_to_firebase_storage(file_path, bucket, destination_blob_name):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    return blob.public_url

def change_bar_colors(svg_content, measurement_unit, mapping_column, source_data):
    # Parse the SVG content
    soup = BeautifulSoup(svg_content, 'xml')
    
    # Embed source data as metadata
    metadata = soup.new_tag('metadata')
    metadata.string = source_data.to_json()
    soup.svg.append(metadata)

    rects = soup.find_all('rect')
    
    for rect in rects:
        if 'id' in rect.attrs and rect['id'].startswith('bar'):
            bar_id = rect['id']
            provider_name = bar_id.split('-')[1].strip().lower()
            provider_title = provider_name.title()
            
            if provider_title in source_data.index:
                actual_value = source_data.loc[provider_title, mapping_column]
                rect_title = soup.new_tag('title')
                rect_title.string = f"Value: {actual_value:.2f} {measurement_unit}"
                rect.append(rect_title)
                rect['onmouseover'] = "evt.target.style.opacity=0.6"
                rect['onmouseout'] = "evt.target.style.opacity=1"
            else:
                rect_title = soup.new_tag('title')
                rect_title.string = "No data available"
                rect.append(rect_title)

    # Remove x and y axis labels
    for text in soup.find_all('text'):
        if text.get('x') == '745' or text.get('x') == '4':
            text.decompose()
    
    return str(soup)

# Streamlit UI
st.title("SVG Modifier")

uploaded_file = st.file_uploader("Upload SVG file", type="svg")
uploaded_data = st.file_uploader("Upload CSV data file", type=["csv"])
measurement_unit = st.text_input("Enter the unit of measurement:")
mapping_column = st.text_input("Enter the column name for mapping values:")

if uploaded_file is not None and uploaded_data is not None and measurement_unit and mapping_column:
    svg_content = uploaded_file.read().decode("utf-8")
    source_data = pd.read_csv(uploaded_data, index_col='VPN provider')
    
    modified_svg_content = change_bar_colors(svg_content, measurement_unit, mapping_column, source_data)
    
    # Prompt user for file name and date
    file_name = st.text_input("Enter the file name:")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    if file_name:
        full_name = f"{file_name}_{current_date}.svg"
        
        # Save the modified SVG
        with open(full_name, "w") as file:
            file.write(modified_svg_content)
        
        # Convert SVG to JPG
        output_jpg_path = full_name.replace('.svg', '.jpg')
        cairosvg.svg2png(url=full_name, write_to=output_jpg_path)
        
        # Provide download link for modified SVG
        st.download_button(
            label="Download modified SVG",
            data=modified_svg_content,
            file_name=full_name,
            mime="image/svg+xml"
        )
        
        # Provide download link for modified JPG
        with open(output_jpg_path, "rb") as img_file:
            st.download_button(
                label="Download modified JPG",
                data=img_file,
                file_name=full_name.replace('.svg', '.jpg'),
                mime="image/jpeg"
            )
        
        # Upload to Firebase Storage
        bucket = storage.bucket()
        svg_url = upload_to_firebase_storage(full_name, bucket, full_name)
        jpg_url = upload_to_firebase_storage(output_jpg_path, bucket, output_jpg_path)
        
        st.write(f"SVG uploaded to: {svg_url}")
        st.write(f"JPG uploaded to: {jpg_url}")
