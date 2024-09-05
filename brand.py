import streamlit as st
import pandas as pd
import json
import re
import uuid

# Define VPN colors with less transparency for a more defined look
vpn_colors = {
    'nordvpn': 'rgba(62, 95, 255, 0.8)',
    'surfshark': 'rgba(30, 191, 191, 0.8)',
    'expressvpn': 'rgba(218, 57, 64, 0.8)',
    'ipvanish': 'rgba(112, 187, 68, 0.8)',
    'cyberghost': 'rgba(255, 204, 0, 0.8)',
    'purevpn': 'rgba(133, 102, 231, 0.8)',
    'protonvpn': 'rgba(109, 74, 255, 0.8)',
    'privatevpn': 'rgba(159, 97, 185, 0.8)',
    'pia': 'rgba(109, 200, 98, 0.8)',
    'hotspot shield': 'rgba(109, 192, 250, 0.8)',
    'strongvpn': 'rgba(238, 170, 29, 0.8)'
}

# Function to assign colors based on provider names
def get_provider_color(provider_name):
    if isinstance(provider_name, str):
        provider_name = provider_name.lower()
        return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')
    return 'rgba(75, 192, 192, 0.8)'

# Function to extract colors from existing chart data in HTML
def extract_colors_from_html(html_content):
    try:
        # Extract color arrays from the HTML content
        background_color_pattern = r'backgroundColor":\s*\[(.*?)\]'
        border_color_pattern = r'borderColor":\s*\[(.*?)\]'
        
        # Find the matches for background and border colors
        background_colors_match = re.search(background_color_pattern, html_content)
        border_colors_match = re.search(border_color_pattern, html_content)

        # Extract the color values (handle it as a string, cleaning up extra characters)
        if background_colors_match:
            background_colors_str = background_colors_match.group(1)
            background_colors = re.findall(r'rgba?\([^\)]+\)', background_colors_str)
        else:
            background_colors = []

        if border_colors_match:
            border_colors_str = border_colors_match.group(1)
            border_colors = re.findall(r'rgba?\([^\)]+\)', border_colors_str)
        else:
            border_colors = []

        return background_colors, border_colors
    except Exception as e:
        st.error(f"Failed to extract colors from HTML: {e}")
        return [], []

# Function to generate a unique ID for the chart
def generate_unique_id(title):
    unique_id = title.replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:6]
    return unique_id

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

def load_chart_data_from_html(html_content):
    try:
        start_marker = '<script type="application/ld+json">'
        end_marker = '</script>'
        start = html_content.find(start_marker)
        end = html_content.find(end_marker, start)
        if start == -1 or end == -1:
            raise ValueError("Could not find the JSON data section in the provided HTML content.")
        
        json_data = html_content[start+len(start_marker):end].strip()
        data = json.loads(json_data)
        return data
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON data from HTML content: {e}")
        return None
    except ValueError as e:
        st.error(e)
        return None

# Radio button for creating or updating chart
action = st.radio("Choose an action:", ["Create New Chart", "Update Existing Chart"], key='action_choice')

# Initialize variables for form fields
seo_title = ""
seo_description = ""
label_column = ""
value_columns = []
measurement_unit = "Mbps"
chart_size = "Full Width"
chart_width = 805
chart_height = 600
source_data = None

if action == "Create New Chart":
    uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
    if uploaded_file is not None:
        source_data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        source_data = st.data_editor(source_data, key='data_editor_new')

elif action == "Update Existing Chart":
    chart_html = st.text_area("Paste the HTML content of the existing chart:")
    if chart_html:
        chart_data = load_chart_data_from_html(chart_html)
        if chart_data:
            labels = list(chart_data["data"].values())[0].keys()
            datasets = []

            # Extract colors from existing HTML
            background_colors, border_colors = extract_colors_from_html(chart_html)
            
            # Log the extracted colors in the Streamlit UI for verification
            st.write("Extracted Background Colors:", background_colors)
            st.write("Extracted Border Colors:", border_colors)
            
            # Loop through the data to extract values and apply color logic
            for k, v in chart_data["data"].items():
                data_values = [float(re.sub("[^0-9.]", "", str(val))) if isinstance(val, str) else val for val in v.values()]
                
                # Use extracted colors or fallback to provider-based color logic
                bg_colors = background_colors if background_colors else [get_provider_color(k)] * len(data_values)
                br_colors = border_colors if border_colors else bg_colors
                
                datasets.append({
                    "label": k,
                    "data": data_values,
                    "backgroundColor": bg_colors,
                    "borderColor": br_colors,
                    "borderWidth": 1
                })

            seo_title = chart_data.get("name", "")
            seo_description = chart_data.get("description", "")
            measurement_unit = "Mbps"
            chart_width = 805
            chart_height = 600
            label_column = "VPN provider"
            data_dict = {label_column: labels}
            for dataset in datasets:
                data_dict[dataset["label"]] = dataset["data"]
            source_data = pd.DataFrame(data_dict)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data, key='data_editor_update')

if source_data is not None:
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart", "Radar Chart"])
    
    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        valid_columns = list(source_data.columns)
        default_columns = valid_columns[1:] if len(valid_columns) > 1 else valid_columns
        value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=default_columns, key='value_columns')

    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title, key='seo_title')
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description, key='seo_description')

    if chart_type != "Scatter Chart":
        y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)", key='y_axis_label')
    measurement_unit = st.text_input("Enter the measurement unit:", measurement_unit, key='measurement_unit')

    if st.button("Generate HTML"):
        datasets = []
        null_value = 0.05  
        labels = source_data[label_column].tolist()
        for provider in labels:
            data = [source_data[col].values[0] for col in value_columns]
            background_colors = [get_provider_color(provider)] * len(data)
            border_colors = background_colors
            datasets.append({
                "label": provider,
                "data": data,
                "backgroundColor": background_colors,
                "borderColor": border_colors,
                "borderWidth": 1
            })

        # Log the generated colors in the Streamlit UI for verification
        st.write("Generated Background Colors:", background_colors)
        st.write("Generated Border Colors:", border_colors)

        # Create HTML content with chart
        unique_id_safe = generate_unique_id(seo_title)
        html_content = f"""
<div id="{unique_id_safe}" style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart_{unique_id_safe}" width="{chart_width}" height="{chart_height}"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('vpnSpeedChart_{unique_id_safe}').getContext('2d');
        var vpnSpeedChart = new Chart(ctx, {{
            type: '{chart_type.lower()}',
            data: {{
                labels: {json.dumps(labels)},
                datasets: {json.dumps(datasets, default=str)}
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: {json.dumps(seo_title)},
                        font: {{ size: 18 }}
                    }},
                    legend: {{
                        display: true
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '{y_axis_label}'
                        }}
                    }}
                }}
            }}
        }});
    }});
</script>
"""

        st.download_button("Download HTML", data=html_content, file_name=f"{unique_id_safe}.html", mime="text/html")

