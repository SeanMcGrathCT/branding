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

# Initialize a list to collect chart data
chart_js_files = []

# Step 2: Prompt the user for a URL
st.write("Enter the URL to find the corresponding VPN data:")
input_url = st.text_input("URL", "")

def process_consolidated_data(input_url):
    global chart_js_files

    if not input_url:
        st.write("Please enter a URL to search for.")
        return  # Exit the function if no URL is entered

    provider_names = []  # List to hold unique provider names
    overall_scores_data = {}
    processed_providers = set()  # To avoid duplicates
    speed_test_data_per_provider = {}

    i = 0
    while i < len(consolidated_data):
        row = consolidated_data[i]
        # Check if the row is a header row starting with 'URL'
        if row and row[0] and row[0].strip().lower() == 'url':
            headers_row = row
            st.write(f"Found header row at index {i}: {headers_row}")
            i += 1  # Move to the next row after the header

            # Process the data rows until the next header or end of data
            while i < len(consolidated_data):
                provider_row = consolidated_data[i]
                # Check if we've reached the next header row
                if provider_row and provider_row[0] and provider_row[0].strip().lower() == 'url':
                    break  # Next header row found, break to process the new dataset

                # Skip empty rows or rows without URLs or VPN Provider
                if not provider_row or len(provider_row) < 2 or not provider_row[0] or not provider_row[1]:
                    i += 1
                    continue

                url = provider_row[0].strip()
                provider_name = provider_row[1].strip()

                # Only process the rows where the URL matches the input
                if input_url.strip() != url.strip():
                    i += 1
                    continue  # Skip rows where the URL doesn't match the user input

                # Use a combination of URL and provider name to ensure uniqueness across datasets
                unique_provider_key = f"{url}_{provider_name}"
                if unique_provider_key not in processed_providers:
                    processed_providers.add(unique_provider_key)
                    provider_names.append(provider_name)  # Add provider name once

                    # Collect all columns that contain 'speed test'
                    matched_speed_columns = [header for header in headers_row if header and 'speed test' in header.lower()]
                    st.write(f"Matched Speed Test Columns: {matched_speed_columns}")

                    # Extract speed test data for the provider
                    provider_speed_data = []
                    for col in matched_speed_columns:
                        try:
                            col_index = headers_row.index(col)
                            score = provider_row[col_index]
                            if score:
                                provider_speed_data.append(float(score))  # Convert to float for chart data
                            else:
                                provider_speed_data.append(0)
                        except (ValueError, IndexError):
                            provider_speed_data.append(0)  # If there's an error, default to 0

                    speed_test_data_per_provider[provider_name] = (matched_speed_columns, provider_speed_data)

                    # Collect all columns that contain 'overall score' in the header
                    matched_overall_columns = [header for header in headers_row if header and 'overall score' in header.lower()]
                    st.write(f"Matched Overall Score Columns: {matched_overall_columns}")

                    # Initialize overall_scores_data for new columns
                    for header in matched_overall_columns:
                        if header not in overall_scores_data:
                            overall_scores_data[header] = []

                    # Extract overall score data for the provider
                    for col in matched_overall_columns:
                        try:
                            col_index = headers_row.index(col)
                            score = provider_row[col_index]
                            if score:
                                overall_scores_data[col].append(float(score))  # Convert to float
                            else:
                                overall_scores_data[col].append(0)
                        except (ValueError, IndexError):
                            overall_scores_data[col].append(0)  # Handle errors by adding a default value
                else:
                    # Provider already processed
                    pass

                i += 1  # Move to next provider row
            # End of current dataset
            continue  # Go back to look for the next header row
        else:
            i += 1  # Move to next row

    if not provider_names:
        st.write("No data found for the given URL.")
        return

    # Generate charts for overall scores
    for score_type, scores in overall_scores_data.items():
        overall_score_chart_js = f"""
        <div style="max-width: 805px; margin: 0 auto;">
            <canvas id="{score_type}_Chart" width="805" height="600"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('{score_type}_Chart').getContext('2d');
                var chart = new Chart(ctx, {{
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
                                text: 'VPN Providers {score_type}'
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        """
        chart_js_files.append((f"{score_type}_chart.txt", overall_score_chart_js))

    # Generate individual speed charts per provider
    for provider_name, (speed_test_columns, speed_data) in speed_test_data_per_provider.items():
        speed_test_chart_js = f"""
        <div style="max-width: 500px; margin: 0 auto;">
            <canvas id="{provider_name}_SpeedChart" width="500" height="300"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('{provider_name}_SpeedChart').getContext('2d');
                var chart = new Chart(ctx, {{
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
process_consolidated_data(input_url)

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
