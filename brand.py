import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import zipfile
import json
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

if input_url:
    # Process the data to collect headers and provider names
    provider_names = []
    overall_scores_data = {}
    processed_providers = set()
    speed_test_data_per_provider = {}
    matching_headers = set()
    i = 0
    while i < len(consolidated_data):
        row = consolidated_data[i]
        # Check if the row is a header row starting with 'URL'
        if row and row[0] and row[0].strip().lower() == 'url':
            headers_row = row
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

                # Collect headers
                matching_headers.update(headers_row)

                # Use a combination of URL and provider name to ensure uniqueness across datasets
                unique_provider_key = f"{url}_{provider_name}"
                if unique_provider_key not in processed_providers:
                    processed_providers.add(unique_provider_key)
                    provider_names.append(provider_name)  # Add provider name once

                    # Collect all columns that contain 'overall score' in the header
                    matched_overall_columns = [header for header in headers_row if header and 'overall score' in header.lower()]

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

                i += 1  # Move to next provider row
            # End of current dataset
            continue  # Go back to look for the next header row
        else:
            i += 1  # Move to next row

    if not provider_names:
        st.write("No data found for the given URL.")
    else:
        # We have collected the matching headers
        headers_list = list(matching_headers)
        # Remove 'URL' and 'VPN provider' from headers
        headers_list = [header for header in headers_list if header not in ['URL', 'VPN provider']]
        # Sort headers for better presentation
        headers_list.sort()

        # Now present the headers to the user for selection
        st.write("Select the columns you want to include in the per-provider charts:")
        selected_columns = st.multiselect("Available columns", headers_list)

        # Now, if the user has selected columns, process the data to generate the per-provider charts
        if selected_columns:
            # Reset data structures
            speed_test_data_per_provider = {}
            processed_providers = set()
            provider_names = []

            i = 0
            while i < len(consolidated_data):
                row = consolidated_data[i]
                # Check if the row is a header row starting with 'URL'
                if row and row[0] and row[0].strip().lower() == 'url':
                    headers_row = row
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

                            # Extract data for selected columns for the provider
                            provider_selected_data = []
                            selected_labels = []
                            for col in selected_columns:
                                if col in headers_row:
                                    col_index = headers_row.index(col)
                                    value = provider_row[col_index]
                                    try:
                                        value = float(value)
                                    except (ValueError, TypeError):
                                        value = 0
                                    provider_selected_data.append(value)
                                    selected_labels.append(col)
                                else:
                                    # Column not in this dataset's headers
                                    provider_selected_data.append(0)
                                    selected_labels.append(col)

                            # Store data for provider
                            speed_test_data_per_provider[provider_name] = (selected_labels, provider_selected_data)

                        i += 1  # Move to next provider row
                    # End of current dataset
                    continue  # Go back to look for the next header row
                else:
                    i += 1  # Move to next row

            # Now generate charts using speed_test_data_per_provider
            for provider_name, (labels, data_values) in speed_test_data_per_provider.items():
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
                                labels: {json.dumps(labels)},
                                datasets: [{{
                                    label: '{provider_name} Data',
                                    data: {json.dumps(data_values)},
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
                                            text: 'Value'
                                        }}
                                    }}
                                }},
                                plugins: {{
                                    title: {{
                                        display: true,
                                        text: '{provider_name} Data'
                                    }}
                                }}
                            }}
                        }});
                    }});
                </script>
                """
                chart_js_files.append((f"{provider_name}_data_chart.txt", speed_test_chart_js))

            # Generate overall score charts as before
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

            # Provide download button for the zip file
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
        else:
            st.write("Please select at least one column to generate per-provider charts.")

else:
    st.write("Please enter a URL to search for.")
