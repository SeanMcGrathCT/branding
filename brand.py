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

# Define default colors for test types
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

# Function to preprocess and structure the chart data uniformly
def preprocess_chart_data(chart_data):
    st.write("Preprocessing chart data...")
    formatted_data = []
    
    # Iterate over each provider in the chart data
    for provider, tests in chart_data['data'].items():
        row = {"VPN provider": provider}
        row.update(tests)
        formatted_data.append(row)
    
    # Create a dataframe with the structured data
    df = pd.DataFrame(formatted_data)
    st.write("Preprocessed Data:")
    st.write(df)
    return df

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
null_value = 0.05  # Fix: Define null_value to handle empty data points
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
            # Preprocess the chart data to ensure consistent structure
            source_data = preprocess_chart_data(chart_data)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data)

if source_data is not None:
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart", "Radar Chart"])
    
    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        valid_columns = list(source_data.columns)
        default_columns = valid_columns[1:] if len(valid_columns) > 1 else valid_columns
        
        value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=default_columns, key='value_columns')

    seo_title = st.text_input("Enter the SEO title for the chart:", "VPN Speed Comparison")
    seo_description = st.text_area("Enter the SEO description for the chart:", "This chart compares VPN speeds.")

    y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)")
    measurement_unit = st.text_input("Enter the measurement unit:", "Mbps")
    chart_size = st.selectbox("Select the chart size:", ["Full Width", "Medium", "Small"])

    if chart_type == "Grouped Bar Chart":
        grouping_method = st.selectbox("Group by Provider or Test Type:", ["Provider", "Test Type"], key='grouping_method')

    display_legend = st.checkbox("Display legend", value=True)

    # Add this to define `html_type`
    html_type = st.radio("HTML Type:", ["Standalone", "Production"], index=0)

    if st.button("Generate HTML"):
        datasets = []
        labels = list(value_columns)
        unique_providers = source_data[label_column].unique()
        color_index = 0
        
        for provider in unique_providers:
            provider_data = source_data[source_data[label_column] == provider]
            data = [float(provider_data[col].values[0]) for col in value_columns]
            background_colors = [get_provider_color(provider)] * len(value_columns)
            border_colors = background_colors
            datasets.append({
                'label': provider,
                'data': data,
                'backgroundColor': background_colors,
                'borderColor': border_colors,
                'borderWidth': 1
            })

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
                                return context.dataset.label + ': ' + context.raw + ' {measurement_unit}';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: ''
                        }}
                    }},
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

        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )
