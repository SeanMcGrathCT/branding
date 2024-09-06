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

# Define nice colors for test types
nice_colors = [
    'rgba(255, 99, 132, 0.8)',
    'rgba(54, 162, 235, 0.8)',
    'rgba(255, 206, 86, 0.8)',
    'rgba(75, 192, 192, 0.8)',
    'rgba(153, 102, 255, 0.8)',
    'rgba(255, 159, 64, 0.8)'
]

# Function to assign colors based on provider names
def get_provider_color(provider_name):
    st.write(f"Getting color for provider: {provider_name}")
    if isinstance(provider_name, str):
        provider_name = provider_name.lower()
        color = vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')
        st.write(f"Assigned color: {color}")
        return color
    st.write(f"Provider name not a string: {provider_name}")
    return 'rgba(75, 192, 192, 0.8)'

# Function to extract colors from existing chart data in HTML
def extract_colors_from_html(html_content):
    try:
        st.write("Extracting colors from HTML...")
        background_color_pattern = r'backgroundColor":\s*\[(.*?)\]'
        border_color_pattern = r'borderColor":\s*\[(.*?)\]'
        
        background_colors_match = re.search(background_color_pattern, html_content)
        border_colors_match = re.search(border_color_pattern, html_content)

        background_colors = re.findall(r'rgba?\([^\)]+\)', background_colors_match.group(1)) if background_colors_match else []
        border_colors = re.findall(r'rgba?\([^\)]+\)', border_colors_match.group(1)) if border_colors_match else []

        st.write(f"Extracted background colors: {background_colors}")
        st.write(f"Extracted border colors: {border_colors}")
        
        return background_colors, border_colors
    except Exception as e:
        st.error(f"Failed to extract colors from HTML: {e}")
        return [], []

# Function to extract VPN provider from the HTML content
def extract_vpn_provider_from_html(html_content):
    st.write("Scanning HTML for VPN provider names...")
    for provider in vpn_colors.keys():
        if provider.lower() in html_content.lower():
            st.write(f"Found VPN provider: {provider}")
            return provider
    st.write("No known VPN provider found in HTML.")
    return None

# Updated function to update the existing chart
def update_chart(chart_html, source_data, label_column, value_columns):
    st.write("Updating chart with HTML content...")
    chart_data = load_chart_data_from_html(chart_html)
    
    if chart_data:
        st.write("Loaded chart data from HTML.")

        # Extract the VPN provider name from the HTML
        provider_name = extract_vpn_provider_from_html(chart_html)
        
        if not provider_name:
            st.error("No known VPN provider found. Default colors will be used.")
            provider_name = "default"

        # The test labels like "Speed test: UK (a.m.)", "Speed test: UK (noon)"
        labels = list(chart_data["data"].values())[0].keys()
        datasets = [{"label": provider_name, "data": list(chart_data["data"][provider_name].values())}]
        
        st.write(f"Chart labels: {labels}")
        st.write(f"Provider name: {provider_name}")
        st.write(f"Chart datasets: {datasets}")

        # Extract and apply colors from the HTML if they exist
        background_colors, border_colors = extract_colors_from_html(chart_html)

        for dataset in datasets:
            st.write(f"Processing dataset for provider: {provider_name}")

            # Apply extracted background colors if available
            if background_colors:
                dataset["backgroundColor"] = background_colors
                st.write(f"Using extracted background colors: {background_colors}")
            else:
                # Assign colors based on the provider found in the HTML
                dataset["backgroundColor"] = [get_provider_color(provider_name)] * len(dataset["data"])
                st.write(f"Using provider color for {provider_name}: {dataset['backgroundColor']}")

            # Apply extracted border colors if available
            if border_colors:
                dataset["borderColor"] = border_colors
                st.write(f"Using extracted border colors: {border_colors}")
            else:
                dataset["borderColor"] = dataset["backgroundColor"]
                st.write(f"Using default border color: {dataset['borderColor']}")

        # Display updated data and colors
        data_dict = {label_column: labels}
        for dataset in datasets:
            data_dict[dataset["label"]] = dataset["data"]

        source_data = pd.DataFrame(data_dict)
        st.write("Updated Data Preview:")
        source_data = st.data_editor(source_data)

# Function to generate a unique ID for the chart
def generate_unique_id(title):
    unique_id = title.replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:6]
    return unique_id

# Function to generate ld+json metadata
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

# Function to load chart data from HTML
def load_chart_data_from_html(html_content):
    try:
        st.write("Loading chart data from HTML...")
        start_marker = '<script type="application/ld+json">'
        end_marker = '</script>'
        start = html_content.find(start_marker)
        end = html_content.find(end_marker, start)
        if start == -1 or end == -1:
            raise ValueError("Could not find the JSON data section in the provided HTML content.")
        
        json_data = html_content[start+len(start_marker):end].strip()
        data = json.loads(json_data)
        st.write(f"Loaded data: {data}")
        return data
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON data from HTML content: {e}")
        return None
    except ValueError as e:
        st.error(e)
        return None

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# Radio button for creating or updating chart
action = st.radio("Choose an action:", ["Create New Chart", "Update Existing Chart"], key='action_choice')

# Initialize variables for form fields
seo_title = ""
seo_description = ""
label_column = ""
value_columns = []
measurement_unit = "Mbps"
empty_bar_text = "No data available"
chart_size = "Full Width"
chart_width = 805
chart_height = 600
grouping_method = "Provider"
display_legend = True
source_data = None

if action == "Create New Chart":
    uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
    if uploaded_file is not None:
        source_data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        source_data = st.data_editor(source_data)
elif action == "Update Existing Chart":
    chart_html = st.text_area("Paste the HTML content of the existing chart:")
    if chart_html:
        chart_data = load_chart_data_from_html(chart_html)
        if chart_data:
            labels = list(chart_data["data"].values())[0].keys()
            datasets = [{"label": k, "data": list(v.values())} for k, v in chart_data["data"].items()]

            # Extract and apply colors
            background_colors, border_colors = extract_colors_from_html(chart_html)

            # Apply colors to the dataset if extracted, else use defaults
            for dataset in datasets:
                dataset["data"] = [float(re.sub("[^0-9.]", "", str(val))) if isinstance(val, str) else val for val in dataset["data"]]
                dataset["backgroundColor"] = background_colors if background_colors else [get_provider_color(dataset["label"])] * len(dataset["data"])
                dataset["borderColor"] = border_colors if border_colors else dataset["backgroundColor"]

            seo_title = chart_data.get("name", "")
            seo_description = chart_data.get("description", "")
            measurement_unit = "Mbps"
            empty_bar_text = "No data available"
            display_legend = True
            grouping_method = "Provider"
            chart_size = "Full Width"
            chart_width = 805
            chart_height = 600
            label_column = "VPN provider"
            data_dict = {label_column: labels}
            for dataset in datasets:
                data_dict[dataset["label"]] = dataset["data"]
            source_data = pd.DataFrame(data_dict)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data)

if source_data is not None:
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart", "Radar Chart"])
    
    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        valid_columns = list(source_data.columns)
        default_columns = valid_columns[1:] if len(valid_columns) > 1 else valid_columns
        if chart_type == "Scatter Chart":
            x_column = st.selectbox("Select the column for X-axis values:", valid_columns, key='x_column')
            y_column = st.selectbox("Select the column for Y-axis values:", valid_columns, key='y_column')
        else:
            value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=default_columns, key='value_columns')

    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title)
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description)

    if chart_type != "Scatter Chart":
        y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)")
    measurement_unit = st.text_input("Enter the measurement unit:", measurement_unit)
    empty_bar_text = st.text_input("Enter the text for empty bar tooltips:", empty_bar_text)
    chart_size = st.selectbox("Select the chart size:", ["Full Width", "Medium", "Small"])
    if chart_size == "Full Width":
        chart_width = 805
        chart_height = 600
    elif chart_size == "Medium":
        chart_width = 605
        chart_height = 500
    else:
        chart_width = 405
        chart_height = 400
    if chart_type == "Grouped Bar Chart":
        grouping_method = st.selectbox("Group by Provider or Test Type:", ["Provider", "Test Type"], key='grouping_method')
    else:
        grouping_method = "Provider"

    display_legend = st.checkbox("Display legend", value=display_legend)

    # Add this to define `html_type`
    html_type = st.radio("HTML Type:", ["Standalone", "Production"], index=0)

    if st.button("Generate HTML"):
        datasets = []
        null_value = 0.05  
        if chart_type == "Scatter Chart":
            labels = []
            x_values = []
            y_values = []
            for provider in source_data[label_column].unique():
                provider_data = source_data[source_data[label_column] == provider]
                try:
                    x_val = float(provider_data[x_column].values[0])
                    y_val = float(provider_data[y_column].values[0])
                    x_values.append(x_val)
                    y_values.append(y_val)
                    scatter_data = [{'x': x_val, 'y': y_val}]
                    background_colors = [get_provider_color(provider)]
                    border_colors = background_colors
                    datasets.append({
                        'label': provider,
                        'data': scatter_data,
                        'backgroundColor': background_colors,
                        'borderColor': border_colors,
                        'borderWidth': 1,
                        'showLine': False
                    })
                except ValueError as e:
                    st.error(f"Error converting values to float for provider '{provider}': {e}")
                    continue
            if x_values and y_values:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)
        elif chart_type == "Radar Chart":
            labels = value_columns
            for provider in source_data[label_column].unique():
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    float(provider_data[col].values[0].split(' ')[0]) if isinstance(provider_data[col].values[0], str) else provider_data[col].values[0]
                    for col in value_columns
                    if pd.api.types.is_numeric_dtype(source_data[col])
                ]
                background_colors = get_provider_color(provider)
                border_colors = background_colors
                datasets.append({
                    'label': provider,
                    'data': data,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
        elif grouping_method == "Provider":
            labels = list(value_columns)
            unique_providers = source_data[label_column].unique()
            for provider in unique_providers:
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    float(provider_data[col].values[0].split(' ')[0]) if isinstance(provider_data[col].values[0], str) else provider_data[col].values[0]
                    for col in value_columns
                    if pd.api.types.is_numeric_dtype(source_data[col])
                ]
                background_colors = [
                    get_provider_color(provider) if not pd.isna(provider_data[col].values[0]) else 'rgba(169, 169, 169, 0.8)'
                    for col in value_columns
                ]
                border_colors = background_colors
                datasets.append({
                    'label': provider,
                    'data': data,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
        else:
            labels = source_data[label_column].tolist()
            color_index = 0
            for col in value_columns:
                values = [
                    float(value.split(' ')[0]) if isinstance(value, str) and ' ' in value else value
                    for value in source_data[col].tolist()
                    if pd.api.types.is_numeric_dtype(source_data[col])
                ]
                background_colors = [
                    nice_colors[color_index % len(nice_colors)] if not pd.isna(value) else 'rgba(169, 169, 169, 0.8)'
                    for value in values
                ]
                border_colors = background_colors
                datasets.append({
                    'label': col,
                    'data': values,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
                color_index += 1

        # Escape special characters in seo_title and unique_id
        seo_title_escaped = json.dumps(seo_title)
        unique_id_safe = re.sub(r'[^a-zA-Z0-9_]', '_', generate_unique_id(seo_title))

        metadata = generate_metadata(seo_title, seo_description, source_data, label_column, value_columns, measurement_unit)

        html_content = f"""
<div id="{unique_id_safe}" style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart_{unique_id_safe}" width="{chart_width}" height="{chart_height}"></canvas>
</div>
"""
        if html_type == "Standalone":
            html_content += f"""
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
"""

        html_content += f"""
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('vpnSpeedChart_{unique_id_safe}').getContext('2d');
        
        var vpnSpeedChart = new Chart(ctx, {{
            type: '{'radar' if chart_type == 'Radar Chart' else 'scatter' if chart_type == 'Scatter Chart' else 'bar'}',
            data: {{
                labels: {json.dumps(labels)},
                datasets: {json.dumps(datasets, default=str)}
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: {seo_title_escaped},
                        font: {{
                            size: 18
                        }}
                    }},
                    legend: {{
                        display: {str(display_legend).lower()}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                if (context.raw <= {null_value * 1.1}) {{
                                    return '{empty_bar_text}';
                                }}
                                if (context.raw && context.raw.x !== undefined && context.raw.y !== undefined) {{
                                    return context.dataset.label + ': (' + context.raw.x + ', ' + context.raw.y + ')';
                                }}
                                return context.dataset.label + ': ' + context.raw + ' {measurement_unit}';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: {str(chart_type != 'Radar Chart').lower()},
                        min: {(x_min - 1) if chart_type == 'Scatter Chart' else 'null'},
                        max: {(x_max + 1) if chart_type == 'Scatter Chart' else 'null'},
                        title: {{
                            display: true,
                            text: '{x_column if chart_type == 'Scatter Chart' else ''}'
                        }}
                    }},
                    y: {{
                        beginAtZero: {str(chart_type != 'Radar Chart').lower()},
                        min: {(y_min - 5) if chart_type == 'Scatter Chart' else 'null'},
                        max: {(y_max + 5) if chart_type == 'Scatter Chart' else 'null'},
                        title: {{
                            display: true,
                            text: '{y_column if chart_type == 'Scatter Chart' else y_axis_label}'
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

        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )
