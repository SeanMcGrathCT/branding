import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import zipfile
import json
from fuzzywuzzy import fuzz, process
import logging

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

# Initialize a batch for updates
chart_js_files = []

# Function to match headers with fuzzy matching
def match_headers_with_scores(headers_row, target_keyword):
    # Strip ': overall score' from headers for comparison
    headers_to_match = [header.replace(": overall score", "").strip().lower() for header in headers_row]

    # Fuzzy match with an adjustable threshold
    best_match, best_score = process.extractOne(target_keyword.lower(), headers_to_match, scorer=fuzz.ratio)

    if best_score >= 70:  # Set a matching threshold
        return headers_row[headers_to_match.index(best_match)]  # Return the exact header from headers_row
    else:
        return None

# Step 2: Prompt the user for a URL
st.write("Enter the URL to find the corresponding VPN data:")
input_url = st.text_input("URL", "")

# Function to process the consolidated sheet and map scores
def process_consolidated_data():
    global chart_js_files
    provider_names = []
    overall_scores_data = {"streaming ability": [], "security & privacy": [], "overall score": []}
    speed_test_data_per_provider = {}

    for i, row in enumerate(consolidated_data):
        if row[0].lower() == 'url':  # Check if the row is a header row starting with 'URL'
            headers_row = row
            st.write(f"Found header row at index {i}: {headers_row}")

            # Process each provider row after the header row
            providers_data = consolidated_data[i + 1:]  # Get the rows following the header row

            # Process each provider row
            for provider_row in providers_data:
                # Skip empty rows or rows without URLs or VPN Provider
                if not provider_row or not provider_row[0].startswith("http") or not provider_row[1]:
                    continue  # Skip rows that aren't valid

                url = provider_row[0]
                provider_name = provider_row[1].strip()

                if url == input_url:
                    provider_names.append(provider_name)

                    # Fuzzy match columns related to speed tests
                    speed_test_columns = ["am", "noon", "pm"]
                    matched_speed_columns = [match_headers_with_scores(headers_row, col) for col in speed_test_columns]
                    matched_speed_columns = [col for col in matched_speed_columns if col]  # Filter out None

                    st.write(f"Matched Speed Test Columns: {matched_speed_columns}")

                    # Extract speed test data for the provider
                    provider_speed_data = []
                    for col in matched_speed_columns:
                        try:
                            score = provider_row[headers_row.index(col)]
                            provider_speed_data.append(float(score))  # Convert to float for chart data
                        except (ValueError, IndexError):
                            provider_speed_data.append(0)  # If there's an error, default to 0

                    speed_test_data_per_provider[provider_name] = provider_speed_data

                    # Process overall score columns
                    overall_score_columns = ["overall score", "streaming ability", "security & privacy"]
                    matched_overall_columns = [match_headers_with_scores(headers_row, col) for col in overall_score_columns]
                    matched_overall_columns = [col for col in matched_overall_columns if col]  # Filter out None

                    st.write(f"Matched Overall Score Columns: {matched_overall_columns}")

                    # Extract overall score data for the provider
                    for idx, col in enumerate(overall_score_columns):
                        if idx < len(matched_overall_columns) and matched_overall_columns[idx]:
                            try:
                                score = provider_row[headers_row.index(matched_overall_columns[idx])]
                                overall_scores_data[col].append(float(score))  # Convert to float
                            except (ValueError, IndexError):
                                overall_scores_data[col].append(0)

    # Generate a single Chart.js for each overall score category for all providers
    for score_type, scores in overall_scores_data.items():
        overall_score_chart_js = f"""
        <div style="max-width: 805px; margin: 0 auto;">
            <canvas id="{score_type}_Chart" width="805" height="600"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('{score_type}_Chart').getContext('2d');
                var {score_type}_Chart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(provider_names)},
                        datasets: [{{
                            label: 'VPN Providers {score_type.capitalize()}',
                            data: {json.dumps(scores)},
                            backgroundColor: {json.dumps(['rgba(62, 95, 255, 0.8)'] * len(provider_names))},
                            borderColor: {json.dumps(['rgba(31, 47, 127, 0.8)'] * len(provider_names))},
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
                                text: 'VPN Providers {score_type.capitalize()}'
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        """
        chart_js_files.append((f"{score_type}_chart.txt", overall_score_chart_js))

    # Generate individual speed charts per provider
    for provider_name, speed_data in speed_test_data_per_provider.items():
        speed_test_chart_js = f"""
        <div style="max-width: 500px; margin: 0 auto;">
            <canvas id="{provider_name}_SpeedChart" width="500" height="300"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('{provider_name}_SpeedChart').getContext('2d');
                var {provider_name}_SpeedChart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(speed_test_columns)},
                        datasets: [{{
                            label: '{provider_name} Speed Test (Mbps)',
                            data: {json.dumps(speed_data)},
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
                                text: '{provider_name} Speed Test (Mbps)'
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        """
        chart_js_files.append((f"{provider_name}_speed_chart.txt", speed_test_chart_js))

# Run the data processing
process_consolidated_data()

# Step 3: Provide download button for the zip file
if chart_js_files:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for filename, content in chart_js_files:
            zf.writestr(filename, content)

    # Provide download button
    st.download_button(
        label="Download Chart.js Files as ZIP",
        data=zip_buffer.getvalue(),
        file_name=f"{input_url.split('/')[-1]}_charts.zip",
        mime="application/zip"
    )
