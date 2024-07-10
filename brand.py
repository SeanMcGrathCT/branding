import streamlit as st
import pandas as pd
import cairosvg
from PIL import Image
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, storage
import json
from datetime import datetime
import copy

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_credentials = dict(st.secrets["FIREBASE_CREDENTIALS"])
    # Convert the string private key into the required format
    firebase_credentials['private_key'] = firebase_credentials['private_key'].replace('\\n', '\n')
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

def map_bars_to_providers(soup, providers):
    id_provider_map = {}
    ticks = soup.find_all('g', {'class': 'tick'})
    
    # Extract positions of the labels
    label_positions = [float(tick['transform'].split('(')[1].split(',')[0]) for tick in ticks if tick.find('text').get_text().strip().lower() in vpn_colors]
    provider_label_map = {pos: providers[i] for i, pos in enumerate(label_positions)}
    
    # Map each bar to the closest label based on x position
    bars = soup.find_all('rect')
    for i, bar in enumerate(bars):
        if 'x' in bar.attrs:
            bar_x = float(bar['x'])
            closest_label_position = min(label_positions, key=lambda pos: abs(pos - bar_x))
            provider = provider_label_map[closest_label_position]
            bar_id = f'bar-{i}'  # Create a unique id based on the index
            bar['id'] = bar_id
            id_provider_map[bar_id] = provider
    
    return id_provider_map

def extract_unique_labels(svg_content):
    soup = BeautifulSoup(svg_content, 'xml')
    bars = soup.find_all('rect')
    
    unique_labels = {}
    for bar in bars:
        if 'id' in bar.attrs:  # Check if 'id' attribute exists
            original_id = bar['id']
            clean_id = original_id.replace("undefined - ", "").strip()
            label = bar.find_next_sibling('title').string if bar.find_next_sibling('title') else clean_id
            unique_labels[clean_id] = label
    
    return unique_labels

def generate_column_mapping(unique_labels, source_data):
    value_column_mapping = {}
    for label, clean_id in unique_labels.items():
        column = st.selectbox(f"Select the column for {label}:", list(source_data.columns), key=label)
        value_column_mapping[clean_id] = column
    return value_column_mapping

def change_bar_colors(svg_content, measurement_unit, source_data, value_column_mapping, seo_title, seo_description, svg_size):
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

    providers = extract_providers_from_labels(soup)
    provider_map = {provider: i for i, provider in enumerate(providers)}

    add_gradients_to_svg(soup, vpn_colors)

    id_provider_map = map_bars_to_providers(soup, providers)
    
    # Filter source_data to include only the mapped columns
    mapped_columns = set(value_column_mapping.values())
    available_columns = [col for col in mapped_columns if col in source_data.columns]
    filtered_data = source_data[available_columns].copy()

    # Append unit of measurement to each value in filtered data
    for provider in filtered_data.index:
        for column in filtered_data.columns:
            if pd.notna(filtered_data.at[provider, column]):
                filtered_data.at[provider, column] = f"{filtered_data.at[provider, column]} {measurement_unit}"

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
        "data": {provider: filtered_data.loc[provider].to_dict() for provider in filtered_data.index}
    }
    seo_script = soup.new_tag('script', type='application/ld+json')
    seo_script.string = json.dumps(seo_metadata, indent=4)
    soup.svg.append(seo_script)

    for rect in rects:
        rect_id = rect['id']
        
        if rect_id in id_provider_map:
            provider_name = id_provider_map[rect_id].title()
            if provider_name.lower() in vpn_colors:
                rect['fill'] = f'url(#gradient-{provider_name.lower()})'
    
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

    # Adjust the SVG size
    if svg_size == 'small':
        svg_start = '''<?xml version="1.0" encoding="utf-8"?>
<div style="max-width: 500px;">
  <svg viewBox="0 0 500 300" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">'''
        svg_end = '</svg></div>'
    else:
        svg_start = '''<?xml version="1.0" encoding="utf-8"?>
<svg viewBox="0 0 805 600" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">'''
        svg_end = '</svg>'

    svg_content = str(soup)
    svg_content = svg_content.replace('<?xml version="1.0" encoding="utf-8"?>', '')
    modified_svg_content = f"{svg_start}{svg_content}{svg_end}"
    
    return modified_svg_content

def assign_tooltips(svg_content, measurement_unit, source_data, value_column_mapping):
    soup = BeautifulSoup(svg_content, 'xml')

    bars_group = soup.find('g', {'class': 'bars'})
    if bars_group:
        rects = bars_group.find_all('rect')
    else:
        rects = soup.find_all('rect')

    id_provider_map = map_bars_to_providers(soup, extract_providers_from_labels(soup))
    
    for provider in extract_providers_from_labels(soup):
        provider = provider.lower().strip()
        provider_bars = {rect['id']: float(rect['height']) for rect in rects if id_provider_map[rect['id']] == provider}
        if provider not in source_data.index:
            st.warning(f"Provider '{provider}' not found in the source data.")
            continue
        
        provider_data = source_data.loc[provider]

        # Ensure provider_data is a Series and filter out non-numeric values
        provider_data = provider_data.apply(pd.to_numeric, errors='coerce').dropna()
        
        sorted_bars = sorted(provider_bars.items(), key=lambda x: x[1], reverse=True)
        sorted_values = sorted(provider_data.items(), key=lambda x: x[1], reverse=True)[:len(sorted_bars)]

        st.write(f"Provider: {provider}")
        st.write(f"Sorted Bars: {sorted_bars}")
        st.write(f"Sorted Values: {sorted_values}")

        if len(sorted_bars) == len(sorted_values):
            for (bar_id, _), (column_name, value) in zip(sorted_bars, sorted_values):
                rect = soup.find(id=bar_id)
                if rect:
                    rect_title = soup.new_tag('title')
                    rect_title.string = f"{provider.title()} - {column_name}: {value:.2f} {measurement_unit}"
                    rect.append(rect_title)
    
    return str(soup)

def change_label_if_single_provider(svg_content, custom_label):
    soup = BeautifulSoup(svg_content, 'xml')
    providers = extract_providers_from_labels(soup)
    
    if len(providers) == 1:
        for g in soup.find_all('g', {'class': 'tick'}):
            text = g.find('text')
            if text and text.get_text().strip().lower() in vpn_colors:
                text.string = custom_label
    
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
svg_size = st.radio("Choose the SVG size:", ('small', 'full width'))
custom_label = None

if uploaded_file is not None and uploaded_data is not None and measurement_unit and seo_title and seo_description and svg_size:
    svg_content = uploaded_file.read().decode("utf-8")
    source_data = pd.read_csv(uploaded_data)
    
    # Check if 'VPN provider' is in columns and normalize the index
    if 'VPN provider' in source_data.columns:
        source_data.set_index('VPN provider', inplace=True)
    else:
        st.error("CSV file must have a 'VPN provider' column.")
        st.stop()
    
    source_data.index = source_data.index.str.lower().str.strip()  # Normalize index to lowercase and strip spaces

    # Extract unique labels from the SVG
    unique_labels = extract_unique_labels(svg_content)

    # Generate column mapping using Streamlit selectbox
    value_column_mapping = generate_column_mapping(unique_labels, source_data)

    # Apply the column mapping to change bar colors
    modified_svg_content = change_bar_colors(svg_content, measurement_unit, source_data, value_column_mapping, seo_title, seo_description, svg_size)
    
    # Assign tooltips based on values
    modified_svg_content = assign_tooltips(modified_svg_content, measurement_unit, source_data, value_column_mapping)
    
    # Check if there's only one provider and ask for custom label
    if len(extract_providers_from_labels(BeautifulSoup(modified_svg_content, 'xml'))) == 1:
        custom_label = st.text_input("Enter custom label for the single provider:")

    if custom_label:
        modified_svg_content = change_label_if_single_provider(modified_svg_content, custom_label)
    
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
                label="Download modified JPG",
                data=img_file,
                file_name=full_name.replace('.svg', '.jpg'),
                mime="image/jpeg"
            )

# Ensure to include logging for each step
st.write("Log:")
