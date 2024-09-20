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
    'cyberghost': 'rgba(255, 204, 0.8)',
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
    if isinstance(provider_name, str):
        provider_name = provider_name.lower()
        return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')
    return 'rgba(75, 192, 192, 0.8)'

# Function to preprocess and structure the chart data uniformly
def preprocess_chart_data(chart_data):
    formatted_data = []
    for provider, tests in chart_data['data'].items():
        row = {"VPN provider": provider}
        for test_name, value in tests.items():
            numeric_value = float(re.sub(r'[^\d.]+', '', value))
            row[test_name] = numeric_value
        formatted_data.append(row)

    df = pd.DataFrame(formatted_data)
    return df

# Function to load chart data from HTML and extract fields
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

        # Extract title and description
        seo_title = data.get("name", "VPN Speed Comparison")
        seo_description = data.get("description", "This chart compares VPN speeds.")

        # Extract chart dimensions
        chart_dimensions = re.search(r'width="(\d+)" height="(\d+)"', html_content)
        if chart_dimensions:
            width, height = chart_dimensions.groups()
            chart_width, chart_height = int(width), int(height)
        else:
            chart_width, chart_height = 805, 600

        # Set chart size
        chart_size = "Full Width" if chart_width == 805 else "Small" if chart_width == 405 else "Medium"

        return data, seo_title, seo_description, chart_width, chart_height, chart_size
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON data from HTML content: {e}")
        return None, None, None, None, None, None
    except ValueError as e:
        st.error(e)
        return None, None, None, None, None, None

# Function to generate a unique ID for the chart
def generate_unique_id(title):
    return title.replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:6]

# Function to generate ld+json metadata
def generate_metadata(seo_title, seo_description, source_data, label_column, value_columns, measurement_unit):
    data_dict = {provider: {col: f"{source_data.at[source_data[source_data[label_column] == provider].index[0], col]} {measurement_unit}".split(' ')[0] + ' ' + measurement_unit for col in value_columns} for provider in source_data[label_column]}
    return {
        "@context": "http://schema.org",
        "@type": "Dataset",
        "name": seo_title,
        "description": seo_description,
        "data": data_dict
    }

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

# Handle "Create New Chart" action
if action == "Create New Chart":
    uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
    if uploaded_file is not None:
        source_data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        source_data = st.data_editor(source_data)

# Handle "Update Existing Chart" action
elif action == "Update Existing Chart":
    chart_html = st.text_area("Paste the HTML content of the existing chart:")
    if chart_html:
        chart_data, seo_title, seo_description, chart_width, chart_height, chart_size = load_chart_data_from_html(chart_html)
        if chart_data:
            # Preprocess the chart data to ensure consistent structure
            source_data = preprocess_chart_data(chart_data)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data)

            # Offer an option to replace the dataset with new data
            replace_dataset = st.checkbox("Replace data with a new CSV upload?")
            if replace_dataset:
                uploaded_file = st.file_uploader("Upload new CSV file to replace existing data", type="csv")
                if uploaded_file is not None:
                    source_data = pd.read_csv(uploaded_file)
                    st.write("New Data Preview:")
                    source_data = st.data_editor(source_data)

# If source data is available, proceed to chart creation options
if source_data is not None:
    # SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title)
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description)

    # Select chart type
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart", "Radar Chart"])

    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        valid_columns = list(source_data.columns)
        default_columns = valid_columns[1:] if len(valid_columns) > 1 else valid_columns
        value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=default_columns, key='value_columns')

    # Chart settings
    y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)")
    measurement_unit = st.text_input("Enter the measurement unit:", measurement_unit)

    # Chart size options
    size_mapping = {
        "Full Width": (805, 600),
        "Medium": (605, 450),
        "Small": (405, 400)
    }
    chart_size = st.selectbox("Select the chart size:", ["Full Width", "Medium", "Small"], index=["Full Width", "Medium", "Small"].index(chart_size))
    chart_width, chart_height = size_mapping.get(chart_size, (805, 600))

    # Grouping method for grouped bar charts
    if chart_type == "Grouped Bar Chart":
        grouping_method = st.selectbox("Group by Provider or Test Type:", ["Provider", "Test Type"], key='grouping_method')

    # Display legend option
    display_legend = st.checkbox("Display legend", value=True)

    # Let the user select whether to include the 'Average' chart
    include_average = st.checkbox("Include 'Average' chart comparing all providers?", value=False)

    # HTML type selection - default to "Production"
    html_type = st.radio("HTML Type:", ["Standalone", "Production"], index=1)

    # Generate HTML button
    if st.button("Generate HTML"):
        datasets = []
        null_value = 0.05  # Represents an empty or invalid data point for tooltips

        if chart_type == "Scatter Chart":
            # For Scatter Chart
            labels = []
            unique_providers = source_data[label_column].unique()
            for provider in unique_providers:
                provider_data = source_data[source_data[label_column] == provider]
                x_values = provider_data[value_columns[0]].tolist()
                y_values = provider_data[value_columns[1]].tolist()
                data = [{'x': x, 'y': y} for x, y in zip(x_values, y_values)]
                background_colors = get_provider_color(provider)
                border_colors = background_colors
                datasets.append({'label': provider, 'data': data, 'backgroundColor': background_colors, 'borderColor': border_colors, 'borderWidth': 1})
        else:
            if grouping_method == "Provider":
                labels = list(value_columns)
                unique_providers = source_data[label_column].unique()
                for provider in unique_providers:
                    provider_data = source_data[source_data[label_column] == provider]
                    data = []
                    for col in value_columns:
                        value = provider_data[col].values[0]
                        if isinstance(value, (int, float)):
                            data.append(float(value))
                        elif isinstance(value, str) and value.strip() != '':
                            data.append(float(value))
                        else:
                            data.append(null_value)
                    background_colors = [get_provider_color(provider) if not pd.isna(provider_data[col].values[0]) else 'rgba(169, 169, 169, 0.8)' for col in value_columns]
                    border_colors = background_colors
                    datasets.append({'label': provider, 'data': data, 'backgroundColor': background_colors, 'borderColor': border_colors, 'borderWidth': 1})
            else:
                labels = source_data[label_column].tolist()
                color_index = 0
                for col in value_columns:
                    values = []
                    for value in source_data[col].tolist():
                        if isinstance(value, (int, float)):
                            values.append(float(value))
                        elif isinstance(value, str) and value.strip() != '':
                            values.append(float(value))
                        else:
                            values.append(null_value)
                    background_colors = [nice_colors[color_index % len(nice_colors)] if not pd.isna(value) else 'rgba(169, 169, 169, 0.8)' for value in values]
                    border_colors = background_colors
                    datasets.append({'label': col, 'data': values, 'backgroundColor': background_colors, 'borderColor': border_colors, 'borderWidth': 1})
                    color_index += 1

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
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '{y_axis_label}'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: {'true' if chart_type == 'Scatter Chart' else 'false'},
                            text: '{value_columns[0] if chart_type == 'Scatter Chart' else ''}'
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

        # Check if 'Average' chart is to be included
        if include_average:
            # Compute average values across providers
            average_row = pd.DataFrame(source_data[value_columns].mean().to_dict(), index=[0])
            average_row[label_column] = 'Average'

            # Prepare data for 'Average' chart
            if chart_type == "Scatter Chart":
                # For Scatter Chart, average of x and y values
                average_x = average_row[value_columns[0]].values[0]
                average_y = average_row[value_columns[1]].values[0]
                data_average = [{'x': average_x, 'y': average_y}]
                datasets_average = [{
                    'label': 'Average',
                    'data': data_average,
                    'backgroundColor': get_provider_color('Average'),
                    'borderColor': get_provider_color('Average'),
                    'borderWidth': 1
                }]
                labels_average = []
            else:
                average_values = average_row[value_columns].values.flatten().tolist()
                labels_average = value_columns
                datasets_average = [{
                    'label': 'Average',
                    'data': average_values,
                    'backgroundColor': [get_provider_color('Average') for _ in labels_average],
                    'borderColor': [get_provider_color('Average') for _ in labels_average],
                    'borderWidth': 1
                }]

            seo_title_average = f"Average {seo_title}"
            seo_title_average_escaped = json.dumps(seo_title_average)
            unique_id_safe_average = re.sub(r'[^a-zA-Z0-9_]', '_', generate_unique_id(seo_title_average))
            metadata_average = generate_metadata(seo_title_average, seo_description, average_row, label_column, value_columns, measurement_unit)

            # Generate HTML content for the 'Average' chart
            html_content_average = f"""
<div id="{unique_id_safe_average}" style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart_{unique_id_safe_average}" width="{chart_width}" height="{chart_height}"></canvas>
</div>
"""
            if html_type == "Standalone":
                html_content_average += f"""
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
"""

            html_content_average += f"""
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('vpnSpeedChart_{unique_id_safe_average}').getContext('2d');
        var vpnSpeedChart = new Chart(ctx, {{
            type: '{'radar' if chart_type == 'Radar Chart' else 'scatter' if chart_type == 'Scatter Chart' else 'bar'}',
            data: {{
                labels: {json.dumps(labels_average)},
                datasets: {json.dumps(datasets_average, default=str)}
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: {seo_title_average_escaped},
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
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '{y_axis_label}'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: {'true' if chart_type == 'Scatter Chart' else 'false'},
                            text: '{value_columns[0] if chart_type == 'Scatter Chart' else ''}'
                        }}
                    }}
                }}
            }}
        }});
    }});
</script>
<script type="application/ld+json">
{json.dumps(metadata_average, indent=4)}
</script>
"""
            # Combine the original html_content and the average chart
            full_html_content = html_content + html_content_average
        else:
            full_html_content = html_content

        # Provide download button for the combined HTML
        st.download_button(
            label="Download HTML",
            data=full_html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )

        # Provide download option for .txt format
        st.download_button(
            label="Download as .txt",
            data=full_html_content,
            file_name="vpn_speed_comparison.txt",
            mime="text/plain"
        )
