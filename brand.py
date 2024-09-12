import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fuzzywuzzy import fuzz, process
import json
import logging

# Set up logging to display on the console and in Streamlit
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
st.write("Starting VPN Speed Comparison Chart Generator")

# Access the service account credentials from secrets
credentials_info = st.secrets["gsheet_service_account"]

# Define the scope and load credentials from secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize client
client = gspread.authorize(creds)

# Define sheet URLs
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
sheet2_url = 'https://docs.google.com/spreadsheets/d/1V2p0XcGSEYDJHWCL9HsNKRRvfGRvrR-7Tr4kUQVIsfk'

# Open the Google Sheets
try:
    sheet1 = client.open_by_url(sheet1_url)
    sheet2 = client.open_by_url(sheet2_url)
    st.write("Successfully opened both Google Sheets.")
    logging.info("Successfully opened both Google Sheets.")
except Exception as e:
    st.error(f"Failed to open Google Sheets: {e}")
    logging.error(f"Failed to open Google Sheets: {e}")

# Load the 'Consolidated' worksheet from Sheet 1
consolidated_sheet = sheet1.worksheet('Consolidated')
consolidated_data = consolidated_sheet.get_all_values()

# Load the 'mapping' worksheet from Sheet 2
mapping_sheet = sheet2.worksheet('mapping')
mapping_df = pd.DataFrame(mapping_sheet.get_all_records())

# Function to match headers with scraped scores using fuzzy matching
def match_headers_with_scores(cleaned_headers, scraped_score_name):
    logging.debug(f"\n=== Matching Scraped Score Name: '{scraped_score_name}' ===")
    
    # Strip ': overall score' from headers for comparison
    headers_to_match = [header.replace(": overall score", "").strip().lower() for header in cleaned_headers]
    
    # Fuzzy match with an adjustable threshold
    best_match, best_score = process.extractOne(scraped_score_name.lower(), headers_to_match, scorer=fuzz.ratio)
    
    logging.debug(f"Best fuzzy match for '{scraped_score_name}' is '{best_match}' with a score of {best_score}")
    
    if best_score >= 70:  # Set a matching threshold
        return headers_to_match.index(best_match)
    else:
        logging.debug(f"No match found for '{scraped_score_name}' with a score above 70.")
        return None

# Function to extract the necessary speed test data for generating charts
def extract_chart_data(url, consolidated_data, mapping_df):
    logging.info(f"Extracting chart data for URL: {url}")
    
    for i, row in enumerate(consolidated_data):
        if row[0].startswith("http"):  # Check if the row contains a URL
            logging.debug(f"Checking row {i} for URL match: {row[0]}")
            if row[0] == url:
                logging.info(f"Found URL match at row {i}: {row[0]}")
                
                headers_row = consolidated_data[i + 1]  # The headers are in the next row
                provider_data = consolidated_data[i + 2:]  # Provider data follows headers

                # Strip ": overall score" from headers
                cleaned_headers = [header.replace(": overall score", "").strip().lower() for header in headers_row]
                logging.debug(f"Cleaned headers for URL {url}: {cleaned_headers}")

                # Extract relevant data for this URL
                matching_providers = mapping_df[mapping_df['URL'] == url]

                if not matching_providers.empty:
                    logging.info(f"Found {len(matching_providers)} matching providers in the mapping sheet.")
                    
                    speed_test_data = []
                    for _, mapping_row in matching_providers.iterrows():
                        scraped_score_name = mapping_row['Scraped Score Name'].lower()
                        logging.debug(f"Trying to match scraped score name: {scraped_score_name}")

                        # Match headers with the current scraped score name
                        matched_header_idx = match_headers_with_scores(cleaned_headers, scraped_score_name)

                        if matched_header_idx is not None:
                            extracted_value = provider_data[0][matched_header_idx]  # Assuming first provider
                            logging.info(f"Match found! {scraped_score_name} -> {cleaned_headers[matched_header_idx]}: {extracted_value}")
                            speed_test_data.append((mapping_row['Mapped Header'], extracted_value))
                        else:
                            logging.warning(f"No match found for scraped score name: {scraped_score_name}")

                    return speed_test_data
                else:
                    logging.warning(f"No matching providers found in the mapping sheet for URL: {url}")
    logging.warning(f"No matching data found for URL: {url} in the consolidated sheet.")
    return None

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# User input for URL
url = st.text_input("Enter the URL to compare:")

if url:
    # Get mapping and extract relevant data for the chart
    logging.info(f"Processing URL: {url}")
    chart_data = extract_chart_data(url, consolidated_data, mapping_df)
    
    if chart_data:
        # Extract labels and data for the chart (you can modify this based on real extracted values)
        labels = ["UK", "US", "Australia", "Italy", "Brazil"]
        datasets = []

        # Assuming `chart_data` contains tuples of (mapped_header, extracted_value)
        for i, (label, value) in enumerate(chart_data):
            datasets.append({
                "label": label,
                "data": [float(value)],  # Example data, replace with actual extracted data
                "backgroundColor": f"rgba(62, 95, 255, 0.{8-i})",  # Dynamic color change
                "borderColor": "rgba(31, 47, 127, 0.8)",
                "borderWidth": 1
            })

        # HTML for Chart.js
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

        # Provide download buttons for .html and .txt versions
        st.download_button("Download Chart as HTML", data=chart_html, file_name="vpn_speed_chart.html", mime="text/html")
        st.download_button("Download Chart as TXT", data=chart_html, file_name="vpn_speed_chart.txt", mime="text/plain")
    else:
        st.write("No data available for the provided URL.")
        logging.warning(f"No data available for URL: {url}")
