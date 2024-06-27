import streamlit as st
import firebase_admin
from firebase_admin import credentials, storage
import cairosvg
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime

# Initialize Firebase
if not firebase_admin._apps:
    firebase_credentials = json.loads(st.secrets["FIREBASE_CREDENTIALS"].to_json())
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

def change_bar_colors(svg_content, measurement_unit):
    soup = BeautifulSoup(svg_content, 'xml')

    # Remove specific text elements
    for text in soup.find_all('text'):
        if 'Value' in text.get_text() or 'Sets' in text.get_text():
            text.decompose()

    # Remove x and y labels
    for text in soup.find_all('text'):
        if text.get('x') == '4' and text.get('y') == '-4':
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

    for rect in rects:
        rect_id = rect['id']
        if rect_id in id_provider_map:
            provider_name = id_provider_map[rect_id]
            if provider_name in vpn_colors:
                rect['fill'] = f'url(#gradient-{provider_name})'
                
            # Add tooltip with Y-axis value
            y_value = float(rect['height'])
            title = soup.new_tag('title')
            title.string = f'Value: {y_value:.2f} {measurement_unit}'
            rect.append(title)

    # Add hover effect using CSS
    style = soup.new_tag('style')
    style.string = """
    rect:hover {
        opacity: 0.7;
        cursor: pointer;
    }
    """
    soup.svg.insert(0, style)

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

if uploaded_file is not None:
    svg_content = uploaded_file.read().decode("utf-8")
    measurement_unit = st.text_input("Enter the measurement unit (e.g., Mbps):", value="Mbps")

    if st.button("Modify SVG"):
        modified_svg_content = change_bar_colors(svg_content, measurement_unit)
        
        # Prompt user for file name and date
        file_name = st.text_input("Enter the file name:")
        date = st.date_input("Enter the date:", value=datetime.today())

        if file_name and date:
            formatted_date = date.strftime("%Y-%m-%d")
            full_svg_name = f"{file_name}_{formatted_date}.svg"
            full_jpg_name = full_svg_name.replace('.svg', '.jpg')
            
            with open(full_svg_name, 'w') as f:
                f.write(modified_svg_content)
            
            # Convert modified SVG to JPG
            output_jpg_path = convert_svg_to_jpg(modified_svg_content, full_svg_name)
            
            st.image(output_jpg_path, caption="Modified VPN Speed Test Visualization", use_column_width=True)
            
            # Download modified SVG
            st.download_button(
                label="Download modified SVG",
                data=modified_svg_content,
                file_name=full_svg_name,
                mime="image/svg+xml"
            )
            
            # Download modified JPG
            with open(output_jpg_path, "rb") as img_file:
                st.download_button(
                    label="Download modified JPG",
                    data=img_file,
                    file_name=full_jpg_name,
                    mime="image/jpeg"
                )
            
            # Upload to Firebase Storage
            bucket = storage.bucket()
            svg_url = upload_to_firebase_storage(full_svg_name, bucket, full_svg_name)
            jpg_url = upload_to_firebase_storage(output_jpg_path, bucket, full_jpg_name)
            
            st.write(f"SVG uploaded to: [SVG Link]({svg_url})")
            st.write(f"JPG uploaded to: [JPG Link]({jpg_url})")
