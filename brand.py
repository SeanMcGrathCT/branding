import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fuzzywuzzy import fuzz, process
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

# Open the Google Sheet
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
try:
    sheet1 = client.open_by_url(sheet1_url)
    st.write("Successfully opened the Google Sheet.")
    logging.info("Successfully opened the Google Sheet.")
except Exception as e:
    st.error(f"Failed to open Google Sheet: {e}")
    logging.error(f"Failed to open Google Sheet: {e}")

# Load the 'Consolidated' worksheet
consolidated_sheet = sheet1.worksheet('Consolidated')
consolidated_data = consolidated_sheet.get_all_values()

# Display a snippet of the consolidated data to verify
logging.debug(f"Consolidated data (first 5 rows): {consolidated_data[:5]}")

# Function to extract relevant data for a given URL
def extract_data_from_consolidated(url, consolidated_data):
    logging.info(f"Looking for data for URL: {url}")
    
    for i, row in enumerate(consolidated_data):
        logging.debug(f"Checking row {i}: {row}")
        
        if row[0] == url:  # The URL is in the first column
            logging.info(f"Found data for URL at row {i}: {row}")
            
            # The headers are always in the next row (i + 1)
            headers_row = consolidated_data[i + 1]
            provider_data = consolidated_data[i + 2:]  # Provider data follows headers

            logging.debug(f"Headers for URL {url}: {headers_row}")
            logging.debug(f"Provider data for URL {url}: {provider_data[:3]}")  # Log the first 3 rows of provider data

            # Now we can extract relevant data, assuming 'am', 'noon', and 'pm' are in headers
            relevant_data = []
            for provider in provider_data:
                if provider[0].startswith("http"):  # If we reach the next URL, break the loop
                    logging.debug(f"Reached another URL at row {provider}. Stopping.")
                    break
                
                provider_name = provider[1]  # Assuming provider name is in column B
                try:
                    speed_data = {
                        'provider': provider_name,
                        'am': provider[headers_row.index('Speed test: UK (a.m.)')],
                        'noon': provider[headers_row.index('Speed test: UK (noon)')],
                        'pm': provider[headers_row.index('Speed test: UK (p.m.)')]
                    }
                    relevant_data.append(speed_data)
                except ValueError as ve:
                    logging.error(f"Failed to extract data for {provider_name}: {ve}")
            
            return headers_row, relevant_data
    
    logging.warning(f"No data found for URL: {url}")
    return None, None

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# User input for URL
url = st.text_input("Enter the URL to compare:")

if url:
    # Get mapping and extract relevant data from the correct tab
    logging.info(f"Processing URL: {url}")
    headers_row, chart_data = extract_data_from_consolidated(url, consolidated_data)
    
    if chart_data:
        # Example chart data using extracted data (you can modify this based on real extracted values)
        labels = ["UK", "US", "Australia", "Italy", "Brazil"]  # Modify this based on your headers if necessary
        datasets = []

        # Construct dataset for each provider
        for data in chart_data:
            datasets.append({
                "label": data['provider'],
                "data": [float(data['am']), float(data['noon']), float(data['pm'])],
                "backgroundColor": "rgba(62, 95, 255, 0.8)",
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
