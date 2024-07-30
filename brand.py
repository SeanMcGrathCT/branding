import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import uuid
import random
import string

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
    provider_name = provider_name.lower()
    return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')

# Function to generate a unique ID
def generate_unique_id(title):
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"{title.replace(' ', '_')}_{random_str}"

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_credentials = dict(st.secrets["FIREBASE_CREDENTIALS"])
    # Convert the string private key into the required format
    firebase_credentials['private_key'] = firebase_credentials['private_key'].replace('\\n', '\n')
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred, {
        'storageBucket': f"{firebase_credentials['project_id']}.appspot.com"
    })

def upload_to_firebase_storage(file_path, bucket, destination_blob_name):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    return blob.public_url

def load_chart_data_from_html(html_content):
    try:
        # Locate the start and end of the JSON data within the script
        start_marker = '<script type="application/ld+json">'
        end_marker = '</script>'
        
        start = html_content.find(start_marker)
        end = html_content.find(end_marker, start)

        if start == -1 or end == -1:
            raise ValueError("Could not find the JSON data section in the provided HTML content.")
        
        # Extract and clean the JSON data
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
empty_bar_text = "No data available"
chart_size = "Full Width"
chart_width = 805
chart_height = 600
grouping_method = "Provider"
display_legend = True
source_data = None
chart_type = "Single Bar Chart"  # Default value

if action == "Create New Chart":
    # Upload CSV file
    uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
    if uploaded_file is not None:
        source_data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        source_data.columns = ["VPN provider"] + source_data.columns.tolist()[1:]
        source_data = st.data_editor(source_data)

elif action == "Update Existing Chart":
    chart_html = st.text_area("Paste the HTML content of the existing chart:")
    if chart_html:
        chart_data = load_chart_data_from_html(chart_html)
        if chart_data:
            datasets = [{"label": k, "data": v} for k, v in chart_data["data"].items()]
            seo_title = chart_data.get("name", "")
            seo_description = chart_data.get("description", "")
            measurement_unit = "Mbps"  # Assuming the unit is always Mbps
            empty_bar_text = "No data available"
            display_legend = True
            grouping_method = "Provider"
            chart_size = "Full Width"
            chart_width = 805
            chart_height = 600
            
            # Determine chart type based on data structure
            if datasets and isinstance(datasets[0]["data"], dict):
                first_dataset = datasets[0]["data"]
                if 'x' in first_dataset and 'y' in first_dataset:
                    chart_type = "Scatter Chart"
                    label_column = "VPN provider"
                    x_column = list(first_dataset.keys())[0]
                    y_column = list(first_dataset.keys())[1]
                    data_dict = {label_column: [], x_column: [], y_column: []}
                    for dataset in datasets:
                        for x, y in zip(dataset["data"][x_column], dataset["data"][y_column]):
                            data_dict[label_column].append(dataset["label"])
                            data_dict[x_column].append(x)
                            data_dict[y_column].append(y)
                    source_data = pd.DataFrame(data_dict)
                else:
                    chart_type = "Grouped Bar Chart"
                    label_column = "VPN provider"
                    value_columns = list(first_dataset.keys())
                    data_dict = {label_column: list(first_dataset.keys())}
                    for dataset in datasets:
                        data_dict[dataset["label"]] = list(dataset["data"].values())
                    source_data = pd.DataFrame(data_dict).transpose()
                    source_data.columns = source_data.iloc[0]
                    source_data = source_data.drop(source_data.index[0])
                    source_data.reset_index(inplace=True)
                    source_data.rename(columns={'index': 'VPN provider'}, inplace=True)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data)

if source_data is not None:
    # Select the type of chart
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart"], index=["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart"].index(chart_type))

    # Select the columns for the chart
    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        # Ensure the default value columns are valid columns in the dataframe
        valid_columns = list(source_data.columns)
        default_columns = valid_columns[1:] if len(valid_columns) > 1 else valid_columns
        if chart_type == "Scatter Chart":
            x_column = st.selectbox("Select the column for X-axis values:", valid_columns, key='x_column')
            y_column = st.selectbox("Select the column for Y-axis values:", valid_columns, key='y_column')
        else:
            value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=default_columns, key='value_columns')

    # Input SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title)
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description)

    if chart_type != "Scatter Chart":
        # Input Y axis label
        y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)")

        # Input text for empty bars
        empty_bar_text = st.text_input("Enter text for empty bars (e.g., 'No servers in Egypt'):", empty_bar_text)

        # Select grouping method
        grouping_method = st.selectbox("Group data by:", ["Provider", "Test Type"])

    # Select chart size
    chart_size = st.selectbox("Select the chart size:", ["Small", "Full Width"])
    if chart_size == "Small":
        chart_width = 500
        chart_height = 300
    else:
        chart_width = 805
        chart_height = 600

    # Select whether to display the legend
    display_legend = st.checkbox("Display legend", value=display_legend)

    if st.button("Generate HTML"):
        datasets = []
        null_value = 0.05  # Small fixed value for null entries
        if chart_type == "Scatter Chart":
            labels = []
            x_values = []
            y_values = []
            for provider in source_data[label_column].unique():
                provider_data = source_data[source_data[label_column] == provider]
                try:
                    x_val = provider_data[x_column].values[0]
                    y_val = provider_data[y_column].values[0]
                    if isinstance(x_val, list):
                        x_val = x_val[0]
                    if isinstance(y_val, list):
                        y_val = y_val[0]
                    x_val = float(str(x_val))
                    y_val = float(str(y_val))
                    x_values.append(x_val)
                    y_values.append(y_val)
                except ValueError as e:
                    st.error(f"Error converting values to float for provider '{provider}': {e}")
                    continue
                except KeyError as e:
                    st.error(f"Missing data for provider '{provider}': {e}")
                    continue
                except IndexError as e:
                    st.error(f"List index error for provider '{provider}': {e}")
                    continue
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
            if x_values and y_values:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)
            else:
                x_min, x_max = 0, 0
                y_min, y_max = 0, 0
        elif grouping_method == "Provider":
            labels = list(value_columns)
            unique_providers = source_data[label_column].unique()
            for provider in unique_providers:
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    float(provider_data[col].values[0].split(' ')[0]) if isinstance(provider_data[col].values[0], str) else provider_data[col].values[0]
                    for col in value_columns
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
        else:  # Group by Test Type
            labels = source_data[label_column].tolist()
            for i, col in enumerate(value_columns):
                values = [
                    float(value.split(' ')[0]) if isinstance(value, str) and ' ' in value else value
                    for value in source_data[col].tolist()
                ]
                background_colors = [
                    get_provider_color(source_data[label_column][j]) if not pd.isna(value) else 'rgba(169, 169, 169, 0.8)'
                    for j, value in enumerate(values)
                ]
                border_colors = background_colors
                datasets.append({
                    'label': col,
                    'data': values,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })

        # Generate ld+json metadata
        if chart_type == "Scatter Chart":
            data_dict = {provider: {x_column: provider_data[x_column].tolist(), y_column: provider_data[y_column].tolist()} for provider, provider_data in source_data.groupby(label_column)}
        else:
            data_dict = {provider: {col: f"{source_data.at[source_data[source_data[label_column] == provider].index[0], col]} {measurement_unit}".split(' ')[0] + ' ' + measurement_unit for col in value_columns} for provider in source_data[label_column]}
        
        metadata = {
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": seo_title,
            "description": seo_description,
            "data": data_dict
        }

        # Generate the HTML content for insertion
        unique_id = generate_unique_id(seo_title)
        html_content = f"""
<div id="{unique_id}" style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart_{unique_id}" width="{chart_width}" height="{chart_height}"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('vpnSpeedChart_{unique_id}').getContext('2d');
        
        var vpnSpeedChart = new Chart(ctx, {{
            type: '{'scatter' if chart_type == 'Scatter Chart' else 'bar'}',
            data: {{
                labels: {json.dumps(labels)},
                datasets: {json.dumps(datasets, default=str)}
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: '{seo_title}',
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
                                if ('x' in context.raw && 'y' in context.raw) {{
                                    return context.dataset.label + ': (' + context.raw.x + ', ' + context.raw.y + ')';
                                }}
                                return context.dataset.label + ': ' + context.raw + ' {measurement_unit}';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: false,
                        min: {x_min - 1},
                        max: {x_max + 1},
                        title: {{
                            display: true,
                            text: '{x_column if chart_type == 'Scatter Chart' else ''}'
                        }}
                    }},
                    y: {{
                        beginAtZero: false,
                        min: {y_min - 5},
                        max: {y_max + 5},
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

        # Save the HTML content to a file
        html_file_path = f"{unique_id}.html"
        with open(html_file_path, "w") as html_file:
            html_file.write(html_content)

        # Upload the file to Firebase Storage
        bucket = storage.bucket()
        public_url = upload_to_firebase_storage(html_file_path, bucket, f"charts/{unique_id}.html")

        # Log the upload to Google Sheets
        google_credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets["GCP_SERVICE_ACCOUNT"])
        )
        service = build('sheets', 'v4', credentials=google_credentials)
        sheet = service.spreadsheets()

        # Prepare the data to be logged
        log_data = [
            unique_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            seo_title,
            seo_description,
            public_url
        ]

        # Append the data to the Google Sheets
        sheet.values().append(
            spreadsheetId="1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q",
            range="charts!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": [log_data]}
        ).execute()

        # Display download button for the HTML content
        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )

        # Provide the public URL of the uploaded chart
        st.write(f"Chart has been uploaded to Firebase. [View Chart]({public_url})")
