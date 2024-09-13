import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import zipfile
import json
import logging
import uuid  # For generating unique IDs

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
    overall_score_headers = set()
    i = 0
    while i < len(consolidated_data):
        row = consolidated_data[i]
        # Check if the row is a header row starting with 'URL'
        if row and row[0] and row[0].strip().lower() == 'url':
            # Extract the article name from the previous row
            if i > 0:
                previous_row = consolidated_data[i - 1]
                if previous_row and previous_row[0].startswith('Sheet:'):
                    article_name = previous_row[0].replace('Sheet:', '').strip()
                else:
                    article_name = 'VPN Analysis'
            else:
                article_name = 'VPN Analysis'
            st.write(f"Processing data for article: {article_name}")

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

                # Collect overall score headers
                matched_overall_columns = [header for header in headers_row if header and 'overall score' in header.lower()]
                overall_score_headers.update(matched_overall_columns)

                # Use a combination of URL and provider name to ensure uniqueness across datasets
                unique_provider_key = f"{url}_{provider_name}"
                if unique_provider_key not in processed_providers:
                    processed_providers.add(unique_provider_key)
                    provider_names.append(provider_name)  # Add provider name once

                    # Initialize overall_scores_data for new columns
                    for header in matched_overall_columns:
                        if header not in overall_scores_data:
                            overall_scores_data[header] = {}

                    # Extract overall score data for the provider
                    for col in matched_overall_columns:
                        try:
                            col_index = headers_row.index(col)
                            score = provider_row[col_index]
                            if score:
                                score_value = float(score)  # Convert to float
                            else:
                                score_value = 0
                        except (ValueError, IndexError):
                            score_value = 0  # Handle errors by assigning a default value

                        overall_scores_data[col][provider_name] = score_value

                    # Store the article name associated with this provider
                    speed_test_data_per_provider[provider_name] = {'article_name': article_name}

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

        # Allow the user to select which overall scores to export
        overall_score_headers_list = list(overall_score_headers)
        overall_score_headers_list.sort()
        st.write("Select the overall scores you want to export to charts:")
        selected_overall_scores = st.multiselect("Available overall scores", overall_score_headers_list, default=overall_score_headers_list)

        # Now, if the user has selected columns or overall scores, process the data to generate the charts
        if selected_columns or selected_overall_scores:
            # Reset data structures
            processed_providers = set()
            provider_names = []

            i = 0
            while i < len(consolidated_data):
                row = consolidated_data[i]
                # Check if the row is a header row starting with 'URL'
                if row and row[0] and row[0].strip().lower() == 'url':
                    # Extract the article name from the previous row
                    if i > 0:
                        previous_row = consolidated_data[i - 1]
                        if previous_row and previous_row[0].startswith('Sheet:'):
                            article_name = previous_row[0].replace('Sheet:', '').strip()
                        else:
                            article_name = 'VPN Analysis'
                    else:
                        article_name = 'VPN Analysis'
                    st.write(f"Processing data for article: {article_name}")

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
                            if provider_name not in provider_names:
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
                            if provider_name not in speed_test_data_per_provider:
                                speed_test_data_per_provider[provider_name] = {'data': {}, 'article_name': article_name}
                            speed_test_data_per_provider[provider_name]['data'] = (selected_labels, provider_selected_data)

                            # Extract overall score data for selected overall scores
                            for col in selected_overall_scores:
                                if col in headers_row:
                                    col_index = headers_row.index(col)
                                    score = provider_row[col_index]
                                    try:
                                        score_value = float(score)
                                    except (ValueError, TypeError):
                                        score_value = 0
                                else:
                                    score_value = 0

                                if col not in overall_scores_data:
                                    overall_scores_data[col] = {}
                                overall_scores_data[col][provider_name] = score_value

                        i += 1  # Move to next provider row
                    # End of current dataset
                    continue  # Go back to look for the next header row
                else:
                    i += 1  # Move to next row

            # Generate per-provider charts
            if selected_columns:
                for provider_name, provider_info in speed_test_data_per_provider.items():
                    labels, data_values = provider_info.get('data', ([], []))
                    article_name = provider_info.get('article_name', 'VPN Analysis')

                    # Assign color based on provider name
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
                    nice_colors = [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ]
                    provider_color = vpn_colors.get(provider_name.lower(), 'rgba(75, 192, 192, 0.8)')

                    # Generate unique IDs
                    chart_id = f"{provider_name}_chart_{uuid.uuid4().hex[:6]}"

                    # Prepare datasets
                    datasets = [{
                        'label': provider_name,
                        'data': data_values,
                        'backgroundColor': [provider_color] * len(labels),
                        'borderColor': [provider_color] * len(labels),
                        'borderWidth': 1
                    }]

                    # Generate chart title
                    chart_title = f"{provider_name} Speed Tests for {article_name}"

                    # Prepare the chart JS
                    speed_test_chart_js = f"""
                    <div id="{chart_id}" style="max-width: 405px; margin: 0 auto;">
                        <canvas class="jschartgraphic" id="vpnSpeedChart_{chart_id}" width="405" height="400"></canvas>
                    </div>
                    <script>
                        document.addEventListener('DOMContentLoaded', function() {{
                            var ctx = document.getElementById('vpnSpeedChart_{chart_id}').getContext('2d');
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
                                            text: {json.dumps(chart_title)},
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
                                                    if (context.raw <= 0.05500000000000001) {{
                                                        return 'No data available';
                                                    }}
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
                    """

                    # Generate schema data
                    data_schema = {
                        "@context": "http://schema.org",
                        "@type": "Dataset",
                        "name": chart_title,
                        "description": f"This chart shows the speed test results for {provider_name} when used for {article_name}.",
                        "data": {
                            provider_name: {
                                label: f"{value} Mbps" for label, value in zip(labels, data_values)
                            }
                        }
                    }

                    speed_test_chart_js += f"""
                    <script type="application/ld+json">
                    {json.dumps(data_schema, indent=4)}
                    </script>
                    """

                    chart_js_files.append((f"{provider_name}_data_chart.txt", speed_test_chart_js))

            # Generate overall score charts
            if selected_overall_scores:
                for score_type in selected_overall_scores:
                    # Prepare data
                    datasets = []
                    labels = [score_type]
                    for provider_name in provider_names:
                        score_value = overall_scores_data.get(score_type, {}).get(provider_name, 0)
                        # Assign color based on provider name
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
                        provider_color = vpn_colors.get(provider_name.lower(), 'rgba(75, 192, 192, 0.8)')
                        datasets.append({
                            'label': provider_name,
                            'data': [score_value],
                            'backgroundColor': [provider_color],
                            'borderColor': [provider_color],
                            'borderWidth': 1
                        })

                    # Generate unique IDs
                    chart_id = f"overall_{score_type.replace(' ', '_').lower()}_{uuid.uuid4().hex[:6]}"

                    # Prepare the chart JS
                    overall_score_chart_js = f"""
                    <div id="{chart_id}" style="max-width: 805px; margin: 0 auto;">
                        <canvas class="jschartgraphic" id="vpnSpeedChart_{chart_id}" width="805" height="600"></canvas>
                    </div>
                    <script>
                        document.addEventListener('DOMContentLoaded', function() {{
                            var ctx = document.getElementById('vpnSpeedChart_{chart_id}').getContext('2d');
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
                                            text: {json.dumps(score_type)},
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
                                                    if (context.raw <= 0.05500000000000001) {{
                                                        return 'No data available';
                                                    }}
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
                    """

                    # Generate schema data
                    data_schema = {
                        "@context": "http://schema.org",
                        "@type": "Dataset",
                        "name": score_type,
                        "description": f"Chart showing the {score_type} for each VPN provider tested.",
                        "data": {
                            provider_name: {
                                labels[0]: f"{overall_scores_data.get(score_type, {}).get(provider_name, 0)} Score out of 10"
                            } for provider_name in provider_names
                        }
                    }

                    overall_score_chart_js += f"""
                    <script type="application/ld+json">
                    {json.dumps(data_schema, indent=4)}
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
            st.write("Please select at least one column or overall score to generate charts.")

else:
    st.write("Please enter a URL to search for.")
