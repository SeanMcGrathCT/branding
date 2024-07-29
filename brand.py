import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
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
    provider_name = provider_name.lower()
    return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')

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
action = st.radio("Choose an action:", ["Create New Chart", "Update Existing Chart"])

# Initialize variables for form fields
seo_title = ""
seo_description = ""
label_column = ""
value_columns = []
measurement_unit = "Mbps"
y_axis_label = "Speed (Mbps)"
empty_bar_text = "No data available"
chart_size = "Full Width"
chart_width = 805
chart_height = 600
grouping_method = "Provider"
display_legend = True
source_data = None

if action == "Create New Chart":
    # Upload CSV file
    uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
    if uploaded_file is not None:
        source_data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        st.dataframe(source_data)
elif action == "Update Existing Chart":
    chart_html = st.text_area("Paste the HTML content of the existing chart:")
    if chart_html:
        chart_data = load_chart_data_from_html(chart_html)
        if chart_data:
            labels = list(chart_data["data"].values())[0].keys()
            datasets = [{"label": k, "data": list(v.values())} for k, v in chart_data["data"].items()]
            seo_title = chart_data.get("name", "")
            seo_description = chart_data.get("description", "")
            # Reconstruct the source_data dataframe from the datasets
            label_column = "Provider"
            data_dict = {label_column: labels}
            for dataset in datasets:
                data_dict[dataset["label"]] = dataset["data"]
            source_data = pd.DataFrame(data_dict)
            st.write("Data Preview:")
            st.dataframe(source_data)

if source_data is not None:
    # Select the type of chart
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart"])

    # Select the columns for the chart
    label_column = st.selectbox("Select the column for VPN providers:", source_data.columns)
    value_columns = st.multiselect("Select the columns for tests:", source_data.columns)
    mapped_columns = {col: col for col in value_columns}

    # Input measurement unit
    measurement_unit = st.text_input("Enter the unit of measurement (e.g., Mbps):", measurement_unit)

    # Input SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title)
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description)

    # Input Y axis label
    y_axis_label = st.text_input("Enter the Y axis label:", y_axis_label)

    # Input text for empty bars
    empty_bar_text = st.text_input("Enter text for empty bars (e.g., 'No servers in Egypt'):", empty_bar_text)

    # Select chart size
    chart_size = st.selectbox("Select the chart size:", ["Small", "Full Width"])
    if chart_size == "Small":
        chart_width = 500
        chart_height = 300
    else:
        chart_width = 805
        chart_height = 600

    # Select grouping method
    grouping_method = st.selectbox("Group data by:", ["Provider", "Test Type"])

    # Select whether to display the legend
    display_legend = st.checkbox("Display legend", value=display_legend)

    if st.button("Generate HTML"):
        datasets = []
        null_value = 0.05  # Small fixed value for null entries
        if grouping_method == "Provider":
            labels = list(mapped_columns.keys())
            unique_providers = source_data[label_column].unique()
            for provider in unique_providers:
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    provider_data[col].values[0] if not pd.isna(provider_data[col].values[0]) else null_value
                    for col in mapped_columns.values()
                ]
                background_colors = [
                    get_provider_color(provider) if not pd.isna(provider_data[col].values[0]) else 'rgba(169, 169, 169, 0.8)'
                    for col in mapped_columns.values()
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
            for i, col in enumerate(mapped_columns.values()):
                values = [
                    value if not pd.isna(value) else null_value
                    for value in source_data[col].tolist()
                ]
                background_colors = [
                    nice_colors[i % len(nice_colors)] if not pd.isna(value) else 'rgba(169, 169, 169, 0.8)'
                    for value in values
                ]
                border_colors = [
                    nice_colors[i % len(nice_colors)] if not pd.isna(value) else 'rgba(169, 169, 169, 0.8)'
                    for value in values
                ]
                datasets.append({
                    'label': col,
                    'data': values,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })

        # Generate ld+json metadata
        metadata = {
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": seo_title,
            "description": seo_description,
            "data": {provider: {col: f"{source_data.loc[source_data[label_column] == provider, col].values[0]} {measurement_unit}" for col in mapped_columns.values()} for provider in source_data[label_column].unique()}
        }

        # Generate the HTML content for insertion
        unique_id = str(uuid.uuid4())
        html_content = f"""
<div id="{unique_id}" style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart" width="{chart_width}" height="{chart_height}"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('vpnSpeedChart').getContext('2d');
        
        var vpnSpeedChart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: {json.dumps(datasets)}
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

# Ensure to include logging for each step
st.write("Log:")
