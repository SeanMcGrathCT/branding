import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import zipfile
import json
import uuid  # For generating unique IDs
import re

# Step 1: Set up Google Sheets access
credentials_info = st.secrets["gsheet_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize client
client = gspread.authorize(creds)

# Load the Google Sheet
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
sheet1 = client.open_by_url(sheet1_url)
consolidated_sheet = sheet1.worksheet('Consolidated')
consolidated_data = consolidated_sheet.get_all_values()

# Initialize a list to collect chart data
chart_js_files = []

# Function to make titles more natural
def make_title_natural(article_name):
    article_name = article_name.strip()
    if article_name.lower().startswith('how to'):
        # Remove 'How to' and make the rest more natural
        title = article_name[6:].capitalize()
        return f"for {title}"
    else:
        return article_name

# Function to extract data from consolidated sheet and generate charts
def process_consolidated_data():
    global chart_js_files
    overall_scores_data = {}
    speed_test_data_per_provider = {}
    article_title = ""

    for i, row in enumerate(consolidated_data):
        if row[0].lower().startswith('sheet:'):  # Capture the article name from the 'Sheet:' row
            article_title = make_title_natural(row[0].split(":")[1])
        elif row[0].lower() == 'url':  # Header row with the relevant columns
            headers_row = row
            provider_data = consolidated_data[i + 1:]
            break  # Exit after we have headers and provider rows

    if not article_title:
        st.write("No article title found.")
        return

    # Get list of overall score options
    overall_score_headers = [header for header in headers_row if 'overall score' in header.lower()]
    
    # UI: User selects overall score headers
    selected_overall_scores = st.multiselect('Select Overall Score categories for export:', overall_score_headers, default=overall_score_headers)

    # If 'Select All' is chosen, select all available overall score headers
    if st.checkbox('Select All Overall Scores'):
        selected_overall_scores = overall_score_headers

    # Process each provider row
    provider_names = []
    for row in provider_data:
        url = row[0].strip()
        provider_name = row[1].strip()
        if provider_name and url.startswith("http"):
            provider_names.append(provider_name)
            speed_test_data_per_provider[provider_name] = row

            # Collect overall score data for selected categories
            for header in selected_overall_scores:
                if header not in overall_scores_data:
                    overall_scores_data[header] = []
                try:
                    score = float(row[headers_row.index(header)]) if row[headers_row.index(header)] else 0
                except ValueError:
                    score = 0  # Default to 0 if the score cannot be converted to float
                overall_scores_data[header].append(score)

    # Generate Chart.js code for each overall score
    for score_type, scores in overall_scores_data.items():
        unique_id = str(uuid.uuid4().hex[:6])  # Generate unique ID for each chart
        chart_js = f"""
        <div id="overall_{score_type.lower().replace(':', '').replace(' ', '_')}_{unique_id}" style="max-width: 805px; margin: 0 auto;">
            <canvas class="jschartgraphic" id="vpnSpeedChart_overall_{score_type.lower().replace(':', '').replace(' ', '_')}_{unique_id}" width="805" height="600"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('vpnSpeedChart_overall_{score_type.lower().replace(':', '').replace(' ', '_')}_{unique_id}').getContext('2d');
                var vpnSpeedChart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(provider_names)},
                        datasets: [{{
                            label: 'VPN Providers {score_type}',
                            data: {json.dumps(scores)},
                            backgroundColor: {json.dumps(['rgba(62, 95, 255, 0.8)'] * len(provider_names))},
                            borderColor: {json.dumps(['rgba(31, 47, 127, 0.8)'] * len(provider_names))},
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            title: {{
                                display: true,
                                text: "Overall {score_type} {article_title}",
                                font: {{
                                    size: 18
                                }}
                            }},
                            legend: {{
                                display: true
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return context.dataset.label + ': ' + context.raw + ' Score out of 10';
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Score out of 10'
                                }}
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": "Overall {score_type} {article_title}",
            "description": "This chart shows the {score_type} for VPN providers {article_title}.",
            "data": {{
                {', '.join([f'"{provider_name}": {{"{score_type}": "{scores[i]} out of 10"}}' for i, provider_name in enumerate(provider_names)])}
            }}
        }}
        </script>
        """
        chart_js_files.append((f"overall_{score_type.lower().replace(' ', '_')}_chart.txt", chart_js))

    # Provider-level speed test data generation
    for provider_name, row in speed_test_data_per_provider.items():
        unique_id = str(uuid.uuid4().hex[:6])
        speed_columns = [header for header in headers_row if 'speed test' in header.lower()]
        provider_speed_data = [float(row[headers_row.index(col)]) if row[headers_row.index(col)] else 0 for col in speed_columns]

        chart_js = f"""
        <div id="{provider_name.lower().replace(' ', '_')}_speed_chart_{unique_id}" style="max-width: 405px; margin: 0 auto;">
            <canvas class="jschartgraphic" id="vpnSpeedChart_{provider_name.lower().replace(' ', '_')}_speed_{unique_id}" width="405" height="400"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('vpnSpeedChart_{provider_name.lower().replace(' ', '_')}_speed_{unique_id}').getContext('2d');
                var vpnSpeedChart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(speed_columns)},
                        datasets: [{{
                            label: '{provider_name} Speed Test (Mbps)',
                            data: {json.dumps(provider_speed_data)},
                            backgroundColor: ['rgba(62, 95, 255, 0.8)'],
                            borderColor: 'rgba(62, 95, 255, 0.8)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            title: {{
                                display: true,
                                text: "{provider_name} Speed Tests {article_title}",
                                font: {{
                                    size: 18
                                }}
                            }},
                            legend: {{
                                display: true
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return context.dataset.label + ': ' + context.raw + ' Mbps';
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Mbps'
                                }}
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": "{provider_name} Speed Tests {article_title}",
            "description": "This chart shows the speed test results for {provider_name} when used {article_title}.",
            "data": {{
                {', '.join([f'"{col}": "{provider_speed_data[i]} Mbps"' for i, col in enumerate(speed_columns)])}
            }}
        }}
        </script>
        """
        chart_js_files.append((f"{provider_name.lower().replace(' ', '_')}_speed_chart.txt", chart_js))


    # Step 2: Provide download button for the zip file
    if chart_js_files:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in chart_js_files:
                zf.writestr(filename, content)

        # Provide download button
        st.download_button(
            label="Download Chart.js Files as ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"vpn_speed_tests_{uuid.uuid4().hex[:6]}.zip",
            mime="application/zip"
        )

# Run the function to process the consolidated data and generate the charts
process_consolidated_data()
