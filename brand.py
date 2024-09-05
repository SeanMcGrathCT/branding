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

def get_provider_color(provider_name):
    if isinstance(provider_name, str):
        provider_name = provider_name.lower()
        return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')
    return 'rgba(75, 192, 192, 0.8)'

def extract_colors_from_html(html_content):
    try:
        background_color_pattern = r'backgroundColor":\s*\[(.*?)\]'
        border_color_pattern = r'borderColor":\s*\[(.*?)\]'
        
        background_colors_match = re.search(background_color_pattern, html_content)
        border_colors_match = re.search(border_color_pattern, html_content)

        background_colors = re.findall(r'rgba?\([^\)]+\)', background_colors_match.group(1)) if background_colors_match else []
        border_colors = re.findall(r'rgba?\([^\)]+\)', border_colors_match.group(1)) if border_colors_match else []

        return background_colors, border_colors
    except Exception as e:
        st.error(f"Failed to extract colors from HTML: {e}")
        return [], []

def generate_unique_id(title):
    unique_id = title.replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:6]
    return unique_id

def generate_metadata(seo_title, seo_description, source_data, label_column, value_columns, measurement_unit):
    data_dict = {provider: {col: f"{source_data.at[source_data[source_data[label_column] == provider].index[0], col]} {measurement_unit}".split(' ')[0] + ' ' + measurement_unit for col in value_columns} for provider in source_data[label_column]}
    
    metadata = {
        "@context": "http://schema.org",
        "@type": "Dataset",
        "name": seo_title,
        "description": seo_description,
        "data": data_dict
    }
    return metadata

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

action = st.radio("Choose an action:", ["Create New Chart", "Update Existing Chart"], key='action_choice')

# Initialize variables
seo_title = ""
seo_description = ""
label_column = ""
value_columns = []
measurement_unit = "Mbps"
empty_bar_text = "No data available"
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
            labels = list(chart_data["data"].keys())  
            datasets = []

            # Extract colors from HTML
            background_colors, border_colors = extract_colors_from_html(chart_html)
            st.write("Extracted Background Colors:", background_colors)
            st.write("Extracted Border Colors:", border_colors)

            # Extract data and apply color logic
            for k, v in chart_data["data"].items():
                data_values = [float(re.sub("[^0-9.]", "", str(val))) if isinstance(val, str) else val for val in v.values()]
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
            label_column = "VPN provider"
            max_len = max(len(d["data"]) for d in datasets)
            data_dict = {label_column: labels[:max_len]}  
            for dataset in datasets:
                data_dict[dataset["label"]] = dataset["data"][:max_len]  

            source_data = pd.DataFrame(data_dict)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data, key='data_editor_update')

if source_data is not None:
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart", "Radar Chart"])

    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        valid_columns = list(source_data.columns)
        if chart_type != "Scatter Chart":
            value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=valid_columns[1:], key='value_columns')

    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title, key='seo_title')
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description, key='seo_description')

    if chart_type != "Scatter Chart":
        y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)", key='y_axis_label')
    
    display_legend = st.checkbox("Display legend", value=True, key='display_legend')

    if st.button("Generate HTML"):
        datasets = []
        if chart_type == "Grouped Bar Chart":
            labels = list(value_columns)
            for provider in source_data[label_column].unique():
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    float(provider_data[col].values[0]) if pd.api.types.is_numeric_dtype(source_data[col]) else provider_data[col].values[0]
                    for col in value_columns
                ]
                background_colors = [get_provider_color(provider)] * len(data)
                border_colors = background_colors
                datasets.append({
                    'label': provider,
                    'data': data,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })

        unique_id_safe = generate_unique_id(seo_title)
        metadata = generate_metadata(seo_title, seo_description, source_data, label_column, value_columns, measurement_unit)

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
                        display: {str(display_legend).lower()}
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
<script type="application/ld+json">
{json.dumps(metadata, indent=4)}
</script>
"""
        st.download_button("Download HTML", data=html_content, file_name=f"{unique_id_safe}.html", mime="text/html")

