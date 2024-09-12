import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import zipfile
import json

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

# Convert the sheet data to a DataFrame
columns = consolidated_data[0]  # Header row
rows = consolidated_data[1:]  # Data rows
sheet_data = pd.DataFrame(rows, columns=columns)

# Clean column names (handle empty or duplicate columns)
def clean_column_names(columns):
    clean_columns = []
    seen = set()
    for i, col in enumerate(columns):
        if col == '' or col in seen:
            col = f"Column_{i+1}"  # Assign unique placeholder names to empty or duplicate columns
        clean_columns.append(col)
        seen.add(col)
    return clean_columns

sheet_data.columns = clean_column_names(sheet_data.columns)

# Step 2: Prompt the user for a URL
st.write("Enter the URL to find the corresponding VPN data:")
input_url = st.text_input("URL", "")

# Step 3: Search for the URL in the dataset
if input_url:
    matching_rows = sheet_data[sheet_data[sheet_data.columns[0]] == input_url]

    if not matching_rows.empty:
        st.write(f"Data found for URL: {input_url}")
        
        # Extract VPN provider and test results
        vpn_column = matching_rows[sheet_data.columns[1]].values[0]
        st.write(f"VPN Provider: {vpn_column}")
        
        # Step 4: Find speed test and overall score columns
        speed_test_columns = [col for col in sheet_data.columns if 'Speed test' in col]
        overall_score_columns = [col for col in sheet_data.columns if 'Overall Score' in col]

        # Extract speed test data
        speed_test_data = matching_rows[speed_test_columns].astype(float)
        overall_score_data = matching_rows[overall_score_columns].astype(float)

        # Generate Chart.js code for speed tests
        def generate_chart_js(chart_id, labels, dataset, title, ylabel):
            chart_js = f"""
            <div style="max-width: 500px; margin: 0 auto;">
                <canvas id="{chart_id}" width="500" height="300"></canvas>
            </div>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    var ctx = document.getElementById('{chart_id}').getContext('2d');
                    var {chart_id} = new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(labels)},
                            datasets: [{{
                                label: '{title}',
                                data: {json.dumps(dataset)},
                                backgroundColor: 'rgba(62, 95, 255, 0.8)',
                                borderColor: 'rgba(62, 95, 255, 0.8)',
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    title: {{
                                        display: true,
                                        text: '{ylabel}'
                                    }}
                                }}
                            }},
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: '{title}'
                                }}
                            }}
                        }}
                    }});
                }});
            </script>
            """
            return chart_js

        # Generate Chart.js code for speed test
        speed_test_labels = speed_test_columns
        speed_test_dataset = speed_test_data.values.flatten().tolist()
        speed_test_chart_js = generate_chart_js(f"{vpn_column}_SpeedChart", speed_test_labels, speed_test_dataset, f"{vpn_column} Speed Test (Mbps)", "Speed (Mbps)")

        # Generate Chart.js code for overall scores
        overall_score_labels = overall_score_columns
        overall_score_dataset = overall_score_data.values.flatten().tolist()
        overall_score_chart_js = generate_chart_js(f"{vpn_column}_OverallScoreChart", overall_score_labels, overall_score_dataset, f"{vpn_column} Overall Scores", "Score")

        # Step 5: Save the generated Chart.js code as .txt files and zip them
        chart_js_files = [
            (f"{vpn_column}_speed_chart.txt", speed_test_chart_js),
            (f"{vpn_column}_overall_score_chart.txt", overall_score_chart_js)
        ]

        # Create a zip file of the .txt files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for filename, content in chart_js_files:
                zf.writestr(filename, content)

        # Step 6: Provide download button for the zip file
        st.download_button(
            label="Download Chart.js Files as ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"{vpn_column}_charts.zip",
            mime="application/zip"
        )

    else:
        st.write(f"No data found for URL: {input_url}")
