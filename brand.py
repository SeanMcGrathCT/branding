import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fuzzywuzzy import fuzz, process
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Access the service account credentials from secrets
credentials_info = st.secrets["gsheet_service_account"]

# Define the scope and load credentials from secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize client
client = gspread.authorize(creds)

# Define sheet URLs
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'

# Open the Google Sheet
try:
    sheet1 = client.open_by_url(sheet1_url)
    st.write("Successfully opened the Google Sheet.")
except Exception as e:
    st.error(f"Failed to open Google Sheet: {e}")

# Load the 'Consolidated' worksheet from Sheet 1
consolidated_sheet = sheet1.worksheet('Consolidated')
consolidated_data = consolidated_sheet.get_all_values()

# Display first few rows of consolidated data for debugging
st.write("Consolidated data (first 5 rows):", consolidated_data[:5])

# Sample headers for fuzzy matching reference
expected_headers = ['am', 'noon', 'pm', 'overall score']

# Function to fuzzy match and interpret headers dynamically
def find_best_matches(headers_row):
    normalized_headers = [header.lower() for header in headers_row]
    
    matched_headers = {}
    for expected in expected_headers:
        best_match, best_score = process.extractOne(expected, normalized_headers, scorer=fuzz.partial_ratio)
        if best_score > 70:  # Threshold for fuzzy match acceptance
            matched_headers[expected] = best_match
        else:
            logging.warning(f"No good match found for expected header: {expected}")
    
    logging.info(f"Matched headers: {matched_headers}")
    return matched_headers

# Function to extract provider data based on matched headers
def extract_provider_data(headers_row, provider_row, matched_headers):
    extracted_data = {}
    
    for key, matched_header in matched_headers.items():
        try:
            col_index = headers_row.index(matched_header)
            extracted_data[key] = provider_row[col_index]
        except ValueError as e:
            logging.error(f"Failed to find column for header '{matched_header}' in row: {headers_row}")
    
    return extracted_data

# Function to process the data for a given URL
def process_data_for_url(headers_row, provider_rows):
    matched_headers = find_best_matches(headers_row)  # Perform fuzzy matching for headers
    
    extracted_results = []
    for provider_row in provider_rows:
        if not provider_row or not provider_row[0].startswith("http"):  # Skip if no valid URL or provider
            continue
        
        logging.info(f"Processing provider: {provider_row[1]} for URL: {provider_row[0]}")
        
        # Extract provider data using the matched headers
        provider_data = extract_provider_data(headers_row, provider_row, matched_headers)
        extracted_results.append((provider_row[1], provider_data))
        logging.info(f"Extracted data: {provider_data}")
    
    return extracted_results

# Function to find the relevant row for the given URL in the consolidated data
def find_row_for_url(url, consolidated_data):
    for idx, row in enumerate(consolidated_data):
        if row[0].startswith(url):
            logging.info(f"Found data for URL at row {idx}: {row}")
            return idx, row
    return None, None

# Function to extract data for chart generation
def extract_chart_data(url):
    row_idx, headers_row = None, None
    for idx, row in enumerate(consolidated_data):
        if "url" in row[0].lower():  # Identify the header row
            headers_row = row
            provider_rows = consolidated_data[idx + 1:]
            logging.info(f"Headers for URL {url}: {headers_row}")
        elif row[0].startswith(url):
            logging.info(f"Found data for URL {url} at row {idx}")
            row_idx = idx
            break

    if row_idx is not None and headers_row is not None:
        return process_data_for_url(headers_row, consolidated_data[row_idx:row_idx + 6])
    
    return None

# Streamlit UI for VPN Speed Comparison Chart Generator
st.title("VPN Speed Comparison Chart Generator")

# User input for URL
url = st.text_input("Enter the URL to compare:")

if url:
    # Extract relevant data for the entered URL
    extracted_data = extract_chart_data(url)
    
    if extracted_data:
        # Prepare data for chart
        labels = ["UK", "US", "Australia", "Italy", "Brazil"]
        datasets = []

        for provider, data in extracted_data:
            speed_data = [data.get('am', 0), data.get('noon', 0), data.get('pm', 0)]  # Example data extraction
            datasets.append({
                "label": provider,
                "data": speed_data,
                "backgroundColor": "rgba(62, 95, 255, 0.8)",
                "borderColor": "rgba(31, 47, 127, 0.8)",
                "borderWidth": 1
            })

        # Generate chart HTML using Chart.js
        chart_html = f"""
        <div style="max-width: 805px; margin: 0 auto;">
            <canvas id="speedTestResultsChart" width="805" height="600"></canvas>
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var ctx = document.getElementById('speedTestResultsChart').getContext('2d');
            var speedTestResultsChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: {json.dumps(datasets)}
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Download Speed (Mbps)'
                            }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        """

        # Display chart in Streamlit
        st.components.v1.html(chart_html, height=600)

        # Provide download buttons for .html and .txt versions of the chart
        st.download_button("Download Chart as HTML", data=chart_html, file_name="vpn_speed_chart.html", mime="text/html")
        st.download_button("Download Chart as TXT", data=chart_html, file_name="vpn_speed_chart.txt", mime="text/plain")
    else:
        st.write("No data available for the provided URL.")
