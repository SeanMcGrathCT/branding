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
        
        # Step 4: Extract speed test data for each VPN provider
        vpn_column = sheet_data.columns[1]  # VPN provider column
        providers = matching_rows[vpn_column].unique()  # Unique VPN providers for the given URL

        # Define the columns for the speed tests (am, noon, pm)
        speed_test_columns = ["am", "noon", "pm"]

        # Define the columns for overall scores
        overall_score_columns = ["Streaming Ability: Overall Score", "UK Speed: Overall Score"]

        # List to store Chart.js code
        chart_js_files = []

        # Generate individual speed test charts for each provider
        for provider in providers:
            provider_data = matching_rows[matching_rows[vpn_column] == provider]

            # Get the speed test data for the provider
            speed_test_data = provider_data[speed_test_columns].astype(float).values.flatten().tolist()

            # Generate Chart.js code for the provider's speed test
            speed_test_chart_js = f"""
            <div style="max-width: 500px; margin: 0 auto;">
                <canvas id="{provider}_SpeedChart" width="500" height="300"></canvas>
            </div>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    var ctx = document.getElementById('{provider}_SpeedChart').getContext('2d');
                    var {provider}_SpeedChart = new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: ['a.m.', 'noon', 'p.m.'],
                            datasets: [{{
                                label: '{provider} Speed Test (Mbps)',
                                data: {json.dumps(speed_test_data)},
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
                                        text: 'Speed (Mbps)'
                                    }}
                                }}
                            }},
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: '{provider} Speed Test (Mbps)'
                                }}
                            }}
                        }}
                    }});
                }});
            </script>
            """
            # Add the Chart.js code for the provider's speed test to the list
            chart_js_files.append((f"{provider}_speed_chart.txt", speed_test_chart_js))

        # Generate comparison charts for overall scores across all providers
        for score_col in overall_score_columns:
            score_data = matching_rows[[vpn_column, score_col]].dropna()

            # Generate the comparison chart for the score category
            overall_score_chart_js = f"""
            <div style="max-width: 805px; margin: 0 auto;">
                <canvas id="{score_col.replace(' ', '_')}_OverallScoreChart" width="805" height="600"></canvas>
            </div>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    var ctx = document.getElementById('{score_col.replace(' ', '_')}_OverallScoreChart').getContext('2d');
                    var {score_col.replace(' ', '_')}_OverallScoreChart = new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(score_data[vpn_column].tolist())},
                            datasets: [{{
                                label: '{score_col}',
                                data: {json.dumps(score_data[score_col].astype(float).tolist())},
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
                                        text: 'Score'
                                    }}
                                }}
                            }},
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: '{score_col}'
                                }}
                            }}
                        }}
                    }});
                }});
            </script>
            """
            # Add the Chart.js code for the comparison chart to the list
            chart_js_files.append((f"{score_col.replace(' ', '_')}_overall_score_chart.txt", overall_score_chart_js))

        # Step 5: Save the generated Chart.js code as .txt files and zip them
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for filename, content in chart_js_files:
                zf.writestr(filename, content)

        # Step 6: Provide download button for the zip file
        st.download_button(
            label="Download Chart.js Files as ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"{input_url.split('/')[-1]}_charts.zip",
            mime="application/zip"
        )

    else:
        st.write(f"No data found for URL: {input_url}")
