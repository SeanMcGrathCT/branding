import streamlit as st
import pandas as pd
import cairosvg
from PIL import Image
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, storage
import json
from datetime import datetime

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_credentials = st.secrets["FIREBASE_CREDENTIALS"]
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred, {
        'storageBucket': f"{firebase_credentials['project_id']}.appspot.com"
    })

# Define VPN colors
vpn_colors = {
    'nordvpn': '#3e5fff',
    'surfshark': '#1EBFBF',
    'expressvpn': '#DA3940',
    'ipvanish': '#70BB44',
    'cyberghost': '#FFCC00',
    'purevpn': '#8566E7',
    'pure vpn': '#8566E7',
    'protonvpn': '#6D4AFF',
    'proton vpn': '#6D4AFF',
    'privatevpn': '#9f61b9',
    'private vpn': '#9f61b9',
    'pia': '#6dc862',
    'private internet access': '#6dc862',
    'hotspot shield': '#6DC0FA',
    'strongvpn': '#EEAA1D',
    'strong vpn': '#EEAA1D'
}

def add_gradients_to_svg(soup, gradients):
    defs = soup.new_tag('defs')
    for vpn_name, color in gradients.items():
        gradient = soup.new_tag('linearGradient', id=f'gradient-{vpn_name}', x1="0%", y1="0%", x2="0%", y2="100%")
        stop1 = soup.new_tag('stop', offset="0%", style=f'stop-color:{color};stop-opacity:1')
        stop2 = soup.new_tag('stop', offset="100%", style=f'stop-color:{adjust_brightness(color, -0.5)};stop-opacity:1')
        gradient.append(stop1)
        gradient.append(stop2)
        defs.append(gradient)
    soup.svg.insert(0, defs)

def adjust_brightness(hex_color, factor):
    hex_color = hex_color.lstrip('#')
    rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
    rgb = [int(max(min(c * (1 + factor), 255), 0)) for c in rgb]
    return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

def extract_providers_from_labels(soup):
    providers = []
    for g in soup.find_all('g', {'class': 'tick'}):
        text = g.find('text').get_text().strip().lower()
        if text in vpn_colors:
            providers.append(text)
    return providers

def extract_bar_ids(soup):
    bar_ids = []
    bars = soup.find_all('rect')
    for i, bar in enumerate(bars):
        if 'id' in bar.attrs:
            bar_ids.append(f"{bar['id']}_{i}")  # Add unique suffix to each bar ID
    return bar_ids

def change_bar_colors(svg_content, measurement_unit, source_data, value_column_mapping, seo_title, seo_description):
    soup = BeautifulSoup(svg_content, 'xml')

    # Remove specific text elements
    for text in soup.find_all('text'):
        if 'Value' in text.get_text() or 'Sets' in text.get_text():
            text.decompose()

    # Remove x and y labels
    for text in soup.find_all('text'):
        if text.get('x') == '4' or text.get('y') == '-4':
            text.decompose()

    background = soup.find('rect', {'id': 'background'})
    if background:
        background['fill'] = '#FFFFFF'

    bars_group = soup.find('g', {'class': 'bars'})
    if bars_group:
        rects = bars_group.find_all('rect')
    else:
        rects = soup.find_all('rect')

    add_gradients_to_svg(soup, vpn_colors)

    # Embed source data as metadata
    metadata = soup.new_tag('metadata')
    metadata.string = source_data.to_json()
    soup.svg.append(metadata)

    # Add SEO metadata
    seo_metadata = {
        "@context": "http://schema.org",
        "@type": "Dataset",
        "name": seo_title,
        "description": seo_description,
        "data": source_data.to_dict(orient='records')
    }
    seo_script = soup.new_tag('script', type='application/ld+json')
    seo_script.string = json.dumps(seo_metadata)
    soup.svg.append(seo_script)

    for rect in rects:
        rect_id = rect['id']
        rect_id_suffix = f"{rect_id}_{rects.index(rect)}"  # Ensure unique ID for each rect
        if rect_id_suffix in value_column_mapping:
            provider_name, csv_column = value_column_mapping[rect_id_suffix]
            if provider_name.lower() in vpn_colors:
                rect['fill'] = f'url(#gradient-{provider_name.lower()})'
                if provider_name.lower() in source_data.index:
                    actual_value = source_data.loc[provider_name.lower(), csv_column]
                    rect_title = soup.new_tag('title')
                    rect_title.string = f"Value: {actual_value:.2f} {measurement_unit}"
                    rect.append(rect_title)
    
    # Add CSS for highlighting bars on hover
    style = """
    <style>
    rect:hover {
        stroke: #000000;
        stroke-width: 2;
        filter: brightness(1.2);
    }
    </style>
    """
    soup.svg.append(BeautifulSoup(style, 'html.parser'))

    return str(soup)

def convert_svg_to_jpg(svg_content, output_path):
    temp_svg_path = 'temp_modified_viz.svg'
    with open(temp_svg_path, 'w') as file:
        file.write(svg_content)

    temp_png_path = 'temp_modified_viz.png'
    cairosvg.svg2png(url=temp_svg_path, write_to=temp_png_path)

    output_jpg_path = output_path.replace('.svg', '.jpg')
    with Image.open(temp_png_path) as img:
        img = img.convert('RGB')
        img.save(output_jpg_path, 'JPEG')

    return output_jpg_path

def upload_to_firebase_storage(file_path, bucket, destination_blob_name):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    return blob.public_url

# Streamlit UI
st.title("Visualization Branding Tool")
st.write("Upload an SVG file to modify its bar colors based on VPN providers.")

uploaded_file = st.file_uploader("Choose an SVG file", type="svg")
uploaded_data = st.file_uploader("Choose a CSV file with source data", type="csv")
measurement_unit = st.text_input("Enter the unit of measurement:")
seo_title = st.text_input("Enter the SEO title for the visualization:")
seo_description = st.text_area("Enter the SEO description for the visualization:")

if uploaded_file is not None and uploaded_data is not None and measurement_unit and seo_title and seo_description:
    svg_content = uploaded_file.read().decode("utf-8")
    source_data = pd.read_csv(uploaded_data, index_col='VPN provider')
    source_data.index = source_data.index.str.lower()  # Normalize index to lowercase

    # Extract all bar IDs from the SVG for dynamic mapping
    soup = BeautifulSoup(svg_content, 'xml')
    bar_ids = extract_bar_ids(soup)

    # Create a dictionary to map each bar ID to a CSV column
    value_column_mapping = {}
    for i, bar_id in enumerate(bar_ids):
        provider_name = bar_id.split(' - ')[0].lower()
        value_column_mapping[bar_id] = (provider_name, st.selectbox(f"Select the column for {bar_id}:", list(source_data.columns), key=f"{bar_id}_{i}"))

    modified_svg_content = change_bar_colors(svg_content, measurement_unit, source_data, value_column_mapping, seo_title, seo_description)
    
    # Prompt user for file name and date
    file_name = st.text_input("Enter the file name:")
    current_date = datetime.now().strftime("%Y-%m-%d")

    if file_name:
        full_name = f"{file_name}_{current_date}.svg"
        
        # Save modified SVG
        with open(full_name, 'w') as file:
            file.write(modified_svg_content)
        
        st.download_button(
            label="Download modified SVG",
            data=modified_svg_content,
            file_name=full_name,
            mime="image/svg+xml"
        )
        
        # Convert modified SVG to JPG
        output_jpg_path = convert_svg_to_jpg(modified_svg_content, full_name)
        st.image(output_jpg_path, caption="Modified VPN Speed Test Visualization", use_column_width=True)
        
        # Upload to Firebase Storage
        bucket = storage.bucket()
        svg_url = upload_to_firebase_storage(full_name, bucket, full_name)
        jpg_url = upload_to_firebase_storage(output_jpg_path, bucket, output_jpg_path)

        st.write(f"SVG uploaded to: {svg_url}")
        st.write(f"JPG uploaded to: {jpg_url}")

        with open(output_jpg_path, "rb") as img_file:
            st.download_button(
                label="Download
        
        # Upload to Firebase Storage
        bucket = storage.bucket()
        svg_url = upload_to_firebase_storage(full_name, bucket, full_name)
        jpg_url = upload_to_firebase_storage(output_jpg_path, bucket, output_jpg_path)

        st.write(f"SVG uploaded to: {svg_url}")
        st.write(f"JPG uploaded to: {jpg_url}")

        with open(output_jpg_path, "rb") as img_file:
            st.download_button(
                label="Download modified JPG",
                data=img_file,
                file_name=full_name.replace('.svg', '.jpg'),
                mime="image/jpeg"
            )
